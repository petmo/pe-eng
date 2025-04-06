"""
Dependency injection for the API.
"""

from fastapi import Depends
from api.models.violations import ViolationRequest, GroupViolationRequest
from api.models.optimization import OptimizationRequest
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger
from typing import Union, List

logger = setup_logger(__name__)


async def get_optimization_engine(
    request: Union[
        ViolationRequest, OptimizationRequest, GroupViolationRequest, None
    ] = None,
):
    """
    Dependency provider for optimization engine that creates an engine specifically for the request.

    Args:
        request: The API request containing product_ids or group_ids

    Returns:
        OptimizationEngine: Optimization engine instance with relevant data
    """
    # Initialize data loader
    loader = get_data_loader()

    # Extract product IDs from the request if available
    product_ids = []

    if request:
        if hasattr(request, "product_ids") and request.product_ids:
            # Direct product IDs from ViolationRequest or OptimizationRequest
            product_ids = request.product_ids
        elif hasattr(request, "group_ids") and request.group_ids:
            # Get products from group IDs (GroupViolationRequest)
            group_ids = request.group_ids

            # Get item groups
            df_item_groups = loader.get_item_groups()
            df_item_group_members = loader.get_item_group_members()

            # Filter to the specified groups
            df_members = df_item_group_members[
                df_item_group_members["group_id"].isin(group_ids)
            ]

            if not df_members.empty:
                product_ids = df_members["product_id"].unique().tolist()

    # Load only the data needed for these product IDs
    logger.info(
        f"Loading data for {len(product_ids)} products to create optimization engine"
    )
    data = loader.get_product_group_data(product_ids)

    # Create and return the optimization engine with just the necessary data
    return OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )
