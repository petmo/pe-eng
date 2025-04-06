"""
Equal price constraint implementation.
"""

import pandas as pd
from typing import List, Dict
import pulp
from core.constraints.base import Constraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class EqualPriceConstraint(Constraint):
    """
    Constraint ensuring that items in a group have the same price.
    """

    def __init__(self, group_id: str, product_ids: List[str]):
        """
        Initialize the equal price constraint.

        Args:
            group_id: ID of the item group.
            product_ids: List of product IDs in the group.
        """
        self.group_id = group_id
        self.product_ids = product_ids

    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of the equal price constraint.

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

        # Check if all prices are the same
        reference_price = df_group_products["price"].iloc[0]
        df_violations = df_group_products[
            df_group_products["price"] != reference_price
        ].copy()

        if df_violations.empty:
            # No violations
            return pd.DataFrame()

        # Add violation information
        df_violations["constraint_type"] = "equal_price"
        df_violations["group_id"] = self.group_id
        df_violations["expected_value"] = reference_price
        df_violations["actual_value"] = df_violations["price"]
        df_violations["reference_product_id"] = df_group_products["product_id"].iloc[0]

        logger.info(
            f"Found {len(df_violations)} equal price violations in group {self.group_id}"
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
        # Filter products in the group
        product_ids = [p_id for p_id in self.product_ids if p_id in variables]

        if len(product_ids) <= 1:
            # No constraints needed if only one product or none
            return

        # First product in the group
        first_product_id = product_ids[0]

        # Add constraints to ensure all products in the group have the same price
        for product_id in product_ids[1:]:
            model += (
                variables[product_id] == variables[first_product_id],
                f"equal_price_{self.group_id}_{product_id}",
            )

        logger.debug(
            f"Added equal price constraint for group {self.group_id} with {len(product_ids)} products"
        )
