"""
Audiobook Prep - AI-powered manuscript analysis for audiobook narrators.

A standalone tool for analyzing books before recording, providing:
- Structural breakdown (chapters, scenes, journal entries)
- Character extraction with descriptions and aliases
- Pronunciation flagging for unusual words
- Word counts and duration estimates
"""

__version__ = "0.1.0"

from .analyzer import AudiobookAnalyzer, analyze_book
from .models import AnalysisResult, BookMetadata, Character, PronunciationEntry

__all__ = [
    'AudiobookAnalyzer',
    'analyze_book',
    'AnalysisResult',
    'BookMetadata',
    'Character',
    'PronunciationEntry',
]
