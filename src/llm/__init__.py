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

# Provider utilities
from .providers import (
    LLMProvider,
    DEFAULT_URLS,
    get_default_url,
    detect_available_models,
    detect_context_length,
    test_connection,
)

# Model management
from .models import (
    CONTEXT_PERCENT,
    ModelConfig,
    RECOMMENDED_MODELS,
    get_model_for_hardware,
    get_default_model,
)

# Ollama-specific utilities
from .ollama import (
    pull_ollama_model,
    delete_ollama_model,
    get_ollama_model_info,
)

# Prompts
from .prompts import PromptConfig, DEFAULT_PROMPTS

# Exceptions
from .exceptions import (
    LLMAnalysisError,
    ChapterDetectionError,
    CharacterProfileError,
    ChapterSummaryError,
    PronunciationFilterError,
    CharacterMergeError,
    RelationshipExtractionError,
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
