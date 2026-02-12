"""
Character Extraction V2: Summary-Driven Architecture

This module implements the profile-first approach to character extraction:
1. Extract main cast profiles from chapter summaries (F1)
2. Search for mentions deterministically (F2)
3. Apply grounding gate to reject hallucinations (F2b)
4. Extract supporting cast via NER (F3)
5. Detect narrator from summaries (F4)

The key insight is that the LLM already identifies who matters in summaries.
We formalize this into a character list with aliases provided upfront,
eliminating the need for complex merge heuristics.
"""

from .grounding import GroundingGate, GroundingReport, adaptive_min_mentions
from .main_cast import MainCastExtractor, MainCastProfile
from .mention_search import MentionResult, MentionSearcher
from .narrator import NarratorDetector, NarratorInfo
from .supporting import SupportingCastExtractor

__all__ = [
    "MainCastExtractor",
    "MainCastProfile",
    "MentionSearcher",
    "MentionResult",
    "GroundingGate",
    "GroundingReport",
    "adaptive_min_mentions",
    "NarratorDetector",
    "NarratorInfo",
    "SupportingCastExtractor",
]
