"""
Parameter normalization utilities.
"""

from typing import TypeVar, Optional, List, Dict, Any, Collection
import pandas as pd
from utils import setup_logger

logger = setup_logger(__name__)


T = TypeVar('T')


def normalize_empty_collection(value: Optional[Collection[T]]) -> Optional[Collection[T]]:
    """
    Normalize a parameter value, treating empty collections as None.

    Args:
        value: A collection parameter (list, dict, set, etc.) or None

    Returns:
        The original collection if it has items, None if it's empty or None
    """
    if value is None or len(value) == 0:
        return None
    return value


def ensure_numeric_columns(df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
    """
    Ensure specified columns in a DataFrame are numeric.

    Args:
        df: The DataFrame to process
        numeric_columns: List of column names that should be numeric

    Returns:
        DataFrame with numeric columns converted to appropriate types
    """
    if df.empty:
        return df

    df_copy = df.copy()

    for col in numeric_columns:
        if col in df_copy.columns:
            # Try to convert to numeric, coercing errors to NaN
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')

            # Log any conversions that failed (resulting in NaN)
            nan_count = df_copy[col].isna().sum()
            if nan_count > 0:
                logger.warning(f"Column '{col}' had {nan_count} values that couldn't be converted to numeric")

    return df_copy