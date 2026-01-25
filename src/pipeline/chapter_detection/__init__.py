"""
Chapter detection pipeline using multi-agent consensus.
"""

from .models import (
    Chapter,
    ChapterBoundary,
    ChapterMap,
    ChapterProposal,
    DocumentProfile,
    PipelineCheckpoint,
    ValidationResult,
)
from .pipeline import ChapterDetectionPipeline
from .scene_breaks import (
    find_scene_breaks,
    get_scene_break_line_numbers,
    get_scene_break_positions,
    is_near_scene_break,
)

__all__ = [
    "DocumentProfile",
    "ChapterProposal",
    "ValidationResult",
    "ChapterBoundary",
    "Chapter",
    "ChapterMap",
    "PipelineCheckpoint",
    "ChapterDetectionPipeline",
    # Scene break detection
    "find_scene_breaks",
    "is_near_scene_break",
    "get_scene_break_positions",
    "get_scene_break_line_numbers",
]
