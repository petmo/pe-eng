"""
API endpoints for the pricing engine.
"""

from typing import Dict, List, Any
import json
from data.loader import SupabaseLoader
from optimization.engine import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)


def check_violations(event, context):
    """
    Endpoint to check violations for a set of products.

    Args:
        event: API event
        context: API context

    Returns:
        Dict: Response containing violations
    """
    try:
        # Parse request body
        body = (
            json.loads(event["body"])
            if isinstance(event.get("body"), str)
            else event.get("body", {})
        )

        # Get product IDs from request
        product_ids = body.get("product_ids", [])
        constraint_types = body.get("constraint_types")  # Optional

        if not product_ids:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"success": False, "error": "No product IDs provided"}
                ),
            }

        # Load data from Supabase
        loader = SupabaseLoader()
        data = loader.get_product_group_data(product_ids)

        # Check if products exist
        if data["products"].empty:
            return {
                "statusCode": 404,
                "body": json.dumps({"success": False, "error": "No products found"}),
            }

        # Create violation detector
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run hygiene check
        result = engine.run_hygiene_check(product_ids)

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Error in check_violations: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }


def optimize_prices(event, context):
    """
    Endpoint to optimize prices for a set of products.

    Args:
        event: API event
        context: API context

    Returns:
        Dict: Response containing optimized prices
    """
    try:
        # Parse request body
        body = (
            json.loads(event["body"])
            if isinstance(event.get("body"), str)
            else event.get("body", {})
        )

        # Get parameters from request
        product_ids = body.get("product_ids", [])
        hygiene_only = body.get("hygiene_only", True)

        if not product_ids:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"success": False, "error": "No product IDs provided"}
                ),
            }

        # Load data from Supabase
        loader = SupabaseLoader()
        data = loader.get_product_group_data(product_ids)

        # Check if products exist
        if data["products"].empty:
            return {
                "statusCode": 404,
                "body": json.dumps({"success": False, "error": "No products found"}),
            }

        # Create optimization engine
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run optimization
        result = engine.run_optimization(product_ids, hygiene_only)

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Error in optimize_prices: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }
