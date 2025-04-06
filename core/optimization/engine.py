"""
Main optimization engine for the pricing engine.
"""

import pandas as pd
import numpy as np
import pulp
from typing import List, Dict, Any, Optional
from core.constraints.base import Constraint
from core.constraints.equal_price import EqualPriceConstraint
from core.constraints.price_order import PriceOrderConstraint
from core.constraints.pack_value import PackValueConstraint
from core.violations.violation import ViolationDetector
from config.config import config
from utils.logging import setup_logger
from utils.validation import ensure_numeric_columns

logger = setup_logger(__name__)


class OptimizationEngine:
    """
    Main optimization engine for price optimization.

    Supports three modes of operation:
    1. Violation Detection - Identifies constraint violations without suggesting changes
    2. Hygiene Mode - Recommends minimal price changes to comply with constraints
    3. Optimization Mode - Optimizes KPIs (profit, revenue, etc.) while respecting constraints
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
        # Double-check numeric columns are properly typed
        # (in case data came from a different source than our loaders)
        df_products = ensure_numeric_columns(df_products, ["price", "unit_price"])

        df_item_group_members = ensure_numeric_columns(
            df_item_group_members, ["order", "min_index", "max_index"]
        )

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

    def detect_violations(
        self, scope_product_ids: List[str], constraint_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Mode 1: Violation Detection - Identify constraint violations for the given products
        without suggesting any price changes.

        Args:
            scope_product_ids: List of product IDs to check for violations.
            constraint_types: Optional list of constraint types to check. If None, checks all.

        Returns:
            Dict[str, Any]: Results of the violation detection, including violations.
        """
        logger.info(
            f"Running violation detection for {len(scope_product_ids)} products "
            f"with constraint_types={constraint_types if constraint_types else 'ALL'}"
        )

        # Detect violations using the underlying ViolationDetector
        df_violations = self.violation_detector.detect_violations(
            product_ids=scope_product_ids,
            constraint_types=constraint_types,  # pass it on for filtering
        )

        # Generate summary
        violations_summary = self.violation_detector.get_violations_summary(
            df_violations
        )

        return {
            "success": True,
            "mode": "violation_detection",
            "violations": (
                df_violations.to_dict(orient="records")
                if not df_violations.empty
                else []
            ),
            "summary": violations_summary,
        }

    def run_hygiene_optimization(self, scope_product_ids: List[str]) -> Dict[str, Any]:
        """
        Mode 2: Hygiene Optimization - Recommend minimal price changes to comply with constraints.

        Args:
            scope_product_ids: List of product IDs to optimize for constraint compliance.

        Returns:
            Dict[str, Any]: Results of the hygiene optimization, including new prices and any remaining violations.
        """
        logger.info(
            f"Running hygiene optimization for {len(scope_product_ids)} products"
        )

        # First check for violations
        df_violations = self.violation_detector.detect_violations(
            product_ids=scope_product_ids
        )
        violations_summary = self.violation_detector.get_violations_summary(
            df_violations
        )

        # If no violations, no changes needed
        if df_violations.empty:
            return {
                "success": True,
                "mode": "hygiene_optimization",
                "message": "No violations found. No price changes needed.",
                "optimized_prices": [],
                "violations": [],
                "summary": violations_summary,
            }

        # Run optimization with minimal price changes objective
        result = self._run_optimization_model(
            scope_product_ids=scope_product_ids,
            objective_type="minimal_changes",
            kpi_weights=None,
        )

        # Add mode information
        result["mode"] = "hygiene_optimization"

        return result

    def run_kpi_optimization(
        self, scope_product_ids: List[str], kpi_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Mode 3: KPI Optimization - Optimize KPIs (profit, revenue, etc.) while respecting constraints.

        Args:
            scope_product_ids: List of product IDs to optimize.
            kpi_weights: Dictionary of KPI weights for the optimization objective.
                         e.g. {"profit": 0.7, "revenue": 0.3}

        Returns:
            Dict[str, Any]: Results of the KPI optimization, including new prices, KPI impacts, and any constraint violations.
        """
        logger.info(f"Running KPI optimization for {len(scope_product_ids)} products")

        # Set default KPI weights if not provided
        if kpi_weights is None:
            kpi_weights = {"profit": 1.0}  # Default to profit maximization

        # Run optimization with KPI optimization objective
        result = self._run_optimization_model(
            scope_product_ids=scope_product_ids,
            objective_type="kpi_optimization",
            kpi_weights=kpi_weights,
        )

        # Add mode and KPI weights information
        result["mode"] = "kpi_optimization"
        result["kpi_weights"] = kpi_weights

        # TODO: Calculate KPI impacts when AI forecasting model is integrated
        # For now, we'll just add a placeholder
        result["kpi_impacts"] = {
            "estimated_profit_change": "Not yet implemented - requires AI forecast model",
            "estimated_revenue_change": "Not yet implemented - requires AI forecast model",
        }

        return result

    def run_optimization(
        self,
        scope_product_ids: List[str],
        mode: str = "violation_detection",
        kpi_weights: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for running optimization in any of the three modes.

        Args:
            scope_product_ids: List of product IDs to optimize.
            mode: Optimization mode ("violation_detection", "hygiene_optimization", or "kpi_optimization").
            kpi_weights: Dictionary of KPI weights for KPI optimization (only used in "kpi_optimization" mode).

        Returns:
            Dict[str, Any]: Results of the optimization, format depends on the mode.
        """
        logger.info(
            f"Running optimization in '{mode}' mode for {len(scope_product_ids)} products"
        )

        if mode == "violation_detection":
            # If we want to allow constraint_types, we can pass them as a separate argument
            # or handle it in the higher-level code.
            return self.detect_violations(scope_product_ids)
        elif mode == "hygiene_optimization":
            return self.run_hygiene_optimization(scope_product_ids)
        elif mode == "kpi_optimization":
            return self.run_kpi_optimization(scope_product_ids, kpi_weights)
        else:
            error_msg = f"Unknown optimization mode: {mode}. Valid modes are 'violation_detection', 'hygiene_optimization', and 'kpi_optimization'."
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _run_optimization_model(
        self,
        scope_product_ids: List[str],
        objective_type: str,
        kpi_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Internal method to run the optimization model with different objectives.

        Args:
            scope_product_ids: List of product IDs to optimize.
            objective_type: Type of objective ("minimal_changes" or "kpi_optimization").
            kpi_weights: Dictionary of KPI weights for KPI optimization (ignored for minimal_changes).

        Returns:
            Dict[str, Any]: Results of the optimization.
        """
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
        model = pulp.LpProblem(
            name=f"Price_{objective_type}",
            sense=(
                pulp.LpMaximize
                if objective_type == "kpi_optimization"
                else pulp.LpMinimize
            ),
        )

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

        # Set objective function based on objective_type
        if objective_type == "minimal_changes":
            # Minimize price changes
            deviation_vars = {}
            for pid in scope_product_ids:
                current_price = self.df_products.loc[
                    self.df_products["product_id"] == pid, "price"
                ].iloc[0]

                # Create variable for absolute deviation
                deviation_vars[pid] = pulp.LpVariable(
                    name=f"deviation_{pid}", lowBound=0, cat=pulp.LpContinuous
                )

                # Add constraints for absolute deviation
                model += (
                    price_vars[pid] - current_price <= deviation_vars[pid],
                    f"deviation_pos_{pid}",
                )
                model += (
                    current_price - price_vars[pid] <= deviation_vars[pid],
                    f"deviation_neg_{pid}",
                )

            # Objective: minimize sum of deviations
            model += pulp.lpSum(deviation_vars.values()), "Minimize_Price_Changes"

        elif objective_type == "kpi_optimization":
            # For now, we'll use a simple profit model
            # In the future, this would be replaced with AI model predictions

            # Default to profit maximization if no weights provided
            if not kpi_weights:
                kpi_weights = {"profit": 1.0}

            # Simple profit model: price * estimated_units_sold
            # For now, we'll assume a simple linear demand model where
            # units_sold = base_units * (1 - price_elasticity * (price/base_price - 1))
            objective_terms = []

            for pid in scope_product_ids:
                current_price = self.df_products.loc[
                    self.df_products["product_id"] == pid, "price"
                ].iloc[0]

                # Simple assumptions for demonstration:
                base_units = 100  # Base units sold at current price
                price_elasticity = 1.5  # Price elasticity of demand
                cost = current_price * 0.6  # Assume cost is 60% of current price

                # Revenue component: price * estimated_units_sold
                if "revenue" in kpi_weights and kpi_weights["revenue"] > 0:
                    # For now, use a linear approximation for the demand curve
                    # In reality, this would come from the AI forecasting model
                    revenue_weight = kpi_weights.get("revenue", 0)
                    revenue_term = revenue_weight * price_vars[pid] * base_units
                    objective_terms.append(revenue_term)

                # Profit component: (price - cost) * estimated_units_sold
                if "profit" in kpi_weights and kpi_weights["profit"] > 0:
                    profit_weight = kpi_weights.get("profit", 0)
                    profit_term = profit_weight * (price_vars[pid] - cost) * base_units
                    objective_terms.append(profit_term)

            # Set the objective
            if objective_terms:
                model += pulp.lpSum(objective_terms), "Maximize_KPIs"
            else:
                # Fallback to minimal changes if no valid KPIs were specified
                logger.warning(
                    "No valid KPI weights provided, falling back to minimal changes objective"
                )
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

            # Update unit price too, keeping the same ratio
            current_unit_price = self.df_products.loc[
                self.df_products["product_id"] == p["product_id"], "unit_price"
            ].iloc[0]
            current_price = self.df_products.loc[
                self.df_products["product_id"] == p["product_id"], "price"
            ].iloc[0]

            if current_price > 0:
                ratio = current_unit_price / current_price
                df_new_prices.loc[
                    df_new_prices["product_id"] == p["product_id"], "unit_price"
                ] = (p["optimized_price_on_ladder"] * ratio)

        # Check violations with the new prices
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
