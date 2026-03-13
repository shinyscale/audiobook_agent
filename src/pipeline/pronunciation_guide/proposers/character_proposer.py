"""
Character name proposer.

Flags character names from the character extraction pipeline for pronunciation attention.
"""

import logging
from typing import TYPE_CHECKING, Optional, Set

from ..models import PronunciationFlag, PronunciationProposal
from .base import BasePronunciationProposer
from .cmu_proposer import COMMON_WORDS_WHITELIST

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)


class CharacterProposer(BasePronunciationProposer):
    """Proposes character names for pronunciation attention."""

    name = "character"

    def __init__(
        self,
        additional_whitelist: Optional[set[str]] = None,
        cmu_known_words: Optional[Set[str]] = None,
    ):
        """
        Args:
            additional_whitelist: Additional words to never flag
            cmu_known_words: Set of words in the CMU pronouncing dictionary.
                Words found in CMU have standard pronunciations a narrator already
                knows; skip them to reduce false-positive noise. If not provided,
                loaded automatically from the pronouncing library.
        """
        self.whitelist = COMMON_WORDS_WHITELIST.copy()
        if additional_whitelist:
            self.whitelist.update(additional_whitelist)
        # Words in the CMU dict have standard English pronunciations — skip them
        # even when they appear as character names (e.g., "Price", "Sergeant").
        if cmu_known_words is not None:
            self.cmu_known_words: Set[str] = cmu_known_words
        else:
            self.cmu_known_words = self._load_cmu_dict()

    def _load_cmu_dict(self) -> Set[str]:
        """Load words from CMU dictionary via pronouncing library."""
        try:
            import pronouncing
            words = set(pronouncing.cmudict.dict().keys())
            logger.info(f"CharacterProposer loaded {len(words)} words from CMU dictionary")
            return words
        except (ImportError, Exception) as e:
            logger.warning(f"Could not load CMU dictionary: {e}")
            return set()

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        """Flag character names for pronunciation attention.

        Uses WordIndex if available for O(1) lookups, otherwise falls back
        to full text scanning.
        """
        if not character_names:
            logger.debug("No character names provided to CharacterProposer")
            return []

        proposals = []
        seen_words = set()

        def is_descriptive_handle(name: str) -> bool:
            """
            Check if this is a descriptive character handle (not a proper name).

            Descriptive handles use common English words and should not have
            individual words flagged for pronunciation.

            Examples: "the Red Death", "masked figure", "the creature"
            """
            name_lower = name.lower().strip()

            # Starts with article (the, a, an)
            if name_lower.startswith(("the ", "a ", "an ")):
                return True

            # Common descriptive patterns (all lowercase, no proper nouns)
            # Check if all words are lowercase common words
            words = name.split()
            if len(words) >= 2 and all(w[0].islower() or w.lower() in self.whitelist for w in words):
                return True

            return False

        for name in character_names:
            # For descriptive handles, don't split into individual words
            # (prevents flagging common words like "death", "figure", "masked")
            if is_descriptive_handle(name):
                logger.debug(
                    f"Skipping word-split for descriptive handle: '{name}' "
                    "(would flag common words unnecessarily)"
                )
                continue

            # Split multi-word names and process each word
            words = name.split()

            for word in words:
                word_lower = word.lower()

                # Skip if already processed
                if word_lower in seen_words:
                    continue

                # Skip whitelist
                if word_lower in self.whitelist:
                    continue

                # Skip very short words
                if len(word) < 2:
                    continue

                # Skip common titles
                if word_lower.rstrip(".") in {
                    "mr",
                    "mrs",
                    "ms",
                    "miss",
                    "dr",
                    "sir",
                    "lady",
                    "lord",
                }:
                    continue

                # Skip if in CMU dictionary — narrators already know standard English
                # pronunciations; only flag words that require special guidance.
                if word_lower in self.cmu_known_words:
                    logger.debug(
                        f"Character proposer: skipping '{word}' — found in CMU dictionary"
                    )
                    continue

                seen_words.add(word_lower)

                # Find all occurrences (uses WordIndex if provided)
                mentions = self._find_all_occurrences(
                    full_text, word, chapter_boundaries, case_sensitive=False, word_index=word_index
                )

                if mentions:
                    proposals.append(
                        PronunciationProposal(
                            strategy=self.name,
                            word=word,  # Preserve original capitalization
                            flag_reason=PronunciationFlag.CHARACTER,
                            mentions=mentions,
                            confidence=0.85,  # High confidence - these are known characters
                            reasoning="Character name from extraction pipeline",
                        )
                    )

        logger.info(f"Character proposer found {len(proposals)} character name words")
        return proposals
