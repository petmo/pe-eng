from fastapi import APIRouter, HTTPException, Request
from api.models.violations import (
    ViolationRequest,
    ViolationResponse,
    GroupViolationRequest,
)
from data import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/check-violations", response_model=ViolationResponse)
async def check_violations(
    request: Request, violation_request: ViolationRequest
) -> ViolationResponse:
    """
    Check constraint violations for the specified product_ids (and optional constraint types).
    Now we initialize the OptimizationEngine directly inside the endpoint.
    """
    try:
        # 1. Load data
        loader = get_data_loader()

        # If you want ALL products:
        df_products = loader.get_products()
        df_item_groups = loader.get_item_groups()
        df_item_group_members = loader.get_item_group_members()

        # 2. Initialize the engine
        engine = OptimizationEngine(
            df_products=df_products,
            df_item_groups=df_item_groups,
            df_item_group_members=df_item_group_members,
        )

        # 3. Detect violations for these product_ids
        result = engine.detect_violations(
            scope_product_ids=violation_request.product_ids,
            constraint_types=violation_request.constraint_types,
        )

        return ViolationResponse(**result)

    except Exception as e:
        logger.error(f"Error in check_violations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-violations-by-group", response_model=ViolationResponse)
async def check_violations_by_group(
    request: Request, group_request: GroupViolationRequest
) -> ViolationResponse:
    """
    Check constraint violations for all products in one or more specified groups,
    optionally filtered by constraint_types.

    Now we initialize the OptimizationEngine inside the endpoint (no FastAPI Depends).
    """
    try:
        # 1. Load all or partial data
        loader = get_data_loader()
        df_item_groups = loader.get_item_groups()
        df_item_group_members = loader.get_item_group_members()
        df_products = loader.get_products()  # or load partial if you want

        # 2. Figure out which products are in the requested groups
        group_ids = group_request.group_ids  # e.g. ["GROUP1","GROUP2"]
        df_valid_groups = df_item_groups[df_item_groups["group_id"].isin(group_ids)]
        if df_valid_groups.empty:
            raise HTTPException(status_code=404, detail="No valid groups found")

        df_members = df_item_group_members[
            df_item_group_members["group_id"].isin(group_ids)
        ]
        if df_members.empty:
            raise HTTPException(
                status_code=404, detail="No products found in the specified group(s)"
            )

        product_ids = df_members["product_id"].unique().tolist()
        if not product_ids:
            raise HTTPException(
                status_code=404, detail="No products found in these groups"
            )

        # 3. Initialize the engine
        engine = OptimizationEngine(df_products, df_item_groups, df_item_group_members)

        # 4. Detect violations for just those product IDs
        result = engine.detect_violations(
            scope_product_ids=product_ids,
            constraint_types=group_request.constraint_types,
        )

        return ViolationResponse(**result)

    except Exception as e:
        logger.error(f"Error in check_violations_by_group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
