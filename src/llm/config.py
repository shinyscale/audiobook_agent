"""
Backward-compatible shim for LLM configuration.

This module re-exports from the new module locations for backward compatibility.
All new code should import directly from src.llm instead.
"""

# Re-export from providers
# Re-export from models
from .models import (
    CONTEXT_PERCENT,
    RECOMMENDED_MODELS,
    ModelConfig,
    get_default_model,
    get_model_for_hardware,
)

# Re-export from ollama
from .ollama import (
    delete_ollama_model,
    get_ollama_model_info,
    pull_ollama_model,
)
from .providers import (
    DEFAULT_URLS,
    LLMProvider,
    detect_available_models,
    detect_context_length,
    get_default_url,
    test_connection,
)

__all__ = [
    # Provider utilities
    "LLMProvider",
    "DEFAULT_URLS",
    "get_default_url",
    "detect_available_models",
    "detect_context_length",
    "test_connection",
    # Model management
    "CONTEXT_PERCENT",
    "ModelConfig",
    "RECOMMENDED_MODELS",
    "get_model_for_hardware",
    "get_default_model",
    # Ollama utilities
    "pull_ollama_model",
    "delete_ollama_model",
    "get_ollama_model_info",
]
