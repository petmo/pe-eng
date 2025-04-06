"""
Data validation utilities for the pricing engine.

This module provides functions for validating and converting data types
in pandas DataFrames to ensure consistent processing throughout the application.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Set
from utils.logging import setup_logger

logger = setup_logger(__name__)


def ensure_numeric_columns(
        df: pd.DataFrame,
        numeric_columns: List[str],
        log_failures: bool = True
) -> pd.DataFrame:
    """
    Ensure specified columns in a DataFrame are numeric types.

    Args:
        df: The DataFrame to process
        numeric_columns: List of column names that should be numeric
        log_failures: Whether to log warnings for values that couldn't be converted

    Returns:
        DataFrame with numeric columns converted to appropriate types
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original DataFrame
    df_copy = df.copy()

    # List of columns that exist in the DataFrame
    existing_columns = [col for col in numeric_columns if col in df_copy.columns]

    # Log warning for any requested columns that don't exist
    missing_columns = set(numeric_columns) - set(existing_columns)
    if missing_columns and log_failures:
        logger.warning(f"Columns not found for numeric conversion: {list(missing_columns)}")

    # Process each existing column
    for col in existing_columns:
        # Skip columns that are already numeric
        if pd.api.types.is_numeric_dtype(df_copy[col]):
            continue

        # Try to convert to numeric, coercing errors to NaN
        original_values = df_copy[col].copy()
        df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')

        # Log any conversions that failed (resulting in NaN)
        if log_failures:
            # Find rows where conversion failed
            conversion_failures = df_copy[df_copy[col].isna() & ~original_values.isna()]
            nan_count = len(conversion_failures)

            if nan_count > 0:
                # Get a sample of values that failed conversion
                sample_failures = original_values[conversion_failures.index[:min(3, nan_count)]].tolist()
                logger.warning(
                    f"Column '{col}' had {nan_count} values that couldn't be converted to numeric. "
                    f"Sample values: {sample_failures}"
                )

    return df_copy


def validate_dataframe_columns(
        df: pd.DataFrame,
        required_columns: List[str],
        raise_error: bool = False
) -> bool:
    """
    Validate that a DataFrame contains all required columns.

    Args:
        df: The DataFrame to validate
        required_columns: List of column names that must be present
        raise_error: Whether to raise an error if validation fails

    Returns:
        bool: True if validation succeeds, False otherwise

    Raises:
        ValueError: If validation fails and raise_error is True
    """
    if df.empty:
        message = "Cannot validate columns on empty DataFrame"
        logger.warning(message)
        if raise_error:
            raise ValueError(message)
        return False

    # Check for missing columns
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        message = f"Missing required columns: {list(missing_columns)}"
        logger.warning(message)
        if raise_error:
            raise ValueError(message)
        return False

    return True


def validate_group_data(
        df_item_groups: pd.DataFrame,
        df_item_group_members: pd.DataFrame
) -> Dict[str, Any]:
    """
    Validate consistency between item groups and item group members.

    Args:
        df_item_groups: DataFrame containing item group data
        df_item_group_members: DataFrame containing item group member data

    Returns:
        Dict with validation results:
        {
            'valid': bool,
            'orphaned_groups': List of group IDs found in group table but with no members,
            'unknown_groups': List of group IDs found in members table but not in group table
        }
    """
    result = {
        'valid': True,
        'orphaned_groups': [],
        'unknown_groups': []
    }

    if df_item_groups.empty or df_item_group_members.empty:
        logger.warning("Cannot validate group data with empty DataFrames")
        result['valid'] = False
        return result

    # Ensure the group_id column exists in both DataFrames
    if 'group_id' not in df_item_groups.columns or 'group_id' not in df_item_group_members.columns:
        logger.warning("Cannot validate group data: missing group_id column")
        result['valid'] = False
        return result

    # Find group IDs in each DataFrame
    group_ids = set(df_item_groups['group_id'])
    member_group_ids = set(df_item_group_members['group_id'])

    # Check for orphaned groups (no members)
    orphaned_groups = group_ids - member_group_ids
    if orphaned_groups:
        result['orphaned_groups'] = list(orphaned_groups)
        result['valid'] = False
        logger.warning(f"Found {len(orphaned_groups)} groups with no members")

    # Check for unknown groups (members reference non-existent group)
    unknown_groups = member_group_ids - group_ids
    if unknown_groups:
        result['unknown_groups'] = list(unknown_groups)
        result['valid'] = False
        logger.warning(f"Found {len(unknown_groups)} unknown group IDs in member table")

    return result


def clean_dataframe(
        df: pd.DataFrame,
        numeric_columns: Optional[List[str]] = None,
        categorical_columns: Optional[List[str]] = None,
        fill_na: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Clean a DataFrame by ensuring data types and handling missing values.

    Args:
        df: The DataFrame to clean
        numeric_columns: List of column names that should be numeric
        categorical_columns: List of column names that should be categorical
        fill_na: Dictionary mapping column names to values for filling NAs

    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original DataFrame
    df_clean = df.copy()

    # Convert numeric columns
    if numeric_columns:
        df_clean = ensure_numeric_columns(df_clean, numeric_columns)

    # Convert categorical columns
    if categorical_columns:
        for col in categorical_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype('category')

    # Fill missing values
    if fill_na:
        for col, value in fill_na.items():
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna(value)

    return df_clean