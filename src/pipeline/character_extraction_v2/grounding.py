"""
Grounding Gate (F2b) - Anti-Hallucination

The grounding gate ensures that characters extracted from summaries actually
appear in the raw text. This prevents summary hallucinations from becoming
hallucinated characters in the final output.

Rules:
1. Each main-cast character must have >= MIN_MENTIONS total hits (default 3)
2. Aliases with 0 hits are removed or flagged as ungrounded
3. Characters with 0 hits are excluded from high-confidence main cast
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ...models import Character, ConfidenceLevel
from .mention_search import MentionResult

logger = logging.getLogger(__name__)


@dataclass
class GroundingResult:
    """Result of grounding validation for a character."""

    character_id: str
    canonical_name: str
    is_grounded: bool
    total_mentions: int
    grounded_aliases: list[str]
    ungrounded_aliases: list[str]
    reason: Optional[str] = None


@dataclass
class GroundingReport:
    """Complete report from the grounding gate."""

    grounded_characters: list[Character]
    ungrounded_characters: list[Character]
    grounding_results: list[GroundingResult]
    total_grounded: int = 0
    total_ungrounded: int = 0


class GroundingGate:
    """
    Applies grounding rules to prevent hallucinated characters.

    The gate validates that characters and their aliases actually appear
    in the raw text, demoting or excluding those that don't.
    """

    def __init__(
        self,
        min_mentions: int = 3,
        remove_ungrounded_aliases: bool = True,
    ):
        """
        Initialize the grounding gate.

        Args:
            min_mentions: Minimum total mentions required for a grounded character
            remove_ungrounded_aliases: If True, remove aliases with 0 hits;
                                       if False, just flag them
        """
        self.min_mentions = min_mentions
        self.remove_ungrounded_aliases = remove_ungrounded_aliases

    def apply(
        self,
        characters: list[Character],
        mention_results: dict[str, MentionResult],
    ) -> GroundingReport:
        """
        Apply grounding rules to characters based on mention search results.

        Args:
            characters: List of main cast characters
            mention_results: Dict mapping character_id to MentionResult

        Returns:
            GroundingReport with grounded/ungrounded characters and details
        """
        grounded = []
        ungrounded = []
        results = []

        for char in characters:
            mention_result = mention_results.get(char.id)

            if mention_result is None:
                # No search was performed - treat as ungrounded
                result = GroundingResult(
                    character_id=char.id,
                    canonical_name=char.canonical_name,
                    is_grounded=False,
                    total_mentions=0,
                    grounded_aliases=[],
                    ungrounded_aliases=char.aliases.copy(),
                    reason="No mention search performed",
                )
                results.append(result)
                char.confidence = ConfidenceLevel.LOW
                ungrounded.append(char)
                continue

            # Check which aliases are grounded
            grounded_aliases = []
            ungrounded_aliases = []

            for alias in [char.canonical_name] + char.aliases:
                alias_count = mention_result.mentions_by_alias.get(alias, 0)
                if alias_count > 0:
                    grounded_aliases.append(alias)
                else:
                    ungrounded_aliases.append(alias)

            # Check if this is a narrator/protagonist placeholder
            # These placeholders should be allowed through even with 0 mentions,
            # as they will be matched to their actual character name in a later step
            char_name_lower = char.canonical_name.lower()
            narrator_placeholders = [
                "the narrator",
                "narrator",
                "the protagonist",
                "protagonist",
                "the main character",
                "main character",
            ]
            is_narrator_placeholder = any(
                placeholder in char_name_lower for placeholder in narrator_placeholders
            )

            # Determine if character is grounded
            # Narrator placeholders are always grounded (will be resolved later)
            if is_narrator_placeholder:
                is_grounded = True
            else:
                is_grounded = mention_result.total_mentions >= self.min_mentions

            # Build reason if not grounded
            reason = None
            if not is_grounded:
                if mention_result.total_mentions == 0:
                    reason = "No mentions found in text (possible summary hallucination)"
                else:
                    reason = (
                        f"Only {mention_result.total_mentions} mentions "
                        f"(minimum {self.min_mentions} required)"
                    )

            result = GroundingResult(
                character_id=char.id,
                canonical_name=char.canonical_name,
                is_grounded=is_grounded,
                total_mentions=mention_result.total_mentions,
                grounded_aliases=grounded_aliases,
                ungrounded_aliases=ungrounded_aliases,
                reason=reason,
            )
            results.append(result)

            # Update character based on grounding
            if is_grounded:
                char.confidence = ConfidenceLevel.HIGH

                # Optionally remove ungrounded aliases
                if self.remove_ungrounded_aliases:
                    # Keep canonical name even if ungrounded (it's the identity)
                    # but remove ungrounded non-canonical aliases
                    char.aliases = [a for a in char.aliases if a in grounded_aliases]

                grounded.append(char)
            else:
                char.confidence = ConfidenceLevel.LOW
                ungrounded.append(char)

        report = GroundingReport(
            grounded_characters=grounded,
            ungrounded_characters=ungrounded,
            grounding_results=results,
            total_grounded=len(grounded),
            total_ungrounded=len(ungrounded),
        )

        logger.info(
            f"Grounding gate: {report.total_grounded} grounded, "
            f"{report.total_ungrounded} ungrounded"
        )

        return report

    def log_report(self, report: GroundingReport) -> None:
        """Log detailed grounding report for debugging."""
        for result in report.grounding_results:
            status = "GROUNDED" if result.is_grounded else "UNGROUNDED"
            logger.info(
                f"  [{status}] {result.canonical_name}: " f"{result.total_mentions} mentions"
            )

            if result.ungrounded_aliases:
                logger.debug(f"    Ungrounded aliases: {result.ungrounded_aliases}")

            if result.reason:
                logger.debug(f"    Reason: {result.reason}")
