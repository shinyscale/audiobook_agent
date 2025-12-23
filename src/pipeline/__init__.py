"""
Multi-agent pipeline for audiobook analysis.

This pipeline uses a staged approach where each stage builds confidence
before passing results to the next stage.
"""

from .chapter_detection import ChapterDetectionPipeline, ChapterMap
from .character_extraction import (
    CharacterExtractionPipeline,
    CharacterMap as CharacterMapResult,
    extract_characters,
)
from .chapter_summary import (
    ChapterSummaryPipeline,
    ChapterSummaryMap,
    summarize_chapters,
)
from .pronunciation_guide import (
    PronunciationGuidePipeline,
    PronunciationMap,
    generate_pronunciation_guide,
)

__all__ = [
    "ChapterDetectionPipeline",
    "ChapterMap",
    "CharacterExtractionPipeline",
    "CharacterMapResult",
    "extract_characters",
    "ChapterSummaryPipeline",
    "ChapterSummaryMap",
    "summarize_chapters",
    "PronunciationGuidePipeline",
    "PronunciationMap",
    "generate_pronunciation_guide",
]
