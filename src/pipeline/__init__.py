"""
Multi-agent pipeline for audiobook analysis.

This pipeline uses a staged approach where each stage builds confidence
before passing results to the next stage.
"""

from .chapter_detection import ChapterDetectionPipeline, ChapterMap

__all__ = ["ChapterDetectionPipeline", "ChapterMap"]
