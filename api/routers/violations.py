"""
API routes for violation detection.
"""

from fastapi import APIRouter, HTTPException
from api.models.violations import (
    ViolationRequest,
    ViolationResponse,
    GroupViolationRequest,
)
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger
from utils.parameters import normalize_empty_collection

logger = setup_logger(__name__)

router = APIRouter()  # No prefix here! Prefix is added in __init__.py


@router.post("/check-by-group", response_model=ViolationResponse)
async def check_violations_by_group(request: GroupViolationRequest):
    """
    Check constraint violations for all products in one or more specified groups,
    optionally filtered by constraint_types.
    """
    try:
        # Normalize constraint_types parameter at API boundary
        normalized_constraint_types = normalize_empty_collection(
            request.constraint_types
        )

        logger.info(
            f"Checking violations for {len(request.group_ids)} groups with "
            f"constraint types: {normalized_constraint_types or 'ALL'}"
        )

        # Create optimization engine
        loader = get_data_loader()
        df_item_groups = loader.get_item_groups()
        df_item_group_members = loader.get_item_group_members()

        # Get group members
        df_members = df_item_group_members[
            df_item_group_members["group_id"].isin(request.group_ids)
        ]

        if df_members.empty:
            logger.warning(f"No products found in groups: {request.group_ids}")
            raise HTTPException(
                status_code=404, detail="No products found in the specified group(s)"
            )

        # Get product IDs in these groups
        product_ids = df_members["product_id"].unique().tolist()
        logger.info(f"Found {len(product_ids)} products in the specified groups")

        # Get complete data
        data = loader.get_product_group_data(product_ids)
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Pass normalized parameters to core component
        result = engine.detect_violations(
            scope_product_ids=product_ids,
            constraint_types=normalized_constraint_types,  # Already normalized
        )

        logger.info(f"Detected {len(result.get('violations', []))} violations")
        return ViolationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_violations_by_group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
