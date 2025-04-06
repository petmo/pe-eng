"""
Configuration loader for the pricing engine.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
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

        # Data source configuration
        if os.environ.get("USE_LOCAL_DATA") in ["true", "True", "1", "yes"]:
            self._set_nested_value("data_source.use_local", True)
        elif os.environ.get("USE_LOCAL_DATA") in ["false", "False", "0", "no"]:
            self._set_nested_value("data_source.use_local", False)

        if os.environ.get("LOCAL_DATA_PATH"):
            self._set_nested_value(
                "data_source.local_data_path", os.environ["LOCAL_DATA_PATH"]
            )

        # Price ladder configuration
        if os.environ.get("PRICE_LADDER_TYPE"):
            self._set_nested_value("price_ladder.type", os.environ["PRICE_LADDER_TYPE"])

        if os.environ.get("PRICE_LADDER_MAX"):
            try:
                max_price = float(os.environ["PRICE_LADDER_MAX"])
                self._set_nested_value("price_ladder.max_price", max_price)
            except ValueError:
                logging.warning(
                    f"Invalid PRICE_LADDER_MAX value: {os.environ['PRICE_LADDER_MAX']}"
                )

        # Price change constraints
        if os.environ.get("PRICE_CHANGE_MIN_PCT"):
            try:
                min_pct = float(os.environ["PRICE_CHANGE_MIN_PCT"])
                self._set_nested_value("price_change.min_pct", min_pct)
            except ValueError:
                logging.warning(
                    f"Invalid PRICE_CHANGE_MIN_PCT value: {os.environ['PRICE_CHANGE_MIN_PCT']}"
                )

        if os.environ.get("PRICE_CHANGE_MAX_PCT"):
            try:
                max_pct = float(os.environ["PRICE_CHANGE_MAX_PCT"])
                self._set_nested_value("price_change.max_pct", max_pct)
            except ValueError:
                logging.warning(
                    f"Invalid PRICE_CHANGE_MAX_PCT value: {os.environ['PRICE_CHANGE_MAX_PCT']}"
                )

        # Logging level can be set via environment for convenience in different environments
        if os.environ.get("LOG_LEVEL"):
            self._set_nested_value("logging.level", os.environ["LOG_LEVEL"])

        # API configuration
        if os.environ.get("API_HOST"):
            self._set_nested_value("api.host", os.environ["API_HOST"])

        if os.environ.get("API_PORT"):
            try:
                port = int(os.environ["API_PORT"])
                self._set_nested_value("api.port", port)
            except ValueError:
                logging.warning(f"Invalid API_PORT value: {os.environ['API_PORT']}")

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

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.

        Returns:
            Dict[str, Any]: Logging configuration.
        """
        return {
            "level": self.get("logging.level", "INFO"),
            "use_color": self.get("logging.use_color", True),
            "format": self.get(
                "logging.format",
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            ),
            "datefmt": self.get("logging.datefmt", "%Y-%m-%d %H:%M:%S"),
        }

    def get_api_config(self) -> Dict[str, Any]:
        """
        Get API configuration.

        Returns:
            Dict[str, Any]: API configuration.
        """
        return {
            "host": self.get("api.host", "0.0.0.0"),
            "port": self.get("api.port", 8000),
        }

    def get_data_source_config(self) -> Dict[str, Any]:
        """
        Get data source configuration.

        Returns:
            Dict[str, Any]: Data source configuration.
        """
        return {
            "use_local": self.get("data_source.use_local", False),
            "local_data_path": self.get("data_source.local_data_path", "data/local"),
        }

    def get_price_ladder_config(self) -> Dict[str, Any]:
        """
        Get price ladder configuration.

        Returns:
            Dict[str, Any]: Price ladder configuration.
        """
        return {
            "type": self.get("price_ladder.type", "x.99"),
            "max_price": self.get("price_ladder.max_price", 2000.0),
        }

    def get_price_change_config(self) -> Dict[str, Any]:
        """
        Get price change configuration.

        Returns:
            Dict[str, Any]: Price change configuration.
        """
        return {
            "min_pct": self.get("price_change.min_pct", -10.0),
            "max_pct": self.get("price_change.max_pct", 10.0),
        }

    def get_supabase_config(self) -> Optional[Dict[str, Any]]:
        """
        Get Supabase configuration if available.

        Returns:
            Optional[Dict[str, Any]]: Supabase configuration or None if not configured.
        """
        url = self.get("supabase.url")
        key = self.get("supabase.key")

        if not url or not key:
            return None

        return {
            "url": url,
            "key": key,
            "tables": self.get(
                "supabase.tables",
                {
                    "products": "products",
                    "item_groups": "item_groups",
                    "item_group_members": "item_group_members",
                },
            ),
        }


# Create a global configuration instance
config = Config()
