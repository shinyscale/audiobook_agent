"""
LLM-based character proposer.

Uses an LLM to identify characters in text with semantic understanding.
"""

import re
from typing import Optional
import logging

from .base import BaseCharacterProposer
from ..models import CharacterProposal, CharacterMention
from ...llm import LLMClient

logger = logging.getLogger(__name__)


CHARACTER_SYSTEM_PROMPT = """You are a literary analyst identifying characters in fiction.

Your task is to find all CHARACTER NAMES mentioned in the text. A character is a person who:
- Has a name (first name, last name, title+name, or nickname)
- Appears in the narrative as a person (not a place, object, or concept)
- May be referred to by different names/titles

Focus on finding:
- Full names: "Jay Gatsby", "Elizabeth Bennet"
- First names only: "Nick", "Daisy"
- Titled names: "Mr. Buchanan", "Lady Catherine"
- Nicknames: "Lizzy", "Old Sport"

Do NOT include:
- Places (East Egg, London)
- Days/months (Monday, January)
- Generic titles without names (the doctor, a woman)
- Non-person entities (companies, newspapers)"""


CHARACTER_PROMPT_TEMPLATE = """Find all CHARACTER NAMES mentioned in this text excerpt.

TEXT:
{text}

Return a JSON array of character names found. For each character:
- "name": The character's name as it appears in the text
- "mentions": Number of times this name appears in this excerpt
- "in_dialogue": Whether this character speaks or is mentioned in dialogue (true/false)
- "confidence": Your confidence this is a real character name (0.0-1.0)

Example response:
```json
[
  {{"name": "Jay Gatsby", "mentions": 5, "in_dialogue": true, "confidence": 0.95}},
  {{"name": "Nick", "mentions": 3, "in_dialogue": false, "confidence": 0.90}}
]
```

Return ONLY the JSON array, no other text. If no characters found, return: []"""


class LLMCharacterProposer(BaseCharacterProposer):
    """
    Proposes characters using LLM semantic analysis.

    Provides deeper understanding than NER, can identify:
    - Characters mentioned indirectly
    - Nicknames and aliases
    - Context about character roles
    """

    name = "llm_character"

    def __init__(
        self,
        llm_client: LLMClient,
        chunk_size: int = 8000,
        context_window: int = 100,
    ):
        """
        Args:
            llm_client: LLM client for queries
            chunk_size: Maximum characters to send to LLM at once
            context_window: Characters of context for mentions
        """
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.context_window = context_window

    def propose(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_start_position: int,
    ) -> list[CharacterProposal]:
        """Extract character proposals from a chapter using LLM."""
        # For shorter chapters, process in one go
        if len(chapter_text) <= self.chunk_size:
            return self._process_chunk(chapter_text, chapter_index, chapter_start_position, 0)

        # For longer chapters, process in chunks and merge
        proposals = []
        chunk_start = 0

        while chunk_start < len(chapter_text):
            chunk_end = min(chunk_start + self.chunk_size, len(chapter_text))

            # Try to break at paragraph boundary
            if chunk_end < len(chapter_text):
                para_break = chapter_text.rfind("\n\n", chunk_start + self.chunk_size - 500, chunk_end)
                if para_break > chunk_start:
                    chunk_end = para_break

            chunk = chapter_text[chunk_start:chunk_end]
            chunk_proposals = self._process_chunk(
                chunk, chapter_index, chapter_start_position, chunk_start
            )
            proposals.extend(chunk_proposals)

            chunk_start = chunk_end

        # Merge proposals for same character across chunks
        return self._merge_chunk_proposals(proposals)

    def _process_chunk(
        self,
        text: str,
        chapter_index: int,
        chapter_start: int,
        chunk_offset: int,
    ) -> list[CharacterProposal]:
        """Process a single chunk of text."""
        prompt = CHARACTER_PROMPT_TEMPLATE.format(text=text[:self.chunk_size])

        result, response = self.llm.query_json(prompt, system=CHARACTER_SYSTEM_PROMPT)

        if result is None:
            logger.warning(f"LLM character proposer failed to parse response")
            return []

        if not isinstance(result, list):
            logger.warning(f"LLM character proposer returned non-list: {type(result)}")
            return []

        proposals = []
        for item in result:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "")
            if not name or len(name) < 2:
                continue

            # Find actual mentions in the text
            mentions = self._find_mentions(text, name, chapter_index, chapter_start, chunk_offset)

            if not mentions:
                # LLM hallucinated a name not in the text
                logger.debug(f"LLM proposed '{name}' but not found in text")
                continue

            confidence = float(item.get("confidence", 0.7))

            proposals.append(CharacterProposal(
                strategy=self.name,
                name=name,
                mentions=mentions,
                confidence=confidence,
                chapter_index=chapter_index,
                reasoning=f"LLM identified as character with {len(mentions)} mentions",
            ))

        return proposals

    def _find_mentions(
        self,
        text: str,
        name: str,
        chapter_index: int,
        chapter_start: int,
        chunk_offset: int,
    ) -> list[CharacterMention]:
        """Find all mentions of a name in the text."""
        mentions = []

        # Escape for regex but allow flexible whitespace
        pattern = re.escape(name)
        pattern = pattern.replace(r"\ ", r"\s+")

        for match in re.finditer(pattern, text, re.IGNORECASE):
            local_pos = match.start()
            global_pos = chapter_start + chunk_offset + local_pos
            context = self._extract_context(text, local_pos, self.context_window)
            in_dialogue = self._is_in_dialogue(text, local_pos)

            mentions.append(CharacterMention(
                text=match.group(0),  # Keep exact text as found
                position=global_pos,
                chapter_index=chapter_index,
                context=context,
                in_dialogue=in_dialogue,
            ))

        return mentions

    def _merge_chunk_proposals(self, proposals: list[CharacterProposal]) -> list[CharacterProposal]:
        """Merge proposals for the same character from different chunks."""
        # Group by normalized name
        by_name = {}

        for prop in proposals:
            name_lower = prop.name.lower()

            if name_lower in by_name:
                # Merge mentions
                existing = by_name[name_lower]
                existing.mentions.extend(prop.mentions)
                # Keep higher confidence
                existing.confidence = max(existing.confidence, prop.confidence)
            else:
                by_name[name_lower] = CharacterProposal(
                    strategy=prop.strategy,
                    name=prop.name,
                    mentions=list(prop.mentions),
                    confidence=prop.confidence,
                    chapter_index=prop.chapter_index,
                    reasoning=prop.reasoning,
                )

        return list(by_name.values())
