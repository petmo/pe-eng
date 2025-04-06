"""
File system utilities for local data files.
"""

import os
from pathlib import Path
from config.config import config
from utils.logging import setup_logger

logger = setup_logger(__name__)


class FileSystem:
    """
    File system utilities for working with local data files.
    """

    @staticmethod
    def get_data_path() -> Path:
        """
        Get the configured data directory path.

        Returns:
            Path: Path to data directory.
        """
        data_path = config.get("data_source.local_data_path", "data/local")
        return Path(data_path)

    @staticmethod
    def get_file_path(filename: str) -> Path:
        """
        Get the full path to a data file.

        Args:
            filename: Name of the file (with or without extension).

        Returns:
            Path: Full path to the file.
        """
        data_path = FileSystem.get_data_path()

        # Add .csv extension if not provided
        if not filename.endswith(".csv"):
            filename = f"{filename}.csv"

        return data_path / filename

    @staticmethod
    def exists(filename: str) -> bool:
        """
        Check if a data file exists.

        Args:
            filename: Name of the file (with or without extension).

        Returns:
            bool: True if the file exists, False otherwise.
        """
        file_path = FileSystem.get_file_path(filename)
        return file_path.exists()

    @staticmethod
    def ensure_dir() -> None:
        """
        Ensure the data directory exists.
        """
        data_path = FileSystem.get_data_path()
        os.makedirs(data_path, exist_ok=True)
        logger.debug(f"Ensured data directory exists: {data_path}")

    @staticmethod
    def list_files() -> list:
        """
        List all CSV files in the data directory.

        Returns:
            list: List of CSV filenames.
        """
        data_path = FileSystem.get_data_path()

        if not data_path.exists():
            return []

        files = [f.name for f in data_path.glob("*.csv")]
        return files
