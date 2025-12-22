"""
Base class for character proposers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import re

from ..models import CharacterProposal, CharacterMention


class BaseCharacterProposer(ABC):
    """Abstract base class for character extraction proposers."""

    name: str = "base"

    @abstractmethod
    def propose(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_start_position: int,
    ) -> list[CharacterProposal]:
        """
        Extract character proposals from a single chapter.

        Args:
            chapter_text: The text of the chapter
            chapter_index: The chapter number (1-indexed)
            chapter_start_position: Character offset where this chapter starts in full document

        Returns:
            List of character proposals found in this chapter
        """
        pass

    def _is_in_dialogue(self, text: str, position: int, context_window: int = 50) -> bool:
        """Check if a position is within quoted dialogue."""
        # Get text around the position
        start = max(0, position - context_window)
        end = min(len(text), position + context_window)
        context = text[start:end]

        # Simple heuristic: count quotes before position
        relative_pos = position - start
        before = context[:relative_pos]

        # Count different quote types
        double_quotes = before.count('"') + before.count('"') + before.count('"')
        single_quotes = before.count("'")  # More complex due to apostrophes

        # Odd number of double quotes means we're inside dialogue
        return double_quotes % 2 == 1

    def _extract_context(self, text: str, position: int, context_chars: int = 100) -> str:
        """Extract context around a position."""
        start = max(0, position - context_chars // 2)
        end = min(len(text), position + context_chars // 2)
        return text[start:end].strip()
