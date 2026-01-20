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
from typing import Optional

from ...llm.client import LLMClient
from ...models import Character

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
        main_cast: list[Character],
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
            f"Chapter {i+1}:\n{s}"
            for i, s in enumerate(selected)
            if not s.startswith("[...")
        )

        # Format main cast for context
        cast_text = "\n".join(
            f"- {c.canonical_name} ({c.role}): {self._get_description(c)}"
            for c in main_cast
        )

        prompt = NARRATOR_DETECTION_PROMPT.format(
            summaries=summaries_text,
            main_cast=cast_text,
        )

        result, response = self.llm.query_json(prompt)

        if not response.success or result is None:
            logger.warning(f"Narrator detection failed: {response.error}")
            return self._fallback_detection(chapter_summaries)

        return self._parse_result(result, main_cast)

    def _get_description(self, char: Character) -> str:
        """Get a brief description from a character."""
        if char.descriptions:
            return char.descriptions[0].text[:100]
        return "No description"

    def _parse_result(
        self,
        result: dict,
        main_cast: list[Character],
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
        main_cast: list[Character],
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

            # Partial match (first name or last name)
            if name_lower in char.canonical_name.lower():
                return char.id

        return None

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
        characters: list[Character],
        narrator_info: NarratorInfo,
    ) -> list[Character]:
        """
        Update character objects with narrator information.

        Args:
            characters: List of characters
            narrator_info: Detected narrator info

        Returns:
            Updated character list with narrator flags set
        """
        for char in characters:
            # Reset narrator flags
            char.is_narrator = False
            char.narrative_role = None

            # Set narrator flag for the primary narrator
            if char.id == narrator_info.narrator_character_id:
                char.is_narrator = True
                char.narrative_role = f"{narrator_info.pov.title()} narrator"

            # For nested narratives, mark secondary narrators
            elif char.id in narrator_info.nested_narrators:
                char.is_narrator = True
                char.narrative_role = "Secondary narrator (nested narrative)"

        return characters
