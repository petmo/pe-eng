"""
Base constraint class for the pricing engine.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Optional
from utils.logging import setup_logger

logger = setup_logger(__name__)


class Constraint(ABC):
    """
    Base class for all constraints in the pricing engine.

    All specific constraints should inherit from this class and implement
    both the check_violations and apply_to_model methods.
    """

    # Default priority levels (lower number = higher priority)
    PRIORITY_CRITICAL = 1  # Business critical constraints that should rarely be relaxed
    PRIORITY_HIGH = 2  # Important constraints but can be relaxed if necessary
    PRIORITY_MEDIUM = 3  # Preferred constraints that can be relaxed
    PRIORITY_LOW = 4  # Nice-to-have constraints that can be easily relaxed

    def __init__(self):
        """Initialize the constraint with default priority."""
        self._priority = self.PRIORITY_MEDIUM
        self._relaxable = True
        self._name = self.__class__.__name__

    @property
    def priority(self) -> int:
        """Get the priority level of this constraint."""
        return self._priority

    @priority.setter
    def priority(self, value: int):
        """Set the priority level of this constraint."""
        self._priority = value

    @property
    def relaxable(self) -> bool:
        """Check if this constraint can be relaxed."""
        return self._relaxable

    @relaxable.setter
    def relaxable(self, value: bool):
        """Set whether this constraint can be relaxed."""
        self._relaxable = value

    @property
    def name(self) -> str:
        """Get the name of this constraint."""
        return self._name

    @name.setter
    def name(self, value: str):
        """Set the name of this constraint."""
        self._name = value

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
    def apply_to_model(
        self, model: Any, variables: Dict[str, Any], df_products: pd.DataFrame, **kwargs
    ) -> None:
        """
        Apply this constraint to an optimization model.

        Args:
            model: The optimization model.
            variables: Dictionary of decision variables.
            df_products: DataFrame containing product data.
            **kwargs: Additional arguments for specific constraint types.
        """
        pass

    def get_relaxed_version(
        self, relaxation_factor: float = 0.1
    ) -> Optional["Constraint"]:
        """
        Get a relaxed version of this constraint.
        Default implementation returns None, meaning no relaxation is possible.

        Args:
            relaxation_factor: Factor by which to relax the constraint

        Returns:
            Optional[Constraint]: A relaxed version of this constraint, or None if not implemented
        """
        return None
