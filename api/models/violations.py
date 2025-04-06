"""
API models for violation detection requests and responses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ViolationRequest(BaseModel):
    """
    Model for violation detection request.
    """

    product_ids: List[str] = Field(
        ..., min_items=1, description="List of product IDs to check for violations"
    )
    constraint_types: Optional[List[str]] = Field(
        None,
        description="Optional list of constraint types to check (if None, checks all constraints)",
    )


class GroupViolationRequest(BaseModel):
    """
    Request model for checking violations by one or many groups.
    """

    group_ids: List[str] = Field(
        ...,
        min_items=1,
        description="List of one or more group IDs to check for violations",
    )
    constraint_types: Optional[List[str]] = Field(
        None,
        description="Optional list of constraint types to check (if None, checks all constraints)",
    )


class Violation(BaseModel):
    """
    Model for a pricing constraint violation.
    """

    product_id: str
    constraint_type: str
    group_id: str
    expected_value: Any
    actual_value: Any
    reference_product_id: Optional[str] = None
    order: Optional[int] = None
    size_quantity: Optional[float] = None


class ViolationsSummary(BaseModel):
    """
    Summary of pricing violations.
    """

    total_violations: int
    products_with_violations: int
    violation_types: Dict[str, int]


class ViolationResponse(BaseModel):
    """
    Model for violation detection response.
    """

    success: bool
    mode: str = "violation_detection"
    violations: List[Violation] = []
    summary: ViolationsSummary
    constraint_types_filter: Optional[List[str]] = None
    error: Optional[str] = None
