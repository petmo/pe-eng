"""
Command-line interface for the pricing engine.

This module provides CLI functionality for running the pricing engine
in different modes (API server or command-line operations).
"""

import argparse
import os
import sys
import json
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from utils.logging import setup_logger
from config.config import config
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from app import start_server

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = setup_logger(__name__)


def detect_violations(
    product_ids: List[str],
    constraint_types: Optional[List[str]] = None,
    output_file: Optional[str] = None,
) -> int:
    """
    Detect constraint violations for the given product IDs.

    Args:
        product_ids: List of product IDs to check
        constraint_types: Optional list of constraint types to check
        output_file: Optional output file path to save results in JSON format

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Load data from configured source
    loader = get_data_loader()
    data = loader.get_product_group_data(product_ids)

    # Check if products exist
    if data["products"].empty:
        logger.error("No products found")
        return 1

    # Create optimization engine
    engine = OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )

    # Run violation detection
    result = engine.detect_violations(product_ids)

    # Print results
    if result["violations"]:
        logger.info(f"Found {len(result['violations'])} violations")
        for violation in result["violations"]:
            logger.warning(f"Violation: {violation}")
    else:
        logger.info("No violations found")

    # Save results to file if output specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {output_file}")

    return 0


def run_hygiene_optimization(
    product_ids: List[str], output_file: Optional[str] = None
) -> int:
    """
    Run hygiene optimization for the given product IDs.

    Args:
        product_ids: List of product IDs to optimize
        output_file: Optional output file path to save results in JSON format

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Load data from configured source
    loader = get_data_loader()
    data = loader.get_product_group_data(product_ids)

    # Check if products exist
    if data["products"].empty:
        logger.error("No products found")
        return 1

    # Create optimization engine
    engine = OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )

    # Run hygiene optimization
    result = engine.run_hygiene_optimization(product_ids)

    # Print results
    if result["success"]:
        logger.info("Hygiene optimization successful")

        if result["optimized_prices"]:
            logger.info("Optimized prices:")
            for price in result["optimized_prices"]:
                if (
                    abs(price["price_change_pct"]) > 0.01
                ):  # Only show prices that changed
                    logger.info(
                        f"Product {price['product_id']}: {price['current_price']} -> {price['optimized_price_on_ladder']} ({price['price_change_pct']:.2f}%)"
                    )
        else:
            logger.info("No price changes needed")

        if result["violations"]:
            logger.warning(
                f"Found {len(result['violations'])} remaining violations after optimization"
            )
    else:
        logger.error(f"Hygiene optimization failed: {result.get('error')}")
        return 1

    # Save results to file if output specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {output_file}")

    return 0


def run_kpi_optimization(
    product_ids: List[str],
    kpi_weights: Optional[Dict[str, float]] = None,
    output_file: Optional[str] = None,
) -> int:
    """
    Run KPI optimization for the given product IDs.

    Args:
        product_ids: List of product IDs to optimize
        kpi_weights: Optional dictionary of KPI weights
        output_file: Optional output file path to save results in JSON format

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Set default KPI weights if not provided
    if not kpi_weights:
        kpi_weights = {"profit": 1.0}

    # Load data from configured source
    loader = get_data_loader()
    data = loader.get_product_group_data(product_ids)

    # Check if products exist
    if data["products"].empty:
        logger.error("No products found")
        return 1

    # Create optimization engine
    engine = OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )

    # Run KPI optimization
    result = engine.run_kpi_optimization(product_ids, kpi_weights)

    # Print results
    if result["success"]:
        logger.info("KPI optimization successful")
        logger.info(f"KPI weights used: {result['kpi_weights']}")

        if result["optimized_prices"]:
            logger.info("Optimized prices:")
            for price in result["optimized_prices"]:
                logger.info(
                    f"Product {price['product_id']}: {price['current_price']} -> {price['optimized_price_on_ladder']} ({price['price_change_pct']:.2f}%)"
                )

        if "kpi_impacts" in result:
            logger.info("Estimated KPI impacts:")
            for kpi, impact in result["kpi_impacts"].items():
                logger.info(f"  {kpi}: {impact}")

        if result["violations"]:
            logger.warning(
                f"Found {len(result['violations'])} violations with optimized prices"
            )
    else:
        logger.error(f"KPI optimization failed: {result.get('error')}")
        return 1

    # Save results to file if output specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {output_file}")

    return 0


def main() -> int:
    """
    Main entry point for the application.

    Parses command-line arguments and runs the appropriate action.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(description="Pricing Engine")

    # Add mode subparser
    mode_parser = parser.add_subparsers(dest="mode", help="Operation mode")

    # API server mode
    api_config = config.get_api_config()
    server_parser = mode_parser.add_parser("serve", help="Run as API server")
    server_parser.add_argument(
        "--host", default=api_config["host"], help="Host to bind to"
    )
    server_parser.add_argument(
        "--port", type=int, default=api_config["port"], help="Port to bind to"
    )

    # Violation detection command
    detect_parser = mode_parser.add_parser(
        "detect", help="Detect constraint violations"
    )
    detect_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to check"
    )
    detect_parser.add_argument(
        "--constraint-types", "-c", nargs="+", help="Constraint types to check"
    )
    detect_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # Hygiene optimization command
    hygiene_parser = mode_parser.add_parser(
        "hygiene", help="Run hygiene optimization to fix violations"
    )
    hygiene_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    hygiene_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # KPI optimization command
    optimize_parser = mode_parser.add_parser("optimize", help="Run KPI optimization")
    optimize_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    optimize_parser.add_argument(
        "--kpi-weights",
        "-k",
        type=json.loads,
        help='KPI weights as JSON string, e.g. \'{"profit": 0.7, "revenue": 0.3}\'',
    )
    optimize_parser.add_argument(
        "--output", "-o", help="Output file for results (JSON)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Run in the selected mode
    if args.mode == "serve":
        # Start the API server
        try:
            start_server(args.host, args.port)
            return 0
        except KeyboardInterrupt:
            logger.info("Server stopped")
            return 0
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            return 1

    elif args.mode == "detect":
        # Run violation detection
        return detect_violations(
            product_ids=args.product_ids,
            constraint_types=args.constraint_types,
            output_file=args.output,
        )

    elif args.mode == "hygiene":
        # Run hygiene optimization
        return run_hygiene_optimization(
            product_ids=args.product_ids, output_file=args.output
        )

    elif args.mode == "optimize":
        # Run KPI optimization
        return run_kpi_optimization(
            product_ids=args.product_ids,
            kpi_weights=args.kpi_weights,
            output_file=args.output,
        )

    else:
        # No mode selected, show help
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
