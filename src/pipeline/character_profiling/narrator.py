"""
Narrator detection from summaries.

Identifies the narrator and narrative style from chapter summaries and
plot summary, leveraging the LLM's understanding of narrative structure.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .models import IdentifiedCharacter
from ..llm import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class NarratorInfo:
    """Information about the narrative style and narrator."""
    narrative_style: str  # "first-person", "third-person", "mixed"
    narrator_name: Optional[str]  # Character name if first-person
    narrator_role: str  # Brief description of narrator's relationship to events
    confidence: float

    def to_dict(self) -> dict:
        return {
            "narrative_style": self.narrative_style,
            "narrator_name": self.narrator_name,
            "narrator_role": self.narrator_role,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarratorInfo":
        return cls(
            narrative_style=data.get("narrative_style", "unknown"),
            narrator_name=data.get("narrator_name"),
            narrator_role=data.get("narrator_role", ""),
            confidence=data.get("confidence", 0.5),
        )

    @classmethod
    def third_person(cls) -> "NarratorInfo":
        """Create a third-person narrator info."""
        return cls(
            narrative_style="third-person",
            narrator_name=None,
            narrator_role="External omniscient narrator",
            confidence=0.9,
        )


NARRATOR_DETECTION_SYSTEM = """You are a literary analyst identifying narrative style and narrator.

Focus on:
1. Is this told from a character's perspective (first-person)?
2. Is this told by an external narrator (third-person)?
3. If first-person, which character is telling the story?

Common patterns:
- "The story unfolds through the eyes of X" = first-person narrator X
- "X narrates" or "X tells the story" = first-person narrator X
- References to "I" and "my" in summaries = first-person
- References to characters as "he/she" without a clear narrator = third-person

Always respond with valid JSON. No other text."""


NARRATOR_DETECTION_PROMPT = """Identify the narrative style and narrator from this plot summary.

PLOT SUMMARY:
{plot_summary}

IDENTIFIED CHARACTERS:
{character_list}

Determine:
1. Narrative style: Is this first-person (a character tells the story) or third-person (external narrator)?
2. If first-person: Which character is the narrator?
3. The narrator's role: How do they relate to the events?

Return JSON:
```json
{{
  "narrative_style": "first-person" or "third-person" or "mixed",
  "narrator_name": "Character name if first-person, null if third-person",
  "narrator_role": "Brief description of narrator's relationship to events",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of how you determined this"
}}
```

Return ONLY valid JSON. No other text."""


class NarratorDetector:
    """Detects narrator and narrative style from summaries."""

    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client: LLM client for narrator detection
        """
        self.llm = llm_client

    def detect_narrator(
        self,
        plot_summary: str,
        characters: list[IdentifiedCharacter],
    ) -> NarratorInfo:
        """
        Detect narrator from plot summary.

        The plot summary often contains phrases like:
        "The story unfolds through the eyes of Nick Carraway"

        We use the LLM to extract this information.

        Args:
            plot_summary: The overall plot summary
            characters: List of identified characters

        Returns:
            NarratorInfo with narrative style and narrator details
        """
        if not plot_summary:
            logger.warning("No plot summary provided for narrator detection")
            return NarratorInfo.third_person()

        # Build character list for context
        char_list = ", ".join([c.canonical_name for c in characters])

        prompt = NARRATOR_DETECTION_PROMPT.format(
            plot_summary=plot_summary,
            character_list=char_list or "No characters identified",
        )

        result, response = self.llm.query_json(prompt, system=NARRATOR_DETECTION_SYSTEM)

        if not response.success or result is None:
            logger.warning(f"Narrator detection failed: {response.error}")
            # Fall back to heuristic detection
            return self._fallback_detection(plot_summary)

        return self._parse_result(result)

    def _parse_result(self, result: dict) -> NarratorInfo:
        """Parse LLM response into NarratorInfo."""
        narrative_style = result.get("narrative_style", "unknown")
        if narrative_style not in ("first-person", "third-person", "mixed"):
            narrative_style = "unknown"

        narrator_name = result.get("narrator_name")
        if narrative_style == "third-person":
            narrator_name = None

        narrator_role = result.get("narrator_role", "")

        # F14: Warn when confidence is missing
        confidence_raw = result.get("confidence")
        if confidence_raw is None:
            logger.warning(
                "Narrator detection did not return confidence - using default 0.6"
            )
            confidence = 0.6
        else:
            confidence = float(confidence_raw)

        return NarratorInfo(
            narrative_style=narrative_style,
            narrator_name=narrator_name,
            narrator_role=narrator_role,
            confidence=confidence,
        )

    def _fallback_detection(self, plot_summary: str) -> NarratorInfo:
        """
        Fallback heuristic detection when LLM fails.

        Looks for common patterns in the plot summary.
        """
        summary_lower = plot_summary.lower()

        # First-person indicators
        first_person_patterns = [
            "narrates",
            "tells the story",
            "through the eyes of",
            "from the perspective of",
            "recounts",
            "the narrator,",
        ]

        for pattern in first_person_patterns:
            if pattern in summary_lower:
                return NarratorInfo(
                    narrative_style="first-person",
                    narrator_name=None,  # Can't determine name from heuristic
                    narrator_role="First-person narrator",
                    confidence=0.5,
                )

        # Default to third-person
        return NarratorInfo.third_person()

    def mark_narrator_in_characters(
        self,
        characters: list[IdentifiedCharacter],
        narrator_info: NarratorInfo,
    ) -> None:
        """
        Mark the narrator character in the character list.

        Modifies characters in-place to set is_narrator flag.

        Args:
            characters: List of identified characters (modified in-place)
            narrator_info: Detected narrator information
        """
        if not narrator_info.narrator_name:
            return

        narrator_lower = narrator_info.narrator_name.lower()

        for char in characters:
            # Check canonical name
            if char.canonical_name.lower() == narrator_lower:
                char.is_narrator = True
                char.narrative_role = narrator_info.narrator_role
                logger.info(f"Marked {char.canonical_name} as narrator")
                return

            # Check aliases
            for alias in char.aliases:
                if alias.lower() == narrator_lower:
                    char.is_narrator = True
                    char.narrative_role = narrator_info.narrator_role
                    logger.info(f"Marked {char.canonical_name} as narrator (matched alias: {alias})")
                    return

        logger.warning(
            f"Narrator '{narrator_info.narrator_name}' not found in character list"
        )


def detect_narrator_from_summary(
    plot_summary: str,
    characters: list[IdentifiedCharacter],
    llm_client: LLMClient,
) -> NarratorInfo:
    """
    Convenience function for narrator detection.

    Args:
        plot_summary: The overall plot summary
        characters: List of identified characters
        llm_client: LLM client

    Returns:
        NarratorInfo with narrative style and narrator details
    """
    detector = NarratorDetector(llm_client)
    return detector.detect_narrator(plot_summary, characters)
