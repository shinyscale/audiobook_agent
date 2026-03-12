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
1. Is this first-person ("I" narration) or third-person? NOTE: These summaries are written in third-person regardless of the original story's style. To detect POV: first-person means the story uses "I"/"we" from a character's direct perspective; third-person/omniscient uses "he"/"she"/"they" even if one character's emotions are the focus. A character referred to as "he/she" is NOT the first-person narrator. IMPORTANT: In first-person stories, the narrator uses "I" for themselves, so their proper name appears LESS FREQUENTLY than the characters they describe. If your proposed narrator is the most-mentioned character, reconsider — the most-mentioned character is usually the SUBJECT of the story, not the narrator.
2. If first-person, WHO is the narrator? Output their EXACT name from the main cast list below. For frame/nested narratives, the OUTER narrator (whose "I" appears outside quotation marks) is the primary narrator; the inner narrator (whose first-person voice appears within quoted dialogue) is secondary. KEY: If a summary says "X recounts/tells their story/experiences to Y" or "X describes events to Y", then X is the INNER narrator and Y is the OUTER primary narrator — output Y's name.
3. Is this a nested/frame narrative with multiple narrators?

CHAPTER SUMMARIES:
{summaries}

MAIN CAST (potential narrators if first-person):
{main_cast}

{plot_summary_section}OUTPUT FORMAT (JSON):
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

Determine the narrative POV now:"""


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

        # Include plot summary when available — it often captures narrative style explicitly
        plot_summary_section = ""
        if plot_summary:
            plot_summary_section = (
                f"PLOT SUMMARY (for narrative style context):\n{plot_summary[:400]}\n\n"
            )

        prompt = NARRATOR_DETECTION_PROMPT.format(
            summaries=summaries_text,
            main_cast=cast_text,
            plot_summary_section=plot_summary_section,
        )

        result, response = self.llm.query_json(prompt)

        # Unwrap single-element list — some LLMs wrap the JSON object in [...]
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict):
            result = result[0]

        if not response.success or result is None or not isinstance(result, dict):
            logger.warning(f"Narrator detection failed or returned non-dict: {response.error}")
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

        # Universal invariant: in first-person narration the narrator uses "I" so their
        # proper name appears LESS frequently than the characters they describe (the narrator
        # says "I went" not "[Name] went"). If the proposed narrator is the MOST-MENTIONED
        # character with ≥5x more mentions than a plausible lower-mention candidate (who
        # has >15 mentions but ≤ proposed_count/3), the assignment is almost certainly wrong:
        # the LLM mistook the story's subject for its narrator. Override narrator_name to
        # clear the assignment so downstream correction steps can recover the true narrator.
        if pov in ("first-person", "epistolary") and narrator_name and main_cast:
            _proposed_id = self._match_to_character(narrator_name, main_cast)
            _proposed = next((c for c in main_cast if c.id == _proposed_id), None) if _proposed_id else None
            if _proposed is not None:
                _proposed_count = getattr(_proposed, "mention_count", 0) or 0
                _others = [(c, getattr(c, "mention_count", 0) or 0) for c in main_cast if c.id != _proposed.id]
                if _others and _proposed_count > 0:
                    _max_other = max(cnt for _, cnt in _others)
                    if _proposed_count > _max_other:
                        # Proposed narrator is the max-mention character — suspicious
                        _plausible = [(c, cnt) for c, cnt in _others if cnt > 15 and cnt <= _proposed_count // 3]
                        if _plausible and _proposed_count >= 5 * min(cnt for _, cnt in _plausible):
                            logger.warning(
                                f"NarratorDetector: Proposed narrator '{narrator_name}' "
                                f"({_proposed_count} mentions) is the most-mentioned character "
                                f"and has ≥5x the mentions of plausible narrator candidates. "
                                f"In first-person stories the narrator uses 'I' so their name "
                                f"appears rarely — this assignment is likely wrong. "
                                f"Clearing narrator_name so fallback steps can recover true narrator."
                            )
                            narrator_name = None

        # Match narrator to main cast character.
        # Universal invariant: only first-person or epistolary narratives have a narrator
        # character. In third-person/omniscient stories the narrator is an external voice,
        # not a cast member — assigning is_narrator to a character in those stories is wrong.
        narrator_id = None
        if narrator_name and pov in ("first-person", "epistolary"):
            narrator_id = self._match_to_character(narrator_name, main_cast)
            if narrator_id:
                logger.info(f"Narrator '{narrator_name}' matched to character ID: {narrator_id}")
            else:
                logger.warning(
                    f"Narrator '{narrator_name}' identified but NOT found in main_cast. "
                    f"Available characters: {[c.canonical_name for c in main_cast]}"
                )
        elif narrator_name and pov not in ("first-person", "epistolary"):
            logger.info(
                f"Narrator name '{narrator_name}' ignored — POV is '{pov}' (not first-person/epistolary); "
                f"no character should be marked as narrator in this narrative mode."
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

        # Pre-compute primary narrator mention count for secondary narrator guard.
        # Universal invariant: in a frame narrative the primary narrator sets the outer
        # frame for the WHOLE story. A secondary narrator only tells their inner portion.
        # A candidate secondary narrator with MORE mentions than the primary narrator is
        # almost certainly a major CHARACTER being narrated about, not an actual narrator.
        primary_mention_count = 0
        if narrator_info.narrator_character_id:
            for c in characters:
                if c.id == narrator_info.narrator_character_id:
                    primary_mention_count = getattr(c, "mention_count", 0) or 0
                    break

        for char in characters:
            # Reset narrator flags
            char.is_narrator = False
            char.narrative_role = None

            # Set narrator flag for the primary narrator
            if char.id == narrator_info.narrator_character_id:
                # Universal invariant: a narrator must be significantly present in the text.
                # A character with ≤ 5 mentions cannot be the narrator — first-person narrators
                # use "I" extensively, so they appear by name infrequently but still several times.
                # A character named 5 or fewer times is peripheral, not the storytelling voice.
                # We only block when mention_count > 0 (i.e., when count was actually computed).
                # mention_count == 0 means "not yet counted" (test/mock scenario), so we allow it.
                mention_count = getattr(char, "mention_count", 0) or 0
                _narrator_blocked = False
                if 0 < mention_count <= 5:
                    logger.warning(
                        f"Narrator '{char.canonical_name}' has only {mention_count} mention(s) — "
                        f"too few to be a first-person narrator (need > 5); skipping narrator assignment"
                    )
                    _narrator_blocked = True
                else:
                    # Relative guard: narrator must have >= 8% of the highest-mention character's count.
                    # Universal invariant: a character whose name-mention count is tiny compared to
                    # the main cast is a background figure, not the storytelling voice.
                    # (First-person narrators use "I" so they have fewer name mentions than characters
                    # they describe — but they still need a meaningful presence in name-based search.)
                    # Only applies when the cast has a high-mention "anchor" character (> 20 mentions),
                    # so this doesn't falsely block narrators in short texts with a flat mention profile.
                    _all_mention_counts = [getattr(c, "mention_count", 0) or 0 for c in characters]
                    _max_mentions = max(_all_mention_counts, default=0)
                    if _max_mentions > 20 and mention_count < _max_mentions * 0.04:
                        logger.warning(
                            f"Narrator '{char.canonical_name}' has only {mention_count} mentions "
                            f"(< 4% of highest-mention character's {_max_mentions}); "
                            f"likely not the narrator — skipping narrator assignment"
                        )
                        _narrator_blocked = True
                if _narrator_blocked:
                    # Clear narrator_info so subsequent pipeline stages don't use this wrong narrator
                    narrator_info.narrator_character_id = None
                    narrator_info.narrator_name = None
                else:
                    char.is_narrator = True
                    char.narrative_role = f"{narrator_info.pov.title()} narrator"
                    # Boost confidence for narrator (they're a key character)
                    char.confidence = ConfidenceLevel.HIGH
                    # Universal invariant: first-person narrators are never minor/supporting.
                    # They are the narrative voice of the story — always protagonist-level.
                    if narrator_info.pov == "first-person" and getattr(char, "role", None) in ("minor", "supporting", "main", None):
                        old_role = getattr(char, "role", None)
                        char.role = "protagonist"
                        logger.info(
                            f"Elevated first-person narrator '{char.canonical_name}' "
                            f"from '{old_role}' to 'protagonist'"
                        )

            # For nested narratives, mark secondary narrators
            elif char.id in narrator_info.nested_narrators:
                secondary_mentions = getattr(char, "mention_count", 0) or 0
                if primary_mention_count > 0 and secondary_mentions > primary_mention_count:
                    logger.warning(
                        f"Secondary narrator candidate '{char.canonical_name}' has "
                        f"{secondary_mentions} mentions vs primary narrator's "
                        f"{primary_mention_count} — rejecting: a character with more mentions "
                        f"than the primary narrator is likely a subject, not a narrator"
                    )
                else:
                    char.is_narrator = True
                    char.narrative_role = "Secondary narrator (nested narrative)"
                    # Also boost confidence for secondary narrators
                    char.confidence = ConfidenceLevel.HIGH

        return characters
