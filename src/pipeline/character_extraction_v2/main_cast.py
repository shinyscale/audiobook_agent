"""
Main Cast Extraction from Chapter Summaries (F1)

This module extracts the main cast (10-15 characters) from chapter summaries.
The LLM provides canonical names AND aliases together - no merge step needed.

Key principles:
- Summaries are the source of truth for WHO matters
- Raw text is the source of truth for WHAT they're called (grounding)
- Unnamed/descriptive characters are supported (e.g., "the creature")
- No inventing proper names not supported by the text
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ...llm.client import LLMClient, LLMConfig
from ...models import Character, ConfidenceLevel

logger = logging.getLogger(__name__)


@dataclass
class MainCastProfile:
    """Profile for a main cast character extracted from summaries."""
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    role: str = "supporting"  # protagonist, antagonist, supporting, minor
    description: str = ""
    is_unnamed: bool = False  # True for descriptive handles like "the creature"


MAIN_CAST_PROMPT = """You are a literary analyst extracting the MAIN CAST of characters from a novel.

TASK: Identify the 10-15 most important characters based on the chapter summaries below.

IMPORTANT RULES:
1. Only extract characters who appear MULTIPLE times across chapters or have significant plot impact
2. For each character, provide their canonical name and ALL aliases/variants used in the story
3. If a character is referenced by multiple full names (e.g., maiden/married names like "Daisy Fay" and "Daisy Buchanan"),
   these are the SAME character - use one as canonical and list the other as an alias
4. A full name and a first-name-only reference (e.g., "Elizabeth Bennet" and "Elizabeth") are usually the SAME person
   - include the shorter form as an alias
5. Unnamed characters referenced by recurring descriptive handles (e.g., "the creature", "the stranger")
   ARE valid main cast entries - use their most distinctive recurring handle as the canonical name
6. DO NOT invent proper names that are not supported by the summaries
7. Characters who share a last name but have DIFFERENT first names are typically DIFFERENT people
   (e.g., spouses, siblings, parent/child) - do NOT merge these
8. Characters with DIFFERENT titles before the same surname (Mr./Mrs./Miss/Dr. + Surname) are DIFFERENT people
   - "Mr. Smith" and "Mrs. Smith" are two separate characters (typically spouses)
   - Create separate character entries for each
   - When the summaries show bare surname references (e.g., "Smith did X"), determine from context which character
     is being referred to and include that bare surname as an alias for that character
   - If the bare surname is used ambiguously for multiple family members, include it as an alias for ALL applicable characters
9. Titles and honorifics with a FULL name (e.g., "Mr. John Smith" vs "John Smith") are aliases of the same character

CHAPTER SUMMARIES:
{summaries}

{plot_summary_section}

OUTPUT FORMAT (JSON):
Return a JSON array of character objects:
```json
[
  {{
    "canonical_name": "Full Name or Descriptive Handle",
    "aliases": ["Alias1", "Alias2", "Title + Name"],
    "role": "protagonist|antagonist|supporting|minor",
    "description": "Brief description of character's role in the story",
    "is_unnamed": false
  }}
]
```

EXAMPLES:

Character with maiden/married name variants (SAME person - one entry):
```json
{{
  "canonical_name": "Elizabeth Bennet",
  "aliases": ["Elizabeth", "Lizzy", "Miss Bennet", "Elizabeth Darcy"],
  "role": "protagonist",
  "description": "Spirited young woman who marries Mr. Darcy",
  "is_unnamed": false
}}
```

Character with first-name-only references (SAME person - one entry):
```json
{{
  "canonical_name": "Fitzwilliam Darcy",
  "aliases": ["Mr. Darcy", "Darcy"],
  "role": "protagonist",
  "description": "Wealthy gentleman who falls in love with Elizabeth",
  "is_unnamed": false
}}
```

Spouses with title+surname only (DIFFERENT people - separate entries):
```json
{{
  "canonical_name": "Mr. Smith",
  "aliases": ["Smith"],
  "role": "protagonist",
  "description": "The father of the family",
  "is_unnamed": false
}},
{{
  "canonical_name": "Mrs. Smith",
  "aliases": ["Smith"],
  "role": "supporting",
  "description": "The mother of the family",
  "is_unnamed": false
}}
```

Note: In this example, both characters have "Smith" as an alias because the bare surname is used for both in the text.
If the text only uses "Smith" for one character, only that character should have it as an alias.

Unnamed character (descriptive handle):
```json
{{
  "canonical_name": "the creature",
  "aliases": ["the monster", "the wretch", "the fiend"],
  "role": "antagonist",
  "description": "Victor's creation, a being of immense size",
  "is_unnamed": true
}}
```

Extract the main cast now:"""


class MainCastExtractor:
    """
    Extracts main cast profiles from chapter summaries.

    This is the core of the v2 architecture: instead of extracting names
    and trying to merge them, we ask the LLM to identify the important
    characters with their aliases directly from the summaries.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def extract(
        self,
        chapter_summaries: list[str],
        plot_summary: Optional[str] = None,
    ) -> list[MainCastProfile]:
        """
        Extract main cast profiles from chapter summaries.

        Args:
            chapter_summaries: List of chapter summary strings
            plot_summary: Optional overall plot summary

        Returns:
            List of MainCastProfile objects representing the main cast
        """
        if not chapter_summaries:
            logger.warning("No chapter summaries provided for main cast extraction")
            return []

        # Format summaries for the prompt
        summaries_text = "\n\n".join(
            f"Chapter {i+1}:\n{summary}"
            for i, summary in enumerate(chapter_summaries)
        )

        # Add plot summary if available
        plot_section = ""
        if plot_summary:
            plot_section = f"\nOVERALL PLOT SUMMARY:\n{plot_summary}\n"

        # Build the prompt
        prompt = MAIN_CAST_PROMPT.format(
            summaries=summaries_text,
            plot_summary_section=plot_section,
        )

        # Query LLM
        result, response = self.llm.query_json(prompt)

        if not response.success:
            logger.error(f"LLM query failed: {response.error}")
            return []

        if result is None:
            logger.error("Failed to parse JSON from LLM response")
            return []

        # Parse the result into profiles
        profiles = self._parse_profiles(result)

        logger.info(f"Extracted {len(profiles)} main cast characters from summaries")
        return profiles

    def _parse_profiles(self, result: list | dict) -> list[MainCastProfile]:
        """Parse LLM result into MainCastProfile objects."""
        profiles = []

        # Handle both list and dict with characters key
        if isinstance(result, dict):
            result = result.get("characters", result.get("main_cast", []))

        if not isinstance(result, list):
            logger.warning(f"Expected list, got {type(result)}")
            return []

        for item in result:
            if not isinstance(item, dict):
                continue

            canonical = item.get("canonical_name", "").strip()
            if not canonical:
                continue

            profile = MainCastProfile(
                canonical_name=canonical,
                aliases=[a.strip() for a in item.get("aliases", []) if a.strip()],
                role=item.get("role", "supporting"),
                description=item.get("description", ""),
                is_unnamed=item.get("is_unnamed", False),
            )

            # Ensure canonical name is not in aliases (avoid duplication)
            profile.aliases = [
                a for a in profile.aliases
                if a.lower() != canonical.lower()
            ]

            profiles.append(profile)

        return profiles

    def profiles_to_characters(
        self,
        profiles: list[MainCastProfile],
    ) -> list[Character]:
        """
        Convert MainCastProfile objects to Character model objects.

        Note: These characters are NOT yet grounded - they need mention search
        and grounding gate validation before being considered high-confidence.
        """
        characters = []

        for i, profile in enumerate(profiles):
            char = Character(
                id=f"main_cast_{i}",
                canonical_name=profile.canonical_name,
                aliases=profile.aliases,
                role=profile.role,
                confidence=ConfidenceLevel.MEDIUM,  # Not yet grounded
            )

            # Store description in the descriptions list for compatibility
            if profile.description:
                from ...models import CharacterDescription
                char.descriptions = [
                    CharacterDescription(
                        text=profile.description,
                        source_position=0,
                        confidence=ConfidenceLevel.MEDIUM,
                    )
                ]

            characters.append(char)

        return characters
