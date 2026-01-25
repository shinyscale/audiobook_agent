"""
System detection module.

Provides hardware detection and profile matching for optimal configuration.
"""

from .profiles import (
    HARDWARE_PROFILES,
    HardwareProfile,
    apply_profile_to_config,
    detect_optimal_profile,
    format_specs_display,
    get_profile_by_name,
    get_profile_names,
)
from .specs import SystemSpecs, detect_system_specs

__all__ = [
    "SystemSpecs",
    "detect_system_specs",
    "HardwareProfile",
    "HARDWARE_PROFILES",
    "detect_optimal_profile",
    "apply_profile_to_config",
    "format_specs_display",
    "get_profile_names",
    "get_profile_by_name",
]
