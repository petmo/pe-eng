"""
Main optimization engine for the pricing engine.
"""

import pandas as pd
import numpy as np
import pulp
from typing import List, Dict, Any, Optional, Tuple
from optimization.constraints.base import Constraint
from optimization.constraints.equal_price import EqualPriceConstraint
from optimization.constraints.price_order import PriceOrderConstraint
from optimization.constraints.pack_value import PackValueConstraint
from optimization.violation import ViolationDetector
from config.config import config
from utils.logging import setup_logger

logger = setup_logger(__name__)


class OptimizationEngine:
    """
    Main optimization engine for price optimization.
    """

    def __init__(
        self,
        df_products: pd.DataFrame,
        df_item_groups: pd.DataFrame,
        df_item_group_members: pd.DataFrame,
    ):
        """
        Initialize the optimization engine.

        Args:
            df_products: DataFrame containing product data.
            df_item_groups: DataFrame containing item group data.
            df_item_group_members: DataFrame containing item group member data.
        """
        self.df_products = df_products
        self.df_item_groups = df_item_groups
        self.df_item_group_members = df_item_group_members
        self.violation_detector = ViolationDetector(
            df_products, df_item_groups, df_item_group_members
        )
        self.price_ladder = self._generate_price_ladder()

    def _generate_price_ladder(self) -> List[float]:
        """
        Generate the price ladder based on configuration or load from CSV.

        Returns:
            List[float]: List of valid prices.
        """
        use_local = config.get("data_source.use_local", False)

        if use_local:
            # Load price ladder from CSV if using local data
            from data.local_loader import LocalCSVLoader

            local_loader = LocalCSVLoader()
            price_ladder = local_loader.get_price_ladder()

            if price_ladder:
                logger.info(f"Loaded {len(price_ladder)} prices from price ladder CSV")
                return price_ladder

        # Fall back to generating the price ladder from configuration
        ladder_type = config.get("price_ladder.type", "x.99")
        max_price = config.get("price_ladder.max_price", 2000)

        if ladder_type == "x.99":
            # Generate prices like 0.99, 1.99, 2.99, etc.
            ladder = [float(f"{i}.99") for i in range(int(max_price))]
            logger.info(f"Generated {len(ladder)} prices for price ladder")
            return ladder
        else:
            # Default: 0.01 increments
            ladder = [round(i * 0.01, 2) for i in range(1, int(max_price * 100) + 1)]
            logger.info(f"Generated {len(ladder)} prices for price ladder")
            return ladder

    def _build_constraints(self, scope_product_ids: List[str]) -> List[Constraint]:
        """
        Build all constraints for the optimization model.

        Args:
            scope_product_ids: List of product IDs in scope for optimization.

        Returns:
            List[Constraint]: List of constraints.
        """
        constraints = []

        # Process each item group
        for _, group_row in self.df_item_groups.iterrows():
            group_id = group_row["group_id"]
            group_type = group_row["group_type"]

            # Get members of this group
            df_members = self.df_item_group_members[
                self.df_item_group_members["group_id"] == group_id
            ]

            # Check if any members are in scope
            if not any(pid in scope_product_ids for pid in df_members["product_id"]):
                continue

            # Create appropriate constraint based on group type
            if group_type == "equal":
                product_ids = df_members["product_id"].tolist()
                constraints.append(EqualPriceConstraint(group_id, product_ids))

            elif group_type == "good-better-best":
                use_price_per_unit = group_row.get("use_price_per_unit", False)
                constraints.append(
                    PriceOrderConstraint(group_id, df_members, use_price_per_unit)
                )

            elif group_type == "bigger-pack-better-value":
                constraints.append(PackValueConstraint(group_id, df_members))

        logger.info(f"Built {len(constraints)} constraints for optimization")
        return constraints

    def _find_nearest_price_ladder(self, price: float) -> float:
        """
        Find the nearest price on the price ladder.

        Args:
            price: Original price.

        Returns:
            float: Nearest price on the ladder.
        """
        if not self.price_ladder:
            return price

        # Find the closest price on the ladder
        idx = np.abs(np.array(self.price_ladder) - price).argmin()
        return self.price_ladder[idx]

    def run_hygiene_check(self, scope_product_ids: List[str]) -> Dict[str, Any]:
        """
        Run a hygiene check for the given products.

        Args:
            scope_product_ids: List of product IDs to check.

        Returns:
            Dict[str, Any]: Results of the hygiene check, including violations.
        """
        logger.info(f"Running hygiene check for {len(scope_product_ids)} products")

        # Detect violations
        df_violations = self.violation_detector.detect_violations(
            product_ids=scope_product_ids
        )

        # Generate summary
        violations_summary = self.violation_detector.get_violations_summary(
            df_violations
        )

        return {
            "success": True,
            "violations": (
                df_violations.to_dict(orient="records")
                if not df_violations.empty
                else []
            ),
            "summary": violations_summary,
        }

    def run_optimization(
        self, scope_product_ids: List[str], hygiene_only: bool = True
    ) -> Dict[str, Any]:
        """
        Run price optimization for the given products.

        Args:
            scope_product_ids: List of product IDs to optimize.
            hygiene_only: If True, only run a hygiene check. If False, run full optimization.

        Returns:
            Dict[str, Any]: Results of the optimization, including new prices and violations.
        """
        if hygiene_only:
            return self.run_hygiene_check(scope_product_ids)

        logger.info(f"Running optimization for {len(scope_product_ids)} products")

        # Get products in scope
        df_scope_products = self.df_products[
            self.df_products["product_id"].isin(scope_product_ids)
        ]

        if df_scope_products.empty:
            return {
                "success": False,
                "error": "No products found in scope",
                "optimized_prices": [],
            }

        # Create the optimization model
        model = pulp.LpProblem(name="Price_Optimization", sense=pulp.LpMaximize)

        # Create decision variables for each product in scope
        # Note: Even though we're only optimizing scope products, we need variables for all
        # products involved in constraints
        all_product_ids = set(scope_product_ids)

        # Add products from the same groups
        for pid in scope_product_ids:
            # Find groups containing this product
            group_ids = self.df_item_group_members[
                self.df_item_group_members["product_id"] == pid
            ]["group_id"].unique()

            # Add all products from these groups
            for group_id in group_ids:
                related_pids = self.df_item_group_members[
                    self.df_item_group_members["group_id"] == group_id
                ]["product_id"].unique()
                all_product_ids.update(related_pids)

        # Create price variables
        price_vars = {}

        # Get min and max allowed price changes
        min_pct_change = config.get("price_change.min_pct", -10) / 100
        max_pct_change = config.get("price_change.max_pct", 10) / 100

        for pid in all_product_ids:
            # Get current price
            current_price = self.df_products.loc[
                self.df_products["product_id"] == pid, "price"
            ].iloc[0]

            # Calculate min and max allowed prices
            min_price = max(0.01, current_price * (1 + min_pct_change))
            max_price = current_price * (1 + max_pct_change)

            # Create variable with bounds
            if pid in scope_product_ids:
                # For scope products, allow price changes within range
                price_vars[pid] = pulp.LpVariable(
                    name=f"price_{pid}",
                    lowBound=min_price,
                    upBound=max_price,
                    cat=pulp.LpContinuous,
                )
            else:
                # For non-scope products, fix at current price
                price_vars[pid] = pulp.LpVariable(
                    name=f"price_{pid}",
                    lowBound=current_price,
                    upBound=current_price,
                    cat=pulp.LpContinuous,
                )

        # For hygiene runs, we're just checking if the current prices satisfy constraints
        # So we'll set the objective to a dummy value
        model += 0, "Dummy_Objective"

        # Build and apply constraints
        constraints = self._build_constraints(list(all_product_ids))

        for constraint in constraints:
            constraint.apply_to_model(model, price_vars, self.df_products)

        # Solve the model
        solver = pulp.PULP_CBC_CMD(msg=False)
        result = model.solve(solver)

        # Process the result
        if result != pulp.LpStatusOptimal:
            logger.warning(f"Optimization failed with status: {pulp.LpStatus[result]}")

            return {
                "success": False,
                "error": f"Optimization failed with status: {pulp.LpStatus[result]}",
                "status": pulp.LpStatus[result],
                "optimized_prices": [],
            }

        # Extract optimized prices
        optimized_prices = []

        for pid in scope_product_ids:
            current_price = self.df_products.loc[
                self.df_products["product_id"] == pid, "price"
            ].iloc[0]

            new_price = pulp.value(price_vars[pid])
            new_price_on_ladder = self._find_nearest_price_ladder(new_price)

            optimized_prices.append(
                {
                    "product_id": pid,
                    "current_price": current_price,
                    "optimized_price": new_price,
                    "optimized_price_on_ladder": new_price_on_ladder,
                    "price_change_pct": (
                        (new_price / current_price - 1) * 100
                        if current_price > 0
                        else 0
                    ),
                }
            )

        # Check for violations with the new prices
        # Create a temporary dataframe with the new prices
        df_new_prices = self.df_products.copy()

        for p in optimized_prices:
            df_new_prices.loc[
                df_new_prices["product_id"] == p["product_id"], "price"
            ] = p["optimized_price_on_ladder"]

            # Update unit price too
            current_unit_price = self.df_products.loc[
                self.df_products["product_id"] == p["product_id"], "unit_price"
            ].iloc[0]

            current_price = self.df_products.loc[
                self.df_products["product_id"] == p["product_id"], "price"
            ].iloc[0]

            # Maintain the same ratio between price and unit price
            if current_price > 0:
                ratio = current_unit_price / current_price
                df_new_prices.loc[
                    df_new_prices["product_id"] == p["product_id"], "unit_price"
                ] = (p["optimized_price_on_ladder"] * ratio)

        # Check violations with new prices
        temp_detector = ViolationDetector(
            df_new_prices, self.df_item_groups, self.df_item_group_members
        )
        df_violations = temp_detector.detect_violations(product_ids=scope_product_ids)
        violations_summary = temp_detector.get_violations_summary(df_violations)

        return {
            "success": True,
            "status": pulp.LpStatus[result],
            "optimized_prices": optimized_prices,
            "violations": (
                df_violations.to_dict(orient="records")
                if not df_violations.empty
                else []
            ),
            "violations_summary": violations_summary,
        }
