"""
Base constraint class for the pricing engine.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any
from utils.logging import setup_logger

logger = setup_logger(__name__)


class Constraint(ABC):
    """
    Base class for all constraints in the pricing engine.

    All specific constraints should inherit from this class and implement
    both the check_violations and apply_to_model methods.
    """

    @abstractmethod
    def check_violations(self, df_products: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Check for violations of this constraint.

        Args:
            df_products: DataFrame containing product data.
            **kwargs: Additional arguments for specific constraint types.

        Returns:
            pd.DataFrame: DataFrame containing information about violations.
                          Empty DataFrame if no violations.
        """
        pass

    @abstractmethod
    def apply_to_model(self, model: Any, variables: Dict[str, Any], df_products: pd.DataFrame, **kwargs) -> None:
        """
        Apply this constraint to an optimization model.

        Args:
            model: The optimization model.
            variables: Dictionary of decision variables.
            df_products: DataFrame containing product data.
            **kwargs: Additional arguments for specific constraint types.
        """
        pass