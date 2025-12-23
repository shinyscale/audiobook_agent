"""
Foreign language pattern proposer.

Identifies words that appear to be from foreign languages based on patterns.
"""

import re
from typing import Optional
from collections import defaultdict
import logging

from .base import BasePronunciationProposer
from ..models import PronunciationProposal, PronunciationMention, PronunciationFlag

logger = logging.getLogger(__name__)

# Patterns suggesting foreign words
FOREIGN_PATTERNS = {
    'French': [
        r'\b\w*(?:eau|eux|aux|ois|oir|eur|ienne|ette|ique)\b',
        r'\b(?:le|la|les|du|des|un|une|mon|ma|mes|notre|votre)\s+\w+',
        r'\b\w*(?:tion|sion)(?:s)?\b',  # Also common in English but often French origin
    ],
    'German': [
        r'\b\w*(?:burg|berg|stein|mann|schaft|keit|heit|chen|lein)\b',
        r'\b(?:der|die|das|ein|eine)\s+\w+',
        r'\b\w*(?:schlag|fahr|wald|dorf)\b',
    ],
    'Spanish': [
        r'\b\w*(?:ción|ñ|ería|ero|illo|ita|ísimo)\b',
        r'\b(?:el|la|los|las|un|una)\s+[A-Z]\w+',  # Spanish articles before names
    ],
    'Italian': [
        r'\b\w*(?:zione|etto|etta|issimo|ino|ini|ismo)\b',
        r'\b(?:il|lo|la|gli|le)\s+\w+',
    ],
    'Latin': [
        r'\b(?:et|ad|de|ex|per|pro|sub|cum|sine)\s+[a-z]{4,}',
        r'\b\w*(?:ium|ius|orum|arum)\b',
    ],
}

# Words that match patterns but are common English
ENGLISH_EXCEPTIONS = {
    'station', 'nation', 'motion', 'action', 'section', 'mention',
    'question', 'attention', 'position', 'condition', 'addition',
    'education', 'situation', 'information', 'direction', 'election',
    'tradition', 'solution', 'revolution', 'decision', 'television',
    'the', 'a', 'an', 'and', 'or', 'but', 'for', 'to', 'of',
    'mansion', 'passion', 'mission', 'session', 'profession',
    'permission', 'expression', 'impression', 'discussion',
    'unique', 'technique', 'antique', 'boutique', 'critique',
}


class ForeignProposer(BasePronunciationProposer):
    """Proposes words matching foreign language patterns."""

    name = "foreign"

    def __init__(self, min_word_length: int = 4):
        self.min_word_length = min_word_length
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, list[re.Pattern]]:
        """Compile regex patterns for each language."""
        compiled = {}
        for language, patterns in FOREIGN_PATTERNS.items():
            compiled[language] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
    ) -> list[PronunciationProposal]:
        """Find words matching foreign language patterns."""
        # Track found words by language
        word_matches: dict[str, dict[str, list[tuple[int, str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )  # language -> word_lower -> [(position, original, pattern_matched)]

        for language, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(full_text):
                    text = match.group(0)

                    # Skip very short matches
                    if len(text) < self.min_word_length:
                        continue

                    # For multi-word matches (articles), just take the last word
                    words = text.split()
                    if len(words) > 1:
                        word = words[-1]
                        # Adjust position to the last word
                        position = match.start() + text.rfind(word)
                    else:
                        word = text
                        position = match.start()

                    word_lower = word.lower()

                    # Skip English exceptions
                    if word_lower in ENGLISH_EXCEPTIONS:
                        continue

                    word_matches[language][word_lower].append((position, word, pattern.pattern))

        # Build proposals
        proposals = []
        seen_words = set()

        for language, words in word_matches.items():
            for word_lower, occurrences in words.items():
                if word_lower in seen_words:
                    continue
                seen_words.add(word_lower)

                # Build mentions
                mentions = []
                for position, original, _ in occurrences:
                    chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
                    context = self._extract_context(full_text, position, len(original))
                    mentions.append(PronunciationMention(
                        word_form=original,
                        position=position,
                        chapter_index=chapter_idx,
                        context=context,
                    ))

                # Use most common form as canonical
                word_forms = [o[1] for o in occurrences]
                canonical = max(set(word_forms), key=word_forms.count)

                proposals.append(PronunciationProposal(
                    strategy=self.name,
                    word=canonical,
                    flag_reason=PronunciationFlag.FOREIGN,
                    mentions=mentions,
                    confidence=0.7,
                    language_hint=language,
                    reasoning=f"Matches {language} language pattern",
                ))

        logger.info(f"Foreign proposer found {len(proposals)} foreign words")
        return proposals
