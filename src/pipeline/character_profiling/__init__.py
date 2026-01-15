"""
Character profiling pipeline.

Summary-driven character identification and rich profile generation
for audiobook narration preparation.
"""

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    CharacterProfileMap,
    ActionAnalysis,
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
from .reconciler import CharacterReconciler, reconcile_characters
from .pipeline import CharacterProfilingPipeline, profile_characters
from .converter import (
    profile_to_character,
    profile_map_to_characters,
    character_to_rich_dict,
)
from .moral_valence import (
    MoralValence,
    MoralValenceResult,
    MoralValenceClassifier,
)

__all__ = [
    # Models
    "IdentifiedCharacter",
    "CharacterProfile",
    "CharacterProfileMap",
    "ActionAnalysis",
    "AppearanceProfile",
    "PersonalityProfile",
    "VoiceGuidance",
    "CharacterRelationship",
    "ProfileEvidence",
    "CharacterPassage",
    # Moral Valence
    "MoralValence",
    "MoralValenceResult",
    "MoralValenceClassifier",
    # Components
    "SummaryDrivenCharacterIdentifier",
    "CharacterPassageGatherer",
    "CharacterProfileGenerator",
    "NarratorDetector",
    "NarratorInfo",
    "detect_narrator_from_summary",
    "CharacterReconciler",
    "reconcile_characters",
    # Pipeline
    "CharacterProfilingPipeline",
    "profile_characters",
    # Converter
    "profile_to_character",
    "profile_map_to_characters",
    "character_to_rich_dict",
]
