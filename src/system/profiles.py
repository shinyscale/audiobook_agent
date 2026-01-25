"""
Hardware profiles for optimal configuration.

Defines profiles for different hardware tiers and matches system specs to profiles.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .specs import SystemSpecs

if TYPE_CHECKING:
    from ..agents.config import OrchestratorConfig

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Configuration profile for a hardware tier."""

    name: str
    description: str
    # Model preferences per agent (ordered by preference)
    recommended_models: dict[str, list[str]] = field(default_factory=dict)
    # Maximum model size in billions of parameters
    max_model_size_b: int = 7
    # Parallel processing settings
    max_parallel_workers: int = 2
    # Context window recommendation
    context_length: int = 8192
    # Whether to enable parallel summaries
    parallel_summaries: bool = False
    # Minimum VRAM/unified memory (GB) for this profile
    min_vram_gb: float = 0.0
    # Minimum RAM (GB) for this profile
    min_ram_gb: float = 8.0


# Hardware profile definitions
HARDWARE_PROFILES: dict[str, HardwareProfile] = {
    "dgx": HardwareProfile(
        name="dgx",
        description="DGX Spark/Station (128GB+ VRAM)",
        recommended_models={
            "structure": ["gpt-oss:20b", "qwen2.5:14b", "llama3.2:latest"],
            "characters": ["gpt-oss:120b", "qwen2.5:72b", "qwen3:32b"],
            "summaries": ["gpt-oss:120b", "qwen2.5:72b", "qwen3:32b"],
            "pronunciation": ["qwen3:14b", "qwen2.5:14b", "llama3.2:latest"],
        },
        max_model_size_b=200,
        max_parallel_workers=12,
        context_length=131072,
        parallel_summaries=True,
        min_vram_gb=96.0,
        min_ram_gb=128.0,
    ),
    "workstation": HardwareProfile(
        name="workstation",
        description="Desktop with 24GB+ GPU (RTX 3090/4090, A6000)",
        recommended_models={
            "structure": ["qwen2.5:14b", "llama3.2:latest", "mistral:7b"],
            "characters": ["qwen2.5:72b", "qwen3:32b", "deepseek-r1:32b"],
            "summaries": ["qwen2.5:72b", "qwen3:32b", "llama3.1:70b"],
            "pronunciation": ["qwen3:14b", "qwen2.5:7b", "mistral:7b"],
        },
        max_model_size_b=72,
        max_parallel_workers=8,
        context_length=65536,
        parallel_summaries=True,
        min_vram_gb=20.0,
        min_ram_gb=32.0,
    ),
    "laptop": HardwareProfile(
        name="laptop",
        description="Gaming laptop (8-16GB GPU)",
        recommended_models={
            "structure": ["qwen2.5:7b", "llama3.2:latest", "mistral:7b"],
            "characters": ["qwen3:14b", "qwen2.5:14b", "deepseek-r1:14b"],
            "summaries": ["qwen3:14b", "qwen2.5:14b", "llama3.1:8b"],
            "pronunciation": ["qwen2.5:7b", "mistral:7b", "llama3.2:latest"],
        },
        max_model_size_b=32,
        max_parallel_workers=4,
        context_length=32768,
        parallel_summaries=False,
        min_vram_gb=6.0,
        min_ram_gb=16.0,
    ),
    "macbook_pro": HardwareProfile(
        name="macbook_pro",
        description="Apple M-series Pro/Max (32GB+ unified memory)",
        recommended_models={
            "structure": ["qwen2.5:7b", "llama3.2:latest", "mistral:7b"],
            "characters": ["qwen3:14b", "qwen2.5:14b", "deepseek-r1:14b"],
            "summaries": ["qwen3:14b", "qwen2.5:14b", "llama3.1:8b"],
            "pronunciation": ["qwen2.5:7b", "mistral:7b", "llama3.2:latest"],
        },
        max_model_size_b=32,
        max_parallel_workers=6,
        context_length=32768,
        parallel_summaries=True,
        min_vram_gb=24.0,  # Unified memory
        min_ram_gb=32.0,
    ),
    "macbook_air": HardwareProfile(
        name="macbook_air",
        description="Apple M-series base (8-16GB unified memory)",
        recommended_models={
            "structure": ["llama3.2:latest", "mistral:7b", "qwen2.5:3b"],
            "characters": ["qwen2.5:7b", "llama3.2:latest", "mistral:7b"],
            "summaries": ["qwen2.5:7b", "llama3.2:latest", "llama3.1:8b"],
            "pronunciation": ["qwen2.5:3b", "llama3.2:latest", "mistral:7b"],
        },
        max_model_size_b=14,
        max_parallel_workers=4,
        context_length=16384,
        parallel_summaries=False,
        min_vram_gb=6.0,
        min_ram_gb=8.0,
    ),
    "cpu_only": HardwareProfile(
        name="cpu_only",
        description="No GPU / integrated only",
        recommended_models={
            "structure": ["llama3.2:latest", "qwen2.5:3b", "phi3:mini"],
            "characters": ["qwen2.5:3b", "llama3.2:latest", "phi3:mini"],
            "summaries": ["qwen2.5:3b", "llama3.2:latest", "phi3:mini"],
            "pronunciation": ["qwen2.5:3b", "phi3:mini", "llama3.2:latest"],
        },
        max_model_size_b=7,
        max_parallel_workers=2,
        context_length=8192,
        parallel_summaries=False,
        min_vram_gb=0.0,
        min_ram_gb=8.0,
    ),
}


def detect_optimal_profile(specs: SystemSpecs) -> HardwareProfile:
    """
    Match system specs to the best hardware profile.

    Args:
        specs: Detected system specifications

    Returns:
        Best matching HardwareProfile
    """
    # Special case: Apple Silicon
    if specs.is_apple_silicon:
        if specs.ram_gb >= 32:
            logger.info(f"Detected Apple Silicon with {specs.ram_gb}GB RAM -> macbook_pro profile")
            return HARDWARE_PROFILES["macbook_pro"]
        else:
            logger.info(f"Detected Apple Silicon with {specs.ram_gb}GB RAM -> macbook_air profile")
            return HARDWARE_PROFILES["macbook_air"]

    # Check GPU VRAM to determine profile
    vram = specs.gpu_vram_gb

    if vram >= 96:
        # DGX-class system
        logger.info(f"Detected {vram}GB VRAM -> dgx profile")
        return HARDWARE_PROFILES["dgx"]
    elif vram >= 20:
        # Workstation GPU
        logger.info(f"Detected {vram}GB VRAM -> workstation profile")
        return HARDWARE_PROFILES["workstation"]
    elif vram >= 6:
        # Gaming laptop GPU
        logger.info(f"Detected {vram}GB VRAM -> laptop profile")
        return HARDWARE_PROFILES["laptop"]
    else:
        # No significant GPU
        logger.info(f"Detected {vram}GB VRAM -> cpu_only profile")
        return HARDWARE_PROFILES["cpu_only"]


def apply_profile_to_config(
    profile: HardwareProfile,
    config: "OrchestratorConfig",
    available_models: Optional[list[str]] = None,
) -> None:
    """
    Apply hardware profile settings to an OrchestratorConfig.

    Args:
        profile: Hardware profile to apply
        config: OrchestratorConfig to modify
        available_models: Optional list of available model names to filter recommendations
    """
    from ..agents.config import RECOMMENDED_AGENT_MODELS, AgentConfig

    available = set(available_models) if available_models else None

    for agent_name, model_preferences in profile.recommended_models.items():
        # Find first available model from preferences
        selected_model = None

        for model in model_preferences:
            if available is None or model in available:
                selected_model = model
                break

        if selected_model:
            # Get recommended settings for this agent (temperature, think_mode, etc.)
            agent_recommendations = RECOMMENDED_AGENT_MODELS.get(agent_name, {})

            config.set_agent_config(
                agent_name,
                AgentConfig(
                    model=selected_model,
                    temperature=agent_recommendations.get("temperature", 0.7),
                    think_mode=agent_recommendations.get("think_mode", False),
                    system_prompt=agent_recommendations.get("system_prompt"),
                ),
            )
            logger.debug(
                f"Set {agent_name} agent to use {selected_model} with temperature={agent_recommendations.get('temperature', 0.7)}"
            )


def format_specs_display(specs: SystemSpecs, profile: HardwareProfile) -> str:
    """
    Format system specs for display.

    Args:
        specs: System specifications
        profile: Matched hardware profile

    Returns:
        Formatted string for display
    """
    lines = [
        f"System Profile: {profile.name.replace('_', ' ').title()}",
        f"  Platform:    {specs.platform.title()} ({specs.architecture})",
        f"  CPU Cores:   {specs.cpu_cores}",
        f"  RAM:         {specs.ram_gb:.0f} GB",
    ]

    if specs.gpu_type != "none":
        vram_str = f"{specs.gpu_vram_gb:.0f} GB"
        if specs.is_apple_silicon:
            vram_str += " unified"
        else:
            vram_str += " VRAM"
        lines.append(f"  GPU:         {specs.gpu_name} ({vram_str})")

        if len(specs.gpus) > 1:
            lines.append(f"  GPU Count:   {len(specs.gpus)}")
            lines.append(f"  Total VRAM:  {specs.total_gpu_vram_gb:.0f} GB")
    else:
        lines.append("  GPU:         None detected")

    lines.append("")
    lines.append("Recommended Settings:")
    lines.append(f"  Max Model Size:    {profile.max_model_size_b}B")
    lines.append(f"  Parallel Workers:  {profile.max_parallel_workers}")
    lines.append(f"  Context Length:    {profile.context_length:,}")

    if profile.recommended_models:
        lines.append("")
        lines.append("Recommended Models:")
        for agent, models in profile.recommended_models.items():
            if models:
                lines.append(f"  {agent.title()}:  {models[0]}")

    return "\n".join(lines)


def get_profile_names() -> list[str]:
    """Get list of available profile names."""
    return list(HARDWARE_PROFILES.keys())


def get_profile_by_name(name: str) -> Optional[HardwareProfile]:
    """Get profile by name, case-insensitive."""
    return HARDWARE_PROFILES.get(name.lower())
