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
    "than",
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
    # Common English nicknames (should never need pronunciation guidance for narrators)
    "bill",
    "joe",
    "bob",
    "jim",
    "ned",
    "sam",
    "ben",
    "dave",
    "mike",
    "steve",
    "fred",
    "ted",
    "al",
    "kate",
    "meg",
    "sue",
    "ann",
    "nan",
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
    "magnificence",
    "magnificent",
    "manliness",
    "manly",
    "orderlies",
    "orderly",
    "bravery",
    "cowardice",
    "patriotism",
    "patriotic",
    "kindness",
    "generosity",
    "generously",
    "earnestly",
    "earnestness",
    "eagerness",
    "eagerly",
    "steadily",
    "steadiness",
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
    # Common informal / compound words with self-evident pronunciation
    # (narrator would not need guidance to pronounce these)
    "thickset",       # compound adj: thick + set (obvious pronunciation)
    "greenhorns",     # common informal: plural of greenhorn (obvious pronunciation)
    "whippersnapper", # common informal: compound (obvious pronunciation)
    "johnny",         # standard English nickname (same as "john" — always whitelisted)
    "johnnie",        # alternate spelling of the same nickname
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

        # Common starting words that appear in OCR artifacts (missing space after short word)
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
            "me",
            "my",
            "if",
            "he",
            "she",
            "her",
            "his",
            "him",
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

        # Check if word ends with a common short function word (missing space before it)
        # E.g., "Nimdokwith" = "Nimdok" + "with"
        common_suffixes = ["with", "from", "into", "upon", "over", "then", "when", "that"]
        for suffix in common_suffixes:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 3:
                prefix = word_lower[: -len(suffix)]
                # If prefix itself is NOT a known word, this is likely a name+word concatenation
                if prefix not in self.known_words and len(prefix) >= 3:
                    logger.debug(
                        f"Detected OCR artifact: '{word}' = '{prefix}' + '{suffix}'"
                    )
                    return True

        return False

    # Regex to detect URL-like patterns surrounding a word.
    # Matches: scheme://, www., .tld extensions, and path-separators /
    _URL_CONTEXT_PAT = re.compile(
        r'(?:https?://|www\.|\.[a-z]{2,6}(?:/|\s|$)|/[a-zA-Z])',
        re.IGNORECASE,
    )

    def _is_url_context(self, text: str, pos: int, word_len: int) -> bool:
        """Return True if the word at text[pos:pos+word_len] appears inside a URL.

        Checks a window around the token for URL indicators (scheme, TLD, path
        separators). Tokens in URLs are never useful pronunciation entries.
        """
        window_start = max(0, pos - 30)
        window_end = min(len(text), pos + word_len + 30)
        window = text[window_start:window_end]
        return bool(self._URL_CONTEXT_PAT.search(window))

    def _is_common_derivation(self, word: str) -> bool:
        """
        Check if word is a regular derivation of a known word.

        Returns True if the word is formed by adding common suffixes to a word
        that IS in the CMU dictionary, making it a predictable pronunciation.

        Examples:
        - "jingled" → "jingle" + "ed" (if "jingle" is in CMU, "jingled" is common)
        - "familiarly" → "familiar" + "ly" (if "familiar" is in CMU, "familiarly" is common)
        - "recoiling" → "recoil" + "ing" (if "recoil" is in CMU, "recoiling" is common)
        - "unsheathing" → strip "un" → "sheathing" (if in CMU, common)
        - "reapproached" → strip "re" → "approached" (if in CMU, common)
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
            "less",   # thriftless (thrift), useless (use), harmless (harm), hopeless (hope)
            "ful",    # slothful (sloth), truthful (truth), hopeful (hope)
            # Noun suffixes
            "ness",   # happiness, sadness
            "ment",   # enjoyment, improvement
            "tion",   # creation, deletion (but check -ion separately)
            "ion",    # connection, revision
        ]

        def _check_suffix_on(base_word: str) -> bool:
            """Check if base_word with common suffixes stripped is in CMU."""
            if base_word in self.known_words:
                return True
            for suffix in suffixes:
                if base_word.endswith(suffix):
                    base = base_word[:-len(suffix)]
                    if len(base) < 3:
                        continue
                    if base in self.known_words:
                        return True
                    if len(base) >= 2 and base[-1] == base[-2]:
                        if base[:-1] in self.known_words:
                            return True
                    if suffix == "ily" and (base + "y") in self.known_words:
                        return True
                    if suffix in ("ness", "ed", "er", "est") and (base + "y") in self.known_words:
                        return True
                    if suffix in ("ing", "ed", "er", "est", "y") and (base + "e") in self.known_words:
                        return True
            return False

        # First, check suffix stripping on the full word
        if _check_suffix_on(word_lower):
            return True

        # Also try stripping common derivational prefixes before checking suffixes.
        # This catches words like "unsheathing" (un + sheathing) and "reapproached" (re + approached).
        common_prefixes = ["un", "re", "dis", "in", "im", "pre", "out", "mis", "over", "under"]
        for prefix in common_prefixes:
            if word_lower.startswith(prefix) and len(word_lower) > len(prefix) + 3:
                remainder = word_lower[len(prefix):]
                if _check_suffix_on(remainder):
                    return True
                # Also try British-to-American spelling on the remainder
                for brit, amer in [("ising", "izing"), ("ised", "ized"), ("ise", "ize")]:
                    if remainder.endswith(brit):
                        american_remainder = remainder[:-len(brit)] + amer
                        if american_remainder in self.known_words or _check_suffix_on(american_remainder):
                            return True

        # British -ise/-ised/-ising spellings: check if the American -ize/-ized/-izing
        # form is in CMU. These are standard British English variants, not foreign words.
        # e.g., "sympathise" → "sympathize", "sympathised" → "sympathized"
        for brit_suffix, amer_suffix in [("ising", "izing"), ("ised", "ized"), ("ise", "ize")]:
            if word_lower.endswith(brit_suffix):
                american_form = word_lower[:-len(brit_suffix)] + amer_suffix
                if american_form in self.known_words:
                    return True

        return False

    def _is_closed_compound(self, word: str) -> bool:
        """Return True if word is a predictable closed compound of two CMU words.

        Closed compounds like "firelight" (fire+light), "tinfoil" (tin+foil), and
        "deckplates" (deck+plates) are fully predictable from their components —
        a narrator who can say each part needs no extra guidance for the combination.

        Universal invariant: when every component of a concatenated word appears
        independently in the CMU dictionary the combined pronunciation is unambiguous.
        """
        word_lower = word.lower()
        if len(word_lower) < 6:
            return False
        for split in range(3, len(word_lower) - 2):
            left = word_lower[:split]
            right = word_lower[split:]
            if len(left) < 3 or len(right) < 3:
                continue
            if left not in self.known_words:
                continue
            # Right part: try direct match, or strip common plural 's'
            if right in self.known_words:
                return True
            if right.endswith("s") and len(right) > 3 and right[:-1] in self.known_words:
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

            # Skip common derivations (e.g., "jingled" if "jingle" is in CMU)
            if self._is_common_derivation(word_lower):
                continue

            # Skip closed compounds whose every part is in CMU (e.g., "firelight", "tinfoil")
            if self._is_closed_compound(word_lower):
                continue

            # Skip OCR artifacts (missing spaces between words)
            if self._is_ocr_artifact(word):
                continue

            # Skip tokens that appear inside a URL (e.g. "hermiene" from "hermiene.net")
            if self._is_url_context(full_text, match.start(), len(word)):
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
            if self._is_common_derivation(word):
                return False
            if self._is_closed_compound(word):
                return False
            if self._is_ocr_artifact(word):
                return False
            # Hyphenated compounds: "tight-fitting" → ["tight", "fitting"]
            # If ALL parts are in CMU, the pronunciation is predictable from the parts.
            if "-" in word:
                parts = word.split("-")
                if all(p.lower() in self.known_words for p in parts if len(p) >= 2):
                    return False
            # Possessives: "cough's" → base "cough" in CMU
            if word.endswith("'s") and word[:-2].lower() in self.known_words:
                return False
            # Possessives of unknown words (e.g., "Gorrister's"): narrator can infer
            # pronunciation from the base form, which will appear as its own entry.
            if word.endswith("'s") and len(word) > 4:
                return False
            # Contraction-concatenation artifacts (e.g., "we'lldie" = "we'll" + "die"):
            # The pre-apostrophe fragment is a common pronoun/auxiliary.
            if "'" in word and not word.endswith("'s"):
                apostrophe_idx = word.index("'")
                pre = word[:apostrophe_idx].lower()
                if pre in {
                    "we", "it", "i", "you", "they", "he", "she",
                    "do", "can", "let", "might", "must", "have", "has", "had",
                    "would", "should", "could", "will", "shall",
                }:
                    return False
            return True

        # Filter all words through predicate - O(n) where n is unique words
        unknown_words = word_index.filter_by_predicate(is_unknown)

        proposals = []
        for word_lower, occurrences in unknown_words.items():
            if len(occurrences) < self.min_occurrences:
                continue

            # Build mentions from occurrences, skipping URL-context tokens
            mentions = []
            for occ in occurrences:
                if self._is_url_context(full_text, occ.position, len(occ.original_form)):
                    continue
                context = self._extract_context(full_text, occ.position, len(occ.original_form))
                mentions.append(
                    PronunciationMention(
                        word_form=occ.original_form,
                        position=occ.position,
                        chapter_index=occ.chapter_index,
                        context=context,
                    )
                )

            # Skip word if all occurrences were in URL contexts
            if not mentions:
                continue

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
