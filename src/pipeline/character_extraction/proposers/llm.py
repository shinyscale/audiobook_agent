"""
LLM-based character proposer.

Uses an LLM to identify characters in text with semantic understanding.
"""

import re
from typing import Optional
import logging

from .base import BaseCharacterProposer
from ..models import CharacterProposal, CharacterMention, CharacterType
from ...llm import LLMClient

logger = logging.getLogger(__name__)


# Pronoun/determiner stopwords - should never be extracted as characters
PRONOUN_STOPWORDS = {
    'he', 'she', 'it', 'they', 'we', 'i', 'you',
    'him', 'her', 'them', 'us', 'me',
    'his', 'hers', 'its', 'their', 'our', 'my', 'your',
    'this', 'that', 'these', 'those', 'the', 'a', 'an',
}


CHARACTER_SYSTEM_PROMPT = """You are a literary analyst identifying characters in fiction.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or characters.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

Your task is to find all CHARACTER NAMES mentioned in the text and classify them.

CHARACTER TYPES:
- "story": Active participants in the narrative - they appear in scenes, speak, act, or have things happen to them in the story
- "historical": Real historical figures mentioned in passing (e.g., Martin Luther King, Napoleon, Einstein) - not active in the story
- "referenced": Fictional characters from OTHER works mentioned (e.g., Hamlet, Sherlock Holmes, Macduff) - not active in this story
- "descriptive": Recurring descriptive handles for unnamed characters who speak or act (e.g., "the creature", "the detective", "the old man")

Focus on finding:
- Full names: "Sarah Miller", "Robert Chen"
- First names only: "Michael", "Emma"
- Titled names: "Mr. Anderson", "Dr. Williams"
- Nicknames: "Mike", "Liz"
- Descriptive handles: ONLY if they refer to a person who speaks/acts AND appear 3+ times in the excerpt
  Examples: "the creature said", "the monster walked", "the old man replied"

Do NOT include:
- Places (Riverside, London)
- Days/months (Monday, January)
- One-off generic references (a waiter, some stranger, a woman)
- Non-person entities (companies, newspapers)
- Objects or locations ("the house", "the door", "the room")"""


CHARACTER_PROMPT_TEMPLATE = """Find all CHARACTER NAMES mentioned in this text excerpt and classify each one.

TEXT:
{text}

Return a JSON array of character names found. For each character:
- "name": The character's name as it appears in the text
- "type": Classification - "story", "historical", "referenced", or "descriptive"
- "mentions": Number of times this name appears in this excerpt
- "in_dialogue": Whether this character speaks or is mentioned in dialogue (true/false)
- "acts": Whether this character performs actions in the text (speaks, walks, grabs, etc.) - true/false
- "confidence": Your confidence this is a real character name (0.0-1.0)

For "descriptive" type (unnamed characters like "the creature", "the detective"):
- Only include if the handle appears 3+ times in the excerpt
- Only include if the handle refers to a person who speaks or acts (acts: true)

Example response:
```json
[
  {{"name": "Mike Mitchell", "type": "story", "mentions": 5, "in_dialogue": true, "acts": true, "confidence": 0.95}},
  {{"name": "Martin Luther King", "type": "historical", "mentions": 1, "in_dialogue": false, "acts": false, "confidence": 0.95}},
  {{"name": "the creature", "type": "descriptive", "mentions": 4, "in_dialogue": true, "acts": true, "confidence": 0.85}}
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

        if not response.success:
            # HTTP error or connection failure - fail fast instead of returning empty list
            error_msg = f"LLM character proposer failed: {response.error}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if result is None:
            # JSON parsing failure - fail fast instead of returning empty list
            error_msg = f"LLM character proposer failed to parse response: {response.content[:200] if response.content else 'empty response'}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(result, list):
            # Try to extract list from dict response (some models wrap in {"characters": [...]})
            if isinstance(result, dict):
                # Check common keys that might contain the list
                for key in ["characters", "items", "results", "data"]:
                    if key in result and isinstance(result[key], list):
                        logger.debug(f"LLM character proposer: extracted list from dict key '{key}'")
                        result = result[key]
                        break
                else:
                    error_msg = f"LLM character proposer returned dict without list: {list(result.keys()) if result else 'empty'}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                error_msg = f"LLM character proposer returned non-list: {type(result)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        proposals = []
        for item in result:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "")
            if not name or len(name) < 2:
                continue

            # Filter out pronouns/determiners
            if name.lower() in PRONOUN_STOPWORDS:
                logger.debug(f"Filtered stopword: '{name}'")
                continue

            # Minimum length guardrail: single-word names must be > 2 chars
            if len(name.split()) == 1 and len(name) <= 2:
                logger.debug(f"Filtered short name: '{name}'")
                continue

            # Find actual mentions in the text
            mentions = self._find_mentions(text, name, chapter_index, chapter_start, chunk_offset)

            if not mentions:
                # LLM hallucinated a name not in the text
                logger.debug(f"LLM proposed '{name}' but not found in text")
                continue

            confidence = float(item.get("confidence", 0.7))

            # Extract character type
            char_type_str = item.get("type", "uncertain")
            try:
                char_type = CharacterType(char_type_str)
            except ValueError:
                char_type = CharacterType.UNCERTAIN

            proposals.append(CharacterProposal(
                strategy=self.name,
                name=name,
                mentions=mentions,
                confidence=confidence,
                chapter_index=chapter_index,
                reasoning=f"LLM identified as {char_type.value} character with {len(mentions)} mentions",
                character_type=char_type,
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
        # Add word boundaries to prevent substring matches (e.g., 'he' in 'the')
        pattern = r'\b' + pattern + r'\b'

        for match in re.finditer(pattern, text, re.IGNORECASE):
            local_pos = match.start()
            global_pos = chapter_start + chunk_offset + local_pos
            context = self._extract_context(text, local_pos, self.context_window)
            in_dialogue = self._is_in_dialogue(text, local_pos)
            is_agentive = self._detect_agentive_context(context)

            mentions.append(CharacterMention(
                text=match.group(0),  # Keep exact text as found
                position=global_pos,
                chapter_index=chapter_index,
                context=context,
                in_dialogue=in_dialogue,
                is_agentive=is_agentive,
            ))

        return mentions

    def _detect_agentive_context(self, context: str) -> bool:
        """
        Detect if the context indicates agentive behavior (speaking/acting).

        Returns True if the context contains action verbs that suggest the
        character is performing an action (said, walked, grabbed, etc.).
        """
        agentive_patterns = [
            r'\b(said|asked|replied|whispered|shouted|called|cried|muttered|exclaimed)\b',
            r'\b(walked|ran|stood|turned|looked|smiled|laughed|nodded|frowned)\b',
            r'\b(grabbed|took|held|threw|placed|opened|closed|pushed|pulled)\b',
            r'\b(sat|came|went|entered|left|arrived|departed|approached|retreated)\b',
        ]
        return any(re.search(p, context.lower()) for p in agentive_patterns)

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
                # Keep first non-UNCERTAIN character type
                if existing.character_type == CharacterType.UNCERTAIN and prop.character_type != CharacterType.UNCERTAIN:
                    existing.character_type = prop.character_type
            else:
                by_name[name_lower] = CharacterProposal(
                    strategy=prop.strategy,
                    name=prop.name,
                    mentions=list(prop.mentions),
                    confidence=prop.confidence,
                    chapter_index=prop.chapter_index,
                    reasoning=prop.reasoning,
                    character_type=prop.character_type,
                )

        return list(by_name.values())
