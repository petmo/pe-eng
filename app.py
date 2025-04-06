"""
Main application entry point for the pricing engine.
"""

import argparse
import os
import sys
from dotenv import load_dotenv
from config.config import config
from utils.logging import setup_logger

# Load environment variables from .env file
load_dotenv()

logger = setup_logger(__name__)


def run_api_server(host=None, port=None):
    """
    Run the API server.

    Args:
        host: Host to bind to. If None, uses the value from config.
        port: Port to bind to. If None, uses the value from config.
    """
    # Override config with command line arguments if provided
    if host:
        os.environ["API_HOST"] = host
    if port:
        os.environ["API_PORT"] = str(port)

    from run import main as run_server

    logger.info("Starting API server")
    run_server()


def run_cli():
    """Run the CLI interface."""
    from main import main as run_main

    logger.info("Running CLI command")
    run_main()


def main():
    """
    Main entry point for the application.

    Supports two modes of operation:
    1. API server - Run a FastAPI server for handling HTTP requests
    2. CLI - Run the command-line interface
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

    # CLI mode
    cli_parser = mode_parser.add_parser("cli", help="Run as CLI command")
    # CLI arguments are forwarded to main.py

    # Parse arguments
    args = parser.parse_args()

    # Run in the selected mode
    if args.mode == "serve":
        run_api_server(args.host, args.port)
    elif args.mode == "cli":
        run_cli()
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
