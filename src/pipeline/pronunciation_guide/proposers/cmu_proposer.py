"""
CMU Dictionary-based pronunciation proposer.

Identifies words not found in the CMU Pronouncing Dictionary.
"""

import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, Set

from ..models import PronunciationFlag, PronunciationMention, PronunciationProposal
from .base import BasePronunciationProposer

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)

# Common words to never flag
COMMON_WORDS_WHITELIST = {
    # Common articles, determiners, and prepositions (should never be flagged)
    "the",
    "a",
    "an",
    "of",
    "at",
    "in",
    "on",
    "to",
    "for",
    "by",
    "near",
    "under",
    "over",
    "between",
    "among",
    "through",
    "during",
    "without",
    "within",
    "against",
    "toward",
    "towards",
    "around",
    "beside",
    "besides",
    "beyond",
    "across",
    # Common conjunctions
    "and",
    "or",
    "but",
    "nor",
    "so",
    "yet",
    "if",
    "though",
    "although",
    "because",
    "since",
    "unless",
    "while",
    "whereas",
    # Common verbs (forms of "be", "have", etc.)
    "was",
    "were",
    "is",
    "are",
    "be",
    "been",
    "being",
    "has",
    "have",
    "had",
    "having",
    "do",
    "does",
    "did",
    "done",
    "doing",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    # Common adjectives and descriptive words that appear in character epithets
    "present",
    "absent",
    "dead",
    "living",
    "former",
    "current",
    "previous",
    "next",
    "last",
    "first",
    "second",
    "third",
    "other",
    "another",
    "same",
    "different",
    "certain",
    "main",
    "chief",
    "principal",
    # Common names
    "michael",
    "james",
    "william",
    "david",
    "richard",
    "joseph",
    "thomas",
    "mary",
    "patricia",
    "jennifer",
    "linda",
    "elizabeth",
    "barbara",
    "susan",
    "john",
    "robert",
    "charles",
    "daniel",
    "matthew",
    "anthony",
    "mark",
    "sarah",
    "jessica",
    "emily",
    "ashley",
    "amanda",
    "melissa",
    "stephanie",
    "tom",
    "daisy",
    "nick",
    "jordan",
    "george",
    "catherine",
    "dan",
    "jay",
    "peter",
    "paul",
    "andrew",
    "christopher",
    "kenneth",
    "edward",
    "brian",
    "anna",
    "maria",
    "nancy",
    "lisa",
    "karen",
    "betty",
    "helen",
    "sandra",
    # Common places
    "london",
    "paris",
    "york",
    "boston",
    "chicago",
    "angeles",
    "francisco",
    "washington",
    "america",
    "england",
    "france",
    "germany",
    "italy",
    "spain",
    # Common direction/location words
    "north",
    "south",
    "east",
    "west",
    "island",
    "bay",
    "river",
    "sea",
    "beach",
    "shore",
    "coast",
    "port",
    # Common titles
    "chapter",
    "prologue",
    "epilogue",
    "part",
    "section",
    "book",
    "volume",
    # Days/months
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    # Common descriptive words (often appear in character epithets)
    "old",
    "young",
    "new",
    "little",
    "big",
    "great",
    "small",
    "man",
    "woman",
    "boy",
    "girl",
    "child",
    "baby",
    "person",
    "people",
    "family",
    "families",
    "member",
    "members",
    "father",
    "mother",
    "son",
    "daughter",
    "brother",
    "sister",
    "uncle",
    "aunt",
    "husband",
    "wife",
    "friend",
    "stranger",
    "gentleman",
    "lady",
    "maid",
    "from",
    "with",
    "about",
    "into",
    "upon",
    "after",
    "before",
    "on",
    "off",
    # Common nouns that shouldn't be flagged
    "egg",
    "war",
    "peace",
    "love",
    "hope",
    "faith",
    "truth",
    "justice",
    "house",
    "home",
    "door",
    "window",
    "room",
    "wall",
    "floor",
    "table",
    "chair",
    "bed",
    "garden",
    "street",
    "road",
    "car",
    "train",
    "boat",
    "taxi",
    "cottage",
    "town",
    "village",
    "brought",
    "natural",
    "water",
    "fire",
    "light",
    "night",
    "day",
    "time",
    "place",
    "world",
    "storm",
    "rain",
    "snow",
    "wind",
    "sun",
    "moon",
    "star",
    "stars",
    "cloud",
    "clouds",
    "sky",
    "money",
    "gold",
    "silver",
    "diamond",
    "ring",
    "dress",
    "dresses",
    "shirt",
    "coat",
    "hat",
    "shoe",
    "shoes",
    "book",
    "letter",
    "paper",
    "pen",
    "duster",
    "food",
    "bread",
    "wine",
    "beer",
    "tea",
    "coffee",
    "meat",
    "fish",
    "tree",
    "flower",
    "grass",
    "stone",
    "wood",
    "metal",
    "glass",
    "cloth",
    "city",
    "grocery",
    "habit",
    "other",
    "elevator",
    "gardener",
    "clan",
    "step",
    "steps",
    "wrote",
    # Common colors
    "red",
    "blue",
    "green",
    "yellow",
    "white",
    "black",
    "brown",
    "grey",
    "gray",
    "pink",
    "purple",
    "orange",
    "silver",
    "gold",
    # Common descriptive adjectives
    "pale",
    "dark",
    "bright",
    "dim",
    "loud",
    "quiet",
    "soft",
    "hard",
    "heavy",
    "light",
    "warm",
    "cold",
    "hot",
    "cool",
    "wet",
    "dry",
    "clean",
    "dirty",
    "rich",
    "poor",
    "happy",
    "sad",
    "angry",
    "afraid",
    "brave",
    "kind",
    "cruel",
    "long",
    "short",
    "tall",
    "sober",
    # Common professions and roles
    "doctor",
    "nurse",
    "teacher",
    "student",
    "lawyer",
    "judge",
    "king",
    "queen",
    "prince",
    "princess",
    "lord",
    "duke",
    "count",
    "baron",
    "knight",
    "sir",
    "captain",
    "soldier",
    "sailor",
    "pilot",
    "driver",
    "waiter",
    "cook",
    "chef",
    "butler",
    "servant",
    "servants",
    "maid",
    "maids",
    "slave",
    "master",
    "mistress",
    "clerk",
    "merchant",
    "farmer",
    "worker",
    "miner",
    "sailor",
    "fisherman",
    "policeman",
    "police",
    "officer",
    "detective",
    "guard",
    "watchman",
    "leader",
    "veteran",
    "witness",
    "reporter",
    "minister",
    "chorus",
    "riding",
    # Common pronouns and prepositions that appear in descriptive names
    "who",
    "whom",
    "whose",
    "which",
    "that",
    "their",
    "theirs",
    "them",
    "his",
    "her",
    "hers",
    "its",
    "our",
    "ours",
    "your",
    "yours",
    # Common body parts and descriptive terms
    "eyes",
    "eye",
    "face",
    "hand",
    "hands",
    "hair",
    "head",
    "voice",
    "mouth",
    "nose",
    "ear",
    "ears",
    "arm",
    "arms",
    "leg",
    "legs",
    "foot",
    "feet",
    "heart",
    "mind",
    "soul",
    "spirit",
    "body",
    "blood",
    "bone",
    "skin",
    "teeth",
    "tooth",
    # Common numbers and quantifiers (appearing in descriptive names)
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "first",
    "second",
    "third",
    "many",
    "several",
    "few",
    "some",
    "all",
    "both",
    # Common plural forms of descriptive words
    "men",
    "women",
    "boys",
    "girls",
    "children",
    "babies",
    "people",
    "husbands",
    "wives",
    "friends",
    "strangers",
    "gentlemen",
    "ladies",
}

# Contraction fragments that result from tokenization
CONTRACTION_FRAGMENTS = {
    "hadn",
    "wouldn",
    "couldn",
    "shouldn",
    "didn",
    "isn",
    "aren",
    "wasn",
    "weren",
    "don",
    "doesn",
    "won",
    "can",
    "mustn",
    "needn",
    "shan",
    "mightn",
    "hasn",
    "haven",
    "ain",
    "oughtn",
    "ll",
    "ve",
    "re",
    "em",
    "twas",
    "tis",
    "s",
    "t",
    "d",
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

    def _is_ocr_artifact(self, word: str) -> bool:
        """
        Detect OCR artifacts (missing spaces between words).

        Examples: "wehad" (we had), "ithad" (it had), "tothe" (to the)

        Strategy: Check if the word looks like a concatenation of common English words.
        Common patterns:
        - Starts with common short word (we, it, to, no, us, as, be, is, or, of, at, in, on, for)
        - Followed by another lowercase word
        """
        word_lower = word.lower()

        # Common starting words that appear in OCR artifacts
        common_prefixes = [
            "we",
            "it",
            "to",
            "no",
            "us",
            "as",
            "be",
            "is",
            "or",
            "of",
            "at",
            "in",
            "on",
            "for",
            "the",
            "and",
            "but",
            "not",
            "all",
        ]

        # Check if word starts with a common prefix and has lowercase continuation
        for prefix in common_prefixes:
            if len(word_lower) > len(prefix) and word_lower.startswith(prefix):
                remainder = word_lower[len(prefix) :]
                # Check if remainder starts with lowercase (indicates missing space)
                if remainder and remainder[0].islower() and len(remainder) >= 2:
                    # Extra check: remainder should also be in known words or common
                    if remainder in self.known_words or remainder in COMMON_WORDS_WHITELIST:
                        logger.debug(
                            f"Detected OCR artifact: '{word}' = '{prefix}' + '{remainder}'"
                        )
                        return True

        return False

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
        word_data: dict[str, list[tuple[int, str]]] = defaultdict(
            list
        )  # word_lower -> [(position, original)]

        for match in re.finditer(r"\b([a-zA-Z]+)\b", full_text):
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

            # Skip OCR artifacts (missing spaces between words)
            if self._is_ocr_artifact(word):
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
                mentions.append(
                    PronunciationMention(
                        word_form=original,
                        position=position,
                        chapter_index=chapter_idx,
                        context=context,
                    )
                )

            # Use most common capitalization as canonical
            word_forms = [o[1] for o in occurrences]
            canonical = max(set(word_forms), key=word_forms.count)

            proposals.append(
                PronunciationProposal(
                    strategy=self.name,
                    word=canonical,
                    flag_reason=PronunciationFlag.UNKNOWN,
                    mentions=mentions,
                    confidence=0.6,
                    reasoning="Not found in CMU pronunciation dictionary",
                )
            )

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
            if self._is_ocr_artifact(word):
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
                mentions.append(
                    PronunciationMention(
                        word_form=occ.original_form,
                        position=occ.position,
                        chapter_index=occ.chapter_index,
                        context=context,
                    )
                )

            # Use most common capitalization as canonical
            word_forms = [occ.original_form for occ in occurrences]
            canonical = max(set(word_forms), key=word_forms.count)

            proposals.append(
                PronunciationProposal(
                    strategy=self.name,
                    word=canonical,
                    flag_reason=PronunciationFlag.UNKNOWN,
                    mentions=mentions,
                    confidence=0.6,
                    reasoning="Not found in CMU pronunciation dictionary",
                )
            )

        logger.info(f"CMU proposer found {len(proposals)} unknown words (via WordIndex)")
        return proposals
