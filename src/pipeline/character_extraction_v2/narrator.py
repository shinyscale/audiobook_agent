"""
Narrator Detection from Summaries (F4)

Detects the narrative POV and narrator from chapter summaries.
Runs AFTER main cast extraction so we can match the narrator to a character.

Key improvements over v1:
- Uses summaries, not raw pronoun density
- Runs after main cast is known
- Handles nested/epistolary narratives
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Union

from ...llm.client import LLMClient
from ...models import Character as ModelsCharacter
from ..character_extraction.models import Character as V1Character
from .main_cast import MainCastProfile

logger = logging.getLogger(__name__)


@dataclass
class NarratorInfo:
    """Information about the narrative point of view."""

    pov: str  # "first-person", "third-person", "omniscient", "epistolary"
    narrator_character_id: Optional[str] = None  # If first-person, which character
    narrator_name: Optional[str] = None
    is_nested: bool = False  # Multiple narrators (Frankenstein, Dracula)
    nested_narrators: list[str] = field(default_factory=list)  # Character IDs
    confidence: float = 0.8


NARRATOR_DETECTION_PROMPT = """You are analyzing a novel's narrative point of view.

Based on the summaries below, determine:
1. Is this told in first-person (narrator says "I") or third-person?
2. If first-person, WHO is the narrator? (must be a character from the main cast)
3. Is this a nested/frame narrative with multiple narrators?

CHAPTER SUMMARIES:
{summaries}

MAIN CAST (potential narrators if first-person):
{main_cast}

OUTPUT FORMAT (JSON):
```json
{{
  "pov": "first-person|third-person|omniscient|epistolary",
  "narrator_name": "Character Name or null if third-person",
  "is_nested": false,
  "nested_narrators": [],
  "reasoning": "Brief explanation of your determination"
}}
```

For nested narratives (like Frankenstein with Walton's letters framing Victor's story):
```json
{{
  "pov": "epistolary",
  "narrator_name": "Robert Walton",
  "is_nested": true,
  "nested_narrators": ["Robert Walton", "Victor Frankenstein", "the creature"],
  "reasoning": "Frame narrative: Walton's letters contain Victor's story, which contains the creature's story"
}}
```

Analyze the narrative structure now:"""


class NarratorDetector:
    """
    Detects narrative POV and narrator from summaries.

    Uses the main cast context to identify which character is narrating
    (if first-person), avoiding the v1 problem of running narrator detection
    before knowing who the characters are.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def detect(
        self,
        chapter_summaries: list[str],
        main_cast: list[Union[ModelsCharacter, V1Character, MainCastProfile]],
        plot_summary: Optional[str] = None,
    ) -> NarratorInfo:
        """
        Detect narrative POV and narrator from summaries.

        Args:
            chapter_summaries: List of chapter summary strings
            main_cast: List of main cast characters (for matching)
            plot_summary: Optional overall plot summary

        Returns:
            NarratorInfo with POV and narrator details
        """
        if not chapter_summaries:
            logger.warning("No chapter summaries for narrator detection")
            return NarratorInfo(pov="unknown", confidence=0.0)

        # Format summaries (use first few and last few for long books)
        if len(chapter_summaries) > 8:
            selected = (
                chapter_summaries[:4]
                + ["[... middle chapters omitted ...]"]
                + chapter_summaries[-4:]
            )
        else:
            selected = chapter_summaries

        summaries_text = "\n\n".join(
            f"Chapter {i+1}:\n{s}" for i, s in enumerate(selected) if not s.startswith("[...")
        )

        # Format main cast for context
        cast_text = "\n".join(
            f"- {c.canonical_name} ({c.role}): {self._get_description(c)}" for c in main_cast
        )

        prompt = NARRATOR_DETECTION_PROMPT.format(
            summaries=summaries_text,
            main_cast=cast_text,
        )

        result, response = self.llm.query_json(prompt)

        if not response.success or result is None:
            logger.warning(f"Narrator detection failed: {response.error}")
            return self._fallback_detection(chapter_summaries)

        logger.info(
            f"Narrator detection LLM result: pov={result.get('pov')}, "
            f"narrator_name={result.get('narrator_name')}, is_nested={result.get('is_nested')}"
        )
        return self._parse_result(result, main_cast)

    def _get_description(self, char) -> str:
        """Get a brief description from a character.

        Args:
            char: MainCastProfile, V1Character (with description str), or ModelsCharacter (with descriptions list)
        """
        # Handle V1Character objects (from character_extraction.models - has singular 'description')
        if hasattr(char, 'description') and isinstance(char.description, str):
            return char.description[:100] if char.description else "No description"

        # Handle ModelsCharacter objects (from models.py - has plural 'descriptions')
        if hasattr(char, 'descriptions') and char.descriptions:
            # descriptions is a list of CharacterDescription objects
            return char.descriptions[0].text[:100]

        return "No description"

    def _parse_result(
        self,
        result: dict,
        main_cast: list[Union[ModelsCharacter, V1Character, MainCastProfile]],
    ) -> NarratorInfo:
        """Parse LLM result into NarratorInfo."""
        pov = result.get("pov", "unknown").lower()
        narrator_name = result.get("narrator_name")
        is_nested = result.get("is_nested", False)
        nested_narrators = result.get("nested_narrators", [])

        # Match narrator to main cast character
        narrator_id = None
        if narrator_name:
            narrator_id = self._match_to_character(narrator_name, main_cast)
            if narrator_id:
                logger.info(f"Narrator '{narrator_name}' matched to character ID: {narrator_id}")
            else:
                logger.warning(
                    f"Narrator '{narrator_name}' identified but NOT found in main_cast. "
                    f"Available characters: {[c.canonical_name for c in main_cast]}"
                )

                # DETERMINISTIC FIX: If LLM returned generic "Narrator" and POV is first-person,
                # identify the actual narrator by mention count and role.
                # The narrator is typically the most-mentioned protagonist in first-person narratives.
                if narrator_name.lower() in ("narrator", "the narrator") and pov == "first-person":
                    narrator_id = self._identify_narrator_by_prominence(main_cast)
                    if narrator_id:
                        matched_char = next((c for c in main_cast if c.id == narrator_id), None)
                        if matched_char:
                            narrator_name = matched_char.canonical_name
                            logger.info(
                                f"Deterministic narrator identification: '{narrator_name}' "
                                f"selected as primary narrator based on prominence"
                            )

        # Match nested narrators to characters
        nested_ids = []
        for name in nested_narrators:
            char_id = self._match_to_character(name, main_cast)
            if char_id:
                nested_ids.append(char_id)

        return NarratorInfo(
            pov=pov,
            narrator_character_id=narrator_id,
            narrator_name=narrator_name,
            is_nested=is_nested,
            nested_narrators=nested_ids,
            confidence=0.85 if narrator_id else 0.7,
        )

    def _match_to_character(
        self,
        name: str,
        main_cast: list[Union[ModelsCharacter, V1Character, MainCastProfile]],
    ) -> Optional[str]:
        """Match a narrator name to a main cast character."""
        if not name:
            return None

        name_lower = name.lower()

        for char in main_cast:
            # Check canonical name
            if char.canonical_name.lower() == name_lower:
                return char.id

            # Check aliases
            for alias in char.aliases:
                if alias.lower() == name_lower:
                    return char.id

            # Partial match (bidirectional - handles both "Walton" and "Robert Walton")
            char_name_lower = char.canonical_name.lower()
            if name_lower in char_name_lower or char_name_lower in name_lower:
                return char.id

        return None

    def _identify_narrator_by_prominence(
        self,
        main_cast: list[Union[ModelsCharacter, V1Character, MainCastProfile]],
    ) -> Optional[str]:
        """
        Identify the narrator from main cast using deterministic signals.

        For first-person narratives where LLM returns generic "Narrator":
        1. Prefer characters explicitly marked as protagonist
        2. Prefer characters appearing in more chapters/sections (narrator has broadest presence)
        3. If tied, select the most-mentioned character
        4. If still tied, prefer characters with more aliases (more detail = more likely POV)

        This provides a deterministic fallback when summaries use "the narrator"
        instead of the character's name.

        Args:
            main_cast: List of main cast characters

        Returns:
            Character ID of the most likely narrator, or None if unclear
        """
        if not main_cast:
            return None

        # Signal 1: Explicit protagonist role
        protagonists = [c for c in main_cast if getattr(c, 'role', '') == 'protagonist']
        if len(protagonists) == 1:
            logger.info(
                f"Narrator identified by protagonist role: {protagonists[0].canonical_name}"
            )
            return protagonists[0].id

        # Use all main_cast if no protagonist, or filter to protagonists if multiple
        candidates = protagonists if len(protagonists) > 1 else main_cast

        # Signal 2: Chapter presence (narrator typically appears in most/all chapters)
        # Sort by chapters_present count if available
        candidates_with_chapters = [
            c for c in candidates
            if hasattr(c, 'chapters_present') and c.chapters_present
        ]

        if candidates_with_chapters:
            sorted_by_chapters = sorted(
                candidates_with_chapters,
                key=lambda c: len(c.chapters_present),
                reverse=True,
            )
            top_char = sorted_by_chapters[0]
            top_chapter_count = len(top_char.chapters_present)

            # If one character appears in significantly more chapters, they're likely the narrator
            if (
                len(sorted_by_chapters) == 1
                or top_chapter_count > len(sorted_by_chapters[1].chapters_present) * 1.2
            ):
                logger.info(
                    f"Narrator identified by chapter presence: {top_char.canonical_name} "
                    f"(appears in {top_chapter_count} chapters)"
                )
                return top_char.id

            # Filter to characters with similar chapter presence for next signal
            candidates = [
                c for c in sorted_by_chapters
                if len(c.chapters_present) >= top_chapter_count * 0.9
            ]

        # Signal 3: Highest mention count (narrator is typically well-mentioned)
        sorted_by_mentions = sorted(
            candidates,
            key=lambda c: getattr(c, 'mention_count', 0),
            reverse=True,
        )

        if not sorted_by_mentions:
            return None

        top_char = sorted_by_mentions[0]
        top_mentions = getattr(top_char, 'mention_count', 0)

        # If there's a clear leader in mentions, that's likely the narrator
        if len(sorted_by_mentions) == 1 or (
            len(sorted_by_mentions) > 1
            and top_mentions > getattr(sorted_by_mentions[1], 'mention_count', 0) * 1.2
        ):
            logger.info(
                f"Narrator identified by mention count: {top_char.canonical_name} "
                f"({top_mentions} mentions)"
            )
            return top_char.id

        # Signal 4: Tiebreaker - prefer character with more aliases (more detail)
        tied = [c for c in sorted_by_mentions if getattr(c, 'mention_count', 0) >= top_mentions * 0.9]
        if len(tied) > 1:
            tied_sorted = sorted(tied, key=lambda c: len(c.aliases), reverse=True)
            logger.info(
                f"Narrator identified by alias count (tiebreaker): {tied_sorted[0].canonical_name}"
            )
            return tied_sorted[0].id

        return top_char.id

    def _fallback_detection(self, summaries: list[str]) -> NarratorInfo:
        """Simple fallback using keyword detection."""
        # Combine summaries and look for first-person indicators
        combined = " ".join(summaries).lower()

        first_person_indicators = [
            "the narrator",
            "i went",
            "i saw",
            "i felt",
            "tells the story",
            "recounts",
            "our narrator",
        ]

        for indicator in first_person_indicators:
            if indicator in combined:
                return NarratorInfo(
                    pov="first-person",
                    confidence=0.5,
                )

        return NarratorInfo(
            pov="third-person",
            confidence=0.5,
        )

    def update_characters_with_narrator(
        self,
        characters: list[Union[ModelsCharacter, V1Character, MainCastProfile]],
        narrator_info: NarratorInfo,
    ) -> list[Union[ModelsCharacter, V1Character, MainCastProfile]]:
        """
        Update character objects with narrator information.

        Args:
            characters: List of characters
            narrator_info: Detected narrator info

        Returns:
            Updated character list with narrator flags set
        """
        from ...models import ConfidenceLevel

        for char in characters:
            # Reset narrator flags
            char.is_narrator = False
            char.narrative_role = None

            # Set narrator flag for the primary narrator
            if char.id == narrator_info.narrator_character_id:
                char.is_narrator = True
                char.narrative_role = f"{narrator_info.pov.title()} narrator"
                # Boost confidence for narrator (they're a key character)
                char.confidence = ConfidenceLevel.HIGH

            # For nested narratives, mark secondary narrators
            elif char.id in narrator_info.nested_narrators:
                char.is_narrator = True
                char.narrative_role = "Secondary narrator (nested narrative)"
                # Also boost confidence for secondary narrators
                char.confidence = ConfidenceLevel.HIGH

        return characters
