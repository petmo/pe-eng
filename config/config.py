"""
Configuration loader for the pricing engine.
"""
import os
import yaml
import logging
from typing import Dict, Any


class Config:
    """
    Configuration class for the pricing engine.
    Loads configuration from YAML files.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the configuration.

        Args:
            config_path: Path to the configuration file. If None, uses default paths.
        """
        self._config = {}
        self._config_path = config_path or self._find_config_file()
        self._load_config()

    def _find_config_file(self) -> str:
        """
        Find the configuration file in standard locations.

        Returns:
            str: Path to the configuration file.
        """
        # Check environment variable first
        if os.environ.get("PRICING_ENGINE_CONFIG"):
            return os.environ["PRICING_ENGINE_CONFIG"]

        # Check standard locations
        possible_locations = [
            os.path.join(os.getcwd(), "config", "default.yaml"),
            os.path.join(os.getcwd(), "config.yaml"),
            os.path.join(os.path.dirname(__file__), "default.yaml"),
            "/etc/pricing_engine/config.yaml",
        ]

        for location in possible_locations:
            if os.path.exists(location):
                return location

        # Default to the package config
        return os.path.join(os.path.dirname(__file__), "default.yaml")

    def _load_config(self) -> None:
        """
        Load the configuration from the YAML file.
        """
        try:
            with open(self._config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading configuration from {self._config_path}: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Dot-separated path to the configuration value (e.g., "supabase.url").
            default: Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration.

        Returns:
            Dict[str, Any]: The entire configuration dictionary.
        """
        return self._config


# Create a global configuration instance
config = Config()