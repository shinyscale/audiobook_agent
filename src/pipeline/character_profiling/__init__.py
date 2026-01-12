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
from .narrator import NarratorDetector, NarratorInfo, detect_narrator_from_summary
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
    "NarratorDetector",
    "NarratorInfo",
    "detect_narrator_from_summary",
    # Pipeline
    "CharacterProfilingPipeline",
    "profile_characters",
]
