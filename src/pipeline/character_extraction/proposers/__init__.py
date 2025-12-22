"""
Character extraction proposers.

Each proposer implements a different strategy for finding characters.
"""

from .base import BaseCharacterProposer
from .ner import NERProposer
from .llm import LLMCharacterProposer

__all__ = [
    "BaseCharacterProposer",
    "NERProposer",
    "LLMCharacterProposer",
]
