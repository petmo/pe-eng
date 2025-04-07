"""
Absolute price order constraint implementation (Good-Better-Best with absolute differences).
"""

import pandas as pd
from typing import Dict, Optional
import pulp
from core.constraints.base import Constraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class AbsolutePriceOrderConstraint(Constraint):
    """
    Constraint ensuring that items follow a price order (good-better-best) using absolute price differences.
    """

    def __init__(
        self, group_id: str, df_members: pd.DataFrame, use_price_per_unit: bool = False
    ):
        """
        Initialize the absolute price order constraint.

        Args:
            group_id: ID of the item group.
            df_members: DataFrame containing group members with their order and index ranges.
            use_price_per_unit: Whether to use unit price instead of price.
        """
        super().__init__()
        self.group_id = group_id
        self.df_members = df_members
        self.use_price_per_unit = use_price_per_unit
        self._name = f"AbsolutePriceOrderConstraint_{group_id}"
        self._priority = self.PRIORITY_MEDIUM

    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of the absolute price order constraint.

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

        # Get the base product (order 1) - this is the reference
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

        # Check each product's absolute price difference
        for _, row in df_merged.iterrows():
            price = row[price_col]

            # Calculate absolute price difference
            actual_diff = price - base_price

            # For order 1, difference should be 0
            if (
                row["order"] == 1 and abs(actual_diff) > 1e-6
            ):  # Small epsilon for float comparison
                violations.append(
                    {
                        "product_id": row["product_id"],
                        "constraint_type": "absolute_price_order_base",
                        "group_id": self.group_id,
                        "expected_value": 0,
                        "actual_value": actual_diff,
                        "order": row["order"],
                        "reference_product_id": base_product_id,
                    }
                )
            # For other orders, check min/max constraints
            elif row["order"] > 1:
                min_index = row["min_index"] if pd.notna(row["min_index"]) else None
                max_index = row["max_index"] if pd.notna(row["max_index"]) else None

                # Convert percentage indexes to absolute differences
                if min_index is not None:
                    min_diff = (min_index / 100 - 1) * base_price
                    if actual_diff < min_diff:
                        violations.append(
                            {
                                "product_id": row["product_id"],
                                "constraint_type": "absolute_price_order_min",
                                "group_id": self.group_id,
                                "expected_value": min_diff,
                                "actual_value": actual_diff,
                                "order": row["order"],
                                "reference_product_id": base_product_id,
                            }
                        )
                if max_index is not None:
                    max_diff = (max_index / 100 - 1) * base_price
                    if actual_diff > max_diff:
                        violations.append(
                            {
                                "product_id": row["product_id"],
                                "constraint_type": "absolute_price_order_max",
                                "group_id": self.group_id,
                                "expected_value": max_diff,
                                "actual_value": actual_diff,
                                "order": row["order"],
                                "reference_product_id": base_product_id,
                            }
                        )

        if not violations:
            return pd.DataFrame()

        logger.info(
            f"Found {len(violations)} absolute price order violations in group {self.group_id}"
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

            # Apply absolute price difference constraints
            if min_index is not None:
                # Convert percentage index to absolute difference
                min_diff = (
                    (min_index / 100 - 1) * variables[base_product_id] * base_factor
                )
                model += (
                    variables[product_id] * product_factor
                    - variables[base_product_id] * base_factor
                    >= min_diff,
                    f"absolute_price_order_min_{self.group_id}_{product_id}",
                )

            if max_index is not None:
                # Convert percentage index to absolute difference
                max_diff = (
                    (max_index / 100 - 1) * variables[base_product_id] * base_factor
                )
                model += (
                    variables[product_id] * product_factor
                    - variables[base_product_id] * base_factor
                    <= max_diff,
                    f"absolute_price_order_max_{self.group_id}_{product_id}",
                )

        logger.debug(
            f"Added absolute price order constraints for group {self.group_id}"
        )

    def get_relaxed_version(
        self, relaxation_factor: float = 0.1
    ) -> Optional["Constraint"]:
        """
        Get a relaxed version of this constraint by adjusting min/max index values.

        Args:
            relaxation_factor: Factor by which to relax the constraint

        Returns:
            AbsolutePriceOrderConstraint: A relaxed version of this constraint
        """
        # Create a copy of members with relaxed min/max indexes
        relaxed_members = self.df_members.copy()

        # Relax min/max indexes by the relaxation factor
        if "min_index" in relaxed_members.columns:
            relaxed_members["min_index"] = relaxed_members["min_index"].apply(
                lambda x: x * (1 - relaxation_factor) if pd.notna(x) else x
            )

        if "max_index" in relaxed_members.columns:
            relaxed_members["max_index"] = relaxed_members["max_index"].apply(
                lambda x: x * (1 + relaxation_factor) if pd.notna(x) else x
            )

        # Create a new constraint with relaxed parameters
        relaxed_constraint = AbsolutePriceOrderConstraint(
            self.group_id, relaxed_members, self.use_price_per_unit
        )
        relaxed_constraint.priority = self.priority
        relaxed_constraint.name = f"Relaxed_{self.name}"

        logger.info(f"Relaxed {self.name} min/max indexes by {relaxation_factor*100}%")

        return relaxed_constraint
