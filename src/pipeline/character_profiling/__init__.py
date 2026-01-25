"""
Character profiling pipeline.

Summary-driven character identification and rich profile generation
for audiobook narration preparation.
"""

from .converter import (
    character_to_rich_dict,
    profile_map_to_characters,
    profile_to_character,
)
from .generator import CharacterProfileGenerator
from .handoff_detector import HandoffCandidate, HandoffDetector, detect_handoffs
from .identifier import SummaryDrivenCharacterIdentifier
from .models import (
    ActionAnalysis,
    AppearanceProfile,
    CharacterProfile,
    CharacterProfileMap,
    CharacterRelationship,
    IdentifiedCharacter,
    PersonalityProfile,
    ProfileEvidence,
    VoiceGuidance,
)
from .moral_valence import (
    MORAL_VALENCE_CONSTRAINTS,
    MoralValence,
    MoralValenceClassifier,
    MoralValenceResult,
)
from .narrator import NarratorDetector, NarratorInfo, detect_narrator_from_summary
from .narrator_commentary import (
    NarratorComment,
    NarratorCommentaryDetector,
    NarratorCommentaryResult,
)
from .passage_gatherer import CharacterPassage, CharacterPassageGatherer
from .pipeline import CharacterProfilingPipeline, profile_characters
from .reconciler import CharacterReconciler, reconcile_characters, verify_handoff_candidates
from .summary_evidence import (
    CharacterSummaryEvidence,
    SummaryEvidence,
    SummaryEvidenceExtractor,
    extract_character_summary_evidence,
)
from .summary_merger import (
    IdentityStatement,
    SummaryMerger,
    SummaryMergeResult,
    apply_summary_merges,
    find_summary_merges,
)
from .tag_identity import (
    TagIdentityExtractor,
    TagIdentityMatch,
    TagIdentityResult,
    apply_tag_identities_to_merge_candidates,
    extract_tag_identities,
    parse_compound_name,
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
    "verify_handoff_candidates",
    # Handoff Detection
    "HandoffDetector",
    "HandoffCandidate",
    "detect_handoffs",
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
