"""
Text hygiene module for detecting and handling non-content regions.

This includes:
- Back matter detection (F11)
- Name normalization (F13)
"""

from .back_matter import (
    BackMatterRegion,
    BackMatterDetector,
    detect_back_matter,
    is_in_back_matter,
)

__all__ = [
    "BackMatterRegion",
    "BackMatterDetector",
    "detect_back_matter",
    "is_in_back_matter",
]
