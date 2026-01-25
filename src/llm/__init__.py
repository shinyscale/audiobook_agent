"""
LLM module for audiobook analysis.

This module provides a unified interface for LLM interactions:
- LLMClient: Simple, synchronous client for Ollama, OpenAI, and Anthropic
- Model management: Recommendations, hardware detection
- Ollama utilities: Model pull/delete/info operations
- Prompts and exceptions for domain-specific tasks
"""

# Client API (primary interface)
from .client import LLMClient, LLMConfig, LLMResponse, create_client

# Exceptions
from .exceptions import (
    ChapterDetectionError,
    ChapterSummaryError,
    CharacterMergeError,
    CharacterProfileError,
    LLMAnalysisError,
    PronunciationFilterError,
    RelationshipExtractionError,
)

# Model management
from .models import (
    CONTEXT_PERCENT,
    RECOMMENDED_MODELS,
    ModelConfig,
    get_default_model,
    get_model_for_hardware,
)

# Ollama-specific utilities
from .ollama import (
    delete_ollama_model,
    get_ollama_model_info,
    pull_ollama_model,
)

# Prompts
from .prompts import DEFAULT_PROMPTS, PromptConfig

# Provider utilities
from .providers import (
    DEFAULT_URLS,
    LLMProvider,
    detect_available_models,
    detect_context_length,
    get_default_url,
    test_connection,
)

__all__ = [
    # Client API
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "create_client",
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
    # Prompts
    "PromptConfig",
    "DEFAULT_PROMPTS",
    # Exceptions
    "LLMAnalysisError",
    "ChapterDetectionError",
    "CharacterProfileError",
    "ChapterSummaryError",
    "PronunciationFilterError",
    "CharacterMergeError",
    "RelationshipExtractionError",
]
