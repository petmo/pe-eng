"""
Absolute range constraint implementation.
"""

import pandas as pd
from typing import List, Dict, Optional
import pulp
from core.constraints.base import Constraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class AbsoluteRangeConstraint(Constraint):
    """
    Constraint ensuring that items in a group have prices within an absolute range.
    The most expensive item can be at most max_diff currency units more expensive than the cheapest.
    """

    def __init__(self, group_id: str, product_ids: List[str], max_diff: float = 5.0):
        """
        Initialize the absolute range constraint.

        Args:
            group_id: ID of the item group.
            product_ids: List of product IDs in the group.
            max_diff: Maximum allowed price difference in currency units.
        """
        super().__init__()
        self.group_id = group_id
        self.product_ids = product_ids
        self.max_diff = max_diff
        self._name = f"AbsoluteRangeConstraint_{group_id}"
        self._priority = self.PRIORITY_HIGH

    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of the absolute range constraint.

        Args:
            df_products: DataFrame containing product data.

        Returns:
            pd.DataFrame: DataFrame containing information about violations.
        """
        # Filter products in the group
        df_group_products = df_products[
            df_products["product_id"].isin(self.product_ids)
        ]

        if len(df_group_products) <= 1:
            # No violations if only one product or none
            return pd.DataFrame()

        # Get min and max prices in the group
        min_price = df_group_products["price"].min()
        max_price = df_group_products["price"].max()

        # Calculate the actual price difference
        actual_diff = max_price - min_price

        # Check if the difference exceeds the maximum allowed
        if actual_diff > self.max_diff:
            # Find the products with max price
            df_violations = df_group_products[
                df_group_products["price"] == max_price
            ].copy()

            # Add violation information
            df_violations["constraint_type"] = "absolute_range"
            df_violations["group_id"] = self.group_id
            df_violations["expected_value"] = self.max_diff
            df_violations["actual_value"] = actual_diff

            # Reference the cheapest product
            cheapest_product_id = df_group_products.loc[
                df_group_products["price"] == min_price, "product_id"
            ].iloc[0]
            df_violations["reference_product_id"] = cheapest_product_id

            logger.info(
                f"Found {len(df_violations)} absolute range violations in group {self.group_id}. "
                f"Max price: {max_price}, Min price: {min_price}, "
                f"Actual diff: {actual_diff}, Max allowed: {self.max_diff}"
            )

            return df_violations[
                [
                    "product_id",
                    "constraint_type",
                    "group_id",
                    "expected_value",
                    "actual_value",
                    "reference_product_id",
                ]
            ]

        # No violations
        return pd.DataFrame()

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
        # Filter products in the group that are in the variables dictionary
        product_ids = [p_id for p_id in self.product_ids if p_id in variables]

        if len(product_ids) <= 1:
            # No constraints needed if only one product or none
            return

        # Create variables for the min and max price in the group
        min_price_var = pulp.LpVariable(
            name=f"min_price_abs_{self.group_id}", lowBound=0, cat=pulp.LpContinuous
        )

        max_price_var = pulp.LpVariable(
            name=f"max_price_abs_{self.group_id}", lowBound=0, cat=pulp.LpContinuous
        )

        # Constraints to define min_price and max_price
        for pid in product_ids:
            # min_price <= price[i] for all i
            model += (
                min_price_var <= variables[pid],
                f"min_price_abs_def1_{self.group_id}_{pid}",
            )

            # max_price >= price[i] for all i
            model += (
                max_price_var >= variables[pid],
                f"max_price_abs_def1_{self.group_id}_{pid}",
            )

        # We also need to ensure that min_price is the actual minimum
        # This is tricky with linear constraints, but we can use a binary variable approach

        # Enforce at least one price equals min_price
        binary_vars = {}
        for pid in product_ids:
            # Create a binary variable for each product
            binary_vars[pid] = pulp.LpVariable(
                name=f"is_min_price_abs_{self.group_id}_{pid}", cat=pulp.LpBinary
            )

            # If binary_vars[pid] = 1, then price[pid] = min_price
            big_M = 1000  # A large number
            model += (
                variables[pid] - min_price_var <= big_M * (1 - binary_vars[pid]),
                f"min_price_abs_def2_{self.group_id}_{pid}_1",
            )
            model += (
                variables[pid] - min_price_var >= -big_M * (1 - binary_vars[pid]),
                f"min_price_abs_def2_{self.group_id}_{pid}_2",
            )

        # Ensure at least one binary variable is 1
        model += (
            pulp.lpSum(binary_vars.values()) >= 1,
            f"min_price_abs_def3_{self.group_id}",
        )

        # Same approach for max_price
        max_binary_vars = {}
        for pid in product_ids:
            # Create a binary variable for each product
            max_binary_vars[pid] = pulp.LpVariable(
                name=f"is_max_price_abs_{self.group_id}_{pid}", cat=pulp.LpBinary
            )

            # If max_binary_vars[pid] = 1, then price[pid] = max_price
            big_M = 1000  # A large number
            model += (
                variables[pid] - max_price_var <= big_M * (1 - max_binary_vars[pid]),
                f"max_price_abs_def2_{self.group_id}_{pid}_1",
            )
            model += (
                variables[pid] - max_price_var >= -big_M * (1 - max_binary_vars[pid]),
                f"max_price_abs_def2_{self.group_id}_{pid}_2",
            )

        # Ensure at least one binary variable is 1
        model += (
            pulp.lpSum(max_binary_vars.values()) >= 1,
            f"max_price_abs_def3_{self.group_id}",
        )

        # Constraint: max_price <= min_price + max_diff
        model += (
            max_price_var <= min_price_var + self.max_diff,
            f"absolute_range_{self.group_id}",
        )

        logger.debug(
            f"Added absolute range constraint for group {self.group_id} with {len(product_ids)} products, "
            f"max difference: {self.max_diff}"
        )

    def get_relaxed_version(
        self, relaxation_factor: float = 0.1
    ) -> Optional["Constraint"]:
        """
        Get a relaxed version of this constraint by increasing the max_diff.

        Args:
            relaxation_factor: Factor by which to relax the constraint

        Returns:
            AbsoluteRangeConstraint: A relaxed version of this constraint
        """
        # Increase the maximum allowed difference by the relaxation factor
        relaxed_constraint = AbsoluteRangeConstraint(
            self.group_id, self.product_ids, self.max_diff * (1 + relaxation_factor)
        )
        relaxed_constraint.priority = self.priority
        relaxed_constraint.name = f"Relaxed_{self.name}"

        logger.info(
            f"Relaxed {self.name} from max_diff={self.max_diff} to {relaxed_constraint.max_diff}"
        )

        return relaxed_constraint
