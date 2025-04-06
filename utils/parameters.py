"""
Parameter normalization utilities.
"""

from typing import TypeVar, Optional, List, Dict, Any, Collection

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