"""
Base data loader interface for the pricing engine.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any, Optional


class DataLoader(ABC):
    """
    Abstract base class for data loaders.
    """

    @abstractmethod
    def get_products(self, product_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch products.

        Args:
            product_ids: Optional list of product IDs to fetch. If None, fetches all products.

        Returns:
            pd.DataFrame: DataFrame containing product data.
        """
        pass

    @abstractmethod
    def get_item_groups(self) -> pd.DataFrame:
        """
        Fetch item groups.

        Returns:
            pd.DataFrame: DataFrame containing item group data.
        """
        pass

    @abstractmethod
    def get_item_group_members(
        self, group_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Fetch item group members.

        Args:
            group_ids: Optional list of group IDs to fetch members for. If None, fetches all members.

        Returns:
            pd.DataFrame: DataFrame containing item group member data.
        """
        pass

    @abstractmethod
    def get_price_ladder(self) -> List[float]:
        """
        Fetch price ladder.

        Returns:
            List[float]: List of valid prices on the price ladder.
        """
        pass

    @abstractmethod
    def get_product_group_data(self, product_ids: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch all data needed for pricing optimization.

        Args:
            product_ids: List of product IDs to optimize.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary containing DataFrames for products, item groups, and members.
        """
        pass


from data.local_loader import LocalCSVLoader
from data.supabase_loader import SupabaseLoader

__all__ = ["DataLoader", "LocalCSVLoader", "SupabaseLoader"]
