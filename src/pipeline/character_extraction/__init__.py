"""
Character extraction pipeline using multi-agent consensus.
"""

from .models import (
    CharacterMention,
    CharacterProposal,
    CharacterValidationResult,
    Character,
    CharacterMap,
    CharacterPipelineCheckpoint,
)
from .pipeline import CharacterExtractionPipeline, extract_characters
from .validator import CharacterValidator
from .consensus import CharacterConsensusBuilder

__all__ = [
    "CharacterMention",
    "CharacterProposal",
    "CharacterValidationResult",
    "Character",
    "CharacterMap",
    "CharacterPipelineCheckpoint",
    "CharacterExtractionPipeline",
    "CharacterValidator",
    "CharacterConsensusBuilder",
    "extract_characters",
]
