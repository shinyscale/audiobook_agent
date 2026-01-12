"""
Character passage gatherer.

Gathers relevant passages from the full text for character profile generation.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

from .models import IdentifiedCharacter
from ..chapter_detection.models import ChapterMap, Chapter

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

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chapter_index": self.chapter_index,
            "position": self.position,
            "name_matched": self.name_matched,
            "context_type": self.context_type,
            "score": self.score,
        }


class CharacterPassageGatherer:
    """Gathers passages relevant to a character from full text."""

    def __init__(
        self,
        context_window: int = 500,
        max_passages_per_name: int = 20,
    ):
        """
        Args:
            context_window: Characters of context around each mention
            max_passages_per_name: Max passages to gather per name variant
        """
        self.context_window = context_window
        self.max_passages_per_name = max_passages_per_name

    def gather_passages(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
    ) -> list[CharacterPassage]:
        """
        Gather passages relevant to this character.

        Searches for all name variants, deduplicates, scores, and selects
        the most relevant passages distributed across the narrative.

        Args:
            character: The character to gather passages for
            full_text: Complete document text
            chapter_map: Chapter boundaries

        Returns:
            List of relevant passages, sorted by position
        """
        all_names = [character.canonical_name] + character.aliases

        # Gather passages for each name variant
        all_passages = []
        for name in all_names:
            passages = self._find_passages_for_name(name, full_text, chapter_map)
            all_passages.extend(passages)

        # Deduplicate by position (overlapping contexts)
        passages = self._deduplicate_passages(all_passages)

        # Score passages by descriptive content
        passages = self._score_passages(passages)

        # Select best passages distributed across narrative
        passages = self._select_representative_passages(passages, chapter_map)

        logger.info(
            f"Gathered {len(passages)} passages for {character.canonical_name}"
        )

        return sorted(passages, key=lambda p: p.position)

    def _find_passages_for_name(
        self,
        name: str,
        full_text: str,
        chapter_map: ChapterMap,
    ) -> list[CharacterPassage]:
        """Find passages containing a specific name."""
        passages = []

        # Escape regex special characters but allow word boundaries
        escaped_name = re.escape(name)
        # Match the name as a word (with optional punctuation after)
        pattern = rf'\b{escaped_name}\b'

        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            position = match.start()

            # Get context window
            start = max(0, position - self.context_window // 2)
            end = min(len(full_text), position + len(name) + self.context_window // 2)

            # Expand to sentence boundaries if possible
            context = full_text[start:end]

            # Clean up partial words at boundaries
            if start > 0:
                # Find first space and trim before it
                first_space = context.find(' ')
                if first_space > 0 and first_space < 20:
                    context = "..." + context[first_space + 1:]
            if end < len(full_text):
                # Find last sentence-ending punctuation
                last_period = max(
                    context.rfind('.'),
                    context.rfind('!'),
                    context.rfind('?'),
                    context.rfind('"'),
                )
                if last_period > len(context) - 50:
                    context = context[:last_period + 1]
                else:
                    # Find last space and trim after it
                    last_space = context.rfind(' ')
                    if last_space > len(context) - 20:
                        context = context[:last_space] + "..."

            # Determine chapter
            chapter_idx = self._find_chapter_for_position(position, chapter_map)

            # Determine context type
            context_type = self._classify_context(context, name)

            passages.append(CharacterPassage(
                text=context.strip(),
                chapter_index=chapter_idx,
                position=position,
                name_matched=name,
                context_type=context_type,
            ))

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
        has_said = any(word in context.lower() for word in [
            'said', 'asked', 'replied', 'answered', 'shouted',
            'whispered', 'exclaimed', 'muttered', 'spoke'
        ])

        if has_quotes and has_said:
            return "dialogue"

        # Check for descriptive language
        descriptive_words = [
            'looked', 'appeared', 'wore', 'dressed', 'tall', 'short',
            'eyes', 'hair', 'face', 'voice', 'smile', 'expression',
            'young', 'old', 'beautiful', 'handsome'
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
                'tall', 'short', 'thin', 'fat', 'stout', 'slender',
                'eyes', 'hair', 'face', 'hands', 'voice', 'smile',
                'beautiful', 'handsome', 'ugly', 'pretty', 'elegant'
            ]
            for word in physical_words:
                if word in text_lower:
                    score += 0.5

            # Personality keywords
            personality_words = [
                'kind', 'cruel', 'gentle', 'harsh', 'nervous', 'calm',
                'arrogant', 'humble', 'intelligent', 'foolish',
                'honest', 'deceitful', 'brave', 'cowardly'
            ]
            for word in personality_words:
                if word in text_lower:
                    score += 0.5

            # Relationship keywords
            relationship_words = [
                'husband', 'wife', 'married', 'love', 'hate',
                'friend', 'enemy', 'cousin', 'brother', 'sister',
                'father', 'mother', 'son', 'daughter'
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
    context_window: int = 500,
    max_passages: int = 15,
) -> list[CharacterPassage]:
    """
    Convenience function to gather passages for a character.

    Args:
        character: The character to gather passages for
        full_text: Complete document text
        chapter_map: Chapter boundaries
        context_window: Characters of context around each mention
        max_passages: Maximum passages to return

    Returns:
        List of relevant passages
    """
    gatherer = CharacterPassageGatherer(
        context_window=context_window,
        max_passages_per_name=max_passages * 2,  # Gather more, then select
    )
    return gatherer.gather_passages(character, full_text, chapter_map)
