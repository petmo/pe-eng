"""
Price order constraint implementation (Good-Better-Best).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
import pulp
from optimization.constraints.base import Constraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class PriceOrderConstraint(Constraint):
    """
    Constraint ensuring that items follow a price order (good-better-best).
    """

    def __init__(
        self, group_id: str, df_members: pd.DataFrame, use_price_per_unit: bool = False
    ):
        """
        Initialize the price order constraint.

        Args:
            group_id: ID of the item group.
            df_members: DataFrame containing group members with their order and index ranges.
            use_price_per_unit: Whether to use unit price instead of price.
        """
        self.group_id = group_id
        self.df_members = df_members
        self.use_price_per_unit = use_price_per_unit

    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of the price order constraint.

        Args:
            df_products: DataFrame containing product data.

        Returns:
            pd.DataFrame: DataFrame containing information about violations.
        """
        violations = []

        # Merge products with group members to get all information
        df_merged = pd.merge(self.df_members, df_products, on="product_id", how="inner")

        if df_merged.empty:
            return pd.DataFrame()

        # Get the base product (order 1) - this is the reference for price index
        df_base = df_merged[df_merged["order"] == 1]

        if df_base.empty:
            logger.warning(f"No base product (order 1) found for group {self.group_id}")
            return pd.DataFrame()

        # Get the base price
        price_col = "unit_price" if self.use_price_per_unit else "price"
        base_price = df_base[price_col].iloc[0]
        base_product_id = df_base["product_id"].iloc[0]

        if base_price <= 0:
            logger.warning(f"Base price is zero or negative for group {self.group_id}")
            return pd.DataFrame()

        # Check each product's price index against its min/max index range
        for _, row in df_merged.iterrows():
            price = row[price_col]

            # Calculate the actual price index (relative to base)
            actual_index = (price / base_price) * 100

            # Check if the price index is within the specified range
            min_index = row["min_index"] if pd.notna(row["min_index"]) else None
            max_index = row["max_index"] if pd.notna(row["max_index"]) else None

            # For order 1, the index should be exactly 100
            if (
                row["order"] == 1 and abs(actual_index - 100) > 1e-6
            ):  # Using small epsilon for float comparison
                violations.append(
                    {
                        "product_id": row["product_id"],
                        "constraint_type": "price_order_base",
                        "group_id": self.group_id,
                        "expected_value": 100,
                        "actual_value": actual_index,
                        "order": row["order"],
                        "reference_product_id": base_product_id,
                    }
                )
            # For other orders, check min/max index
            elif row["order"] > 1:
                if min_index is not None and actual_index < min_index:
                    violations.append(
                        {
                            "product_id": row["product_id"],
                            "constraint_type": "price_order_min",
                            "group_id": self.group_id,
                            "expected_value": min_index,
                            "actual_value": actual_index,
                            "order": row["order"],
                            "reference_product_id": base_product_id,
                        }
                    )
                if max_index is not None and actual_index > max_index:
                    violations.append(
                        {
                            "product_id": row["product_id"],
                            "constraint_type": "price_order_max",
                            "group_id": self.group_id,
                            "expected_value": max_index,
                            "actual_value": actual_index,
                            "order": row["order"],
                            "reference_product_id": base_product_id,
                        }
                    )

        if not violations:
            return pd.DataFrame()

        logger.info(
            f"Found {len(violations)} price order violations in group {self.group_id}"
        )
        return pd.DataFrame(violations)

    def apply_to_model(
        self,
        model: pulp.LpProblem,
        variables: Dict[str, pulp.LpVariable],
        df_products: pd.DataFrame,
        **kwargs,
    ) -> None:
        """
        Apply this constraint to an optimization model.

        Args:
            model: The optimization model (PuLP problem).
            variables: Dictionary of decision variables for prices.
            df_products: DataFrame containing product data.
        """
        # Merge products with group members to get all information
        df_merged = pd.merge(self.df_members, df_products, on="product_id", how="inner")

        # Get only the products that are in the variables dictionary
        df_merged = df_merged[df_merged["product_id"].isin(variables.keys())]

        if df_merged.empty:
            return

        # Get the base product (order 1)
        df_base = df_merged[df_merged["order"] == 1]

        if df_base.empty:
            logger.warning(
                f"No base product (order 1) found for group {self.group_id} - skipping constraint"
            )
            return

        # Get the base product ID
        base_product_id = df_base["product_id"].iloc[0]

        # Apply constraints for each product based on its order and index range
        for _, row in df_merged.iterrows():
            product_id = row["product_id"]

            # Skip the base product
            if product_id == base_product_id:
                continue

            min_index = row["min_index"] if pd.notna(row["min_index"]) else None
            max_index = row["max_index"] if pd.notna(row["max_index"]) else None

            # Get the price factor for unit price vs regular price
            if self.use_price_per_unit:
                # Get the current unit prices to calculate the adjustment factor
                base_unit_price = df_products.loc[
                    df_products["product_id"] == base_product_id, "unit_price"
                ].iloc[0]
                product_unit_price = df_products.loc[
                    df_products["product_id"] == product_id, "unit_price"
                ].iloc[0]

                base_price = df_products.loc[
                    df_products["product_id"] == base_product_id, "price"
                ].iloc[0]
                product_price = df_products.loc[
                    df_products["product_id"] == product_id, "price"
                ].iloc[0]

                # Calculate the factors to convert from price to unit price
                base_factor = base_unit_price / base_price if base_price > 0 else 1
                product_factor = (
                    product_unit_price / product_price if product_price > 0 else 1
                )
            else:
                base_factor = 1
                product_factor = 1

            # Apply min index constraint
            if min_index is not None:
                model += (
                    variables[product_id] * product_factor
                    >= (min_index / 100) * variables[base_product_id] * base_factor,
                    f"price_order_min_{self.group_id}_{product_id}",
                )

            # Apply max index constraint
            if max_index is not None:
                model += (
                    variables[product_id] * product_factor
                    <= (max_index / 100) * variables[base_product_id] * base_factor,
                    f"price_order_max_{self.group_id}_{product_id}",
                )

        logger.debug(f"Added price order constraints for group {self.group_id}"),
