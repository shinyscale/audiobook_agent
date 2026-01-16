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

from .normalization import (
    normalize_name,
    normalize_names_list,
    names_match,
    is_possessive,
    extract_base_name,
)

__all__ = [
    # Back matter (F11)
    "BackMatterRegion",
    "BackMatterDetector",
    "detect_back_matter",
    "is_in_back_matter",
    # Name normalization (F13)
    "normalize_name",
    "normalize_names_list",
    "names_match",
    "is_possessive",
    "extract_base_name",
]
