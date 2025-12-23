"""
Pronunciation guide pipeline for audiobook narration preparation.
"""

from .models import (
    PronunciationFlag,
    PronunciationMention,
    PronunciationProposal,
    PronunciationEnrichment,
    PronunciationEntry,
    PronunciationMap,
    PronunciationPipelineCheckpoint,
)
from .pipeline import PronunciationGuidePipeline, generate_pronunciation_guide
from .enricher import PronunciationEnricher
from .consolidator import PronunciationConsolidator
from .proposers import (
    BasePronunciationProposer,
    CMUProposer,
    ForeignProposer,
    HomographProposer,
    CharacterProposer,
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
