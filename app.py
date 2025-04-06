"""
Application factory and configuration for the pricing engine.

This module provides the application factory pattern for creating the FastAPI app
and contains core configuration functionality.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
import time
import uvicorn
from typing import Optional, Dict, Any

from api.routes import violations_router, optimization_router
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


if __name__ == "__main__":
    # This block allows running the app directly with `python app.py`
    start_server()
