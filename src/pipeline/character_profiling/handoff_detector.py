"""
Handoff detector for character profiling.

Detects when Character A disappears and Character B appears in immediately
following chapters, suggesting they may be the same person using different names
(e.g., "Cathy Ames" becomes "Catherine Amesbury", "Cal" is also "Caleb").

This addresses merge failures where the text doesn't explicitly say
"A is later known as B" but the chapter distribution pattern suggests identity.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from .models import IdentifiedCharacter
from ..chapter_summary.models import ChapterSummaryMap

logger = logging.getLogger(__name__)


@dataclass
class HandoffCandidate:
    """A pair of characters that may be the same person based on chapter distribution."""

    name_a: str  # Character who disappears
    name_b: str  # Character who appears
    last_chapter_a: int  # Last chapter where A appears
    first_chapter_b: int  # First chapter where B appears
    confidence: float  # 0.0 to 1.0
    reason: str  # Human-readable explanation

    # Additional context for LLM verification
    chapters_a: list[int] = field(default_factory=list)
    chapters_b: list[int] = field(default_factory=list)
    name_similarity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name_a": self.name_a,
            "name_b": self.name_b,
            "last_chapter_a": self.last_chapter_a,
            "first_chapter_b": self.first_chapter_b,
            "confidence": self.confidence,
            "reason": self.reason,
            "chapters_a": self.chapters_a,
            "chapters_b": self.chapters_b,
            "name_similarity": self.name_similarity,
        }


class HandoffDetector:
    """
    Detects potential character identity handoffs based on chapter distribution.

    A "handoff" occurs when:
    1. Character A appears in chapters [X, Y, Z]
    2. Character B appears in chapters [Z+1, Z+2] (immediately after A stops)
    3. Their chapters are disjoint (no overlap)
    4. B appears in relatively few chapters (suggests alias, not new character)

    This catches cases like:
    - Cathy Ames (ch 7) -> Catherine Amesbury (ch 8)
    - Cal (ch 23+) vs Caleb (ch 21-22)
    """

    def __init__(
        self,
        gap_tolerance: int = 2,
        min_confidence: float = 0.5,
        max_b_chapters: int = 5,
    ):
        """
        Args:
            gap_tolerance: Max chapters between A's last and B's first appearance
            min_confidence: Minimum confidence to report a candidate
            max_b_chapters: Max chapters B can appear in to be considered an alias
        """
        self.gap_tolerance = gap_tolerance
        self.min_confidence = min_confidence
        self.max_b_chapters = max_b_chapters

    def detect_handoffs(
        self,
        characters: list[IdentifiedCharacter],
        summary_map: Optional[ChapterSummaryMap] = None,
    ) -> list[HandoffCandidate]:
        """
        Detect potential handoff candidates among characters.

        Args:
            characters: List of identified characters
            summary_map: Optional summary map for additional context

        Returns:
            List of HandoffCandidate pairs to verify
        """
        candidates = []

        # Build chapter presence map
        char_chapters = self._build_chapter_map(characters)

        # Check each pair
        for i, char_a in enumerate(characters):
            for char_b in characters[i + 1:]:
                candidate = self._check_handoff(char_a, char_b, char_chapters)
                if candidate and candidate.confidence >= self.min_confidence:
                    candidates.append(candidate)

        # Sort by confidence (highest first)
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        logger.info(f"Detected {len(candidates)} handoff candidates")
        for c in candidates:
            logger.debug(f"  {c.name_a} -> {c.name_b} (conf={c.confidence:.2f}): {c.reason}")

        return candidates

    def _build_chapter_map(
        self,
        characters: list[IdentifiedCharacter],
    ) -> dict[str, list[int]]:
        """Build a map of character name -> chapters present."""
        result = {}
        for char in characters:
            chapters = sorted(set(char.chapters_present)) if char.chapters_present else []
            result[char.canonical_name] = chapters
        return result

    def _check_handoff(
        self,
        char_a: IdentifiedCharacter,
        char_b: IdentifiedCharacter,
        char_chapters: dict[str, list[int]],
    ) -> Optional[HandoffCandidate]:
        """Check if two characters might be a handoff pair."""
        chapters_a = char_chapters.get(char_a.canonical_name, [])
        chapters_b = char_chapters.get(char_b.canonical_name, [])

        # Need chapter data for both
        if not chapters_a or not chapters_b:
            return None

        # Check both directions (A -> B and B -> A)
        candidate_ab = self._check_direction(char_a, char_b, chapters_a, chapters_b)
        candidate_ba = self._check_direction(char_b, char_a, chapters_b, chapters_a)

        # Return the higher confidence one
        if candidate_ab and candidate_ba:
            return candidate_ab if candidate_ab.confidence >= candidate_ba.confidence else candidate_ba
        return candidate_ab or candidate_ba

    def _check_direction(
        self,
        char_a: IdentifiedCharacter,
        char_b: IdentifiedCharacter,
        chapters_a: list[int],
        chapters_b: list[int],
    ) -> Optional[HandoffCandidate]:
        """Check if A hands off to B (A disappears, B appears)."""
        # Must be disjoint or minimal overlap
        overlap = set(chapters_a) & set(chapters_b)
        if len(overlap) > 1:  # Allow at most 1 overlapping chapter
            return None

        last_a = max(chapters_a)
        first_b = min(chapters_b)

        # B must start near where A ends
        gap = first_b - last_a
        if gap < 0 or gap > self.gap_tolerance:
            return None

        # B should appear in limited chapters (suggesting alias, not new character)
        if len(chapters_b) > self.max_b_chapters:
            # Unless B has FEWER chapters than A (B might be the alias)
            if len(chapters_b) >= len(chapters_a):
                return None

        # Calculate confidence
        confidence = self._calculate_confidence(char_a, char_b, chapters_a, chapters_b, gap)

        if confidence < self.min_confidence:
            return None

        # Build reason
        reason = self._build_reason(char_a, char_b, chapters_a, chapters_b, gap)

        return HandoffCandidate(
            name_a=char_a.canonical_name,
            name_b=char_b.canonical_name,
            last_chapter_a=last_a,
            first_chapter_b=first_b,
            confidence=confidence,
            reason=reason,
            chapters_a=chapters_a,
            chapters_b=chapters_b,
            name_similarity=self._name_similarity(char_a.canonical_name, char_b.canonical_name),
        )

    def _calculate_confidence(
        self,
        char_a: IdentifiedCharacter,
        char_b: IdentifiedCharacter,
        chapters_a: list[int],
        chapters_b: list[int],
        gap: int,
    ) -> float:
        """Calculate confidence that A and B are the same person."""
        confidence = 0.4  # Base confidence for sequential chapters

        # +0.2 if A is protagonist/antagonist (important characters more likely to use aliases)
        if char_a.role in ("protagonist", "antagonist"):
            confidence += 0.2

        # +0.15 if names share surname or have similarity
        name_sim = self._name_similarity(char_a.canonical_name, char_b.canonical_name)
        if name_sim > 0.4:
            confidence += 0.15 * name_sim

        # Check for shared surname
        if self._share_surname(char_a.canonical_name, char_b.canonical_name):
            confidence += 0.1

        # Check for nickname patterns (Cal/Caleb, Cathy/Catherine)
        if self._is_nickname_variant(char_a.canonical_name, char_b.canonical_name):
            confidence += 0.2

        # +0.1 if B appears in only 1-2 chapters
        if len(chapters_b) <= 2:
            confidence += 0.1

        # -0.1 if gap is > 1
        if gap > 1:
            confidence -= 0.1

        # -0.2 if B appears in many chapters (likely a real separate character)
        if len(chapters_b) > 3:
            confidence -= 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate string similarity between two names."""
        # Extract first names for comparison
        first1 = name1.split()[0].lower() if name1 else ""
        first2 = name2.split()[0].lower() if name2 else ""

        # Full name comparison
        full_sim = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

        # First name comparison (often more relevant)
        first_sim = SequenceMatcher(None, first1, first2).ratio()

        return max(full_sim, first_sim)

    def _share_surname(self, name1: str, name2: str) -> bool:
        """Check if two names share a surname."""
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) < 2 or len(parts2) < 2:
            return False

        # Compare last parts (surnames)
        return parts1[-1].lower() == parts2[-1].lower()

    def _is_nickname_variant(self, name1: str, name2: str) -> bool:
        """
        Check if names are nickname variants of each other.

        Examples:
        - Cal / Caleb
        - Cathy / Catherine
        - Tom / Thomas
        - Nick / Nicholas
        """
        # Common nickname mappings
        nickname_pairs = [
            ("cal", "caleb"),
            ("cathy", "catherine"),
            ("kate", "catherine"),
            ("tom", "thomas"),
            ("nick", "nicholas"),
            ("bill", "william"),
            ("bob", "robert"),
            ("jim", "james"),
            ("joe", "joseph"),
            ("mike", "michael"),
            ("dan", "daniel"),
            ("sam", "samuel"),
            ("ben", "benjamin"),
            ("alex", "alexander"),
            ("beth", "elizabeth"),
            ("liz", "elizabeth"),
            ("katie", "katherine"),
            ("kate", "katherine"),
            ("meg", "margaret"),
            ("peggy", "margaret"),
            ("dick", "richard"),
            ("rick", "richard"),
            ("ted", "edward"),
            ("ed", "edward"),
            ("tony", "anthony"),
            ("jack", "john"),
        ]

        first1 = name1.split()[0].lower() if name1 else ""
        first2 = name2.split()[0].lower() if name2 else ""

        for short, long in nickname_pairs:
            if (first1 == short and first2 == long) or (first1 == long and first2 == short):
                return True
            # Also check if one starts with the other
            if first1.startswith(first2) or first2.startswith(first1):
                if abs(len(first1) - len(first2)) <= 3:  # Reasonable length difference
                    return True

        return False

    def _is_married_couple(
        self,
        char_a: IdentifiedCharacter,
        char_b: IdentifiedCharacter,
    ) -> bool:
        """
        Check if characters are likely a married couple (should NOT be merged).

        Indicators:
        - Different first names + same surname
        - Mr./Mrs. with same surname
        """
        name_a = char_a.canonical_name
        name_b = char_b.canonical_name

        # Check for Mr./Mrs. pattern
        mr_pattern = r'^(Mr\.?|Mrs\.?|Miss|Ms\.?)\s+'
        is_a_titled = bool(re.match(mr_pattern, name_a, re.IGNORECASE))
        is_b_titled = bool(re.match(mr_pattern, name_b, re.IGNORECASE))

        if is_a_titled and is_b_titled:
            # Both have titles - check if different titles but same surname
            surname_a = name_a.split()[-1].lower() if name_a.split() else ""
            surname_b = name_b.split()[-1].lower() if name_b.split() else ""
            if surname_a == surname_b:
                # Check if one is Mr. and other is Mrs./Miss/Ms.
                is_a_mr = bool(re.match(r'^Mr\.?\s+', name_a, re.IGNORECASE))
                is_b_mr = bool(re.match(r'^Mr\.?\s+', name_b, re.IGNORECASE))
                if is_a_mr != is_b_mr:  # One Mr., one not
                    return True

        # Check for different first names + same surname (Tom Wilson vs Myrtle Wilson)
        parts_a = name_a.split()
        parts_b = name_b.split()
        if len(parts_a) >= 2 and len(parts_b) >= 2:
            first_a = parts_a[0].lower()
            first_b = parts_b[0].lower()
            surname_a = parts_a[-1].lower()
            surname_b = parts_b[-1].lower()

            if surname_a == surname_b and first_a != first_b:
                # Different first names, same surname
                # Check if names are nickname variants
                if not self._is_nickname_variant(name_a, name_b):
                    return True

        return False

    def _build_reason(
        self,
        char_a: IdentifiedCharacter,
        char_b: IdentifiedCharacter,
        chapters_a: list[int],
        chapters_b: list[int],
        gap: int,
    ) -> str:
        """Build a human-readable reason for the handoff."""
        reasons = []

        # Chapter pattern
        if gap == 0:
            reasons.append(f"{char_a.canonical_name} last appears in ch.{max(chapters_a)}, "
                          f"{char_b.canonical_name} first appears in same chapter")
        elif gap == 1:
            reasons.append(f"{char_a.canonical_name} last appears in ch.{max(chapters_a)}, "
                          f"{char_b.canonical_name} first appears in next chapter ({min(chapters_b)})")
        else:
            reasons.append(f"{char_a.canonical_name} ends ch.{max(chapters_a)}, "
                          f"{char_b.canonical_name} starts ch.{min(chapters_b)} ({gap} chapters later)")

        # Chapter count
        if len(chapters_b) <= 2:
            reasons.append(f"{char_b.canonical_name} appears in only {len(chapters_b)} chapter(s)")

        # Name similarity
        if self._is_nickname_variant(char_a.canonical_name, char_b.canonical_name):
            reasons.append("Names appear to be nickname variants")
        elif self._share_surname(char_a.canonical_name, char_b.canonical_name):
            reasons.append("Names share surname")

        # Role
        if char_a.role in ("protagonist", "antagonist"):
            reasons.append(f"{char_a.canonical_name} is {char_a.role}")

        return "; ".join(reasons)


def detect_handoffs(
    characters: list[IdentifiedCharacter],
    summary_map: Optional[ChapterSummaryMap] = None,
    gap_tolerance: int = 2,
    min_confidence: float = 0.5,
) -> list[HandoffCandidate]:
    """
    Convenience function to detect handoff candidates.

    Args:
        characters: List of identified characters
        summary_map: Optional summary map for context
        gap_tolerance: Max chapter gap for handoffs
        min_confidence: Minimum confidence to report

    Returns:
        List of HandoffCandidate pairs
    """
    detector = HandoffDetector(
        gap_tolerance=gap_tolerance,
        min_confidence=min_confidence,
    )
    return detector.detect_handoffs(characters, summary_map)
