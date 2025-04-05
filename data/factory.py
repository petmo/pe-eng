"""
Factory for creating the appropriate data loader based on configuration.
"""

from typing import Any
from config.config import config
from utils.logging import setup_logger
from data.loader import SupabaseLoader
from data.local_loader import LocalCSVLoader

logger = setup_logger(__name__)


def get_data_loader() -> Any:
    """
    Get the appropriate data loader based on configuration.

    Returns:
        The data loader instance (SupabaseLoader or LocalCSVLoader).
    """
    use_local = config.get("data_source.use_local", False)

    if use_local:
        logger.info("Using local CSV data loader")
        return LocalCSVLoader()
    else:
        logger.info("Using Supabase data loader")
        return SupabaseLoader()
