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
from .narrator_commentary import (
    NarratorComment,
    NarratorCommentaryResult,
    NarratorCommentaryDetector,
)
from .summary_merger import (
    SummaryMerger,
    SummaryMergeResult,
    IdentityStatement,
    find_summary_merges,
    apply_summary_merges,
)
from .summary_evidence import (
    SummaryEvidence,
    CharacterSummaryEvidence,
    SummaryEvidenceExtractor,
    extract_character_summary_evidence,
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
    # Narrator Commentary
    "NarratorComment",
    "NarratorCommentaryResult",
    "NarratorCommentaryDetector",
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
    # Summary Merger (Feature F1)
    "SummaryMerger",
    "SummaryMergeResult",
    "IdentityStatement",
    "find_summary_merges",
    "apply_summary_merges",
    # Summary Evidence (Feature F2)
    "SummaryEvidence",
    "CharacterSummaryEvidence",
    "SummaryEvidenceExtractor",
    "extract_character_summary_evidence",
]
