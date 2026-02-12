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
    "belief",
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
    "sideboard",
    "mantelpiece",
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
    # Common literary/rhetorical terms
    "metaphor",
    "simile",
    "analogy",
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
    # Common vocabulary words (standard English, not unusual)
    "menial",
    "partook",
    "wretchedness",
    "ecstasies",
    "awaking",
    "loitered",
    "commonest",
    "trembling",
    "frivolity",
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
    # Reflexive pronouns (for OCR artifact detection)
    "myself",
    "yourself",
    "himself",
    "herself",
    "itself",
    "ourselves",
    "yourselves",
    "themselves",
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
    # Common English words that may not be in CMU (fix for false positive flagging)
    # NOTE: This deny-list approach is temporary - should be replaced with frequency-based
    # filtering (e.g., wordfreq library) to avoid endless list expansion.
    "away",
    "dauntless",
    "magnificence",
    "giddiest",
    "moveable",
    "convulsed",
    "unutterable",
    "decorum",
    # Additional common words flagged in berenice analysis (attempt 1)
    "sentiments",
    "refracted",
    "sentient",
    "conformation",
    "tarried",
    "emaciation",
    "multiform",
    "aslant",
    # Additional common words flagged in monkeys_paw analysis (attempt 2)
    "sightless",
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

        Examples: "wehad" (we had), "ithad" (it had), "tothe" (to the), "himselffelt" (himself felt),
                  "himselfin" (himself in), "beliefin" (belief in)

        Strategy: Check if the word looks like a concatenation of known English words.
        Key constraint: At least one part must be a COMMON word (in whitelist) to avoid
        false positives like "flambeaux" = "flam" + "beaux" (both obscure but in CMU).
        """
        word_lower = word.lower()

        # Strategy: Try splitting at different positions
        # For "himselffelt" (11 chars), try splits at positions 3-8
        min_part_length = 2  # Reduced from 3 to catch "in" (2 chars)
        max_split_pos = len(word_lower) - min_part_length

        for split_pos in range(min_part_length, max_split_pos + 1):
            prefix = word_lower[:split_pos]
            remainder = word_lower[split_pos:]

            # Check if parts are known
            prefix_common = prefix in COMMON_WORDS_WHITELIST
            remainder_common = remainder in COMMON_WORDS_WHITELIST
            prefix_known = prefix in self.known_words
            remainder_known = remainder in self.known_words

            # A word is a valid known word if it's either:
            # - In the CMU dictionary, OR
            # - In the common words whitelist (which includes stopwords not in CMU)
            prefix_valid = prefix_known or prefix_common
            remainder_valid = remainder_known or remainder_common

            # OCR artifacts typically involve at least one COMMON word
            # AND both parts must be valid English words (in CMU or whitelist)
            # This prevents false positives like "flambeaux" = "flam" + "beaux"
            if (prefix_common or remainder_common) and (prefix_valid and remainder_valid):
                logger.debug(
                    f"Detected OCR artifact: '{word}' = '{prefix}' + '{remainder}'"
                )
                return True

        return False

    def _is_common_derivation(self, word: str) -> bool:
        """
        Check if word is a regular derivation of a known word.

        Returns True if the word is formed by adding common suffixes to a word
        that IS in the CMU dictionary, making it a predictable pronunciation.

        Examples:
        - "jingled" → "jingle" + "ed" (if "jingle" is in CMU, "jingled" is common)
        - "familiarly" → "familiar" + "ly" (if "familiar" is in CMU, "familiarly" is common)
        - "recoiling" → "recoil" + "ing" (if "recoil" is in CMU, "recoiling" is common)
        """
        word_lower = word.lower()

        # Common English suffixes in order of priority (try longer suffixes first)
        suffixes = [
            # Adverb suffixes
            "ingly",  # lovingly, increasingly
            "edly",   # reportedly, allegedly
            "ily",    # happily, unsteadily (special: remove -ily, add -y)
            "ly",     # familiarly, insufferably
            # Verb suffixes
            "ing",    # jingling, recoiling
            "ed",     # jingled, recoiled
            "s",      # jingles, recoils
            # Adjective suffixes
            "iest",   # happiest, funniest
            "ier",    # happier, funnier
            "est",    # fastest, tallest
            "er",     # faster, taller
            "y",      # filmy, cloudy
            # Noun suffixes
            "ness",   # happiness, sadness
            "ment",   # enjoyment, improvement
            "tion",   # creation, deletion (but check -ion separately)
            "ion",    # connection, revision
        ]

        for suffix in suffixes:
            if word_lower.endswith(suffix):
                # Try removing the suffix
                base = word_lower[:-len(suffix)]

                # Skip if base is too short (likely not a real word)
                if len(base) < 3:
                    continue

                # Check if base word is in CMU dictionary
                if base in self.known_words:
                    return True

                # Handle consonant doubling (e.g., "running" → "run" + "n" + "ing")
                if len(base) >= 2 and base[-1] == base[-2]:
                    base_undoubled = base[:-1]
                    if base_undoubled in self.known_words:
                        return True

                # Handle -ily suffix (e.g., "happily" → "happy", "unsteadily" → "unsteady")
                if suffix == "ily":
                    base_y = base + "y"
                    if base_y in self.known_words:
                        return True

                # Handle y→i transformations (e.g., "happiness" from "happy")
                if suffix in ("ness", "ed", "er", "est"):
                    base_y = base + "y"
                    if base_y in self.known_words:
                        return True

                # Handle e-dropping (e.g., "filing" → "file" + "ing")
                if suffix in ("ing", "ed", "er", "est", "y"):
                    base_e = base + "e"
                    if base_e in self.known_words:
                        return True

        return False

    def _is_obvious_compound(self, word: str) -> bool:
        """
        Check if word is an obvious compound/derivation with clear pronunciation.

        Universal patterns (not word-specific):
        - Hyphenated compounds where both parts are known (e.g., "web-work", "tight-fitting")
        - Archaic hyphenated spellings (e.g., "to-day" = "today")
        - Standard prefix + known root (e.g., "re-echoed", "unsheathing")
        - Common non-hyphenated compounds (e.g., "inmost" = "in" + "most")

        Returns True if pronunciation is obvious and doesn't need guidance.
        """
        word_lower = word.lower()

        # Pattern 1: Hyphenated compounds (e.g., "web-work", "tight-fitting", "to-day")
        if '-' in word_lower:
            parts = word_lower.split('-')
            # If all parts are in CMU dictionary, pronunciation is obvious
            if all(part in self.known_words or part in COMMON_WORDS_WHITELIST for part in parts):
                return True

        # Pattern 2: Standard prefixes + known root
        # re-/un-/pre-/mis-/dis-/over-/under- are transparent prefixes
        transparent_prefixes = ['re', 'un', 'pre', 'mis', 'dis', 'over', 'under', 'non']
        for prefix in transparent_prefixes:
            if word_lower.startswith(prefix) and len(word_lower) > len(prefix):
                root = word_lower[len(prefix):]
                # If root is known, the prefixed form is obvious
                if root in self.known_words:
                    return True

        # Pattern 3: Common non-hyphenated compounds (e.g., "inmost", "outermost", "innermost")
        # These are formed from common preposition/adverb + common word
        common_compound_patterns = [
            ('in', 'most'),      # inmost
            ('out', 'most'),     # outmost
            ('outer', 'most'),   # outermost
            ('inner', 'most'),   # innermost
            ('up', 'most'),      # upmost
            ('fore', 'most'),    # foremost
            ('after', 'most'),   # aftermost
        ]
        for prefix, suffix in common_compound_patterns:
            if word_lower == prefix + suffix:
                return True

        return False

    def _is_possessive_of_known_word(self, word: str) -> bool:
        """
        Check if word is a possessive form of a word in the CMU dictionary.

        Examples: "cough's" → "cough" is in CMU, so filter this out

        Returns True if this is a possessive of a known word.
        """
        word_lower = word.lower()

        # Check for possessive marker
        if word_lower.endswith("'s"):
            base = word_lower[:-2]
            if base in self.known_words or base in COMMON_WORDS_WHITELIST:
                return True

        return False

    def _is_common_monosyllabic_word(self, word: str) -> bool:
        """
        Check if word is a common monosyllabic word that's obviously known.

        Even if not in CMU, words like "leer" are standard English and don't need
        pronunciation guidance.

        Heuristic: Short words (3-4 chars) with common English phonetic patterns.
        """
        word_lower = word.lower()

        # Only apply to short words (3-4 characters)
        if len(word_lower) < 3 or len(word_lower) > 4:
            return False

        # Common monosyllabic words not in CMU but obviously known
        common_short_words = {
            'leer',   # to look with an unpleasant expression
            'veer',   # to change direction
            'seer',   # one who sees/predicts
            'ague',   # fever/chill
            'woe',    # sorrow
        }

        return word_lower in common_short_words

    def _filter_redundant_variants(self, proposals: list[PronunciationProposal]) -> list[PronunciationProposal]:
        """
        Remove redundant plurals and possessives of already-flagged words.

        Example: If "Montresor" is flagged, remove "Montresors" (plural).

        Returns filtered list of proposals.
        """
        # Build set of base words (lowercased)
        base_words = {p.word.lower() for p in proposals}

        filtered = []
        for proposal in proposals:
            word_lower = proposal.word.lower()

            # Check if this is a redundant variant
            is_redundant = False

            # Check for plural (ending in 's')
            if word_lower.endswith('s') and len(word_lower) > 1:
                base = word_lower[:-1]
                if base in base_words:
                    logger.debug(f"Filtering redundant plural: '{proposal.word}' (base: '{base}')")
                    is_redundant = True

            # Check for possessive (ending in 's or ')
            if word_lower.endswith("'s"):
                base = word_lower[:-2]
                if base in base_words:
                    logger.debug(f"Filtering redundant possessive: '{proposal.word}' (base: '{base}')")
                    is_redundant = True

            if not is_redundant:
                filtered.append(proposal)

        if len(filtered) < len(proposals):
            logger.info(f"Filtered {len(proposals) - len(filtered)} redundant variants")

        return filtered

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

            # Skip common derivations (e.g., "jingled" if "jingle" is in CMU)
            if self._is_common_derivation(word_lower):
                continue

            # Skip OCR artifacts (missing spaces between words)
            if self._is_ocr_artifact(word):
                continue

            # Skip obvious compounds (hyphenated, prefixed forms with known roots)
            if self._is_obvious_compound(word):
                continue

            # Skip possessives of known words (e.g., "cough's" when "cough" is in CMU)
            if self._is_possessive_of_known_word(word):
                continue

            # Skip common monosyllabic words obviously known (e.g., "leer")
            if self._is_common_monosyllabic_word(word):
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

        # Post-processing: Remove redundant plurals/possessives of already-flagged words
        proposals = self._filter_redundant_variants(proposals)

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
            if self._is_common_derivation(word):
                return False
            if self._is_ocr_artifact(word):
                return False
            if self._is_obvious_compound(word):
                return False
            if self._is_possessive_of_known_word(word):
                return False
            if self._is_common_monosyllabic_word(word):
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

        # Post-processing: Remove redundant plurals/possessives of already-flagged words
        proposals = self._filter_redundant_variants(proposals)

        logger.info(f"CMU proposer found {len(proposals)} unknown words (via WordIndex)")
        return proposals
