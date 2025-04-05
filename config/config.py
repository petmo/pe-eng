"""
Configuration loader for the pricing engine.
"""

import os
import yaml
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class for the pricing engine.
    Loads configuration from YAML files and environment variables.
    Environment variables take precedence over YAML configuration.
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
        self._override_with_env_vars()

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
            with open(self._config_path, "r") as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            logging.error(
                f"Error loading configuration from {self._config_path}: {e}",
                exc_info=True,
            )
            self._config = {}

    def _override_with_env_vars(self) -> None:
        """
        Override sensitive configuration values with environment variables.
        Only credentials and sensitive values should be in environment variables.
        """
        # Supabase credentials (sensitive)
        if os.environ.get("SUPABASE_URL"):
            self._set_nested_value("supabase.url", os.environ["SUPABASE_URL"])

        if os.environ.get("SUPABASE_KEY"):
            self._set_nested_value("supabase.key", os.environ["SUPABASE_KEY"])

        # Other sensitive credentials would be added here
        # Example: AWS credentials, API keys, etc.

        # Logging level can be set via environment for convenience in different environments
        if os.environ.get("LOG_LEVEL"):
            self._set_nested_value("logging.level", os.environ["LOG_LEVEL"])

    def _set_nested_value(self, key_path: str, value: Any) -> None:
        """
        Set a nested value in the configuration dictionary.

        Args:
            key_path: Dot-separated path to the configuration value (e.g., "supabase.url").
            value: Value to set.
        """
        keys = key_path.split(".")
        current = self._config

        # Navigate to the nested location
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Dot-separated path to the configuration value (e.g., "supabase.url").
            default: Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        keys = key.split(".")
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
