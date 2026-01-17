"""
Summary-driven character identification.

Extracts character list from chapter summaries, which already understand
narrative context and correctly handle complex cases like birth names,
nicknames, and family relationships.
"""

import json
import logging
from typing import Optional

from .models import IdentifiedCharacter
from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


CHARACTER_IDENTIFICATION_SYSTEM = """You are a literary analyst identifying characters from chapter summaries.

Your task is to create a unified character list, correctly merging different names
that refer to the same person while keeping distinct characters separate.

CRITICAL RULES:
1. Birth name and assumed/adopted name are the SAME person
   - Example: "James Gatz" and "Jay Gatsby" = SAME person
   - Example: "Saul" and "Paul" = SAME person (biblical name change)

2. First name and title+last name are often the SAME person
   - Example: "Myrtle" and "Mrs. Wilson" = SAME person (if context confirms)
   - Example: "Tom" and "Mr. Buchanan" = SAME person

3. Family members with same last name are DIFFERENT people
   - Example: "Mr. Wilson" (George) and "Mrs. Wilson" (Myrtle) = DIFFERENT people
   - Example: "Mr. McKee" and "Mrs. McKee" = DIFFERENT people (husband and wife)

4. Use summaries to determine relationships
   - If summaries say "X is married to Y", they are different people
   - If summaries say "X, also known as Y", they are the same person

5. Nickname variants are often the SAME person
   - Example: "Cal" and "Caleb" = likely SAME person
   - Example: "Cathy" and "Catherine" = likely SAME person
   - Example: "Tom" and "Thomas", "Nick" and "Nicholas" = SAME person

6. Characters appearing in ADJACENT chapters with similar names are likely the SAME
   - If Character A disappears after chapter X and Character B appears in chapter X+1
   - And their names share a surname or are nickname variants
   - They are likely the same person using different names

7. Single-chapter characters with formal names may be aliases
   - A character appearing in only 1-2 chapters with a full formal name
   - May be an alias of an established character (especially villains/spies)
   - Check if any major character stopped appearing around the same time

Always respond with valid JSON only. No other text."""


CHARACTER_IDENTIFICATION_PROMPT = """Analyze these chapter summaries and plot summary to identify ALL characters.

CHAPTER SUMMARIES:
{chapter_summaries}

PLOT SUMMARY:
{plot_summary}

Create a list of unique characters. For each character:
1. Choose the most commonly used name as canonical_name
2. List ALL other names/titles as aliases
3. Determine their role (protagonist, antagonist, supporting, minor)
4. Note which chapters they appear in
5. Provide a brief description based on the summaries

IMPORTANT MERGE RULES:
- Birth name + assumed name = SAME person (merge them)
- First name + Mrs./Mr. last name = SAME person (if same family, merge them)
- Mr. X and Mrs. X with same last name = DIFFERENT people (spouses, keep separate)
- Different first names = DIFFERENT people (keep separate)
- Nickname variants = SAME person (Cal/Caleb, Cathy/Catherine, Tom/Thomas)
- Adjacent chapter appearance + similar names = likely SAME person (merge them)
- Short-lived formal name + established character disappearing = likely SAME person (alias)

Return a JSON array:
```json
{{
  "characters": [
    {{
      "canonical_name": "Jay Gatsby",
      "aliases": ["Mr. Gatsby", "James Gatz", "Mr. Gatz"],
      "role": "protagonist",
      "chapters_present": [3, 4, 5, 6, 7, 8, 9],
      "brief_description": "A mysterious millionaire who throws lavish parties..."
    }},
    {{
      "canonical_name": "George Wilson",
      "aliases": ["Mr. Wilson", "Wilson"],
      "role": "supporting",
      "chapters_present": [2, 7, 8],
      "brief_description": "A garage owner in the Valley of Ashes..."
    }},
    {{
      "canonical_name": "Myrtle Wilson",
      "aliases": ["Mrs. Wilson", "Myrtle"],
      "role": "supporting",
      "chapters_present": [2, 7],
      "brief_description": "George Wilson's wife and Tom Buchanan's mistress..."
    }}
  ],
  "narrator": {{
    "name": "Nick Carraway",
    "narrative_style": "first-person",
    "role": "First-person narrator and participant in events"
  }}
}}
```

Return ONLY valid JSON. No other text."""


class SummaryDrivenCharacterIdentifier:
    """Extract character list from chapter summaries."""

    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client: LLM client for character identification
        """
        self.llm = llm_client

    def identify_characters(
        self,
        chapter_summaries: list[ChapterSummary],
        plot_summary: str,
    ) -> tuple[list[IdentifiedCharacter], Optional[str], str]:
        """
        Extract characters from summaries.

        The LLM has already done the hard work of understanding
        who is who in the chapter summaries. We extract and unify here.

        Args:
            chapter_summaries: List of chapter summaries
            plot_summary: Overall plot summary

        Returns:
            Tuple of (characters, narrator_name, narrative_style)
        """
        # Build summaries text
        summaries_text = self._format_summaries(chapter_summaries)

        prompt = CHARACTER_IDENTIFICATION_PROMPT.format(
            chapter_summaries=summaries_text,
            plot_summary=plot_summary or "No plot summary available.",
        )

        result, response = self.llm.query_json(prompt, system=CHARACTER_IDENTIFICATION_SYSTEM)

        if not response.success or result is None:
            logger.error(f"Character identification failed: {response.error}")
            # Fall back to extracting characters directly from summaries
            return self._fallback_extraction(chapter_summaries), None, "unknown"

        # Parse the response
        characters = self._parse_character_list(result, chapter_summaries)

        # Extract narrator info
        narrator_info = result.get("narrator", {})
        narrator_name = narrator_info.get("name") if narrator_info else None
        narrative_style = narrator_info.get("narrative_style", "unknown") if narrator_info else "unknown"

        # Mark the narrator in the character list
        if narrator_name:
            for char in characters:
                if char.canonical_name.lower() == narrator_name.lower():
                    char.is_narrator = True
                    char.narrative_role = narrator_info.get("role", "Narrator")
                    break
                # Also check aliases
                if any(alias.lower() == narrator_name.lower() for alias in char.aliases):
                    char.is_narrator = True
                    char.narrative_role = narrator_info.get("role", "Narrator")
                    break

        logger.info(f"Identified {len(characters)} characters from summaries")
        if narrator_name:
            logger.info(f"Narrator: {narrator_name} ({narrative_style})")

        return characters, narrator_name, narrative_style

    def _format_summaries(self, chapter_summaries: list[ChapterSummary]) -> str:
        """Format chapter summaries for the prompt."""
        lines = []
        for summary in chapter_summaries:
            title = summary.chapter_title or f"Chapter {summary.chapter_index}"
            lines.append(f"Chapter {summary.chapter_index} ({title}):")
            lines.append(f"  Summary: {summary.summary}")
            if summary.characters_present:
                lines.append(f"  Characters: {', '.join(summary.characters_present)}")
            lines.append("")
        return "\n".join(lines)

    def _parse_character_list(
        self,
        result: dict,
        chapter_summaries: list[ChapterSummary],
    ) -> list[IdentifiedCharacter]:
        """Parse LLM response into IdentifiedCharacter objects."""
        characters = []
        seen_names = set()  # Track seen names to avoid duplicates

        for char_data in result.get("characters", []):
            canonical = char_data.get("canonical_name", "").strip()
            if not canonical:
                continue

            # Skip if we've already seen this character
            canonical_lower = canonical.lower()
            if canonical_lower in seen_names:
                continue
            seen_names.add(canonical_lower)

            # Also add aliases to seen set
            aliases = [a.strip() for a in char_data.get("aliases", []) if a.strip()]
            for alias in aliases:
                seen_names.add(alias.lower())

            # Determine role
            role_str = char_data.get("role", "supporting").lower()
            if role_str not in ("protagonist", "antagonist", "supporting", "minor"):
                role_str = "supporting"

            # Get chapters
            chapters_present = char_data.get("chapters_present", [])
            if not chapters_present:
                # Try to determine from summaries
                chapters_present = self._find_chapters_for_character(
                    canonical, aliases, chapter_summaries
                )

            first_chapter = min(chapters_present) if chapters_present else 1

            characters.append(IdentifiedCharacter(
                canonical_name=canonical,
                aliases=aliases,
                role=role_str,
                first_appearance_chapter=first_chapter,
                chapters_present=chapters_present,
                brief_description=char_data.get("brief_description", ""),
            ))

        return characters

    def _find_chapters_for_character(
        self,
        canonical: str,
        aliases: list[str],
        chapter_summaries: list[ChapterSummary],
    ) -> list[int]:
        """Find which chapters a character appears in based on summaries."""
        chapters = []
        names_to_check = [canonical.lower()] + [a.lower() for a in aliases]

        for summary in chapter_summaries:
            # Check if any name variant appears in characters_present
            summary_chars_lower = [c.lower() for c in summary.characters_present]
            for name in names_to_check:
                if name in summary_chars_lower:
                    chapters.append(summary.chapter_index)
                    break
            else:
                # Also check the summary text
                summary_lower = summary.summary.lower()
                for name in names_to_check:
                    if name in summary_lower:
                        chapters.append(summary.chapter_index)
                        break

        return sorted(set(chapters))

    def _fallback_extraction(
        self,
        chapter_summaries: list[ChapterSummary],
    ) -> list[IdentifiedCharacter]:
        """
        Fallback: extract characters directly from chapter summaries.

        Used when LLM identification fails.
        """
        logger.warning("Using fallback character extraction from summaries")

        # Collect all character names from summaries
        char_chapters: dict[str, list[int]] = {}

        for summary in chapter_summaries:
            for char_name in summary.characters_present:
                name_lower = char_name.lower()
                if name_lower not in char_chapters:
                    char_chapters[name_lower] = []
                char_chapters[name_lower].append(summary.chapter_index)

        # Create IdentifiedCharacter for each unique name
        characters = []
        for name_lower, chapters in char_chapters.items():
            # Find the original casing
            original_name = name_lower
            for summary in chapter_summaries:
                for char_name in summary.characters_present:
                    if char_name.lower() == name_lower:
                        original_name = char_name
                        break

            characters.append(IdentifiedCharacter(
                canonical_name=original_name,
                aliases=[],
                role="supporting",
                first_appearance_chapter=min(chapters),
                chapters_present=sorted(set(chapters)),
            ))

        return characters


def identify_characters_from_summaries(
    chapter_summaries: list[ChapterSummary],
    plot_summary: str,
    llm_client: LLMClient,
) -> tuple[list[IdentifiedCharacter], Optional[str], str]:
    """
    Convenience function for character identification.

    Args:
        chapter_summaries: List of chapter summaries
        plot_summary: Overall plot summary
        llm_client: LLM client

    Returns:
        Tuple of (characters, narrator_name, narrative_style)
    """
    identifier = SummaryDrivenCharacterIdentifier(llm_client)
    return identifier.identify_characters(chapter_summaries, plot_summary)
