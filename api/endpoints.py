"""
API endpoints for the pricing engine.
"""

from typing import Dict
import json
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
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
    logger.info("⭐ Supabase Edge Function: check_violations called")
    logger.debug(f"Event: {event}")

    try:
        # Log headers received from Supabase
        headers = event.get("headers", {})
        safe_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() not in ("authorization", "x-api-key")
        }
        logger.debug(f"Received headers: {safe_headers}")

        # Parse request body
        body = (
            json.loads(event["body"])
            if isinstance(event.get("body"), str)
            else event.get("body", {})
        )

        logger.info(f"Request body: {body}")

        # Get product IDs from request
        product_ids = body.get("product_ids", [])
        constraint_types = body.get("constraint_types")  # Optional

        logger.info(f"Processing check_violations for {len(product_ids)} products")

        if not product_ids:
            logger.warning("No product IDs provided in request")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"success": False, "error": "No product IDs provided"}
                ),
            }

        # Load data from configured source
        loader = get_data_loader()
        logger.info(f"Using data loader: {loader.__class__.__name__}")
        data = loader.get_product_group_data(product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning(f"No products found for IDs: {product_ids}")
            return {
                "statusCode": 404,
                "body": json.dumps({"success": False, "error": "No products found"}),
            }

        logger.info(
            f"Found {len(data['products'])} products, {len(data['item_groups'])} item groups, {len(data['item_group_members'])} group members"
        )

        # Create optimization engine
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run violation detection
        logger.info("Running violation detection...")
        result = engine.detect_violations(product_ids)

        violations_count = len(result.get("violations", []))
        logger.info(
            f"Violation detection complete. Found {violations_count} violations."
        )

        # Add constraint types filter info if provided
        if constraint_types:
            result["constraint_types_filter"] = constraint_types

        # Prepare response
        response = {"statusCode": 200, "body": json.dumps(result)}
        logger.info("Returning successful response")
        return response

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
