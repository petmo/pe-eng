"""
API routers for the Pricing Engine.
"""

from fastapi import APIRouter
from api.routers.violations import router as violations_router
from api.routers.optimization import router as optimization_router

# Create a combined router
combined_router = APIRouter()
combined_router.include_router(violations_router, prefix="/violations")
combined_router.include_router(optimization_router, prefix="/optimization")

# Export the routers
__all__ = ["violations_router", "optimization_router", "combined_router"]
