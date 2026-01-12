"""
Character profiling pipeline.

Summary-driven character identification and rich profile generation
for audiobook narration preparation.
"""

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    CharacterProfileMap,
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterRelationship,
    ProfileEvidence,
)
from .identifier import SummaryDrivenCharacterIdentifier
from .passage_gatherer import CharacterPassageGatherer, CharacterPassage
from .generator import CharacterProfileGenerator
from .pipeline import CharacterProfilingPipeline, profile_characters

__all__ = [
    # Models
    "IdentifiedCharacter",
    "CharacterProfile",
    "CharacterProfileMap",
    "AppearanceProfile",
    "PersonalityProfile",
    "VoiceGuidance",
    "CharacterRelationship",
    "ProfileEvidence",
    "CharacterPassage",
    # Components
    "SummaryDrivenCharacterIdentifier",
    "CharacterPassageGatherer",
    "CharacterProfileGenerator",
    # Pipeline
    "CharacterProfilingPipeline",
    "profile_characters",
]
