"""
Product data models for the pricing engine.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import json


class ProductAttributes(BaseModel):
    """
    Model for product attributes.
    """

    vegan: bool = False
    organic: bool = False
    size_unit: str = ""
    unit_size: Optional[float] = None
    gluten_free: bool = False
    lactose_free: bool = False
    pack_quantity: Optional[int] = None
    size_quantity: Optional[float] = None
    unit_size_unit: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields not defined in the model


class Product(BaseModel):
    """
    Model for a product.
    """

    product_id: str
    price: float
    unit_price: float
    categories: Union[List[str], str] = []
    attributes: Union[ProductAttributes, Dict[str, Any], str] = Field(
        default_factory=dict
    )

    @validator("categories", pre=True)
    def parse_categories(cls, v):
        """Parse categories from string to list if needed."""
        if isinstance(v, str):
            if v and "," in v:
                return [cat.strip() for cat in v.split(",")]
            elif v:
                return [v.strip()]
        return v or []

    @validator("attributes", pre=True)
    def parse_attributes(cls, v):
        """Parse attributes from string to dictionary if needed."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields not defined in the model
