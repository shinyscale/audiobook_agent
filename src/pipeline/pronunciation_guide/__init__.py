"""
Pronunciation guide pipeline for audiobook narration preparation.
"""

from .consolidator import PronunciationConsolidator
from .enricher import PronunciationEnricher
from .models import (
    PronunciationEnrichment,
    PronunciationEntry,
    PronunciationFlag,
    PronunciationMap,
    PronunciationMention,
    PronunciationPipelineCheckpoint,
    PronunciationProposal,
)
from .pipeline import PronunciationGuidePipeline, generate_pronunciation_guide
from .proposers import (
    BasePronunciationProposer,
    CharacterProposer,
    CMUProposer,
    ForeignProposer,
    HomographProposer,
)

__all__ = [
    # Models
    "PronunciationFlag",
    "PronunciationMention",
    "PronunciationProposal",
    "PronunciationEnrichment",
    "PronunciationEntry",
    "PronunciationMap",
    "PronunciationPipelineCheckpoint",
    # Pipeline
    "PronunciationGuidePipeline",
    "generate_pronunciation_guide",
    # Components
    "PronunciationEnricher",
    "PronunciationConsolidator",
    # Proposers
    "BasePronunciationProposer",
    "CMUProposer",
    "ForeignProposer",
    "HomographProposer",
    "CharacterProposer",
]
