"""
Context-aware name disambiguation for same-name characters.

Handles cases like father/son pairs sharing a name (John vs John Donaldson),
multi-generational naming patterns, and other ambiguous name references.

Uses multi-signal disambiguation:
1. Relationship markers (highest) - "his father John", "Sr./Jr.", "the elder"
2. Name-shape markers - sentence includes surname → full-name character wins
3. Temporal markers - "years ago", past perfect tense → older generation
4. Chapter presence (tie-breaker) - if only one candidate active, prefer them
5. LLM classification (gated fallback) - only when heuristics fail
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class AmbiguousName:
    """Represents a name form that could refer to multiple characters."""

    short_name: str  # e.g., "John"
    possible_characters: list[str]  # e.g., ["John", "John Donaldson"]

    def __post_init__(self):
        # Ensure lowercase for matching
        self.short_name_lower = self.short_name.lower()
        self.possible_lower = [c.lower() for c in self.possible_characters]


@dataclass
class DisambiguationResult:
    """Result of disambiguating an ambiguous name reference."""

    resolved_character: str  # The canonical name of the resolved character
    confidence: float  # 0-1, how confident we are
    method: str  # "relationship", "name_shape", "temporal", "chapter_presence", "llm", "default"
    reason: str = ""  # Human-readable explanation


class NameAmbiguityMap:
    """
    Identifies which character names are ambiguous.

    An ambiguous name is one that could refer to multiple characters.
    For example:
    - "John" could be "John" or "John Donaldson"
    - "Ames" could be "Ames" (parents) or "Cathy Ames"
    """

    def __init__(self, characters: list):
        """
        Build ambiguity map from character list.

        Args:
            characters: List of IdentifiedCharacter objects or list of name strings
        """
        self.ambiguous_names: dict[str, AmbiguousName] = {}
        self._build_ambiguity_map(characters)

    def _build_ambiguity_map(self, characters: list) -> None:
        """
        Build the map of ambiguous names.

        A name is ambiguous if:
        1. It's a single-word name that appears as part of a longer name
        2. It's a short-form that could refer to multiple characters
        """
        # Extract all names (canonical + aliases)
        all_names: list[str] = []
        for char in characters:
            if hasattr(char, "canonical_name"):
                all_names.append(char.canonical_name)
                all_names.extend(char.aliases)
            else:
                # Assume it's a string
                all_names.append(str(char))

        # Deduplicate while preserving order
        seen = set()
        unique_names = []
        for name in all_names:
            name_lower = name.lower().strip()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_names.append(name)

        # Find ambiguous names
        for name in unique_names:
            name_lower = name.lower().strip()
            name_parts = name_lower.split()

            # Single-word names
            if len(name_parts) == 1:
                # Check if this word appears in any longer name
                candidates = [name]  # Include self
                for other_name in unique_names:
                    other_lower = other_name.lower().strip()
                    other_parts = other_lower.split()

                    # Skip self
                    if other_lower == name_lower:
                        continue

                    # Check if our word appears as a part in other name
                    if name_lower in other_parts:
                        candidates.append(other_name)

                # If we found other candidates, it's ambiguous
                if len(candidates) > 1:
                    self.ambiguous_names[name_lower] = AmbiguousName(
                        short_name=name,
                        possible_characters=candidates,
                    )
                    logger.debug(
                        f"Ambiguous name detected: '{name}' -> {candidates}"
                    )

            # Multi-word names: check if parts create ambiguity
            else:
                for part in name_parts:
                    if len(part) < 2:  # Skip single-letter parts
                        continue

                    # Check if this part appears in other names
                    candidates = []
                    for other_name in unique_names:
                        other_lower = other_name.lower().strip()
                        other_parts = other_lower.split()

                        if part in other_parts:
                            candidates.append(other_name)

                    # If multiple characters share this name part
                    if len(candidates) > 1 and part not in self.ambiguous_names:
                        self.ambiguous_names[part] = AmbiguousName(
                            short_name=part,
                            possible_characters=candidates,
                        )
                        logger.debug(
                            f"Ambiguous name part detected: '{part}' -> {candidates}"
                        )

    def is_ambiguous(self, name: str) -> bool:
        """Check if a name is ambiguous."""
        return name.lower().strip() in self.ambiguous_names

    def get_possible_characters(self, name: str) -> list[str]:
        """Get the list of characters this name could refer to."""
        name_lower = name.lower().strip()
        if name_lower in self.ambiguous_names:
            return self.ambiguous_names[name_lower].possible_characters
        return [name]  # Not ambiguous, returns itself

    def get_ambiguous_names(self) -> dict[str, AmbiguousName]:
        """Get all ambiguous names."""
        return self.ambiguous_names.copy()


# Relationship marker patterns - detect explicit relationship language
RELATIONSHIP_ELDER_PATTERNS = [
    # Possessive relationship (his/her father/mother)
    r"\b(his|her|their)\s+(father|mother|dad|mom|papa|mama)\b",
    r"\b(father|mother|dad|mom|papa|mama)\s+of\b",
    # Generational markers
    r"\b(Sr\.?|Senior)\b",
    r"\bthe\s+elder\b",
    r"\bold\s+(\w+)\b",  # "old John"
    r"\b(\w+)'s\s+father\b",  # "John's father"
    # First-person family references (often used in memoir-style narration)
    # Useful for cases like american_sir where a father's backstory is told as "my brother John ..."
    r"\bmy\s+brother\b",
    r"\bmy\s+older\s+brother\b",
    r"\bmy\s+elder\s+brother\b",
    # Roman numerals for generations
    r"\b[IVX]+\b",  # I, II, III, IV
]

RELATIONSHIP_YOUNGER_PATTERNS = [
    # Possessive relationship (his/her son/daughter)
    r"\b(his|her|their)\s+(son|daughter|child|boy|girl)\b",
    r"\b(son|daughter|child)\s+of\b",
    # Generational markers
    r"\b(Jr\.?|Junior)\b",
    r"\bthe\s+younger\b",
    r"\byoung\s+(\w+)\b",  # "young John"
    r"\b(\w+)'s\s+(son|daughter)\b",  # "John's son"
    # First-person family references indicating youth
    r"\bmy\s+nephew\b",
    r"\bthe\s+boy\b",
    r"\bthe\s+lad\b",
    r"\bteenage\b",
]

# Temporal markers - detect past/flashback context
TEMPORAL_PAST_PATTERNS = [
    # Past perfect tense
    r"\bhad\s+(been|lived|worked|married|preferred|wanted|loved|hated)\b",
    # Temporal phrases
    r"\byears\s+ago\b",
    r"\blong\s+ago\b",
    r"\bin\s+the\s+past\b",
    r"\bbefore\s+\w+\s+was\s+born\b",
    r"\bwhen\s+\w+\s+was\s+(young|a\s+child|a\s+boy|a\s+girl)\b",
    r"\bin\s+(his|her|their)\s+(youth|younger\s+days)\b",
    r"\bback\s+in\b",
    r"\bonce\s+upon\s+a\s+time\b",
    # Memory/flashback markers
    r"\bremembered\s+how\b",
    r"\brecalled\b",
    r"\bused\s+to\b",
]

# Spanish/multilingual generational markers (for books like 100 Years of Solitude)
SPANISH_ELDER_PATTERNS = [
    r"\bel\s+viejo\b",  # the old man
    r"\bpadre\b",  # father
    r"\bmadre\b",  # mother
]

SPANISH_YOUNGER_PATTERNS = [
    r"\bel\s+joven\b",  # the young man
    r"\bhijo\b",  # son
    r"\bhija\b",  # daughter
    r"\bSegundo\b",  # Second (as in José Arcadio Segundo)
    r"\bTercero\b",  # Third
]


class ContextDisambiguator:
    """
    Disambiguates character references using contextual signals.

    Signal priority (highest to lowest):
    1. Relationship markers (0.95) - "his father John", "Sr./Jr."
    2. Name-shape markers (0.90) - sentence includes surname → full-name wins
    3. Temporal markers (0.80) - past context likely refers to older generation
    4. Chapter-range prior (0.85) - use chapters_present to prefer candidates in/near current chapter
    5. Chapter presence (0.70) - if only one candidate active in summary, prefer them
    6. LLM fallback (0.70) - gated, only when heuristics fail
    """

    def __init__(
        self,
        ambiguity_map: NameAmbiguityMap,
        summary_map: Optional[ChapterSummaryMap] = None,
        llm_client: Optional[LLMClient] = None,
        llm_confidence_threshold: float = 0.6,
        characters: Optional[list] = None,
    ):
        """
        Args:
            ambiguity_map: Map of ambiguous names
            summary_map: Chapter summaries for context
            llm_client: Optional LLM for fallback disambiguation
            llm_confidence_threshold: Minimum confidence before using LLM
            characters: Optional list of IdentifiedCharacter objects for chapter-range prior
        """
        self.ambiguity_map = ambiguity_map
        self.summary_map = summary_map
        self.llm = llm_client
        self.llm_confidence_threshold = llm_confidence_threshold

        # Build chapter index for quick lookup
        self._chapter_summary_index: dict[int, ChapterSummary] = {}
        if summary_map:
            for summary in summary_map.summaries:
                self._chapter_summary_index[summary.chapter_index] = summary

        # Build character lookup by name for chapter-range prior
        self._character_by_name: dict[str, object] = {}
        if characters:
            for char in characters:
                if hasattr(char, "canonical_name"):
                    self._character_by_name[char.canonical_name.lower()] = char
                    for alias in getattr(char, "aliases", []):
                        self._character_by_name[alias.lower()] = char

        # Compile regex patterns
        self._elder_patterns = [
            re.compile(p, re.IGNORECASE) for p in RELATIONSHIP_ELDER_PATTERNS
        ]
        self._younger_patterns = [
            re.compile(p, re.IGNORECASE) for p in RELATIONSHIP_YOUNGER_PATTERNS
        ]
        self._temporal_patterns = [
            re.compile(p, re.IGNORECASE) for p in TEMPORAL_PAST_PATTERNS
        ]
        self._spanish_elder = [
            re.compile(p, re.IGNORECASE) for p in SPANISH_ELDER_PATTERNS
        ]
        self._spanish_younger = [
            re.compile(p, re.IGNORECASE) for p in SPANISH_YOUNGER_PATTERNS
        ]

        # Statistics for logging
        self.stats = {
            "total_disambiguations": 0,
            "by_relationship": 0,
            "by_name_shape": 0,
            "by_temporal": 0,
            "by_chapter_range": 0,
            "by_chapter_presence": 0,
            "by_llm": 0,
            "by_default": 0,
        }

    def is_ambiguous(self, name: str) -> bool:
        """Check if a name is ambiguous."""
        return self.ambiguity_map.is_ambiguous(name)

    def get_summary_for_chapter(self, chapter_index: int) -> Optional[ChapterSummary]:
        """Get the summary for a specific chapter."""
        return self._chapter_summary_index.get(chapter_index)

    def disambiguate(
        self,
        name: str,
        sentence: str,
        chapter_summary: Optional[ChapterSummary] = None,
        chapter_index: Optional[int] = None,
        target_character_names: Optional[list[str]] = None,
        surrounding_context: Optional[str] = None,
    ) -> DisambiguationResult:
        """
        Disambiguate an ambiguous name reference.

        Args:
            name: The ambiguous name found in text
            sentence: The sentence containing the name
            chapter_summary: Chapter summary for context (preferred)
            chapter_index: Chapter index (used to look up summary if not provided)
            target_character_names: Names of the character we're extracting for
            surrounding_context: Optional expanded context (sentences before/after)
                for temporal marker detection

        Returns:
            DisambiguationResult with the resolved character
        """
        self.stats["total_disambiguations"] += 1

        # Get chapter summary if not provided
        if chapter_summary is None and chapter_index is not None:
            chapter_summary = self.get_summary_for_chapter(chapter_index)

        # Get possible characters for this ambiguous name
        candidates = self.ambiguity_map.get_possible_characters(name)

        # If only one candidate (not actually ambiguous), return it
        if len(candidates) <= 1:
            return DisambiguationResult(
                resolved_character=candidates[0] if candidates else name,
                confidence=1.0,
                method="not_ambiguous",
                reason="Name is not ambiguous",
            )

        # Identify which candidate is the "fuller" name (more parts)
        # This helps with name-shape detection
        full_name_candidate = max(candidates, key=lambda c: len(c.split()))
        short_name_candidate = min(candidates, key=lambda c: len(c.split()))

        # Signal 1: Relationship markers (confidence 0.95)
        combined_text = sentence
        if surrounding_context:
            combined_text = f"{surrounding_context}\n{sentence}"

        result = self._check_relationship_markers(
            combined_text, candidates, full_name_candidate, short_name_candidate
        )
        if result:
            self.stats["by_relationship"] += 1
            return result

        # Signal 2: Name-shape markers (confidence 0.9)
        result = self._check_name_shape(
            sentence, name, candidates, full_name_candidate
        )
        if result:
            self.stats["by_name_shape"] += 1
            return result

        # Signal 3: Temporal markers (confidence 0.8)
        # Check both sentence AND surrounding context for temporal cues
        result = self._check_temporal_markers(
            combined_text, candidates, full_name_candidate, short_name_candidate
        )
        if result:
            self.stats["by_temporal"] += 1
            return result

        # Signal 4: Chapter-range prior (confidence 0.85)
        # Use chapters_present from IdentifiedCharacter to prefer candidates in/near this chapter
        if chapter_index is not None and self._character_by_name:
            result = self._check_chapter_range_signal(
                name, chapter_index, candidates
            )
            if result:
                self.stats["by_chapter_range"] += 1
                return result

        # Signal 5: Chapter presence from summary (confidence 0.7)
        if chapter_summary:
            result = self._check_chapter_presence(
                chapter_summary, candidates, target_character_names
            )
            if result:
                self.stats["by_chapter_presence"] += 1
                return result

        # Signal 6: LLM fallback (gated)
        if self.llm and len(candidates) >= 2:
            result = self._llm_disambiguation(
                name, combined_text, candidates, chapter_summary
            )
            if result and result.confidence >= self.llm_confidence_threshold:
                self.stats["by_llm"] += 1
                return result

        # Default: return the short name (the one that actually matched)
        self.stats["by_default"] += 1
        return DisambiguationResult(
            resolved_character=name,
            confidence=0.5,
            method="default",
            reason=f"Could not disambiguate '{name}' - defaulting to matched form",
        )

    def _check_relationship_markers(
        self,
        sentence: str,
        candidates: list[str],
        full_name: str,
        short_name: str,
    ) -> Optional[DisambiguationResult]:
        """Check for explicit relationship markers."""
        sentence_lower = sentence.lower()

        # Check for elder markers
        for pattern in self._elder_patterns:
            if pattern.search(sentence):
                # Elder markers suggest the fuller/parent name
                return DisambiguationResult(
                    resolved_character=full_name,
                    confidence=0.95,
                    method="relationship",
                    reason=f"Relationship marker indicates older generation (matched: {pattern.pattern})",
                )

        # Check for younger markers
        for pattern in self._younger_patterns:
            if pattern.search(sentence):
                # Younger markers suggest the shorter/child name
                return DisambiguationResult(
                    resolved_character=short_name,
                    confidence=0.95,
                    method="relationship",
                    reason=f"Relationship marker indicates younger generation (matched: {pattern.pattern})",
                )

        # Check Spanish markers
        for pattern in self._spanish_elder:
            if pattern.search(sentence):
                return DisambiguationResult(
                    resolved_character=full_name,
                    confidence=0.90,
                    method="relationship",
                    reason=f"Spanish relationship marker indicates older generation",
                )

        for pattern in self._spanish_younger:
            if pattern.search(sentence):
                return DisambiguationResult(
                    resolved_character=short_name,
                    confidence=0.90,
                    method="relationship",
                    reason=f"Spanish relationship marker indicates younger generation",
                )

        return None

    def _check_name_shape(
        self,
        sentence: str,
        matched_name: str,
        candidates: list[str],
        full_name: str,
    ) -> Optional[DisambiguationResult]:
        """
        Check if the sentence contains distinguishing name parts.

        If sentence includes a surname like "Donaldson", assign to "John Donaldson".
        """
        sentence_lower = sentence.lower()
        matched_lower = matched_name.lower()

        # Get the distinguishing parts of the full name
        full_parts = full_name.lower().split()
        matched_parts = matched_lower.split()

        # Find parts in full name that aren't in matched name
        distinguishing_parts = [p for p in full_parts if p not in matched_parts]

        # Check if any distinguishing part appears in the sentence
        for part in distinguishing_parts:
            # Use word boundary matching
            pattern = rf"\b{re.escape(part)}\b"
            if re.search(pattern, sentence_lower):
                return DisambiguationResult(
                    resolved_character=full_name,
                    confidence=0.9,
                    method="name_shape",
                    reason=f"Sentence contains distinguishing name part '{part}'",
                )

        return None

    def _check_temporal_markers(
        self,
        sentence: str,
        candidates: list[str],
        full_name: str,
        short_name: str,
    ) -> Optional[DisambiguationResult]:
        """
        Check for temporal markers indicating past/flashback.

        Past context often refers to an older generation.
        """
        for pattern in self._temporal_patterns:
            if pattern.search(sentence):
                # Past tense/flashback typically refers to older generation
                return DisambiguationResult(
                    resolved_character=full_name,
                    confidence=0.8,
                    method="temporal",
                    reason=f"Temporal marker suggests past context/older generation",
                )

        return None

    def _check_chapter_presence(
        self,
        chapter_summary: ChapterSummary,
        candidates: list[str],
        target_names: Optional[list[str]] = None,
    ) -> Optional[DisambiguationResult]:
        """
        Use chapter presence as a tie-breaker.

        If only ONE candidate is active in the chapter, prefer them.
        """
        active_lower = [c.lower() for c in chapter_summary.active_characters]
        mentioned_lower = [c.lower() for c in chapter_summary.mentioned_characters]

        # Count how many candidates are active vs mentioned
        active_candidates = []
        mentioned_candidates = []

        for candidate in candidates:
            candidate_lower = candidate.lower()
            # Check if candidate (or any part of candidate) is in active/mentioned
            is_active = any(
                candidate_lower in ac or ac in candidate_lower
                for ac in active_lower
            )
            is_mentioned = any(
                candidate_lower in mc or mc in candidate_lower
                for mc in mentioned_lower
            )

            if is_active:
                active_candidates.append(candidate)
            elif is_mentioned:
                mentioned_candidates.append(candidate)

        # If exactly one candidate is active and others are just mentioned
        if len(active_candidates) == 1 and len(mentioned_candidates) >= 1:
            return DisambiguationResult(
                resolved_character=active_candidates[0],
                confidence=0.7,
                method="chapter_presence",
                reason=f"Only '{active_candidates[0]}' is active in this chapter",
            )

        # If only one candidate appears at all
        all_present = active_candidates + mentioned_candidates
        if len(all_present) == 1:
            return DisambiguationResult(
                resolved_character=all_present[0],
                confidence=0.7,
                method="chapter_presence",
                reason=f"Only '{all_present[0]}' appears in this chapter",
            )

        return None

    def _check_chapter_range_signal(
        self,
        name: str,
        chapter_index: int,
        candidates: list[str],
    ) -> Optional[DisambiguationResult]:
        """
        Use chapters_present from IdentifiedCharacter as a disambiguation signal.

        If only one candidate appears in (or near) this chapter, prefer them.
        This is powerful for father/son disambiguation where:
        - Father appears in backstory chapters (early)
        - Son appears in present-day chapters (later)

        Args:
            name: The ambiguous name
            chapter_index: Current chapter index
            candidates: Possible character names

        Returns:
            DisambiguationResult if exactly one candidate matches, else None
        """
        if not self._character_by_name:
            return None

        candidates_in_chapter = []
        candidates_near_chapter = []

        def chapters_from_summary_map_for_char(char_obj: object) -> set[int]:
            """
            Fallback when IdentifiedCharacter.chapters_present is missing/empty.

            Uses ChapterSummaryMap.character_appearances (name -> chapters) by matching
            canonical name and aliases. This avoids an upstream dependency where some
            character lists omit chapters_present.
            """
            if not self.summary_map or not getattr(self.summary_map, "character_appearances", None):
                return set()

            keys = []
            if hasattr(char_obj, "canonical_name"):
                keys.append(getattr(char_obj, "canonical_name"))
            for a in getattr(char_obj, "aliases", []) or []:
                keys.append(a)

            chapters: set[int] = set()
            for k in keys:
                if not k:
                    continue
                k_lower = str(k).lower().strip()
                for appear_name, ch_list in self.summary_map.character_appearances.items():
                    appear_lower = str(appear_name).lower().strip()
                    if appear_lower == k_lower or appear_lower in k_lower or k_lower in appear_lower:
                        for ch in ch_list or []:
                            try:
                                chapters.add(int(ch))
                            except Exception:
                                continue
            return chapters

        for candidate in candidates:
            char = self._character_by_name.get(candidate.lower())
            if not char:
                # Try partial match for multi-word names
                for key, c in self._character_by_name.items():
                    if candidate.lower() in key or key in candidate.lower():
                        char = c
                        break

            if not char or not hasattr(char, "chapters_present"):
                continue

            chapters_present = list(getattr(char, "chapters_present", []) or [])
            if not chapters_present:
                chapters_present = sorted(chapters_from_summary_map_for_char(char))
            if not chapters_present:
                continue

            # Exact chapter match
            if chapter_index in chapters_present:
                candidates_in_chapter.append(candidate)
            # Adjacent chapters (±1) for near-matches
            elif any(ch in chapters_present for ch in [chapter_index - 1, chapter_index + 1]):
                candidates_near_chapter.append(candidate)

        # If exactly one candidate is in this chapter
        if len(candidates_in_chapter) == 1:
            return DisambiguationResult(
                resolved_character=candidates_in_chapter[0],
                confidence=0.85,
                method="chapter_range",
                reason=f"Only '{candidates_in_chapter[0]}' appears in chapter {chapter_index}",
            )

        # If no candidates in chapter but exactly one in adjacent chapters
        if len(candidates_in_chapter) == 0 and len(candidates_near_chapter) == 1:
            return DisambiguationResult(
                resolved_character=candidates_near_chapter[0],
                confidence=0.75,
                method="chapter_range",
                reason=f"Only '{candidates_near_chapter[0]}' appears near chapter {chapter_index}",
            )

        return None

    def _llm_disambiguation(
        self,
        name: str,
        sentence: str,
        candidates: list[str],
        chapter_summary: Optional[ChapterSummary],
    ) -> Optional[DisambiguationResult]:
        """
        Use LLM as fallback for difficult cases.

        Only called when heuristics fail and 2+ candidates are plausible.
        """
        if not self.llm:
            return None

        # Build context for the LLM
        context_parts = [f"Sentence: \"{sentence}\"", ""]
        context_parts.append(f"The name '{name}' appears in this sentence.")
        context_parts.append(f"Possible characters: {', '.join(candidates)}")

        if chapter_summary:
            context_parts.append("")
            context_parts.append(f"Chapter context:")
            context_parts.append(f"  Summary: {chapter_summary.summary}")
            context_parts.append(f"  Active characters: {', '.join(chapter_summary.active_characters)}")
            context_parts.append(f"  Mentioned characters: {', '.join(chapter_summary.mentioned_characters)}")

        prompt = f"""Given this sentence and context, determine which character the name '{name}' refers to.

{chr(10).join(context_parts)}

Which character does '{name}' refer to in this sentence? Respond with ONLY the character name, nothing else.
If you cannot determine, respond with "UNKNOWN"."""

        try:
            # Use low temperature (0.1) for classification tasks - more deterministic
            response = self.llm.query(prompt, temperature=0.1, max_tokens=128)
            if response.success and response.content:
                result = response.content.strip().strip('"').strip("'")

                # Check if result matches any candidate
                result_lower = result.lower()
                for candidate in candidates:
                    if candidate.lower() == result_lower or result_lower in candidate.lower():
                        return DisambiguationResult(
                            resolved_character=candidate,
                            confidence=0.7,  # LLM results get moderate confidence
                            method="llm",
                            reason=f"LLM identified as '{candidate}'",
                        )

        except Exception as e:
            logger.warning(f"LLM disambiguation failed: {e}")

        return None

    def get_stats(self) -> dict:
        """Get disambiguation statistics."""
        return self.stats.copy()


def build_disambiguator(
    characters: list,
    summary_map: Optional[ChapterSummaryMap] = None,
    llm_client: Optional[LLMClient] = None,
) -> tuple[NameAmbiguityMap, ContextDisambiguator]:
    """
    Convenience function to build disambiguation components.

    Args:
        characters: List of IdentifiedCharacter objects
        summary_map: Chapter summaries
        llm_client: Optional LLM for fallback

    Returns:
        Tuple of (NameAmbiguityMap, ContextDisambiguator)
    """
    ambiguity_map = NameAmbiguityMap(characters)
    disambiguator = ContextDisambiguator(
        ambiguity_map=ambiguity_map,
        summary_map=summary_map,
        llm_client=llm_client,
        characters=characters,  # Pass for chapter-range prior
    )

    # Log detected ambiguities
    ambiguous = ambiguity_map.get_ambiguous_names()
    if ambiguous:
        logger.info(f"Detected {len(ambiguous)} ambiguous name forms:")
        for name, ambig in ambiguous.items():
            logger.info(f"  '{name}' -> {ambig.possible_characters}")
    else:
        logger.debug("No ambiguous names detected")

    return ambiguity_map, disambiguator
