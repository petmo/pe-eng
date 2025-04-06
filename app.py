"""
Application factory and configuration for the pricing engine.

This module provides the application factory pattern for creating the FastAPI app
and contains core configuration functionality.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError, HTTPException
import time
import uvicorn
from typing import Optional, Dict, Any

from api.models import ViolationRequest, ViolationResponse
from api.routes import violations_router, optimization_router
from core import OptimizationEngine
from data import get_data_loader
from utils.logging import setup_logger
from config.config import config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

    # Add middleware for API key validation
    @app.middleware("http")
    async def validate_api_key(request: Request, call_next):
        """Validate API key for protected routes."""
        # Skip auth for certain paths
        public_paths = ["/docs", "/redoc", "/openapi.json", "/ping", "/"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Get the API key from the request header
        api_key = request.headers.get("X-API-Key")
        expected_api_key = config.get("api.key", "default_api_key")  # Get from config

        # Log information for debugging
        logger.debug(f"Validating API key for path: {request.url.path}")
        logger.debug(f"Received API key: {'[PRESENT]' if api_key else '[MISSING]'}")

        if not api_key or api_key != expected_api_key:
            logger.warning(f"Invalid API key used to access: {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Invalid or missing API key"},
            )

        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests."""
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else "unknown"

        logger.info(f"Request: {method} {path} from {client_host}")

        # Log headers (excluding sensitive ones)
        headers_log = {}
        for k, v in request.headers.items():
            if k.lower() not in ("authorization", "x-api-key"):
                headers_log[k] = v
            else:
                headers_log[k] = "[REDACTED]"

        logger.debug(f"Request headers: {headers_log}")

        try:
            # Attempt to log request body for debugging
            if method in ["POST", "PUT", "PATCH"]:
                # Create a copy of the request to avoid consuming the stream
                body_bytes = await request.body()

                # Try to parse as JSON for better logging
                try:
                    import json

                    body_str = body_bytes.decode()
                    if body_str:
                        body_json = json.loads(body_str)
                        logger.debug(f"Request body: {body_json}")
                except:
                    if len(body_bytes) > 1000:
                        logger.debug(
                            f"Request body: [binary data, {len(body_bytes)} bytes]"
                        )
                    else:
                        logger.debug(f"Request body: {body_bytes}")

                # Create a new request with the same body to pass to the next middleware
                request = Request(
                    scope=request.scope,
                    receive=receive_with_body(body_bytes),
                )
        except Exception as e:
            logger.debug(f"Could not log request body: {e}")

        # Process the request
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            status_code = response.status_code

            # Log the response
            logger.info(
                f"Response: {status_code} for {method} {path} - took {process_time:.4f}s"
            )

            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error during {method} {path}: {e} - took {process_time:.4f}s"
            )
            raise

    # Helper function for request body logging
    def receive_with_body(body: bytes):
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    # Direct route for /api/check-violations endpoint
    @app.post(
        "/api/check-violations", tags=["violations"], response_model=ViolationResponse
    )
    async def check_violations_direct(request: ViolationRequest):
        """
        Direct endpoint for check-violations to match the expected URL path from Supabase.
        """
        logger.info(
            f"Direct check_violations endpoint called with {len(request.product_ids)} products"
        )

        # Load data from configured source
        loader = get_data_loader()
        data = loader.get_product_group_data(request.product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning(f"No products found for IDs: {request.product_ids}")
            raise HTTPException(status_code=404, detail="No products found")

        # Create optimization engine
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run violation detection
        result = engine.detect_violations(request.product_ids)

        # Add constraint types filter info if provided
        if request.constraint_types:
            result["constraint_types_filter"] = request.constraint_types

        return result

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


def start_server(host: Optional[str] = None, port: Optional[int] = None):
    """
    Start the FastAPI server with uvicorn.

    Args:
        host: Host to bind to. If None, uses the value from config.
        port: Port to bind to. If None, uses the value from config.
    """
    # Create the FastAPI app
    app = create_app()

    # Get API configuration from config
    api_config = config.get_api_config()

    # Use provided host/port or fall back to config
    host = host or api_config["host"]
    port = port or api_config["port"]

    logger.info(f"Starting Pricing Engine API server on {host}:{port}")
    uvicorn.run(
        app, host=host, port=port, log_level=config.get("logging.level", "info").lower()
    )


# For functional FastAPI-integration in pycyarm
app = create_app()


if __name__ == "__main__":
    # This block allows running the app directly with `python app.py`
    start_server()
