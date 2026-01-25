"""
Base class for pronunciation proposers.
"""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from ..models import PronunciationMention, PronunciationProposal

if TYPE_CHECKING:
    from ..word_index import WordIndex


class BasePronunciationProposer(ABC):
    """Abstract base class for pronunciation proposers."""

    name: str = "base"

    @abstractmethod
    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],  # (index, start, end)
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        """
        Identify words needing pronunciation attention.

        Args:
            full_text: Complete document text
            chapter_boundaries: List of (chapter_index, start_pos, end_pos)
            character_names: Known character names from previous pipeline
            word_index: Pre-built word index for O(1) lookups (optional)

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
        window: int = 100,
    ) -> str:
        """
        Extract fixed window around word, guaranteeing word is included.

        This is a reliable fixed-window approach that always centers the
        target word in the context. Phase 2 will implement paragraph-based
        context extraction with clickable navigation.

        Args:
            text: Full document text
            position: Character position of word start
            word_length: Length of the target word
            window: Characters of context on each side (default 100)

        Returns:
            Context string with word guaranteed to be included
        """
        start = max(0, position - window)
        end = min(len(text), position + word_length + window)
        context = text[start:end]
        context = " ".join(context.split())  # Normalize whitespace

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
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationMention]:
        """Find all occurrences of a word in text with chapter info.

        Args:
            text: Full document text
            word: Word to find
            chapter_boundaries: Chapter boundary info
            case_sensitive: Whether to match case (default False)
            word_index: Pre-built word index for O(1) lookups (optional)

        Returns:
            List of PronunciationMention with position and context
        """
        mentions = []

        # Use word index if available (O(1) lookup)
        if word_index is not None:
            occurrences = word_index.get_occurrences(word)
            for occ in occurrences:
                # Apply case sensitivity filter if needed
                if case_sensitive and occ.original_form != word:
                    continue
                context = self._extract_context(text, occ.position, len(occ.original_form))
                mentions.append(
                    PronunciationMention(
                        word_form=occ.original_form,
                        position=occ.position,
                        chapter_index=occ.chapter_index,
                        context=context,
                    )
                )
            return mentions

        # Fallback to regex scan
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = r"\b" + re.escape(word) + r"\b"

        for match in re.finditer(pattern, text, flags):
            position = match.start()
            chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
            context = self._extract_context(text, position, len(word))

            mentions.append(
                PronunciationMention(
                    word_form=match.group(0),
                    position=position,
                    chapter_index=chapter_idx,
                    context=context,
                )
            )

        return mentions
