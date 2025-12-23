"""
Pronunciation consolidator.

Merges proposals from different strategies into final pronunciation entries.
"""

from collections import defaultdict
from typing import Optional
import hashlib
import logging

from .models import (
    PronunciationProposal,
    PronunciationEnrichment,
    PronunciationEntry,
    PronunciationMap,
    PronunciationFlag,
)

logger = logging.getLogger(__name__)


class PronunciationConsolidator:
    """Consolidates proposals into final pronunciation map."""

    def __init__(
        self,
        confidence_threshold: float = 0.4,
        max_context_examples: int = 3,
    ):
        """
        Args:
            confidence_threshold: Minimum confidence to include
            max_context_examples: Maximum context examples per entry
        """
        self.confidence_threshold = confidence_threshold
        self.max_context_examples = max_context_examples

    def consolidate(
        self,
        proposals: list[PronunciationProposal],
        enrichments: dict[str, PronunciationEnrichment],
        character_names: list[str],
    ) -> PronunciationMap:
        """
        Consolidate proposals into final pronunciation map.

        Args:
            proposals: All proposals from all strategies
            enrichments: LLM-generated pronunciation data
            character_names: Known character names for prioritization

        Returns:
            Final PronunciationMap
        """
        # Normalize character names for matching
        char_name_words = set()
        for name in character_names:
            for word in name.split():
                char_name_words.add(word.lower())

        # Group proposals by normalized word
        word_groups = self._group_proposals(proposals)

        # Build entries
        entries = []
        low_confidence = []
        category_counts: dict[str, int] = defaultdict(int)
        total_occurrences = 0

        for word_lower, word_proposals in word_groups.items():
            entry = self._build_entry(
                word_lower,
                word_proposals,
                enrichments.get(word_lower),
                char_name_words,
            )

            total_occurrences += entry.occurrence_count
            category_counts[entry.flag_reason.value] += 1

            if entry.confidence >= self.confidence_threshold:
                entries.append(entry)
            else:
                low_confidence.append(entry)

        # Sort entries: character names first, then by occurrence count
        entries.sort(key=lambda e: (not e.is_character_name, -e.occurrence_count))
        low_confidence.sort(key=lambda e: -e.occurrence_count)

        logger.info(
            f"Consolidated {len(entries)} entries, {len(low_confidence)} low confidence"
        )

        return PronunciationMap(
            entries=entries,
            low_confidence_entries=low_confidence,
            total_flagged_words=len(entries) + len(low_confidence),
            total_occurrences=total_occurrences,
            by_category=dict(category_counts),
            character_names=character_names,
        )

    def _group_proposals(
        self,
        proposals: list[PronunciationProposal],
    ) -> dict[str, list[PronunciationProposal]]:
        """Group proposals by normalized word."""
        groups: dict[str, list[PronunciationProposal]] = defaultdict(list)

        for proposal in proposals:
            word_lower = proposal.word.lower()
            groups[word_lower].append(proposal)

        return groups

    def _build_entry(
        self,
        word_lower: str,
        proposals: list[PronunciationProposal],
        enrichment: Optional[PronunciationEnrichment],
        char_name_words: set[str],
    ) -> PronunciationEntry:
        """Build a single pronunciation entry from proposals."""
        # Collect all mentions
        all_mentions = []
        for p in proposals:
            all_mentions.extend(p.mentions)

        # Sort by position
        all_mentions.sort(key=lambda m: m.position)

        # Select best canonical form (prefer character strategy, then most common)
        canonical_word = proposals[0].word
        for p in proposals:
            if p.strategy == "character":
                canonical_word = p.word
                break

        # Determine flag reason (priority: CHARACTER > HOMOGRAPH > FOREIGN > UNKNOWN)
        flag_priority = {
            PronunciationFlag.CHARACTER: 1,
            PronunciationFlag.HOMOGRAPH: 2,
            PronunciationFlag.FOREIGN: 3,
            PronunciationFlag.PROPER_NOUN: 4,
            PronunciationFlag.UNKNOWN: 5,
        }
        flag_reason = min(
            (p.flag_reason for p in proposals),
            key=lambda f: flag_priority.get(f, 99)
        )

        # Collect homograph options if any
        homograph_options = None
        for p in proposals:
            if p.homograph_options:
                homograph_options = p.homograph_options
                break

        # Get unique chapters
        chapters = sorted(set(m.chapter_index for m in all_mentions))

        # Select diverse context examples
        context_examples = self._select_context_examples(all_mentions)

        # Calculate combined confidence
        confidence = self._calculate_confidence(proposals)

        # Check if character name
        is_character = word_lower in char_name_words

        # Build entry
        entry = PronunciationEntry(
            id=self._generate_id(word_lower),
            word=canonical_word,
            flag_reason=flag_reason,
            occurrence_count=len(all_mentions),
            first_position=all_mentions[0].position if all_mentions else 0,
            chapters_present=chapters,
            context_examples=context_examples,
            homograph_options=homograph_options,
            supporting_strategies=list(set(p.strategy for p in proposals)),
            confidence=confidence,
            is_character_name=is_character,
        )

        # Apply enrichment if available
        if enrichment:
            entry.ipa = enrichment.ipa
            entry.phonetic_spelling = enrichment.phonetic_spelling
            entry.notes = enrichment.notes

        return entry

    def _select_context_examples(
        self,
        mentions: list,
    ) -> list[str]:
        """Select diverse context examples from different chapters."""
        if not mentions:
            return []

        # Try to get examples from different chapters
        seen_chapters = set()
        examples = []

        for mention in mentions:
            if len(examples) >= self.max_context_examples:
                break

            if mention.chapter_index not in seen_chapters:
                examples.append(mention.context)
                seen_chapters.add(mention.chapter_index)

        # If we don't have enough, add more from same chapters
        if len(examples) < self.max_context_examples:
            for mention in mentions:
                if len(examples) >= self.max_context_examples:
                    break
                if mention.context not in examples:
                    examples.append(mention.context)

        return examples

    def _calculate_confidence(
        self,
        proposals: list[PronunciationProposal],
    ) -> float:
        """Calculate combined confidence from multiple strategies."""
        if not proposals:
            return 0.0

        # Base confidence is max of individual confidences
        base_confidence = max(p.confidence for p in proposals)

        # Boost for multiple agreeing strategies
        unique_strategies = len(set(p.strategy for p in proposals))
        strategy_boost = min(0.1 * (unique_strategies - 1), 0.2)

        # Boost for high occurrence count
        total_mentions = sum(len(p.mentions) for p in proposals)
        occurrence_boost = min(0.05 * (total_mentions // 5), 0.15)

        return min(base_confidence + strategy_boost + occurrence_boost, 1.0)

    def _generate_id(self, word_lower: str) -> str:
        """Generate a unique ID for a word."""
        return hashlib.md5(word_lower.encode()).hexdigest()[:8]
