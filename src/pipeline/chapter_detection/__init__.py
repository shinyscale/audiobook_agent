"""
Chapter detection pipeline using multi-agent consensus.
"""

from .models import (
    DocumentProfile,
    ChapterProposal,
    ValidationResult,
    ChapterBoundary,
    Chapter,
    ChapterMap,
    PipelineCheckpoint,
)
from .pipeline import ChapterDetectionPipeline
from .scene_breaks import (
    find_scene_breaks,
    is_near_scene_break,
    get_scene_break_positions,
    get_scene_break_line_numbers,
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
