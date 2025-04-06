"""
Main entry point for the pricing engine.
"""

import argparse
import json
from data.factory import get_data_loader
from core.optimization import OptimizationEngine
from utils.logging import setup_logger

logger = setup_logger(__name__)


def main():
    """
    Main entry point for the pricing engine CLI.
    """
    parser = argparse.ArgumentParser(description="Pricing Engine CLI")

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Violation detection command
    detect_parser = subparsers.add_parser("detect", help="Detect constraint violations")
    detect_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to check"
    )
    detect_parser.add_argument(
        "--constraint-types", "-c", nargs="+", help="Constraint types to check"
    )
    detect_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # Hygiene optimization command
    hygiene_parser = subparsers.add_parser(
        "hygiene", help="Run hygiene optimization to fix violations"
    )
    hygiene_parser.add_argument(
        "--product-ids", "-p", nargs="+", required=True, help="Product IDs to optimize"
    )
    hygiene_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # KPI optimization command
    optimize_parser = subparsers.add_parser("optimize", help="Run KPI optimization")
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
    if args.command == "detect":
        result = engine.detect_violations(args.product_ids)

        # Print results
        if result["violations"]:
            logger.info(f"Found {len(result['violations'])} violations")
            for violation in result["violations"]:
                logger.warning(f"Violation: {violation}")
        else:
            logger.info("No violations found")

    elif args.command == "hygiene":
        result = engine.run_hygiene_optimization(args.product_ids)

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

    elif args.command == "optimize":
        kpi_weights = args.kpi_weights if args.kpi_weights else {"profit": 1.0}
        result = engine.run_kpi_optimization(args.product_ids, kpi_weights)

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

    # Save results to file if output specified
    if args.output and "result" in locals():
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
