"""
API routes for price optimization.
"""

from fastapi import APIRouter, HTTPException
from api.models.optimization import OptimizationRequest, OptimizationResponse
from core.optimization import OptimizationEngine
from utils.logging import setup_logger
from data.factory import get_data_loader
from utils.parameters import normalize_empty_collection

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/", response_model=OptimizationResponse)
async def optimize_prices(request: OptimizationRequest):
    """
    Optimize prices for the given products.
    """
    try:
        # Normalize kpi_weights parameter at API boundary
        normalized_kpi_weights = normalize_empty_collection(request.kpi_weights)

        logger.info(
            f"Running optimization in '{request.mode}' mode for {len(request.product_ids)} products "
            f"with KPI weights: {normalized_kpi_weights or 'DEFAULT'}"
        )

        # Create optimization engine
        loader = get_data_loader()
        data = loader.get_product_group_data(request.product_ids)
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Pass normalized parameters to core component
        result = engine.run_optimization(
            scope_product_ids=request.product_ids,
            mode=request.mode,
            kpi_weights=normalized_kpi_weights,  # Already normalized
        )

        return result
    except Exception as e:
        logger.error(f"Error in optimize_prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
