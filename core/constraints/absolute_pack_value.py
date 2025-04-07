"""
Absolute pack value constraint implementation (Bigger-Pack-Better-Value with absolute differences).
"""

import pandas as pd
import json
from typing import Dict, Any, Optional
import pulp
from core.constraints.base import Constraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class AbsolutePackValueConstraint(Constraint):
    """
    Constraint ensuring that bigger packs offer better value (using unit price) with absolute differences.
    """

    def __init__(self, group_id: str, df_members: pd.DataFrame):
        """
        Initialize the absolute pack value constraint.

        Args:
            group_id: ID of the item group.
            df_members: DataFrame containing group members with their order and index ranges.
        """
        super().__init__()
        self.group_id = group_id
        self.df_members = df_members
        self._name = f"AbsolutePackValueConstraint_{group_id}"
        self._priority = self.PRIORITY_MEDIUM

    def _extract_size_quantity(self, attributes):
        """
        Extract size quantity from attributes.

        Args:
            attributes: Product attributes (dict or JSON string).

        Returns:
            float: Size quantity or None if not found.
        """
        try:
            if isinstance(attributes, dict):
                return attributes.get("size_quantity")
            elif isinstance(attributes, str):
                attrs = json.loads(attributes)
                return attrs.get("size_quantity")
            return None
        except Exception as e:
            logger.warning(f"Error extracting size_quantity: {e}")
            return None

    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of the absolute pack value constraint.

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

        # Extract size quantity from attributes
        df_merged["size_quantity"] = df_merged["attributes"].apply(
            self._extract_size_quantity
        )

        # Check if size_quantity is available
        missing_size = df_merged["size_quantity"].isna()
        if missing_size.any():
            for _, row in df_merged[missing_size].iterrows():
                violations.append(
                    {
                        "product_id": row["product_id"],
                        "constraint_type": "absolute_pack_value_missing_size",
                        "group_id": self.group_id,
                        "expected_value": "size_quantity",
                        "actual_value": "missing",
                        "order": row.get("order"),
                    }
                )

            # Remove rows with missing size for further checks
            df_merged = df_merged[~missing_size]

        if df_merged.empty:
            return pd.DataFrame(violations) if violations else pd.DataFrame()

        # Sort by size_quantity to determine order if not already specified
        if "order" not in df_merged.columns or df_merged["order"].isna().any():
            df_merged = df_merged.sort_values(by="size_quantity")
            df_merged["order"] = range(1, len(df_merged) + 1)

        # Get the base product (order 1 or smallest size)
        df_base = df_merged[df_merged["order"] == 1]

        if df_base.empty:
            logger.warning(f"No base product (order 1) found for group {self.group_id}")
            return pd.DataFrame(violations) if violations else pd.DataFrame()

        # Get the base unit price
        base_unit_price = df_base["unit_price"].iloc[0]
        base_product_id = df_base["product_id"].iloc[0]

        if base_unit_price <= 0:
            logger.warning(
                f"Base unit price is zero or negative for group {self.group_id}"
            )
            return pd.DataFrame(violations) if violations else pd.DataFrame()

        # Check each product's absolute unit price difference
        for _, row in df_merged.iterrows():
            if row["product_id"] == base_product_id:
                continue

            unit_price = row["unit_price"]

            # Calculate absolute unit price difference
            actual_diff = unit_price - base_unit_price

            # Check min/max constraints
            min_index = row["min_index"] if pd.notna(row["min_index"]) else None
            max_index = row["max_index"] if pd.notna(row["max_index"]) else None

            # For pack values, a lower unit price is expected for larger packs
            if min_index is not None:
                # Convert percentage to absolute difference (negative for discount)
                min_diff = (min_index / 100 - 1) * base_unit_price
                if actual_diff > min_diff:  # Unit price diff too high
                    violations.append(
                        {
                            "product_id": row["product_id"],
                            "constraint_type": "absolute_pack_value_min",
                            "group_id": self.group_id,
                            "expected_value": min_diff,
                            "actual_value": actual_diff,
                            "order": row["order"],
                            "reference_product_id": base_product_id,
                            "size_quantity": row["size_quantity"],
                        }
                    )
            if max_index is not None:
                # Convert percentage to absolute difference
                max_diff = (max_index / 100 - 1) * base_unit_price
                if actual_diff < max_diff:  # Unit price diff too low
                    violations.append(
                        {
                            "product_id": row["product_id"],
                            "constraint_type": "absolute_pack_value_max",
                            "group_id": self.group_id,
                            "expected_value": max_diff,
                            "actual_value": actual_diff,
                            "order": row["order"],
                            "reference_product_id": base_product_id,
                            "size_quantity": row["size_quantity"],
                        }
                    )

        if violations:
            logger.info(
                f"Found {len(violations)} absolute pack value violations in group {self.group_id}"
            )

        return pd.DataFrame(violations) if violations else pd.DataFrame()

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

        # Extract size quantity from attributes
        df_merged["size_quantity"] = df_merged["attributes"].apply(
            self._extract_size_quantity
        )

        # Check if size_quantity is available
        missing_size = df_merged["size_quantity"].isna()
        if missing_size.any():
            logger.warning(
                f"Some products in group {self.group_id} are missing size_quantity - skipping those"
            )
            df_merged = df_merged[~missing_size]

        if df_merged.empty:
            return

        # Sort by size_quantity to determine order if not already specified
        if "order" not in df_merged.columns or df_merged["order"].isna().any():
            df_merged = df_merged.sort_values(by="size_quantity")
            df_merged["order"] = range(1, len(df_merged) + 1)

        # Get the base product (smallest size)
        base_product_id = df_merged.iloc[0]["product_id"]

        # Apply constraints for each product based on its size and index range
        for _, row in df_merged.iterrows():
            product_id = row["product_id"]

            # Skip the base product
            if product_id == base_product_id:
                continue

            min_index = row["min_index"] if pd.notna(row["min_index"]) else None
            max_index = row["max_index"] if pd.notna(row["max_index"]) else None

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

            # Apply absolute difference constraints
            if min_index is not None:
                # Convert percentage to absolute difference
                min_diff = (
                    (min_index / 100 - 1) * variables[base_product_id] * base_factor
                )
                model += (
                    variables[product_id] * product_factor
                    - variables[base_product_id] * base_factor
                    >= min_diff,
                    f"absolute_pack_value_min_{self.group_id}_{product_id}",
                )

            if max_index is not None:
                # Convert percentage to absolute difference
                max_diff = (
                    (max_index / 100 - 1) * variables[base_product_id] * base_factor
                )
                model += (
                    variables[product_id] * product_factor
                    - variables[base_product_id] * base_factor
                    <= max_diff,
                    f"absolute_pack_value_max_{self.group_id}_{product_id}",
                )

        logger.debug(f"Added absolute pack value constraints for group {self.group_id}")

    def get_relaxed_version(
        self, relaxation_factor: float = 0.1
    ) -> Optional["Constraint"]:
        """
        Get a relaxed version of this constraint by adjusting min/max index values.

        Args:
            relaxation_factor: Factor by which to relax the constraint

        Returns:
            AbsolutePackValueConstraint: A relaxed version of this constraint
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
        relaxed_constraint = AbsolutePackValueConstraint(self.group_id, relaxed_members)
        relaxed_constraint.priority = self.priority
        relaxed_constraint.name = f"Relaxed_{self.name}"

        logger.info(f"Relaxed {self.name} min/max indexes by {relaxation_factor*100}%")

        return relaxed_constraint
