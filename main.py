"""
Main application entry point for the pricing engine API.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
import uvicorn

from api.routes import violations_router, optimization_router
from utils.logging import setup_logger
from config.config import config

# Set up logger
logger = setup_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application.
    """
    # Create FastAPI app
    app = FastAPI(
        title="Pricing Engine API",
        description="API for pricing optimization and violation detection",
        version="1.0.0",
        # Set docs URLs based on configuration
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins by default
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add routers
    app.include_router(violations_router, prefix="/api", tags=["violations"])
    app.include_router(optimization_router, prefix="/api", tags=["optimization"])

    # Add middleware for request timing
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add processing time to response headers."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Custom exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors and return a clean JSON response."""
        errors = []
        for error in exc.errors():
            error_loc = " -> ".join([str(loc) for loc in error["loc"] if loc != "body"])
            errors.append(f"{error_loc}: {error['msg']}")

        return JSONResponse(
            status_code=422,
            content={"success": False, "error": "Validation error", "detail": errors},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions and return a clean JSON response."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc),
            },
        )

    # Health check endpoint
    @app.get("/ping", tags=["health"])
    async def health_check():
        """Health check endpoint to verify API is running."""
        return {"success": True, "message": "Pricing Engine API is running"}

    # Root endpoint redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root endpoint to docs."""
        return RedirectResponse(url="/docs")

    return app


def main():
    """
    Main entry point for the CLI application.
    This is separate from the API server functionality.
    """
    import argparse
    from data.factory import get_data_loader
    from core.optimization import OptimizationEngine
    import json

    parser = argparse.ArgumentParser(description="Pricing Engine CLI")

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Violation detection command
    detect_parser = subparsers.add_parser("detect", help="Detect constraint violations")
    detect_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to check"
    )
    detect_parser.add_argument(
        "--constraint-types", "-c", nargs="+", help="Constraint types to check"
    )
    detect_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # Hygiene optimization command
    hygiene_parser = subparsers.add_parser(
        "hygiene", help="Run hygiene optimization to fix violations"
    )
    hygiene_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    hygiene_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # KPI optimization command
    optimize_parser = subparsers.add_parser("optimize", help="Run KPI optimization")
    optimize_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    optimize_parser.add_argument(
        "--kpi-weights",
        "-k",
        type=json.loads,
        help='KPI weights as JSON string, e.g. \'{"profit": 0.7, "revenue": 0.3}\'',
    )
    optimize_parser.add_argument(
        "--output", "-o", help="Output file for results (JSON)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load data from configured source
    loader = get_data_loader()
    data = loader.get_product_group_data(args.product_ids)

    # Check if products exist
    if data["products"].empty:
        logger.error("No products found")
        return

    # Create optimization engine
    engine = OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )

    # Run command
    if args.command == "detect":
        result = engine.detect_violations(args.product_ids)

        # Print results
        if result["violations"]:
            logger.info(f"Found {len(result['violations'])} violations")
            for violation in result["violations"]:
                logger.warning(f"Violation: {violation}")
        else:
            logger.info("No violations found")

    elif args.command == "hygiene":
        result = engine.run_hygiene_optimization(args.product_ids)

        # Print results
        if result["success"]:
            logger.info("Hygiene optimization successful")

            if result["optimized_prices"]:
                logger.info("Optimized prices:")
                for price in result["optimized_prices"]:
                    if (
                        abs(price["price_change_pct"]) > 0.01
                    ):  # Only show prices that changed
                        logger.info(
                            f"Product {price['product_id']}: {price['current_price']} -> {price['optimized_price_on_ladder']} ({price['price_change_pct']:.2f}%)"
                        )
            else:
                logger.info("No price changes needed")

            if result["violations"]:
                logger.warning(
                    f"Found {len(result['violations'])} remaining violations after optimization"
                )
        else:
            logger.error(f"Hygiene optimization failed: {result.get('error')}")

    elif args.command == "optimize":
        kpi_weights = args.kpi_weights if args.kpi_weights else {"profit": 1.0}
        result = engine.run_kpi_optimization(args.product_ids, kpi_weights)

        # Print results
        if result["success"]:
            logger.info("KPI optimization successful")
            logger.info(f"KPI weights used: {result['kpi_weights']}")

            if result["optimized_prices"]:
                logger.info("Optimized prices:")
                for price in result["optimized_prices"]:
                    logger.info(
                        f"Product {price['product_id']}: {price['current_price']} -> {price['optimized_price_on_ladder']} ({price['price_change_pct']:.2f}%)"
                    )

            if "kpi_impacts" in result:
                logger.info("Estimated KPI impacts:")
                for kpi, impact in result["kpi_impacts"].items():
                    logger.info(f"  {kpi}: {impact}")

            if result["violations"]:
                logger.warning(
                    f"Found {len(result['violations'])} violations with optimized prices"
                )
        else:
            logger.error(f"KPI optimization failed: {result.get('error')}")

    # Save results to file if output specified
    if args.output and "result" in locals():
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    # This block is for running the API server directly from this file
    app = create_app()

    # Get API configuration
    api_config = config.get_api_config()

    logger.info(
        f"Starting Pricing Engine API on http://{api_config['host']}:{api_config['port']}"
    )
    uvicorn.run(
        app,
        host=api_config["host"],
        port=api_config["port"],
        log_level=config.get("logging.level", "info").lower(),
    )
