"""
Base class for chapter proposers.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import ChapterProposal, DocumentProfile


class BaseProposer(ABC):
    """Abstract base class for chapter boundary proposers."""

    name: str = "base"

    @abstractmethod
    def propose(
        self,
        text: str,
        profile: Optional[DocumentProfile] = None,
    ) -> list[ChapterProposal]:
        """
        Analyze the text and propose chapter boundaries.

        Args:
            text: The full document text
            profile: Optional document profile from earlier stage

        Returns:
            List of chapter proposals with positions, titles, and confidence scores
        """
        pass

    def _extract_evidence(self, text: str, position: int, context_chars: int = 100) -> str:
        """Extract text around a position for evidence."""
        start = max(0, position - 20)
        end = min(len(text), position + context_chars)
        return text[start:end].strip()
