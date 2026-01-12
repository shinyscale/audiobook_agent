"""
Character profiling pipeline.

Summary-driven character identification and rich profile generation
for audiobook narration preparation.
"""

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterRelationship,
    ProfileEvidence,
)
from .identifier import SummaryDrivenCharacterIdentifier
from .pipeline import CharacterProfilingPipeline

__all__ = [
    "IdentifiedCharacter",
    "CharacterProfile",
    "AppearanceProfile",
    "PersonalityProfile",
    "VoiceGuidance",
    "CharacterRelationship",
    "ProfileEvidence",
    "SummaryDrivenCharacterIdentifier",
    "CharacterProfilingPipeline",
]
