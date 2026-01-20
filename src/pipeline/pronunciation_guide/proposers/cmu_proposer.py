"""
CMU Dictionary-based pronunciation proposer.

Identifies words not found in the CMU Pronouncing Dictionary.
"""

import re
from typing import Optional, Set, TYPE_CHECKING
from collections import defaultdict
import logging

from .base import BasePronunciationProposer
from ..models import PronunciationProposal, PronunciationMention, PronunciationFlag

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)

# Common words to never flag
COMMON_WORDS_WHITELIST = {
    # Common articles and determiners (should never be flagged)
    'the', 'a', 'an',
    # Common names
    'michael', 'james', 'william', 'david', 'richard', 'joseph', 'thomas',
    'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
    'john', 'robert', 'charles', 'daniel', 'matthew', 'anthony', 'mark',
    'sarah', 'jessica', 'emily', 'ashley', 'amanda', 'melissa', 'stephanie',
    # Common places
    'london', 'paris', 'york', 'boston', 'chicago', 'angeles', 'francisco',
    'washington', 'america', 'england', 'france', 'germany', 'italy', 'spain',
    # Common titles
    'chapter', 'prologue', 'epilogue', 'part', 'section', 'book', 'volume',
    # Days/months
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    # Common descriptive words (often appear in character epithets)
    'old', 'young', 'new', 'little', 'big', 'great', 'small',
    'man', 'woman', 'boy', 'girl', 'child', 'baby', 'person', 'people',
    'father', 'mother', 'son', 'daughter', 'brother', 'sister', 'uncle', 'aunt',
    'husband', 'wife', 'friend', 'stranger', 'gentleman', 'lady', 'maid',
    'from', 'with', 'about', 'into', 'upon', 'after', 'before',
}

# Contraction fragments that result from tokenization
CONTRACTION_FRAGMENTS = {
    "hadn", "wouldn", "couldn", "shouldn", "didn", "isn", "aren",
    "wasn", "weren", "don", "doesn", "won", "can", "mustn",
    "needn", "shan", "mightn", "hasn", "haven", "ain", "oughtn",
    "ll", "ve", "re", "em", "twas", "tis", "s", "t", "d",
}


class CMUProposer(BasePronunciationProposer):
    """Proposes words not found in CMU pronunciation dictionary."""

    name = "cmu"

    def __init__(
        self,
        min_word_length: int = 4,
        min_occurrences: int = 1,
    ):
        """
        Args:
            min_word_length: Minimum word length to consider
            min_occurrences: Minimum occurrences to flag
        """
        self.min_word_length = min_word_length
        self.min_occurrences = min_occurrences
        self.known_words = self._load_cmu_dict()

    def _load_cmu_dict(self) -> Set[str]:
        """Load words from CMU dictionary via pronouncing library."""
        try:
            import pronouncing
            words = set(pronouncing.cmudict.dict().keys())
            logger.debug(f"Loaded {len(words)} words from CMU dictionary")
            return words
        except ImportError:
            logger.warning("pronouncing library not available, CMU proposer disabled")
            return set()

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        """Find words not in CMU dictionary.

        Uses WordIndex if available for O(1) filtering, otherwise falls back
        to full text scanning.
        """
        if not self.known_words:
            return []

        # Use WordIndex if available (O(1) filtering)
        if word_index is not None:
            return self._propose_from_index(word_index, full_text, chapter_boundaries)

        # Fallback: Extract all words and their positions
        word_data: dict[str, list[tuple[int, str]]] = defaultdict(list)  # word_lower -> [(position, original)]

        for match in re.finditer(r'\b([a-zA-Z]+)\b', full_text):
            word = match.group(1)
            word_lower = word.lower()

            # Skip short words
            if len(word_lower) < self.min_word_length:
                continue

            # Skip whitelist
            if word_lower in COMMON_WORDS_WHITELIST:
                continue

            # Skip contraction fragments
            if word_lower in CONTRACTION_FRAGMENTS:
                continue

            # Skip if in CMU dictionary
            if word_lower in self.known_words:
                continue

            word_data[word_lower].append((match.start(), word))

        # Filter by occurrence count and build proposals
        proposals = []
        for word_lower, occurrences in word_data.items():
            if len(occurrences) < self.min_occurrences:
                continue

            # Build mentions
            mentions = []
            for position, original in occurrences:
                chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
                context = self._extract_context(full_text, position, len(original))
                mentions.append(PronunciationMention(
                    word_form=original,
                    position=position,
                    chapter_index=chapter_idx,
                    context=context,
                ))

            # Use most common capitalization as canonical
            word_forms = [o[1] for o in occurrences]
            canonical = max(set(word_forms), key=word_forms.count)

            proposals.append(PronunciationProposal(
                strategy=self.name,
                word=canonical,
                flag_reason=PronunciationFlag.UNKNOWN,
                mentions=mentions,
                confidence=0.6,
                reasoning="Not found in CMU pronunciation dictionary",
            ))

        logger.info(f"CMU proposer found {len(proposals)} unknown words")
        return proposals

    def _propose_from_index(
        self,
        word_index: "WordIndex",
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
    ) -> list[PronunciationProposal]:
        """Use WordIndex for efficient filtering of unknown words."""
        def is_unknown(word: str) -> bool:
            """Check if word is unknown to CMU dictionary."""
            if len(word) < self.min_word_length:
                return False
            if word in COMMON_WORDS_WHITELIST:
                return False
            if word in CONTRACTION_FRAGMENTS:
                return False
            if word in self.known_words:
                return False
            return True

        # Filter all words through predicate - O(n) where n is unique words
        unknown_words = word_index.filter_by_predicate(is_unknown)

        proposals = []
        for word_lower, occurrences in unknown_words.items():
            if len(occurrences) < self.min_occurrences:
                continue

            # Build mentions from occurrences
            mentions = []
            for occ in occurrences:
                context = self._extract_context(full_text, occ.position, len(occ.original_form))
                mentions.append(PronunciationMention(
                    word_form=occ.original_form,
                    position=occ.position,
                    chapter_index=occ.chapter_index,
                    context=context,
                ))

            # Use most common capitalization as canonical
            word_forms = [occ.original_form for occ in occurrences]
            canonical = max(set(word_forms), key=word_forms.count)

            proposals.append(PronunciationProposal(
                strategy=self.name,
                word=canonical,
                flag_reason=PronunciationFlag.UNKNOWN,
                mentions=mentions,
                confidence=0.6,
                reasoning="Not found in CMU pronunciation dictionary",
            ))

        logger.info(f"CMU proposer found {len(proposals)} unknown words (via WordIndex)")
        return proposals
