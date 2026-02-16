"""
Mention Search for Main Cast (F2)

Once we have profiles with aliases, searching for mentions is deterministic.
No ambiguity - we know which name variants belong to which character because
the LLM told us so in the main cast extraction step.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ...models import Character, CharacterMention, StructuralElement, StructureType

logger = logging.getLogger(__name__)


@dataclass
class MentionResult:
    """Result of searching for a character's mentions in text."""

    character_id: str
    canonical_name: str
    total_mentions: int = 0
    mentions_by_alias: dict[str, int] = field(default_factory=dict)
    mentions: list[CharacterMention] = field(default_factory=list)
    first_position: Optional[int] = None
    last_position: Optional[int] = None
    chapter_distribution: dict[int, int] = field(default_factory=dict)

    @property
    def is_grounded(self) -> bool:
        """True if character has at least one mention in the text."""
        return self.total_mentions > 0


class MentionSearcher:
    """
    Searches text for character mentions using their canonical name and aliases.

    The key insight is that profile-first extraction makes mention search
    deterministic: we already know "Gatsby", "Jay Gatsby", "Mr. Gatsby"
    are the same person, so we just search for each and count.
    """

    def __init__(
        self,
        full_text: str,
        chapters: Optional[list[StructuralElement]] = None,
    ):
        """
        Initialize the searcher with the full text and optional chapter info.

        Args:
            full_text: The complete text of the book
            chapters: Optional list of chapter elements for position mapping
        """
        self.full_text = full_text
        self.chapters = chapters or []
        self._chapter_ranges = self._build_chapter_ranges()

    def _build_chapter_ranges(self) -> list[tuple[int, int, int]]:
        """Build list of (start, end, chapter_index) for position mapping."""
        ranges = []
        for ch in self.chapters:
            if ch.type == StructureType.CHAPTER:
                ranges.append((ch.start_position, ch.end_position, ch.index))
        return sorted(ranges, key=lambda x: x[0])

    def _position_to_chapter(self, position: int) -> Optional[int]:
        """Map a text position to its chapter index."""
        for start, end, idx in self._chapter_ranges:
            if start <= position < end:
                return idx
        return None

    def _extract_base_name(self, canonical_name: str) -> str:
        """
        Extract base name without generational suffixes.

        Handles patterns like:
        - "John Donaldson Sr." → "John Donaldson"
        - "John Jr." → "John"
        - "Elizabeth Lavenza III" → "Elizabeth Lavenza"

        Args:
            canonical_name: Full canonical name possibly with suffixes

        Returns:
            Base name without Sr/Jr/roman numeral suffixes
        """
        name = canonical_name.strip()

        # Remove Sr./Jr./III/etc. suffixes
        # Pattern: optional comma + whitespace + Sr/Jr/roman numerals at end
        name = re.sub(r',?\s+(Sr\.?|Jr\.?|[IVX]+)$', '', name, flags=re.IGNORECASE).strip()

        return name

    def build_search_pattern(self, name: str) -> re.Pattern:
        """
        Build a regex pattern for finding a name with robust boundaries.

        Handles:
        - Preventing substring matches (e.g., "Gatsby" should not match "Gatsbyesque")
        - Case-insensitive matching
        - Apostrophe variants: "'" and "’"
        - Hyphen variants: "-" "–" "—"
        - Flexible whitespace between tokens
        - Optional trailing period for common abbreviations/titles (e.g., "Mr." vs "Mr")
        """
        name = (name or "").strip()
        if not name:
            return re.compile(r"(?!x)x")  # never matches

        # Tokenize on whitespace; then escape each token with a few robustifications.
        tokens = name.split()
        token_patterns: list[str] = []

        for tok in tokens:
            raw = tok

            # Allow optional trailing "." for short alpha tokens (titles/initials)
            optional_dot = False
            if raw.endswith(".") and raw[:-1].isalpha() and len(raw[:-1]) <= 4:
                optional_dot = True
                raw = raw[:-1]

            # Normalize punctuation variants via placeholders BEFORE escaping, so we don't
            # accidentally rewrite the regex we inject.
            APOS = "__APOS__"
            DASH = "__DASH__"
            raw = raw.replace("’", APOS).replace("'", APOS)
            raw = raw.replace("–", DASH).replace("—", DASH).replace("-", DASH)

            escaped = re.escape(raw)

            # Restore placeholders as regex character classes
            escaped = escaped.replace(re.escape(APOS), "['’]")
            escaped = escaped.replace(re.escape(DASH), "[-–—]")

            if optional_dot:
                escaped = escaped + r"\.?"

            token_patterns.append(escaped)

        # Flexible whitespace between tokens
        inner = r"\s+".join(token_patterns)

        # Robust "word boundary": do not allow adjacent alphanumerics.
        # This prevents matching inside longer words while still allowing punctuation.
        pattern = rf"(?<![A-Za-z0-9]){inner}(?![A-Za-z0-9])"

        return re.compile(pattern, re.IGNORECASE)

    def search_character(
        self,
        character: Character,
        context_chars: int = 100,
    ) -> MentionResult:
        """
        Search for all mentions of a character in the text.

        Args:
            character: Character with canonical_name and aliases
            context_chars: Number of characters of context to capture

        Returns:
            MentionResult with counts and positions
        """
        result = MentionResult(
            character_id=character.id,
            canonical_name=character.canonical_name,
        )

        # Build list of all name variants to search for
        all_names = [character.canonical_name] + character.aliases

        # If canonical name has generational suffixes (Sr./Jr.) that may not appear in text,
        # also search for the base name without the suffix. This handles cases where:
        # - The LLM extracted "John Donaldson Sr." to disambiguate from "John Donaldson Jr."
        # - But the text never literally uses "Sr." (it says "his father", "the father", etc.)
        canonical_base = self._extract_base_name(character.canonical_name)
        if canonical_base != character.canonical_name:
            all_names.append(canonical_base)
            logger.debug(
                f"Also searching for base name '{canonical_base}' "
                f"(canonical: '{character.canonical_name}')"
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in all_names:
            name_lower = name.lower()
            if name_lower not in seen and name:
                seen.add(name_lower)
                unique_names.append(name)

        # Search for each name variant.
        # We avoid double-counting overlaps (e.g., "Jay Gatsby" vs "Gatsby") by tracking spans.
        spans: list[tuple[int, int]] = []

        # Prefer longer names first so they "claim" the span before shorter substrings.
        unique_names = sorted(unique_names, key=len, reverse=True)

        for name in unique_names:
            pattern = self.build_search_pattern(name)
            count = 0

            for match in pattern.finditer(self.full_text):
                start_pos = match.start()
                end_pos = match.end()

                # Skip if we already counted an overlapping mention span.
                if any(not (end_pos <= s or start_pos >= e) for s, e in spans):
                    continue

                spans.append((start_pos, end_pos))
                count += 1

                # Get context
                ctx_start = max(0, start_pos - context_chars)
                ctx_end = min(len(self.full_text), end_pos + context_chars)
                context = self.full_text[ctx_start:ctx_end].strip()

                # Create mention object
                chapter_idx = self._position_to_chapter(start_pos)
                mention = CharacterMention(
                    name_form=match.group(),
                    position=start_pos,
                    context=context,
                    chapter_index=chapter_idx,
                )
                result.mentions.append(mention)

                # Update first/last positions
                if result.first_position is None or start_pos < result.first_position:
                    result.first_position = start_pos
                if result.last_position is None or start_pos > result.last_position:
                    result.last_position = start_pos

                # Track chapter distribution
                if chapter_idx is not None:
                    result.chapter_distribution[chapter_idx] = (
                        result.chapter_distribution.get(chapter_idx, 0) + 1
                    )

            result.mentions_by_alias[name] = count

        # Calculate total (sum of unique mentions, not sum by alias)
        result.total_mentions = len(spans)

        return result

    def search_all(
        self,
        characters: list[Character],
        context_chars: int = 100,
    ) -> dict[str, MentionResult]:
        """
        Search for mentions of all characters.

        Args:
            characters: List of characters to search for
            context_chars: Number of characters of context to capture

        Returns:
            Dict mapping character_id to MentionResult
        """
        results = {}

        for char in characters:
            result = self.search_character(char, context_chars)
            results[char.id] = result

            logger.debug(f"Character '{char.canonical_name}': {result.total_mentions} mentions")

        return results

    def update_characters_with_mentions(
        self,
        characters: list[Character],
        results: dict[str, MentionResult],
    ) -> list[Character]:
        """
        Update character objects with mention data.

        Args:
            characters: Original character list
            results: Mention search results

        Returns:
            Updated character list with mention counts and appearances
        """
        updated = []

        for char in characters:
            result = results.get(char.id)

            if result:
                char.mention_count = result.total_mentions
                # Transfer actual mentions for profile generation
                char.mentions = result.mentions

                # Set first/last appearance chapters
                if result.chapter_distribution:
                    chapters = sorted(result.chapter_distribution.keys())
                    char.first_appearance_chapter = chapters[0]

            updated.append(char)

        return updated
