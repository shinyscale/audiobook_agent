"""
Chapter boundary proposers.

Each proposer implements a different strategy for finding chapter boundaries.
"""

from .base import BaseProposer
from .regex import RegexProposer
from .llm import LLMMarkerProposer, LLMNarrativeProposer

__all__ = [
    "BaseProposer",
    "RegexProposer",
    "LLMMarkerProposer",
    "LLMNarrativeProposer",
]
