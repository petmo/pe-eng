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

    # Get logging configuration from config
    logging_config = config.get_logging_config()

    # Set the level from config
    level = logging_config["level"]
    logger.setLevel(getattr(logging, level))

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Get color settings from config
        use_color = logging_config["use_color"]

        # Create a handler that outputs to the stdout
        handler = logging.StreamHandler(sys.stdout)

        if use_color:
            # Set up a colored formatter
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s" + logging_config["format"],
                datefmt=logging_config["datefmt"],
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
                logging_config["format"],
                datefmt=logging_config["datefmt"]
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger