"""
Multi-agent pipeline for audiobook analysis.

This pipeline uses a staged approach where each stage builds confidence
before passing results to the next stage.
"""

from .chapter_detection import ChapterDetectionPipeline, ChapterMap
from .chapter_summary import (
    ChapterSummaryMap,
    ChapterSummaryPipeline,
    summarize_chapters,
)
from .character_extraction import CharacterMap as CharacterMapResult
from .pronunciation_guide import (
    PronunciationGuidePipeline,
    PronunciationMap,
    generate_pronunciation_guide,
)

__all__ = [
    "ChapterDetectionPipeline",
    "ChapterMap",
    "CharacterMapResult",
    "ChapterSummaryPipeline",
    "ChapterSummaryMap",
    "summarize_chapters",
    "PronunciationGuidePipeline",
    "PronunciationMap",
    "generate_pronunciation_guide",
]
