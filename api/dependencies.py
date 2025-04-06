"""
Dependency injection for the API.
"""

from fastapi import Depends
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)


def get_data_provider():
    """
    Dependency provider for data loader.

    Returns:
        Object: Data loader instance.
    """
    return get_data_loader()


def get_optimization_engine(data_provider=Depends(get_data_provider)):
    """
    Dependency provider for optimization engine.

    Args:
        data_provider: Data loader instance.

    Returns:
        OptimizationEngine: Optimization engine instance.
    """
    # Load sample data to initialize the engine
    # In a real implementation, this might be cached or handled differently
    data = data_provider.get_product_group_data([])

    return OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )
