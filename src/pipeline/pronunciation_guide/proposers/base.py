"""
Base class for pronunciation proposers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import re

from ..models import PronunciationProposal, PronunciationMention


class BasePronunciationProposer(ABC):
    """Abstract base class for pronunciation proposers."""

    name: str = "base"

    @abstractmethod
    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],  # (index, start, end)
        character_names: Optional[list[str]] = None,
    ) -> list[PronunciationProposal]:
        """
        Identify words needing pronunciation attention.

        Args:
            full_text: Complete document text
            chapter_boundaries: List of (chapter_index, start_pos, end_pos)
            character_names: Known character names from previous pipeline

        Returns:
            List of pronunciation proposals
        """
        pass

    def _get_chapter_for_position(
        self,
        position: int,
        boundaries: list[tuple[int, int, int]],
    ) -> int:
        """Determine which chapter a position falls in."""
        for index, start, end in boundaries:
            if start <= position < end:
                return index
        return 1  # Default to chapter 1

    def _extract_context(
        self,
        text: str,
        position: int,
        word_length: int,
        window: int = 50,
    ) -> str:
        """Extract context around a word position."""
        start = max(0, position - window)
        end = min(len(text), position + word_length + window)

        context = text[start:end].strip()
        # Clean up whitespace
        context = ' '.join(context.split())

        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context

    def _find_all_occurrences(
        self,
        text: str,
        word: str,
        chapter_boundaries: list[tuple[int, int, int]],
        case_sensitive: bool = False,
    ) -> list[PronunciationMention]:
        """Find all occurrences of a word in text with chapter info."""
        mentions = []
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = r'\b' + re.escape(word) + r'\b'

        for match in re.finditer(pattern, text, flags):
            position = match.start()
            chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
            context = self._extract_context(text, position, len(word))

            mentions.append(PronunciationMention(
                word_form=match.group(0),
                position=position,
                chapter_index=chapter_idx,
                context=context,
            ))

        return mentions
