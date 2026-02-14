"""
Foreign language pattern proposer.

Identifies words that appear to be from foreign languages based on patterns.
"""

import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

from ..models import PronunciationFlag, PronunciationMention, PronunciationProposal
from .base import BasePronunciationProposer
from .cmu_proposer import COMMON_WORDS_WHITELIST

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)

# Patterns suggesting foreign words
FOREIGN_PATTERNS = {
    "French": [
        r"\b\w*(?:eau|eux|aux|ois|oir|eur|ienne|ette|ique)\b",
        r"\b(?:le|la|les|du|des|un|une|mon|ma|mes|notre|votre)\s+\w+",
        # Note: -tion/-sion pattern removed - too noisy, flags common English words
    ],
    "German": [
        r"\b\w*(?:burg|berg|stein|mann|schaft|keit|heit|chen|lein)\b",
        r"\b(?:der|die|das|ein|eine)\s+\w+",
        r"\b\w*(?:schlag|fahr|wald|dorf)\b",
    ],
    "Spanish": [
        r"\b\w*(?:ción|ñ|ería|ero|illo|ita|ísimo)\b",
        r"\b(?:el|la|los|las|un|una)\s+[A-Z]\w+",  # Spanish articles before names
    ],
    "Italian": [
        r"\b\w*(?:zione|etto|etta|issimo|ino|ini|ismo)\b",
        r"\b(?:il|lo|la|gli|le)\s+\w+",
    ],
    "Latin": [
        r"\b(?:et|ad|de|ex|per|pro|sub|cum|sine)\s+[a-z]{4,}",
        r"\b\w*(?:ium|ius|orum|arum)\b",
    ],
}

# Words that match patterns but are common English
# Combine with COMMON_WORDS_WHITELIST to ensure common words are never flagged
ENGLISH_EXCEPTIONS = COMMON_WORDS_WHITELIST | {
    # Additional exceptions beyond the common words whitelist
    # (the whitelist already includes articles, conjunctions, and common verbs)
    # -ique words that are standard English
    "unique",
    "technique",
    "antique",
    "boutique",
    "critique",
    # Common Latin-origin -ium/-ius words
    "stadium",
    "radius",
    "genius",
    "podium",
    "tedium",
    "medium",
    "premium",
    "aquarium",
    "auditorium",
    "gymnasium",
    "millennium",
    "symposium",
    "calcium",
    "sodium",
    "potassium",
    "uranium",
    "helium",
    "titanium",
    "bacteria",
    "criteria",
    "media",
    "data",
    "agenda",
    "phenomena",
    # Common -ious/-eous words
    "obvious",
    "previous",
    "serious",
    "curious",
    "various",
    "anxious",
    "gorgeous",
    "religious",
    "precious",
    "conscious",
    "delicious",
    # Common English adverbs/direction words (fix for false foreign detection)
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
    "mysterious",
    "suspicious",
    "ambitious",
    "cautious",
    "spacious",
    # Words that match German article patterns but are English
    "die",
    "dying",
    "died",
    "dies",  # English verb "to die"
    "an",
    "one",
    "a",  # English articles that match German "ein/eine"
    # Common standalone words that appear in foreign phrases but are English words
    "grave",  # Common English word ("serious" or "tomb"), even in wine names like "De Grave"
}


class ForeignProposer(BasePronunciationProposer):
    """Proposes words matching foreign language patterns."""

    name = "foreign"

    def __init__(
        self,
        min_word_length: int = 4,
        llm_client=None,
        skip_llm_validation: bool = False,
    ):
        """
        Args:
            min_word_length: Minimum word length to consider
            llm_client: LLM client for validation (optional)
            skip_llm_validation: Skip LLM validation (faster, less accurate)
        """
        self.min_word_length = min_word_length
        self.llm_client = llm_client
        self.skip_llm_validation = skip_llm_validation
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
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        """Find words matching foreign language patterns.

        Uses WordIndex if available for more efficient filtering, otherwise
        falls back to pattern scanning. Note: ForeignProposer uses pattern
        scanning rather than simple word lookups, so the WordIndex benefit
        is primarily in context extraction.
        """
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
                    mentions.append(
                        PronunciationMention(
                            word_form=original,
                            position=position,
                            chapter_index=chapter_idx,
                            context=context,
                        )
                    )

                # Use most common form as canonical
                word_forms = [o[1] for o in occurrences]
                canonical = max(set(word_forms), key=word_forms.count)

                proposals.append(
                    PronunciationProposal(
                        strategy=self.name,
                        word=canonical,
                        flag_reason=PronunciationFlag.FOREIGN,
                        mentions=mentions,
                        confidence=0.7,
                        language_hint=language,
                        reasoning=f"Matches {language} language pattern",
                    )
                )

        logger.info(f"Foreign proposer found {len(proposals)} candidate words")

        # Validate with LLM if available and not skipped
        if self.llm_client and proposals and not self.skip_llm_validation:
            proposals = self._validate_with_llm(proposals)
            logger.info(f"After LLM validation: {len(proposals)} confirmed foreign words")
        elif self.skip_llm_validation:
            logger.info("LLM validation skipped (skip_llm_validation=True)")

        return proposals

    def _validate_with_llm(
        self,
        proposals: list[PronunciationProposal],
        batch_size: int = 20,
    ) -> list[PronunciationProposal]:
        """Use LLM to validate if flagged words are truly foreign in context."""
        validated = []

        # Process in batches
        for i in range(0, len(proposals), batch_size):
            batch = proposals[i : i + batch_size]

            # Build prompt with words and context
            candidates_text = []
            for p in batch:
                context = p.mentions[0].context if p.mentions else "No context"
                candidates_text.append(
                    f'- Word: "{p.word}" (flagged as {p.language_hint})\n' f'  Context: "{context}"'
                )

            prompt = f"""Review these words that were flagged as potentially foreign based on spelling patterns.
For each, determine if it's ACTUALLY being used as a foreign word/phrase, or if it's just a common English word that happens to match a foreign pattern.

{chr(10).join(candidates_text)}

Return a JSON array with your assessment for each word:
[
  {{"word": "example", "is_foreign": true/false, "reason": "brief explanation"}}
]

Only mark as foreign if the word is genuinely from another language and would need special pronunciation guidance for an English narrator."""

            try:
                result, response = self.llm_client.query_json(prompt)

                if not response.success:
                    # HTTP error or connection failure
                    logger.debug(
                        f"LLM validation failed: {response.error}, keeping batch candidates"
                    )
                    validated.extend(batch)
                elif result and isinstance(result, list):
                    # Create lookup of LLM decisions
                    decisions = {
                        item.get("word", "").lower(): item
                        for item in result
                        if isinstance(item, dict)
                    }

                    for p in batch:
                        decision = decisions.get(p.word.lower(), {})
                        if decision.get("is_foreign", True):  # Default to keeping if not found
                            # Update reasoning with LLM's explanation
                            if decision.get("reason"):
                                p.reasoning = decision["reason"]
                            validated.append(p)
                        else:
                            logger.debug(
                                f"LLM rejected '{p.word}': {decision.get('reason', 'no reason')}"
                            )
                else:
                    # If LLM fails, keep all candidates from this batch
                    error_detail = (
                        f"got {type(result).__name__}"
                        if result is not None
                        else "failed to parse JSON"
                    )
                    logger.warning(
                        f"LLM validation failed ({error_detail}), keeping batch candidates"
                    )
                    validated.extend(batch)

            except Exception as e:
                logger.warning(f"LLM validation error: {e}, keeping batch candidates")
                validated.extend(batch)

        return validated
