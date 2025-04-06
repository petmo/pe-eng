"""
API routes for violation detection.
"""

from fastapi import APIRouter, HTTPException, Depends
from api.models.violations import ViolationRequest, ViolationResponse
from api.dependencies import get_optimization_engine
from core.optimization import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/violations",
    tags=["violations"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ViolationResponse)
async def check_violations(
    request: ViolationRequest,
    engine: OptimizationEngine = Depends(get_optimization_engine),
):
    """
    Check violations for the given products.
    """
    try:
        logger.info(f"Checking violations for {len(request.product_ids)} products")

        result = engine.detect_violations(request.product_ids)

        if request.constraint_types:
            result["constraint_types_filter"] = request.constraint_types

        return result
    except Exception as e:
        logger.error(f"Error in check_violations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
