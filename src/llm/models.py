"""
Model recommendations and hardware detection.
"""

from dataclasses import dataclass
from typing import Optional
import os


# Context usage percentages (of total context length)
CONTEXT_PERCENT = {
    "chapter_detection": 0.75,      # Chapter detection gets 75% of context
    "character_profile": 0.70,      # Character profiles get 70%
    "chapter_summary": 0.60,        # Chapter summaries get 60%
    "alias_resolution": 0.50,       # Alias resolution gets 50%
    "relationship_extraction": 0.50,
    "chunk_processing": 0.40,       # Processing individual chunks
}


@dataclass
class ModelConfig:
    """Configuration for a local LLM model."""
    name: str
    description: str
    min_vram_gb: float
    ollama_name: str
    active_params: str  # e.g., "5.1B active" for MoE models
    context_length: int = 8192
    recommended_for: list[str] = None

    def __post_init__(self):
        if self.recommended_for is None:
            self.recommended_for = []


# Models optimized for the DGX Spark and similar hardware
RECOMMENDED_MODELS = [
    ModelConfig(
        name="GPT-OSS-120B",
        description="OpenAI's open-weight model with Apache 2.0 license. Strong reasoning and agentic capabilities.",
        min_vram_gb=80,
        ollama_name="gpt-oss:120b",
        active_params="5.1B active (MoE)",
        context_length=32768,
        recommended_for=["reasoning", "agentic", "general"],
    ),
    ModelConfig(
        name="Qwen3-Next-80B-A3B",
        description="Alibaba's ultra-efficient model with hybrid attention. Excellent for structured extraction.",
        min_vram_gb=48,
        ollama_name="qwen3-next:80b",
        active_params="3B active (MoE)",
        context_length=262144,  # 256K native
        recommended_for=["extraction", "long-context", "structured"],
    ),
    ModelConfig(
        name="Llama 3.1 70B",
        description="Meta's flagship open model. Good all-around performance.",
        min_vram_gb=48,
        ollama_name="llama3.1:70b",
        active_params="70B",
        context_length=131072,
        recommended_for=["general", "chat"],
    ),
    ModelConfig(
        name="Qwen 2.5 72B",
        description="Strong for code and structured output tasks.",
        min_vram_gb=48,
        ollama_name="qwen2.5:72b",
        active_params="72B",
        context_length=32768,
        recommended_for=["code", "structured"],
    ),
    ModelConfig(
        name="Llama 3.1 8B",
        description="Fast and capable, good for development and testing.",
        min_vram_gb=6,
        ollama_name="llama3.1:8b",
        active_params="8B",
        context_length=131072,
        recommended_for=["testing", "fast"],
    ),
    ModelConfig(
        name="Qwen 2.5 7B",
        description="Excellent for structured JSON extraction, very fast.",
        min_vram_gb=6,
        ollama_name="qwen2.5:7b",
        active_params="7B",
        context_length=32768,
        recommended_for=["testing", "structured", "fast"],
    ),
]


def get_model_for_hardware(vram_gb: float, use_case: str = "general") -> ModelConfig:
    """
    Select the best model for available VRAM and use case.

    Args:
        vram_gb: Available VRAM in gigabytes
        use_case: One of "general", "extraction", "reasoning", "fast"

    Returns:
        Best matching ModelConfig
    """
    # Filter to models that fit in VRAM
    suitable = [m for m in RECOMMENDED_MODELS if m.min_vram_gb <= vram_gb]

    if not suitable:
        # Return smallest model if nothing fits
        return min(RECOMMENDED_MODELS, key=lambda m: m.min_vram_gb)

    # Prefer models matching use case
    for model in suitable:
        if use_case in model.recommended_for:
            return model

    # Default to largest suitable model
    return max(suitable, key=lambda m: m.min_vram_gb)


def get_default_model() -> str:
    """Get the default model name, auto-detecting from LM Studio if available."""
    # Check environment variable first
    if os.environ.get("LLM_MODEL"):
        return os.environ["LLM_MODEL"]

    # Try to auto-detect from LM Studio
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        if response.ok:
            models = response.json().get("data", [])
            if models:
                # Return the first available model
                return models[0]["id"]
    except Exception:
        pass  # Fall back to default

    # Fallback default
    return "gpt-oss:120b"
