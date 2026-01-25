"""
Chapter summary pipeline for audiobook narration preparation.
"""

from .models import (
    ChapterSummary,
    ChapterSummaryMap,
    ChunkSummary,
    DialogueDensity,
    SummaryPipelineCheckpoint,
    ToneType,
)
from .pipeline import ChapterSummaryPipeline, summarize_chapters
from .summarizer import ChapterSummarizer

__all__ = [
    "ChapterSummary",
    "ChapterSummaryMap",
    "ChunkSummary",
    "SummaryPipelineCheckpoint",
    "ToneType",
    "DialogueDensity",
    "ChapterSummaryPipeline",
    "ChapterSummarizer",
    "summarize_chapters",
]
