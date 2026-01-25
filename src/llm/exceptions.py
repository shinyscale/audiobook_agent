"""
Custom exceptions for LLM analysis failures.

These exceptions provide clear, debuggable error messages when LLM-based
analysis fails. The philosophy is fail-fast: if something goes wrong,
raise an exception with context rather than falling back to garbage output.
"""


class LLMAnalysisError(Exception):
    """Base exception for LLM analysis failures."""

    pass


class ChapterDetectionError(LLMAnalysisError):
    """
    Chapter detection failed.

    This can occur when:
    - LLM returns invalid JSON
    - LLM hallucinates chapter text that doesn't exist in the book
    - LLM returns insufficient first_words to locate chapters
    - Detected chapters are suspiciously small (< 500 words)
    """

    pass


class CharacterProfileError(LLMAnalysisError):
    """
    Character profile generation failed.

    This can occur when:
    - No evidence found for a character
    - LLM returns empty profile
    - LLM returns bullet lists instead of synthesized prose
    """

    pass


class ChapterSummaryError(LLMAnalysisError):
    """
    Chapter summary generation failed.

    This can occur when:
    - LLM returns empty summary
    - LLM returns narrator instructions instead of narrative summary
    """

    pass


class PronunciationFilterError(LLMAnalysisError):
    """
    Pronunciation filtering failed.

    This can occur when:
    - LLM returns invalid JSON for word filtering
    """

    pass


class CharacterMergeError(LLMAnalysisError):
    """
    Character alias resolution failed.

    This can occur when:
    - LLM returns invalid alias mapping
    """

    pass


class RelationshipExtractionError(LLMAnalysisError):
    """
    Character relationship extraction failed.

    This can occur when:
    - LLM returns invalid relationship data
    """

    pass
