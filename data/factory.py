"""
Factory for creating the appropriate data loader based on configuration.
"""

from typing import Any
from config.config import config
from utils.logging import setup_logger
from data.loader import DataLoader, LocalCSVLoader, SupabaseLoader

logger = setup_logger(__name__)


def get_data_loader() -> DataLoader:
    """
    Get the appropriate data loader based on configuration.

    Returns:
        DataLoader: The data loader instance (SupabaseLoader or LocalCSVLoader).
    """
    # Get data source configuration from config
    data_source_config = config.get_data_source_config()
    use_local = data_source_config["use_local"]

    if use_local:
        logger.info("Using local CSV data loader")
        return LocalCSVLoader()
    else:
        # Check if Supabase credentials are configured
        supabase_config = config.get_supabase_config()

        if not supabase_config:
            logger.warning(
                "Supabase credentials not configured, falling back to local CSV data loader"
            )
            return LocalCSVLoader()

        logger.info("Using Supabase data loader")
        return SupabaseLoader()
