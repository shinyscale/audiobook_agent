"""
LLM refinement module for audiobook analysis.
Uses local models via Ollama to filter false positives and enrich results.
"""

from .refiner import LLMRefiner, refine_analysis
from .config import ModelConfig, RECOMMENDED_MODELS, get_model_for_hardware

__all__ = [
    "LLMRefiner",
    "refine_analysis",
    "ModelConfig",
    "RECOMMENDED_MODELS",
    "get_model_for_hardware",
]
