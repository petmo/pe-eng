"""
Main FastAPI application for the pricing engine API.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import colorlog

# Load environment variables
load_dotenv()

# Configure logging with color
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)

logger = logging.getLogger("pricing_engine")
logger.addHandler(handler)
logger.setLevel(
    logging.DEBUG
    if os.environ.get("DEBUG", "false").lower() == "true"
    else logging.INFO
)

# Create FastAPI app
app = FastAPI(
    title="Pricing Engine API",
    description="API for price optimization and constraint validation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API key authentication
API_KEY = os.environ.get("API_KEY", "dev_api_key_123")


# API models
class ViolationCheckRequest(BaseModel):
    """Request model for checking pricing constraint violations."""

    product_ids: List[str] = Field(
        ..., description="List of product IDs to check for violations"
    )
    constraint_types: Optional[List[str]] = Field(
        default=[], description="Optional list of constraint types to check"
    )


class OptimizationRequest(BaseModel):
    """Request model for price optimization."""

    product_ids: List[str] = Field(..., description="List of product IDs to optimize")
    mode: str = Field(
        default="violation_detection",
        description="Optimization mode: 'violation_detection', 'hygiene_optimization', or 'kpi_optimization'",
    )
    kpi_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="KPI weights for optimization (only used in kpi_optimization mode)",
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = Field(default=False)
    error: str
    message: Optional[str] = None


# Authentication dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify the API key header."""
    if not x_api_key or x_api_key != API_KEY:
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API-Key"},
        )
    return x_api_key


# Exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and return a consistent JSON response."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc),
        },
    )


@app.get("/ping", summary="Health check endpoint")
async def ping():
    """Test endpoint to check if server is running."""
    logger.info("Health check requested")
    return {"success": True, "message": "Pricing Engine API is running"}


@app.post(
    "/api/check-violations",
    summary="Check price constraint violations",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Successful operation"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def check_violations(
    request: ViolationCheckRequest, api_key: str = Depends(verify_api_key)
):
    """
    Check for price constraint violations on the specified products.

    This endpoint analyzes products for any pricing relationship violations
    without suggesting price changes.
    """
    logger.info(
        f"Received violation check request for {len(request.product_ids)} products"
    )
    logger.debug(f"Products: {request.product_ids}")

    try:
        # Import data loader
        from data.factory import get_data_loader

        # Get data loader (local or Supabase)
        loader = get_data_loader()
        data = loader.get_product_group_data(request.product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning("No products found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "No products found"},
            )

        # Import and initialize optimization engine
        from optimization.engine import OptimizationEngine

        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run violation detection
        result = engine.detect_violations(request.product_ids)
        logger.info(
            f"Violation detection completed with {len(result.get('violations', []))} violations"
        )

        return result

    except Exception as e:
        logger.error(f"Error in check_violations: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Server error processing request",
                "message": str(e),
            },
        )


@app.post(
    "/api/optimize-prices",
    summary="Optimize product prices",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Successful operation"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def optimize_prices(
    request: OptimizationRequest, api_key: str = Depends(verify_api_key)
):
    """
    Optimize prices for the specified products.

    This endpoint supports three modes:
    - violation_detection: Only identifies constraint violations
    - hygiene_optimization: Recommends minimal price changes to comply with constraints
    - kpi_optimization: Optimizes KPIs (profit, revenue) while respecting constraints
    """
    logger.info(
        f"Received price optimization request with mode '{request.mode}' for {len(request.product_ids)} products"
    )

    # Validate the mode
    valid_modes = ["violation_detection", "hygiene_optimization", "kpi_optimization"]
    if request.mode not in valid_modes:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Invalid mode: {request.mode}. Valid modes are: {', '.join(valid_modes)}",
            },
        )

    try:
        # Import data loader
        from data.factory import get_data_loader

        # Get data loader (local or Supabase)
        loader = get_data_loader()
        data = loader.get_product_group_data(request.product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning("No products found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "No products found"},
            )

        # Import and initialize optimization engine
        from optimization.engine import OptimizationEngine

        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run optimization with specified mode
        result = engine.run_optimization(
            scope_product_ids=request.product_ids,
            mode=request.mode,
            kpi_weights=request.kpi_weights,
        )

        logger.info(f"Optimization completed successfully in mode: {request.mode}")
        return result

    except Exception as e:
        logger.error(f"Error in optimize_prices: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Server error processing request",
                "message": str(e),
            },
        )


# Catch-all route for debugging
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path: str):
    """Catch-all route for unhandled paths - provides debugging info."""
    logger.warning(f"Unhandled route accessed: {request.method} {request.url.path}")

    try:
        body = await request.json()
        logger.debug(f"Request body: {body}")
    except:
        pass

    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": f"Route not found: {request.method} {request.url.path}",
            "available_routes": [
                "GET /ping",
                "POST /api/check-violations",
                "POST /api/optimize-prices",
            ],
        },
    )


if __name__ == "__main__":
    # When run directly, start the server
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")
    logger.info(
        f"API key configured: {API_KEY[:3]}..." if API_KEY else "No API key configured!"
    )
    logger.info("Documentation available at: http://localhost:8000/docs")

    uvicorn.run(app, host=host, port=port)
