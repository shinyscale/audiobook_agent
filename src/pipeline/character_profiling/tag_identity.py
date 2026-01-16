"""
Chapter tag identity propagation for character profiling (Feature F5).

Parses chapter tags for compound names (A/B format like 'Cathy/Kate') and uses
them as merge signals. When a chapter summary contains a compound character tag,
this strongly indicates the two names refer to the same person.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap

logger = logging.getLogger(__name__)


# Pattern to match compound names: "Name1/Name2" or "Name1 / Name2"
COMPOUND_NAME_PATTERN = re.compile(r'^([A-Za-z][A-Za-z\s]*?)\s*/\s*([A-Za-z][A-Za-z\s]*?)$')


@dataclass
class TagIdentityMatch:
    """A match indicating two names are the same person based on chapter tags."""
    name1: str
    name2: str
    chapter_index: int
    tag_text: str  # Original tag text
    confidence: float = 0.95  # Very high confidence for explicit A/B tags

    def to_dict(self) -> dict:
        return {
            "name1": self.name1,
            "name2": self.name2,
            "chapter_index": self.chapter_index,
            "tag_text": self.tag_text,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TagIdentityMatch":
        return cls(**data)


@dataclass
class TagIdentityResult:
    """Result of tag identity propagation."""
    matches: list[TagIdentityMatch] = field(default_factory=list)
    total_tags_scanned: int = 0
    compound_tags_found: int = 0

    def to_dict(self) -> dict:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "total_tags_scanned": self.total_tags_scanned,
            "compound_tags_found": self.compound_tags_found,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TagIdentityResult":
        return cls(
            matches=[TagIdentityMatch.from_dict(m) for m in data.get("matches", [])],
            total_tags_scanned=data.get("total_tags_scanned", 0),
            compound_tags_found=data.get("compound_tags_found", 0),
        )


def parse_compound_name(tag: str) -> Optional[tuple[str, str]]:
    """
    Parse a compound name tag into two separate names.

    Args:
        tag: A character tag that may contain a compound name (e.g., "Cathy/Kate")

    Returns:
        Tuple of (name1, name2) if compound, None otherwise

    Examples:
        "Cathy/Kate" -> ("Cathy", "Kate")
        "John / Jane" -> ("John", "Jane")
        "Simple Name" -> None
    """
    tag = tag.strip()
    match = COMPOUND_NAME_PATTERN.match(tag)
    if match:
        name1 = match.group(1).strip()
        name2 = match.group(2).strip()
        # Validate both names have reasonable length
        if len(name1) >= 2 and len(name2) >= 2:
            return (name1, name2)
    return None


def extract_tag_identities(summary_map: ChapterSummaryMap) -> TagIdentityResult:
    """
    Extract identity matches from chapter summary character tags.

    Scans all chapter summaries for compound names in the characters_present field.
    When found, these indicate strong evidence that two names refer to the same person.

    Args:
        summary_map: The chapter summary map to scan

    Returns:
        TagIdentityResult with all found matches
    """
    result = TagIdentityResult()

    for summary in summary_map.summaries:
        for tag in summary.characters_present:
            result.total_tags_scanned += 1

            parsed = parse_compound_name(tag)
            if parsed:
                name1, name2 = parsed
                result.compound_tags_found += 1

                match = TagIdentityMatch(
                    name1=name1,
                    name2=name2,
                    chapter_index=summary.chapter_index,
                    tag_text=tag,
                    confidence=0.95,  # Very high confidence
                )
                result.matches.append(match)

                logger.info(
                    f"Found compound name tag '{tag}' in chapter {summary.chapter_index}: "
                    f"'{name1}' and '{name2}' are likely the same person"
                )

    if result.matches:
        logger.info(
            f"Tag identity propagation found {len(result.matches)} compound name matches "
            f"from {result.compound_tags_found} compound tags"
        )

    return result


def apply_tag_identities_to_merge_candidates(
    tag_result: TagIdentityResult,
    existing_candidates: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Combine tag identity matches with existing merge candidates.

    Tag identity matches have very high confidence (0.95) and should be
    prioritized in merge decisions.

    Args:
        tag_result: Result from extract_tag_identities
        existing_candidates: Optional existing merge candidates to augment

    Returns:
        Combined list of merge candidates with tag identities added
    """
    candidates = list(existing_candidates) if existing_candidates else []

    for match in tag_result.matches:
        # Check if this pair is already in candidates
        pair_exists = any(
            (c.get("name1") == match.name1 and c.get("name2") == match.name2) or
            (c.get("name1") == match.name2 and c.get("name2") == match.name1)
            for c in candidates
        )

        if not pair_exists:
            candidates.append({
                "name1": match.name1,
                "name2": match.name2,
                "reason": f"Compound chapter tag: '{match.tag_text}' (chapter {match.chapter_index})",
                "confidence": match.confidence,
                "source": "tag_identity",
            })
        else:
            # Update existing candidate with higher confidence
            for c in candidates:
                if ((c.get("name1") == match.name1 and c.get("name2") == match.name2) or
                    (c.get("name1") == match.name2 and c.get("name2") == match.name1)):
                    if c.get("confidence", 0) < match.confidence:
                        c["confidence"] = match.confidence
                        c["reason"] = c.get("reason", "") + f"; confirmed by tag '{match.tag_text}'"
                    break

    return candidates


class TagIdentityExtractor:
    """Extracts identity signals from chapter tags."""

    def __init__(self):
        """Initialize the extractor."""
        pass

    def extract(self, summary_map: ChapterSummaryMap) -> TagIdentityResult:
        """
        Extract identity matches from chapter summary character tags.

        Args:
            summary_map: The chapter summary map to scan

        Returns:
            TagIdentityResult with all found matches
        """
        return extract_tag_identities(summary_map)

    def get_merge_candidates(
        self,
        summary_map: ChapterSummaryMap,
        existing_candidates: Optional[list[dict]] = None,
    ) -> list[dict]:
        """
        Get merge candidates from tag identities combined with existing candidates.

        Args:
            summary_map: The chapter summary map to scan
            existing_candidates: Optional existing merge candidates

        Returns:
            Combined list of merge candidates
        """
        result = self.extract(summary_map)
        return apply_tag_identities_to_merge_candidates(result, existing_candidates)
