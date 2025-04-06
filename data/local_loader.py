"""
Local CSV data loader for the pricing engine.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from config.config import config
from utils.logging import setup_logger
from data.loader import DataLoader
from data.local.file_system import FileSystem
from utils.parameters import ensure_numeric_columns

logger = setup_logger(__name__)


class LocalCSVLoader(DataLoader):
    """
    Loader class for fetching data from local CSV files.
    """

    def __init__(self):
        """
        Initialize the local CSV loader.
        """
        self.file_system = FileSystem()

        # File paths
        self.products_path = self.file_system.get_file_path("products")
        self.item_groups_path = self.file_system.get_file_path("item_groups")
        self.item_group_members_path = self.file_system.get_file_path(
            "item_group_members"
        )
        self.price_ladder_path = self.file_system.get_file_path("price_ladder")

        # Check if files exist
        for path, name in [
            (self.products_path, "products"),
            (self.item_groups_path, "item_groups"),
            (self.item_group_members_path, "item_group_members"),
            (self.price_ladder_path, "price_ladder"),
        ]:
            if not path.exists():
                logger.warning(f"Local data file '{name}.csv' not found at '{path}'")

    def get_products(self, product_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch products from local CSV.

        Args:
            product_ids: Optional list of product IDs to fetch. If None, fetches all products.

        Returns:
            pd.DataFrame: DataFrame containing product data.
        """
        try:
            # Use more robust CSV parsing options
            df_products = pd.read_csv(
                self.products_path,
                quotechar='"',
                escapechar="\\",
                skipinitialspace=True,
                na_values=["", "NA", "N/A", "null"],
                keep_default_na=True,
            )
            logger.info(f"Loaded {len(df_products)} products from CSV")

            # Ensure price and unit_price are numeric
            df_products = ensure_numeric_columns(df_products, ["price", "unit_price"])

            # Ensure column names are exactly as expected
            column_mapping = {}

            # Check for case-insensitive matches and create a mapping
            for expected_col in [
                "product_id",
                "price",
                "unit_price",
                "categories",
                "attributes",
            ]:
                for actual_col in df_products.columns:
                    if (
                        expected_col.lower() == actual_col.lower()
                        and expected_col != actual_col
                    ):
                        column_mapping[actual_col] = expected_col
                        break

            # Rename columns if needed
            if column_mapping:
                logger.info(f"Renaming products columns: {column_mapping}")
                df_products = df_products.rename(columns=column_mapping)

            # Parse JSON attributes
            if "attributes" in df_products.columns:
                df_products["attributes"] = df_products["attributes"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )

            # Parse categories as list
            if "categories" in df_products.columns:
                df_products["categories"] = df_products["categories"].apply(
                    lambda x: x.split(",") if isinstance(x, str) else x
                )

            # Filter by product_ids if provided
            if product_ids and "product_id" in df_products.columns:
                df_products = df_products[df_products["product_id"].isin(product_ids)]
                logger.info(f"Filtered to {len(df_products)} products")

            return df_products

        except Exception as e:
            logger.error(f"Error loading products from CSV: {e}", exc_info=True)
            return pd.DataFrame()

    def get_item_groups(self) -> pd.DataFrame:
        """
        Fetch item groups from local CSV.

        Returns:
            pd.DataFrame: DataFrame containing item group data.
        """
        try:
            # Use more robust CSV parsing options
            df_item_groups = pd.read_csv(
                self.item_groups_path,
                quotechar='"',
                escapechar="\\",
                skipinitialspace=True,
                na_values=["", "NA", "N/A", "null"],
                keep_default_na=True,
            )
            logger.info(f"Loaded {len(df_item_groups)} item groups from CSV")

            # Log the column names for debugging
            logger.debug(f"Item groups columns: {df_item_groups.columns.tolist()}")

            # Ensure column names are exactly as expected
            column_mapping = {}

            # Check for case-insensitive matches and create a mapping
            for expected_col in ["group_id", "group_type", "use_price_per_unit"]:
                for actual_col in df_item_groups.columns:
                    if (
                        expected_col.lower() == actual_col.lower()
                        and expected_col != actual_col
                    ):
                        column_mapping[actual_col] = expected_col
                        break

            # Rename columns if needed
            if column_mapping:
                logger.info(f"Renaming item groups columns: {column_mapping}")
                df_item_groups = df_item_groups.rename(columns=column_mapping)

            return df_item_groups

        except Exception as e:
            logger.error(f"Error loading item groups from CSV: {e}", exc_info=True)
            return pd.DataFrame()

    def get_item_group_members(
        self, group_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        try:
            # Use more robust CSV parsing options
            df_item_group_members = pd.read_csv(
                self.item_group_members_path,
                quotechar='"',
                escapechar="\\",
                skipinitialspace=True,
                na_values=["", "NA", "N/A", "null"],
                keep_default_na=True,
            )
            logger.info(
                f"Loaded {len(df_item_group_members)} item group members from CSV"
            )

            # Ensure numeric columns are actually numeric
            df_item_group_members = ensure_numeric_columns(
                df_item_group_members, ["order", "min_index", "max_index"]
            )

            # Ensure column names are exactly as expected
            column_mapping = {}

            # Check for case-insensitive matches and create a mapping
            for expected_col in [
                "group_id",
                "product_id",
                "order",
                "min_index",
                "max_index",
            ]:
                for actual_col in df_item_group_members.columns:
                    if (
                        expected_col.lower() == actual_col.lower()
                        and expected_col != actual_col
                    ):
                        column_mapping[actual_col] = expected_col
                        break

            # Rename columns if needed
            if column_mapping:
                logger.info(f"Renaming columns: {column_mapping}")
                df_item_group_members = df_item_group_members.rename(
                    columns=column_mapping
                )

            # Filter by group_ids if provided
            if group_ids and "group_id" in df_item_group_members.columns:
                df_item_group_members = df_item_group_members[
                    df_item_group_members["group_id"].isin(group_ids)
                ]
                logger.info(
                    f"Filtered to {len(df_item_group_members)} item group members"
                )

            return df_item_group_members

        except Exception as e:
            logger.error(
                f"Error loading item group members from CSV: {e}", exc_info=True
            )
            return pd.DataFrame()

    def get_price_ladder(self) -> List[float]:
        """
        Fetch price ladder from local CSV.

        Returns:
            List[float]: List of valid prices on the price ladder.
        """
        try:
            # Use more robust CSV parsing options
            df_price_ladder = pd.read_csv(
                self.price_ladder_path,
                quotechar='"',
                escapechar="\\",
                skipinitialspace=True,
            )
            logger.info(f"Loaded {len(df_price_ladder)} prices from price ladder CSV")

            # Extract prices as a list
            price_ladder = df_price_ladder["price"].tolist()
            return price_ladder

        except Exception as e:
            logger.error(f"Error loading price ladder from CSV: {e}", exc_info=True)
            return []

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
                "item_group_members": pd.DataFrame(),
            }

        # Get item groups
        df_item_groups = self.get_item_groups()

        if df_item_groups.empty:
            return {
                "products": df_products,
                "item_groups": pd.DataFrame(),
                "item_group_members": pd.DataFrame(),
            }

        # Get all item group members
        df_item_group_members = self.get_item_group_members()

        if df_item_group_members.empty:
            return {
                "products": df_products,
                "item_groups": df_item_groups,
                "item_group_members": pd.DataFrame(),
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
        additional_product_ids = (
            df_all_group_members[~df_all_group_members["product_id"].isin(product_ids)][
                "product_id"
            ]
            .unique()
            .tolist()
        )

        # Fetch these additional products
        if additional_product_ids:
            df_additional_products = self.get_products(additional_product_ids)
            df_products = pd.concat(
                [df_products, df_additional_products], ignore_index=True
            )

        return {
            "products": df_products,
            "item_groups": df_item_groups[
                df_item_groups["group_id"].isin(relevant_groups)
            ],
            "item_group_members": df_all_group_members,
        }
