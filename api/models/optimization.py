"""
API models for optimization requests and responses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class OptimizationRequest(BaseModel):
    """
    Model for price optimization request.
    """

    product_ids: List[str] = Field(
        ..., min_items=1, description="List of product IDs to optimize"
    )
    mode: str = Field(
        "hygiene_optimization",
        description="Optimization mode (violation_detection, hygiene_optimization, or kpi_optimization)",
    )
    kpi_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Dictionary of KPI weights for the optimization objective (only used in kpi_optimization mode)",
    )

    @validator("mode")
    def validate_mode(cls, v):
        """Validate the optimization mode."""
        valid_modes = [
            "violation_detection",
            "hygiene_optimization",
            "kpi_optimization",
        ]
        if v not in valid_modes:
            raise ValueError(f"Mode must be one of: {', '.join(valid_modes)}")
        return v

    @validator("kpi_weights")
    def validate_kpi_weights(cls, v, values):
        """Validate that KPI weights are provided for KPI optimization."""
        if values.get("mode") == "kpi_optimization" and not v:
            v = {"profit": 1.0}  # Default to profit maximization
        return v


class OptimizedPrice(BaseModel):
    """
    Model for an optimized price result.
    """

    product_id: str
    current_price: float
    optimized_price: float
    optimized_price_on_ladder: float
    price_change_pct: float


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


class OptimizationResponse(BaseModel):
    """
    Model for price optimization response.
    """

    success: bool
    mode: str
    status: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    optimized_prices: List[OptimizedPrice] = []
    violations: List[Violation] = []
    violations_summary: Optional[ViolationsSummary] = None
    kpi_weights: Optional[Dict[str, float]] = None
    kpi_impacts: Optional[Dict[str, Any]] = None
