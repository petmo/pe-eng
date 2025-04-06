"""
API routes for price optimization.
"""

from fastapi import APIRouter, HTTPException, Depends
from api.models.optimization import OptimizationRequest, OptimizationResponse
from api.dependencies import get_optimization_engine
from core.optimization import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/optimization",
    tags=["optimization"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=OptimizationResponse)
async def optimize_prices(
    request: OptimizationRequest,
    engine: OptimizationEngine = Depends(get_optimization_engine),
):
    """
    Optimize prices for the given products.
    """
    try:
        logger.info(
            f"Running optimization in '{request.mode}' mode for {len(request.product_ids)} products"
        )

        result = engine.run_optimization(
            scope_product_ids=request.product_ids,
            mode=request.mode,
            kpi_weights=request.kpi_weights,
        )

        return result
    except Exception as e:
        logger.error(f"Error in optimize_prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
