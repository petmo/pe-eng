"""
Run script for the pricing engine API server.
"""

import uvicorn
from main import create_app
from config.config import config
from utils.logging import setup_logger

logger = setup_logger(__name__)


def main():
    """
    Main entry point for running the API server.
    """
    app = create_app()

    # Get API configuration from config
    api_config = config.get_api_config()
    host = api_config["host"]
    port = api_config["port"]

    logger.info(f"Starting Pricing Engine API server on {host}:{port}")
    uvicorn.run(
        app, host=host, port=port, log_level=config.get("logging.level", "info").lower()
    )


if __name__ == "__main__":
    main()
