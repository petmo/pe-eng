"""
API endpoints for the pricing engine.
"""

from typing import Dict, List, Any
import json
from data.factory import get_data_loader
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

        # Load data from configured source
        loader = get_data_loader()
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

        # Run violation detection
        result = engine.detect_violations(product_ids)

        # Add constraint types filter info if provided
        if constraint_types:
            result["constraint_types_filter"] = constraint_types

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Error in check_violations: {e}", exc_info=True)
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
        mode = body.get("mode", "violation_detection")  # Default to violation detection
        kpi_weights = body.get("kpi_weights")  # Only used in kpi_optimization mode

        # Validate mode
        valid_modes = [
            "violation_detection",
            "hygiene_optimization",
            "kpi_optimization",
        ]
        if mode not in valid_modes:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid mode: {mode}. Valid modes are: {', '.join(valid_modes)}",
                    }
                ),
            }

        if not product_ids:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"success": False, "error": "No product IDs provided"}
                ),
            }

        # Load data from configured source
        loader = get_data_loader()
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

        # Run optimization in the specified mode
        result = engine.run_optimization(product_ids, mode, kpi_weights)

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Error in optimize_prices: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }
