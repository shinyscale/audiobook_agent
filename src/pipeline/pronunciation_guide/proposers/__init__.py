"""
Pronunciation proposers for identifying words needing attention.
"""

from .base import BasePronunciationProposer
from .character_proposer import CharacterProposer
from .cmu_proposer import CMUProposer
from .foreign_proposer import ForeignProposer
from .homograph_proposer import HomographProposer

__all__ = [
    "BasePronunciationProposer",
    "CMUProposer",
    "ForeignProposer",
    "HomographProposer",
    "CharacterProposer",
]
