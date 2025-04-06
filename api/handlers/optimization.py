"""
API handler for price optimization (serverless function format).
"""

from typing import Dict, Any
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger
from .common import parse_request_body, create_response, handle_exception

logger = setup_logger(__name__)


def optimize_prices(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Serverless function handler for optimizing prices.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Dict[str, Any]: API Gateway response
    """
    logger.info("⭐ Serverless Function: optimize_prices called")
    logger.debug(f"Event: {event}")

    try:
        # Parse request body
        body = parse_request_body(event)

        # Get parameters from request
        product_ids = body.get("product_ids", [])
        mode = body.get("mode", "violation_detection")  # Default to violation detection
        kpi_weights = body.get("kpi_weights")  # Only used in kpi_optimization mode

        logger.info(
            f"Processing optimize_prices for {len(product_ids)} products in {mode} mode"
        )

        # Validate mode
        valid_modes = [
            "violation_detection",
            "hygiene_optimization",
            "kpi_optimization",
        ]
        if mode not in valid_modes:
            error_msg = (
                f"Invalid mode: {mode}. Valid modes are: {', '.join(valid_modes)}"
            )
            logger.warning(error_msg)
            return create_response(
                status_code=400, body={"success": False, "error": error_msg}
            )

        if not product_ids:
            logger.warning("No product IDs provided in request")
            return create_response(
                status_code=400,
                body={"success": False, "error": "No product IDs provided"},
            )

        # Load data from configured source for these specific product IDs
        loader = get_data_loader()
        data = loader.get_product_group_data(product_ids)

        # Check if products exist
        if data["products"].empty:
            logger.warning(f"No products found for IDs: {product_ids}")
            return create_response(
                status_code=404, body={"success": False, "error": "No products found"}
            )

        # Create optimization engine with only the necessary data
        engine = OptimizationEngine(
            data["products"], data["item_groups"], data["item_group_members"]
        )

        # Run optimization in the specified mode
        result = engine.run_optimization(product_ids, mode, kpi_weights)

        return create_response(body=result)

    except Exception as e:
        return handle_exception(e, "optimize_prices")
