"""
Logging utility for the pricing engine.
"""
import logging
import sys
from config.config import config

def setup_logger(name):
    """
    Set up and return a logger with the given name.

    Args:
        name (str): Name of the logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.get("logging.level", "INFO")))

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(config.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")))
        logger.addHandler(handler)

    return logger