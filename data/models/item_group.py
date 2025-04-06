"""
Item group data models for the pricing engine.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator


class ItemGroupMember(BaseModel):
    """
    Model for an item group member.
    """

    group_id: str
    product_id: str
    order: Optional[int] = None
    min_index: Optional[float] = None
    max_index: Optional[float] = None

    @validator("min_index", "max_index", pre=True)
    def validate_index(cls, v):
        """Validate index values."""
        if v == "":
            return None
        return v

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields not defined in the model


class ItemGroup(BaseModel):
    """
    Model for an item group.
    """

    group_id: str
    group_type: str
    use_price_per_unit: bool = False
    members: List[ItemGroupMember] = []

    @validator("group_type")
    def validate_group_type(cls, v):
        """Validate group type."""
        valid_types = ["equal", "good-better-best", "bigger-pack-better-value"]
        if v not in valid_types:
            raise ValueError(f"Group type must be one of: {', '.join(valid_types)}")
        return v

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields not defined in the model
