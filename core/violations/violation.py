"""
Violation detection functionality for the pricing engine.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from core.constraints.base import Constraint
from core.constraints.equal_price import EqualPriceConstraint
from core.constraints.price_order import PriceOrderConstraint
from core.constraints.pack_value import PackValueConstraint
from utils.logging import setup_logger

logger = setup_logger(__name__)


class ViolationDetector:
    """
    Class for detecting violations of pricing constraints.
    """

    def __init__(
        self,
        df_products: pd.DataFrame,
        df_item_groups: pd.DataFrame,
        df_item_group_members: pd.DataFrame,
    ):
        """
        Initialize the violation detector.

        Args:
            df_products: DataFrame containing product data.
            df_item_groups: DataFrame containing item group data.
            df_item_group_members: DataFrame containing item group member data.
        """
        self.df_products = df_products
        self.df_item_groups = df_item_groups
        self.df_item_group_members = df_item_group_members

        # Validate column names and log warnings if expected columns are missing
        self._validate_columns()

        self.constraints = self._build_constraints()

    def _validate_columns(self):
        """
        Validate column names in the DataFrames and log warnings for missing columns.
        """
        # Expected column names
        expected_products_cols = ["product_id", "price", "unit_price", "attributes"]
        expected_item_groups_cols = ["group_id", "group_type", "use_price_per_unit"]
        expected_item_group_members_cols = [
            "group_id",
            "product_id",
            "order",
            "min_index",
            "max_index",
        ]

        # Check products columns
        missing_product_cols = [
            col for col in expected_products_cols if col not in self.df_products.columns
        ]
        if missing_product_cols:
            logger.warning(
                f"Missing expected columns in products DataFrame: {missing_product_cols}"
            )
            logger.info(
                f"Available columns in products DataFrame: {list(self.df_products.columns)}"
            )

        # Check item groups columns
        missing_group_cols = [
            col
            for col in expected_item_groups_cols
            if col not in self.df_item_groups.columns
        ]
        if missing_group_cols:
            logger.warning(
                f"Missing expected columns in item_groups DataFrame: {missing_group_cols}"
            )
            logger.info(
                f"Available columns in item_groups DataFrame: {list(self.df_item_groups.columns)}"
            )

        # Check item group members columns
        missing_member_cols = [
            col
            for col in expected_item_group_members_cols
            if col not in self.df_item_group_members.columns
        ]
        if missing_member_cols:
            logger.warning(
                f"Missing expected columns in item_group_members DataFrame: {missing_member_cols}"
            )
            logger.info(
                f"Available columns in item_group_members DataFrame: {list(self.df_item_group_members.columns)}"
            )

    def _build_constraints(self) -> Dict[str, List[Constraint]]:
        """
        Build the constraints from the data.

        Returns:
            Dict[str, List[Constraint]]: Dictionary mapping group types to lists of constraints.
        """
        constraints = {
            "equal_price": [],
            "good_better_best": [],
            "bigger_pack_better_value": [],
        }

        # Check if we have all the required columns
        required_group_cols = ["group_id", "group_type"]
        required_member_cols = ["group_id", "product_id"]

        missing_group_cols = [
            col for col in required_group_cols if col not in self.df_item_groups.columns
        ]
        missing_member_cols = [
            col
            for col in required_member_cols
            if col not in self.df_item_group_members.columns
        ]

        if missing_group_cols or missing_member_cols:
            logger.error(
                f"Missing required columns for building constraints: {missing_group_cols + missing_member_cols}"
            )
            return constraints

        # Process each item group
        for _, group_row in self.df_item_groups.iterrows():
            group_id = group_row["group_id"]
            group_type = group_row["group_type"]

            # Get members of this group
            df_members = self.df_item_group_members[
                self.df_item_group_members["group_id"] == group_id
            ]

            if df_members.empty:
                continue

            # Create appropriate constraint based on group type
            if group_type == "equal":
                product_ids = df_members["product_id"].tolist()
                constraints["equal_price"].append(
                    EqualPriceConstraint(group_id, product_ids)
                )

            elif group_type == "good-better-best":
                use_price_per_unit = group_row.get("use_price_per_unit", False)
                constraints["good_better_best"].append(
                    PriceOrderConstraint(group_id, df_members, use_price_per_unit)
                )

            elif group_type == "bigger-pack-better-value":
                constraints["bigger_pack_better_value"].append(
                    PackValueConstraint(group_id, df_members)
                )

        logger.info(f"Built {sum(len(c) for c in constraints.values())} constraints")
        return constraints

    def detect_violations(
        self,
        constraint_types: Optional[List[str]] = None,
        product_ids: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Detect violations of constraints.

        Args:
            constraint_types: Optional list of constraint types to check. If None, checks all.
            product_ids: Optional list of product IDs to check. If None, checks all.

        Returns:
            pd.DataFrame: DataFrame containing information about violations.
        """
        violations = []

        # Filter products if needed
        if product_ids:
            df_products = self.df_products[
                self.df_products["product_id"].isin(product_ids)
            ]
        else:
            df_products = self.df_products

        if df_products.empty:
            logger.warning("No products to check violations for")
            return pd.DataFrame()

        # Determine which constraint types to check
        if constraint_types is None:
            constraint_types = list(self.constraints.keys())

        # Check each constraint type
        for constraint_type in constraint_types:
            if constraint_type not in self.constraints:
                logger.warning(f"Unknown constraint type: {constraint_type}")
                continue

            for constraint in self.constraints[constraint_type]:
                violation_df = constraint.check_violations(df_products)
                if not violation_df.empty:
                    violations.append(violation_df)

        # Combine all violations
        if not violations:
            logger.info("No violations detected")
            return pd.DataFrame()

        df_violations = pd.concat(violations, ignore_index=True)
        logger.info(f"Detected {len(df_violations)} violations")
        return df_violations

    def get_violations_summary(self, df_violations: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a summary of violations.

        Args:
            df_violations: DataFrame containing violation information.

        Returns:
            Dict[str, Any]: Summary of violations.
        """
        if df_violations.empty:
            return {
                "total_violations": 0,
                "products_with_violations": 0,
                "violation_types": {},
            }

        # Count violations by type
        violation_types = df_violations["constraint_type"].value_counts().to_dict()

        # Count products with violations
        products_with_violations = df_violations["product_id"].nunique()

        return {
            "total_violations": len(df_violations),
            "products_with_violations": products_with_violations,
            "violation_types": violation_types,
        }

    def filter_valid_products(
        self, product_ids: List[str], constraint_types: Optional[List[str]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Filter out products that violate constraints.

        Args:
            product_ids: List of product IDs to check.
            constraint_types: Optional list of constraint types to check. If None, checks all.

        Returns:
            Tuple[List[str], List[str]]: Tuple of (valid_product_ids, violating_product_ids).
        """
        # Check violations for the given products
        df_violations = self.detect_violations(constraint_types, product_ids)

        if df_violations.empty:
            return product_ids, []

        # Get products with violations
        violating_products = df_violations["product_id"].unique().tolist()

        # Filter valid products
        valid_products = [
            p_id for p_id in product_ids if p_id not in violating_products
        ]

        logger.info(
            f"Filtered {len(violating_products)} products with violations out of {len(product_ids)}"
        )

        return valid_products, violating_products
