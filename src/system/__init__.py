"""
System detection module.

Provides hardware detection and profile matching for optimal configuration.
"""

from .specs import SystemSpecs, detect_system_specs
from .profiles import (
    HardwareProfile,
    HARDWARE_PROFILES,
    detect_optimal_profile,
    apply_profile_to_config,
    format_specs_display,
    get_profile_names,
    get_profile_by_name,
)

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
