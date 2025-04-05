"""
Logging utility for the pricing engine.
"""
import logging
import sys
import colorlog
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

    # Set the level from config
    level = config.get("logging.level", "INFO")
    logger.setLevel(getattr(logging, level))

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Get color settings from config
        use_color = config.get("logging.use_color", True)

        # Create a handler that outputs to the stdout
        handler = logging.StreamHandler(sys.stdout)

        if use_color:
            # Set up a colored formatter
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                },
                secondary_log_colors={},
                style='%'
            )
        else:
            # Set up a regular formatter
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger