"""
Core module for the Pricing Engine.

This module contains the main optimization and constraint handling logic.
"""

from core.optimization.engine import OptimizationEngine
from core.violations.violation import ViolationDetector

__all__ = ["OptimizationEngine", "ViolationDetector"]
