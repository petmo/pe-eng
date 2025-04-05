"""
Data loader for fetching data from Supabase.
"""
import pandas as pd
from typing import List, Dict, Any, Optional
import json
from supabase import create_client
from config.config import config
from utils.logging import setup_logger

logger = setup_logger(__name__)


class SupabaseLoader:
    """
    Loader class for fetching data from Supabase.
    """

    def __init__(self):
        """
        Initialize the Supabase client.
        """
        self.client = create_client(config.get("supabase.url"), config.get("supabase.key"))

    def get_products(self, product_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch products from Supabase.

        Args:
            product_ids: Optional list of product IDs to fetch. If None, fetches all products.

        Returns:
            pd.DataFrame: DataFrame containing product data.
        """
        query = self.client.table(config.get("supabase.tables.products")).select("*")

        if product_ids:
            query = query.in_("product_id", product_ids)

        response = query.execute()

        if response.data:
            df_products = pd.DataFrame(response.data)
            logger.info(f"Fetched {len(df_products)} products")

            # Parse JSON attributes if they're stored as strings
            if 'attributes' in df_products.columns:
                df_products['attributes'] = df_products['attributes'].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )

            return df_products
        else:
            logger.warning("No products found")
            return pd.DataFrame()

    def get_item_groups(self) -> pd.DataFrame:
        """
        Fetch item groups from Supabase.

        Returns:
            pd.DataFrame: DataFrame containing item group data.
        """
        response = self.client.table(config.get("supabase.tables.item_groups")).select("*").execute()

        if response.data:
            df_item_groups = pd.DataFrame(response.data)
            logger.info(f"Fetched {len(df_item_groups)} item groups")
            return df_item_groups
        else:
            logger.warning("No item groups found")
            return pd.DataFrame()

    def get_item_group_members(self, group_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch item group members from Supabase.

        Args:
            group_ids: Optional list of group IDs to fetch members for. If None, fetches all members.

        Returns:
            pd.DataFrame: DataFrame containing item group member data.
        """
        query = self.client.table(config.get("supabase.tables.item_group_members")).select("*")

        if group_ids:
            query = query.in_("group_id", group_ids)

        response = query.execute()

        if response.data:
            df_item_group_members = pd.DataFrame(response.data)
            logger.info(f"Fetched {len(df_item_group_members)} item group members")
            return df_item_group_members
        else:
            logger.warning("No item group members found")
            return pd.DataFrame()

    def get_product_group_data(self, product_ids: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch all data needed for pricing optimization.

        Args:
            product_ids: List of product IDs to optimize.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary containing DataFrames for products, item groups, and members.
        """
        # Get products
        df_products = self.get_products(product_ids)

        if df_products.empty:
            return {
                "products": pd.DataFrame(),
                "item_groups": pd.DataFrame(),
                "item_group_members": pd.DataFrame()
            }

        # Get item groups and members
        df_item_groups = self.get_item_groups()

        if df_item_groups.empty:
            return {
                "products": df_products,
                "item_groups": pd.DataFrame(),
                "item_group_members": pd.DataFrame()
            }

        # Get item group members that include our products
        df_item_group_members = self.get_item_group_members()

        if df_item_group_members.empty:
            return {
                "products": df_products,
                "item_groups": df_item_groups,
                "item_group_members": pd.DataFrame()
            }

        # Filter to include only members that involve our product_ids
        relevant_groups = df_item_group_members[
            df_item_group_members["product_id"].isin(product_ids)
        ]["group_id"].unique()

        # Get all members of these groups (including those outside our scope)
        df_all_group_members = df_item_group_members[
            df_item_group_members["group_id"].isin(relevant_groups)
        ]

        # Get additional products that are in the same groups but not in our initial scope
        additional_product_ids = df_all_group_members[
            ~df_all_group_members["product_id"].isin(product_ids)
        ]["product_id"].unique().tolist()

        # Fetch these additional products
        if additional_product_ids:
            df_additional_products = self.get_products(additional_product_ids)
            df_products = pd.concat([df_products, df_additional_products], ignore_index=True)

        return {
            "products": df_products,
            "item_groups": df_item_groups[df_item_groups["group_id"].isin(relevant_groups)],
            "item_group_members": df_all_group_members
        }