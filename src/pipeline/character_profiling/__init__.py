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
    MORAL_VALENCE_CONSTRAINTS,
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
from .tag_identity import (
    TagIdentityMatch,
    TagIdentityResult,
    TagIdentityExtractor,
    parse_compound_name,
    extract_tag_identities,
    apply_tag_identities_to_merge_candidates,
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
    "MORAL_VALENCE_CONSTRAINTS",
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
    # Tag Identity (Feature F5)
    "TagIdentityMatch",
    "TagIdentityResult",
    "TagIdentityExtractor",
    "parse_compound_name",
    "extract_tag_identities",
    "apply_tag_identities_to_merge_candidates",
]
