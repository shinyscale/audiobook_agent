"""
Glossary-driven pronunciation proposer.

A book's glossary lists exactly the terms the author judged worth defining —
military lingo, acronyms, and foreign words (ARVN, DEROS, Chieu Hoi, FUBAR,
Klick, …). A narrator needs every one of them. This proposer emits a
pronunciation entry per cleaned glossary term, deliberately bypassing the CMU
"known word" gate so even dictionary terms the author flagged are included.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from ..models import PronunciationFlag, PronunciationMention, PronunciationProposal
from .base import BasePronunciationProposer

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)

# Trailing parenthetical gloss, e.g. "Artillery (arty for short)" -> "Artillery".
_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")
# A mid-term sentence period followed by more text signals a definition spill.
_MID_SENTENCE = re.compile(r"\.\s+\S")
_URLISH = re.compile(r"https?://|www\.|\.(?:com|net|org|edu|gov)\b", re.IGNORECASE)


class GlossaryProposer(BasePronunciationProposer):
    """Proposes a pronunciation entry for every cleaned glossary term."""

    name = "glossary"

    def __init__(self, glossary_entries: Optional[list] = None):
        """
        Args:
            glossary_entries: list of objects exposing `.term`, `.definition`,
                and `.position` (ingestion GlossaryEntry). None/empty disables.
        """
        self.glossary_entries = glossary_entries or []

    def _clean_term(self, term: str) -> Optional[str]:
        """Normalize a glossary headword; return None for non-term junk.

        Rejects definition lines that mis-parsed as terms: sentence fragments,
        overly long phrases, and URLs. Strips a trailing parenthetical gloss.
        """
        if not term:
            return None
        term = _TRAILING_PAREN.sub("", term).strip()
        if not term or not any(c.isalpha() for c in term):
            return None
        if _URLISH.search(term):
            return None
        if _MID_SENTENCE.search(term):
            return None
        # A real headword is short; full sentences/definition spillover are not.
        if len(term.split()) > 4:
            return None
        return term

    @staticmethod
    def _split_aliases(term: str) -> list[str]:
        """Split a comma-list of short aliases ("1-oh, 2-oh, 3-oh") into separate
        terms. Only splits when every comma-part is itself a short token, so
        definitions that slipped through aren't shredded."""
        if "," not in term:
            return [term]
        parts = [p.strip() for p in term.split(",") if p.strip()]
        if len(parts) >= 2 and all(0 < len(p.split()) <= 2 for p in parts):
            return parts
        return [term]

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        if not self.glossary_entries:
            return []

        proposals: list[PronunciationProposal] = []
        seen: set[str] = set()

        for ge in self.glossary_entries:
            raw = getattr(ge, "term", None)
            cleaned = self._clean_term(raw)
            if cleaned is None:
                continue
            definition = getattr(ge, "definition", "") or ""
            gloss_pos = getattr(ge, "position", 0) or 0

            for sub in self._split_aliases(cleaned):
                key = sub.lower()
                if key in seen:
                    continue
                seen.add(key)

                # Prefer real in-body occurrences for accurate mentions/context.
                mentions = self._find_all_occurrences(
                    full_text, sub, chapter_boundaries, word_index=word_index
                )
                if not mentions:
                    # Term defined but not found verbatim in the body (e.g. an
                    # acronym only spelled out): synthesize one mention anchored
                    # at the glossary so the entry still appears.
                    mentions = [
                        PronunciationMention(
                            word_form=sub,
                            position=gloss_pos,
                            chapter_index=self._get_chapter_for_position(
                                gloss_pos, chapter_boundaries
                            ),
                            context=definition[:200],
                        )
                    ]

                proposals.append(
                    PronunciationProposal(
                        strategy=self.name,
                        word=sub,
                        flag_reason=PronunciationFlag.PROPER_NOUN,
                        mentions=mentions,
                        confidence=0.7,
                        reasoning="Author-flagged glossary term",
                    )
                )

        logger.info(f"Glossary proposer produced {len(proposals)} terms")
        return proposals
