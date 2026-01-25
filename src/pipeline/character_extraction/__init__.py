"""
Character extraction models and utilities.

The v1 pipeline has been removed. Use character_extraction_v2 for the active pipeline.
This module now only exports shared models used across the codebase.
"""

from .models import (
    Character,
    CharacterMap,
    CharacterMention,
    CharacterPipelineCheckpoint,
    CharacterProposal,
    CharacterType,
    CharacterValidationResult,
)

__all__ = [
    "CharacterMention",
    "CharacterProposal",
    "CharacterValidationResult",
    "Character",
    "CharacterMap",
    "CharacterPipelineCheckpoint",
    "CharacterType",
]
