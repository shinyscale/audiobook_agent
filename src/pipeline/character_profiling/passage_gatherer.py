"""
Character passage gatherer.

Gathers relevant passages from the full text for character profile generation.

Supports disambiguation for same-name characters (e.g., father/son pairs).
"""

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..chapter_detection.models import ChapterMap
from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from .models import IdentifiedCharacter
from .perspective_filter import should_exclude_narrator_perspective_for_non_narrator

if TYPE_CHECKING:
    from .name_disambiguator import ContextDisambiguator

logger = logging.getLogger(__name__)


@dataclass
class CharacterPassage:
    """A passage of text relevant to a character."""

    text: str
    chapter_index: int
    position: int  # Character position in full text
    name_matched: str  # Which name variant matched
    context_type: str = "mention"  # "mention", "dialogue", "description"
    score: float = 0.0  # Relevance score for prioritization
    # Disambiguation metadata (for same-name character handling)
    ambiguous: bool = False  # Was disambiguation uncertain?
    disambiguation_confidence: float = 1.0  # How confident in character assignment (0-1)
    disambiguation_method: str = ""  # Method used: "relationship", "name_shape", etc.

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chapter_index": self.chapter_index,
            "position": self.position,
            "name_matched": self.name_matched,
            "context_type": self.context_type,
            "score": self.score,
            "ambiguous": self.ambiguous,
            "disambiguation_confidence": self.disambiguation_confidence,
            "disambiguation_method": self.disambiguation_method,
        }


class CharacterPassageGatherer:
    """Gathers passages relevant to a character from full text."""

    def __init__(
        self,
        context_window: int = 2000,
        max_passages_per_name: int = 20,
        disambiguator: Optional["ContextDisambiguator"] = None,
        summary_map: Optional[ChapterSummaryMap] = None,
    ):
        """
        Args:
            context_window: Characters of context around each mention
            max_passages_per_name: Max passages to gather per name variant
            disambiguator: Optional ContextDisambiguator for same-name character handling
            summary_map: Chapter summaries for disambiguation context
        """
        self.context_window = context_window
        self.max_passages_per_name = max_passages_per_name
        self.disambiguator = disambiguator
        self.summary_map = summary_map

        # Build chapter index for quick lookup
        self._chapter_summary_index: dict[int, ChapterSummary] = {}
        if summary_map:
            for summary in summary_map.summaries:
                self._chapter_summary_index[summary.chapter_index] = summary

        # Statistics for disambiguation
        self._disambiguation_stats = {
            "total_passages_considered": 0,
            "skipped_different_character": 0,
            "kept_same_character": 0,
            "kept_ambiguous_low_confidence": 0,
            "not_ambiguous": 0,
        }

    def gather_passages(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
        summary_map: Optional[ChapterSummaryMap] = None,
        narrative_style: str = "unknown",
    ) -> list[CharacterPassage]:
        """
        Gather passages relevant to this character.

        For first-person narrators, searches for first-person pronouns ("I", "my", "me").
        For other characters, searches for all name variants.
        Deduplicates, scores, and selects the most relevant passages.

        Args:
            character: The character to gather passages for
            full_text: Complete document text
            chapter_map: Chapter boundaries
            summary_map: Optional chapter summaries (overrides instance summary_map)

        Returns:
            List of relevant passages, sorted by position
        """
        # Use provided summary_map or fall back to instance summary_map
        effective_summary_map = summary_map or self.summary_map
        if effective_summary_map and not self._chapter_summary_index:
            # Build index if not already built
            for summary in effective_summary_map.summaries:
                self._chapter_summary_index[summary.chapter_index] = summary

        all_passages = []

        # Special handling for first-person narrators
        if (
            character.is_narrator
            and character.narrative_role
            and "first-person" in character.narrative_role.lower()
        ):
            logger.info(
                f"{character.canonical_name} is first-person narrator - gathering 'I' passages"
            )
            # Gather passages containing first-person pronouns
            all_passages = self._find_narrator_passages(
                full_text, chapter_map, character.canonical_name
            )
        else:
            # Standard name-based gathering with disambiguation
            all_names = [character.canonical_name] + character.aliases
            for name in all_names:
                passages = self._find_passages_for_name(
                    name, full_text, chapter_map,
                    character_canonical_name=character.canonical_name,
                    all_character_names=all_names,
                )
                all_passages.extend(passages)

        # Deduplicate by position (overlapping contexts)
        passages = self._deduplicate_passages(all_passages)

        # Filter narrator-centric first-person passages for NON-narrator characters.
        # These often look like "I did X to John" and primarily describe the narrator.
        if narrative_style == "first-person" and not character.is_narrator:
            filtered = []
            for p in passages:
                if should_exclude_narrator_perspective_for_non_narrator(p.text, p.name_matched):
                    continue
                filtered.append(p)
            passages = filtered

        # Score passages by descriptive content
        passages = self._score_passages(passages)

        # Select best passages distributed across narrative
        passages = self._select_representative_passages(passages, chapter_map)

        # Log disambiguation stats if used
        if self.disambiguator:
            stats = self._disambiguation_stats
            ambiguous_kept = stats["kept_ambiguous_low_confidence"]
            logger.info(
                f"Gathered {len(passages)} passages for {character.canonical_name} "
                f"(disambiguation: {stats['skipped_different_character']} skipped, "
                f"{ambiguous_kept} kept as ambiguous)"
            )
        else:
            logger.info(f"Gathered {len(passages)} passages for {character.canonical_name}")

        return sorted(passages, key=lambda p: p.position)

    def _find_narrator_passages(
        self,
        full_text: str,
        chapter_map: ChapterMap,
        narrator_name: str,
    ) -> list[CharacterPassage]:
        """
        Find passages for a first-person narrator by searching for first-person pronouns.

        Samples passages containing "I", "my", "me" distributed throughout the text.
        """
        passages = []

        # First-person pronouns to search for
        # Use word boundary to avoid matching "I" inside words
        fp_pattern = r"\b(I|my|me|myself)\b"

        # Find all first-person pronouns, but sample evenly to avoid overwhelming
        # the profiler with too many passages
        matches = list(re.finditer(fp_pattern, full_text, re.IGNORECASE))

        # Sample passages evenly across the text (take every Nth match)
        total_matches = len(matches)
        if total_matches == 0:
            logger.warning(f"No first-person pronouns found for narrator {narrator_name}")
            return []

        # Target: ~50 passages spread across the story
        target_passages = min(50, total_matches)
        step = max(1, total_matches // target_passages)

        sampled_matches = matches[::step][:target_passages]

        for match in sampled_matches:
            position = match.start()
            pronoun = match.group(0)

            # Get context window
            start = max(0, position - self.context_window // 2)
            end = min(len(full_text), position + len(pronoun) + self.context_window // 2)

            # Expand to sentence boundaries
            context = full_text[start:end]

            # Clean up partial words at boundaries
            if start > 0:
                first_space = context.find(" ")
                if first_space > 0 and first_space < 20:
                    context = "..." + context[first_space + 1 :]
            if end < len(full_text):
                last_period = max(
                    context.rfind("."),
                    context.rfind("!"),
                    context.rfind("?"),
                    context.rfind('"'),
                )
                if last_period > len(context) - 50:
                    context = context[: last_period + 1]
                else:
                    last_space = context.rfind(" ")
                    if last_space > len(context) - 20:
                        context = context[:last_space] + "..."

            # Determine chapter
            chapter_idx = self._find_chapter_for_position(position, chapter_map)

            # Context type for narrator is typically "narration" or "dialogue"
            context_type = self._classify_context(context, pronoun)

            passages.append(
                CharacterPassage(
                    text=context.strip(),
                    chapter_index=chapter_idx,
                    position=position,
                    name_matched=f"[narrator: {pronoun}]",
                    context_type=context_type,
                )
            )

        logger.info(
            f"Found {len(passages)} narrator passages from {total_matches} first-person pronouns"
        )
        return passages

    def _find_passages_for_name(
        self,
        name: str,
        full_text: str,
        chapter_map: ChapterMap,
        character_canonical_name: Optional[str] = None,
        all_character_names: Optional[list[str]] = None,
    ) -> list[CharacterPassage]:
        """
        Find passages containing a specific name.

        Args:
            name: Name to search for
            full_text: Complete document text
            chapter_map: Chapter boundaries
            character_canonical_name: Canonical name of target character (for disambiguation)
            all_character_names: All names/aliases of target character (for disambiguation)
        """
        passages = []

        # Escape regex special characters but allow word boundaries
        escaped_name = re.escape(name)
        # Match the name as a word (with optional punctuation after)
        pattern = rf"\b{escaped_name}\b"

        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            self._disambiguation_stats["total_passages_considered"] += 1
            position = match.start()

            # Get context window
            start = max(0, position - self.context_window // 2)
            end = min(len(full_text), position + len(name) + self.context_window // 2)

            # Expand to sentence boundaries if possible
            context = full_text[start:end]

            # Clean up partial words at boundaries
            if start > 0:
                # Find first space and trim before it
                first_space = context.find(" ")
                if first_space > 0 and first_space < 20:
                    context = "..." + context[first_space + 1 :]
            if end < len(full_text):
                # Find last sentence-ending punctuation
                last_period = max(
                    context.rfind("."),
                    context.rfind("!"),
                    context.rfind("?"),
                    context.rfind('"'),
                )
                if last_period > len(context) - 50:
                    context = context[: last_period + 1]
                else:
                    # Find last space and trim after it
                    last_space = context.rfind(" ")
                    if last_space > len(context) - 20:
                        context = context[:last_space] + "..."

            # Determine chapter
            chapter_idx = self._find_chapter_for_position(position, chapter_map)

            # EARLY FILTER: For split characters (e.g., "John Donaldson (the father)"),
            # skip passages from chapters where this specific split character doesn't appear.
            # This prevents profile contamination where father and son share the same aliases.
            if character_canonical_name and self._chapter_summary_index:
                # Check if this is a split character (has parenthetical label at end)
                if '(' in character_canonical_name and character_canonical_name.endswith(')'):
                    chapter_summary = self._chapter_summary_index.get(chapter_idx)
                    if chapter_summary:
                        # Check if the FULL canonical name (with label) is in active_characters
                        # This ensures "John Donaldson (the father)" only gets passages from
                        # chapters where the father specifically appears
                        active_chars_lower = [c.lower() for c in chapter_summary.active_characters]
                        if character_canonical_name.lower() not in active_chars_lower:
                            # This chapter doesn't have this specific split character - skip passage
                            self._disambiguation_stats["skipped_different_character"] += 1
                            logger.debug(
                                f"Split character filter: Skipping passage for '{character_canonical_name}' "
                                f"in chapter {chapter_idx} (not in active_characters)"
                            )
                            continue

            # Determine context type
            context_type = self._classify_context(context, name)

            # Initialize disambiguation metadata
            is_ambiguous = False
            disambiguation_confidence = 1.0
            disambiguation_method = ""

            # Apply disambiguation if available and name is ambiguous
            if self.disambiguator and self.disambiguator.is_ambiguous(name):
                # Get chapter summary for context
                chapter_summary = self._chapter_summary_index.get(chapter_idx)

                result = self.disambiguator.disambiguate(
                    name=name,
                    sentence=context,
                    chapter_summary=chapter_summary,
                    chapter_index=chapter_idx,
                    target_character_names=all_character_names,
                )

                # Check if disambiguation resolved to a different character
                resolved_lower = result.resolved_character.lower()
                target_names_lower = [n.lower() for n in (all_character_names or [name])]
                canonical_lower = (character_canonical_name or name).lower()

                # If resolved to a different character entirely, skip this passage
                is_same_character = (
                    resolved_lower == canonical_lower
                    or resolved_lower in target_names_lower
                    or any(resolved_lower in n or n in resolved_lower for n in target_names_lower)
                )

                if not is_same_character and result.confidence >= 0.7:
                    # High confidence that this is about a different character - skip
                    self._disambiguation_stats["skipped_different_character"] += 1
                    logger.debug(
                        f"Disambiguation: Skipping passage for '{name}' -> "
                        f"'{result.resolved_character}' (confidence={result.confidence:.2f}, "
                        f"method={result.method})"
                    )
                    continue
                elif not is_same_character and result.confidence < 0.7:
                    # Low confidence - keep but mark as ambiguous
                    is_ambiguous = True
                    disambiguation_confidence = result.confidence
                    disambiguation_method = result.method
                    self._disambiguation_stats["kept_ambiguous_low_confidence"] += 1
                    logger.debug(
                        f"Disambiguation: Keeping ambiguous passage for '{name}' "
                        f"(low confidence={result.confidence:.2f})"
                    )
                else:
                    # Same character - keep with full confidence
                    disambiguation_confidence = result.confidence
                    disambiguation_method = result.method
                    self._disambiguation_stats["kept_same_character"] += 1
            else:
                self._disambiguation_stats["not_ambiguous"] += 1

            passages.append(
                CharacterPassage(
                    text=context.strip(),
                    chapter_index=chapter_idx,
                    position=position,
                    name_matched=name,
                    context_type=context_type,
                    ambiguous=is_ambiguous,
                    disambiguation_confidence=disambiguation_confidence,
                    disambiguation_method=disambiguation_method,
                )
            )

            # Limit per name variant
            if len(passages) >= self.max_passages_per_name:
                break

        return passages

    def _find_chapter_for_position(
        self,
        position: int,
        chapter_map: ChapterMap,
    ) -> int:
        """Find which chapter a position belongs to."""
        for chapter in chapter_map.chapters:
            if chapter.start_position <= position < chapter.end_position:
                return chapter.index
        # Default to chapter 1 if not found
        return 1

    def _classify_context(self, context: str, name: str) -> str:
        """Classify the type of context (dialogue, description, mention)."""
        # Check for dialogue markers
        has_quotes = '"' in context or "'" in context
        has_said = any(
            word in context.lower()
            for word in [
                "said",
                "asked",
                "replied",
                "answered",
                "shouted",
                "whispered",
                "exclaimed",
                "muttered",
                "spoke",
            ]
        )

        if has_quotes and has_said:
            return "dialogue"

        # Check for descriptive language
        descriptive_words = [
            "looked",
            "appeared",
            "wore",
            "dressed",
            "tall",
            "short",
            "eyes",
            "hair",
            "face",
            "voice",
            "smile",
            "expression",
            "young",
            "old",
            "beautiful",
            "handsome",
        ]
        if any(word in context.lower() for word in descriptive_words):
            return "description"

        return "mention"

    def _deduplicate_passages(
        self,
        passages: list[CharacterPassage],
    ) -> list[CharacterPassage]:
        """Remove passages with overlapping contexts."""
        if not passages:
            return []

        # Sort by position
        sorted_passages = sorted(passages, key=lambda p: p.position)

        deduplicated = [sorted_passages[0]]
        for passage in sorted_passages[1:]:
            last = deduplicated[-1]
            # Check if positions are too close (overlapping contexts)
            if passage.position - last.position > self.context_window // 2:
                deduplicated.append(passage)
            elif passage.score > last.score:
                # Replace with higher-scoring passage
                deduplicated[-1] = passage

        return deduplicated

    def _score_passages(
        self,
        passages: list[CharacterPassage],
    ) -> list[CharacterPassage]:
        """Score passages by relevance for profiling."""
        for passage in passages:
            score = 0.0

            text_lower = passage.text.lower()

            # Dialogue is valuable for voice
            if passage.context_type == "dialogue":
                score += 2.0

            # Descriptions are valuable
            if passage.context_type == "description":
                score += 3.0

            # Physical description keywords
            physical_words = [
                "tall",
                "short",
                "thin",
                "fat",
                "stout",
                "slender",
                "eyes",
                "hair",
                "face",
                "hands",
                "voice",
                "smile",
                "beautiful",
                "handsome",
                "ugly",
                "pretty",
                "elegant",
            ]
            for word in physical_words:
                if word in text_lower:
                    score += 0.5

            # Personality keywords
            personality_words = [
                "kind",
                "cruel",
                "gentle",
                "harsh",
                "nervous",
                "calm",
                "arrogant",
                "humble",
                "intelligent",
                "foolish",
                "honest",
                "deceitful",
                "brave",
                "cowardly",
            ]
            for word in personality_words:
                if word in text_lower:
                    score += 0.5

            # Relationship keywords
            relationship_words = [
                "husband",
                "wife",
                "married",
                "love",
                "hate",
                "friend",
                "enemy",
                "cousin",
                "brother",
                "sister",
                "father",
                "mother",
                "son",
                "daughter",
            ]
            for word in relationship_words:
                if word in text_lower:
                    score += 0.5

            passage.score = score

        return passages

    def _select_representative_passages(
        self,
        passages: list[CharacterPassage],
        chapter_map: ChapterMap,
        max_passages: int = 15,
    ) -> list[CharacterPassage]:
        """
        Select representative passages distributed across the narrative.

        Ensures coverage of early, middle, and late sections.
        """
        if len(passages) <= max_passages:
            return passages

        # Divide chapters into thirds
        num_chapters = len(chapter_map.chapters)
        early_end = num_chapters // 3
        mid_end = 2 * num_chapters // 3

        early_passages = [p for p in passages if p.chapter_index <= early_end]
        mid_passages = [p for p in passages if early_end < p.chapter_index <= mid_end]
        late_passages = [p for p in passages if p.chapter_index > mid_end]

        # Sort each group by score (descending)
        early_passages.sort(key=lambda p: p.score, reverse=True)
        mid_passages.sort(key=lambda p: p.score, reverse=True)
        late_passages.sort(key=lambda p: p.score, reverse=True)

        # Select from each group (5 each, roughly)
        per_group = max_passages // 3
        selected = []
        selected.extend(early_passages[:per_group])
        selected.extend(mid_passages[:per_group])
        selected.extend(late_passages[:per_group])

        # Fill remaining slots with highest-scoring overall
        remaining = max_passages - len(selected)
        if remaining > 0:
            all_remaining = [p for p in passages if p not in selected]
            all_remaining.sort(key=lambda p: p.score, reverse=True)
            selected.extend(all_remaining[:remaining])

        return selected


def gather_character_passages(
    character: IdentifiedCharacter,
    full_text: str,
    chapter_map: ChapterMap,
    context_window: int = 2000,
    max_passages: int = 15,
    disambiguator: Optional["ContextDisambiguator"] = None,
    summary_map: Optional[ChapterSummaryMap] = None,
    narrative_style: str = "unknown",
) -> list[CharacterPassage]:
    """
    Convenience function to gather passages for a character.

    Args:
        character: The character to gather passages for
        full_text: Complete document text
        chapter_map: Chapter boundaries
        context_window: Characters of context around each mention
        max_passages: Maximum passages to return
        disambiguator: Optional ContextDisambiguator for same-name character handling
        summary_map: Chapter summaries for disambiguation context

    Returns:
        List of relevant passages
    """
    gatherer = CharacterPassageGatherer(
        context_window=context_window,
        max_passages_per_name=max_passages * 2,  # Gather more, then select
        disambiguator=disambiguator,
        summary_map=summary_map,
    )
    return gatherer.gather_passages(
        character,
        full_text,
        chapter_map,
        summary_map=summary_map,
        narrative_style=narrative_style,
    )
