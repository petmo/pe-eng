"""
API handler for violation detection (serverless function format).
"""

from typing import Dict, Any, List, Optional
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger
from .common import parse_request_body, create_response, handle_exception

logger = setup_logger(__name__)


def check_violations(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Serverless function handler for checking violations.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Dict[str, Any]: API Gateway response
    """
    logger.info("⭐ Serverless Function: check_violations called")
    logger.debug(f"Event: {event}")

    try:
        # Parse request body
        body = parse_request_body(event)

        # Get product IDs from request
        product_ids = body.get("product_ids", [])
        constraint_types = body.get("constraint_types")  # Optional

        logger.info(f"Processing check_violations for {len(product_ids)} products")

        if not product_ids:
            logger.warning("No product IDs provided in request")
            return create_response(
                status_code=400,
                body={"success": False, "error": "No product IDs provided"},
            )

        # Load data from configured source for these specific product IDs
        loader = get_data_loader()
        logger.info(f"Using data loader: {loader.__class__.__name__}")
        data = loader.get_product_group_data(product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning(f"No products found for IDs: {product_ids}")
            return create_response(
                status_code=404, body={"success": False, "error": "No products found"}
            )

        logger.info(
            f"Found {len(data['products'])} products, {len(data['item_groups'])} item groups, {len(data['item_group_members'])} group members"
        )

        # Create optimization engine with only the necessary data
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run violation detection
        logger.info("Running violation detection...")
        result = engine.detect_violations(product_ids, constraint_types)

        violations_count = len(result.get("violations", []))
        logger.info(
            f"Violation detection complete. Found {violations_count} violations."
        )

        # Add constraint types filter info if provided
        if constraint_types:
            result["constraint_types_filter"] = constraint_types

        # Prepare response
        return create_response(body=result)

    except Exception as e:
        return handle_exception(e, "check_violations")
