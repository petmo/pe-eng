"""
Main entry point for the pricing engine.
"""

import argparse
import json
import pandas as pd
from data.factory import get_data_loader
from optimization.engine import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)


def main():
    """
    Main entry point for the pricing engine CLI.
    """
    parser = argparse.ArgumentParser(description="Pricing Engine CLI")

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check violations command
    check_parser = subparsers.add_parser("check", help="Check violations")
    check_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to check"
    )
    check_parser.add_argument(
        "--constraint-types", "-c", nargs="+", help="Constraint types to check"
    )
    check_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize prices")
    optimize_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    optimize_parser.add_argument(
        "--hygiene-only", "-h", action="store_true", help="Run hygiene check only"
    )
    optimize_parser.add_argument(
        "--output", "-o", help="Output file for results (JSON)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load data from configured source
    loader = get_data_loader()
    data = loader.get_product_group_data(args.product_ids)

    # Check if products exist
    if data["products"].empty:
        logger.error("No products found")
        return

    # Create optimization engine
    engine = OptimizationEngine(
        data["products"], data["item_groups"], data["item_group_members"]
    )

    # Run command
    if args.command == "check":
        result = engine.run_hygiene_check(args.product_ids)

        # Print results
        if result["violations"]:
            logger.info(f"Found {len(result['violations'])} violations")
            for violation in result["violations"]:
                logger.info(f"Violation: {violation}")
        else:
            logger.info("No violations found")

    elif args.command == "optimize":
        result = engine.run_optimization(args.product_ids, args.hygiene_only)

        # Print results
        if result["success"]:
            logger.info("Optimization successful")

            if result["optimized_prices"]:
                logger.info("Optimized prices:")
                for price in result["optimized_prices"]:
                    logger.info(
                        f"Product {price['product_id']}: {price['current_price']} -> {price['optimized_price_on_ladder']} ({price['price_change_pct']:.2f}%)"
                    )

            if result["violations"]:
                logger.info(
                    f"Found {len(result['violations'])} violations in optimized prices"
                )
        else:
            logger.error(f"Optimization failed: {result.get('error')}")

    # Save results to file if output specified
    if args.output and "result" in locals():
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
