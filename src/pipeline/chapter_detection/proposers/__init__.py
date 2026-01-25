"""
Chapter boundary proposers.

Each proposer implements a different strategy for finding chapter boundaries.
"""

from .base import BaseProposer
from .llm import LLMMarkerProposer, LLMNarrativeProposer
from .regex import RegexProposer

__all__ = [
    "BaseProposer",
    "RegexProposer",
    "LLMMarkerProposer",
    "LLMNarrativeProposer",
]
