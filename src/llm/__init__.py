"""
LLM refinement module for audiobook analysis.
Uses local models via Ollama to filter false positives and enrich results.
"""

from .refiner import LLMRefiner, refine_analysis
from .config import ModelConfig, RECOMMENDED_MODELS, get_model_for_hardware
from .prompts import PromptConfig, DEFAULT_PROMPTS
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
    "LLMRefiner",
    "refine_analysis",
    "ModelConfig",
    "RECOMMENDED_MODELS",
    "get_model_for_hardware",
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
