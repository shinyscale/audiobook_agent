"""
NER-based character proposer.

Wraps the existing CharacterExtractor from src/analysis/characters.py
to work as a proposer in the pipeline.
"""

import re
from typing import Optional
from collections import defaultdict
import logging

from .base import BaseCharacterProposer
from ..models import CharacterProposal, CharacterMention, CharacterType

logger = logging.getLogger(__name__)

# Try to import spaCy
try:
    import spacy
    _HAS_SPACY = True
except ImportError:
    spacy = None
    _HAS_SPACY = False


# Common false positive names (copied from characters.py for independence)
FALSE_POSITIVE_NAMES = {
    'god', 'lord', 'sir', 'madam', 'ma\'am', 'mr', 'mrs', 'ms', 'miss',
    'dr', 'doctor', 'professor', 'captain', 'colonel', 'general',
    'king', 'queen', 'prince', 'princess', 'duke', 'duchess',
    'dear', 'honey', 'sweetheart', 'darling',
    'mom', 'dad', 'mother', 'father', 'grandma', 'grandpa',
    'uncle', 'aunt', 'brother', 'sister', 'son', 'daughter',
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'chapter', 'prologue', 'epilogue', 'part', 'the', 'and', 'but',
    # Pronouns - should never be extracted as characters
    'he', 'she', 'it', 'they', 'we', 'i', 'you',
    'him', 'her', 'them', 'us', 'me',
}

PLACE_SUFFIXES = {
    'manor', 'house', 'castle', 'hall', 'park', 'gardens', 'street',
    'road', 'abbey', 'priory', 'inn', 'hotel', 'cottage', 'estate',
    'cemetery', 'boulangerie', 'café', 'château', 'salon', 'island',
    'city', 'town', 'village', 'county', 'state', 'country',
}


class NERProposer(BaseCharacterProposer):
    """
    Proposes characters using Named Entity Recognition.

    Uses spaCy NER when available, falls back to regex patterns.
    """

    name = "ner"

    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        min_mentions: int = 1,
        context_window: int = 100,
    ):
        """
        Args:
            spacy_model: spaCy model to use
            min_mentions: Minimum mentions in chapter to propose
            context_window: Characters of context around each mention
        """
        self.min_mentions = min_mentions
        self.context_window = context_window
        self.nlp = None
        self.use_spacy = False

        if _HAS_SPACY:
            for model_name in [spacy_model, "en_core_web_sm", "en_core_web_md", "en_core_web_lg"]:
                try:
                    self.nlp = spacy.load(model_name)
                    self.use_spacy = True
                    logger.info(f"NER proposer using spaCy model: {model_name}")
                    break
                except OSError:
                    continue

        if not self.use_spacy:
            logger.warning("spaCy not available, NER proposer will use regex fallback")

    def propose(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_start_position: int,
    ) -> list[CharacterProposal]:
        """Extract character proposals from a chapter using NER."""
        if self.use_spacy:
            candidates = self._extract_with_spacy(chapter_text, chapter_index, chapter_start_position)
        else:
            candidates = self._extract_with_regex(chapter_text, chapter_index, chapter_start_position)

        # Convert candidates to proposals
        proposals = []
        for name, mentions in candidates.items():
            if len(mentions) >= self.min_mentions:
                # Calculate confidence based on mention count and consistency
                confidence = min(0.9, 0.5 + len(mentions) * 0.1)

                # Infer character type from context
                char_type = self._infer_character_type(name, mentions)

                proposals.append(CharacterProposal(
                    strategy=self.name,
                    name=name,
                    mentions=mentions,
                    confidence=confidence,
                    chapter_index=chapter_index,
                    reasoning=f"Found {len(mentions)} mentions via {'spaCy NER' if self.use_spacy else 'regex patterns'}",
                    character_type=char_type,
                ))

        # Extract first names from full names and create additional proposals
        # This helps with alias resolution (e.g., "Jordan" from "Jordan Baker" or "Miss Jordan Baker")
        first_name_proposals = []
        for proposal in proposals:
            if ' ' in proposal.name:
                first_names = self._extract_first_names(proposal.name)
                for fname in first_names:
                    # Skip if this first name already exists as a standalone proposal
                    if any(p.name == fname for p in proposals):
                        continue

                    # Create new proposals for first name using same mentions as full name
                    # (consensus stage will merge these appropriately)
                    first_name_proposals.append(CharacterProposal(
                        strategy=f"{self.name}_firstname",
                        name=fname,
                        mentions=proposal.mentions,  # Share mentions with full name
                        confidence=0.7,  # Lower confidence than full name
                        chapter_index=chapter_index,
                        reasoning=f"First name extracted from '{proposal.name}'",
                    ))

        proposals.extend(first_name_proposals)
        if first_name_proposals:
            logger.debug(f"Extracted {len(first_name_proposals)} first-name proposals from full names")

        return proposals

    def _extract_with_spacy(
        self,
        text: str,
        chapter_index: int,
        chapter_start: int,
    ) -> dict[str, list[CharacterMention]]:
        """Extract characters using spaCy NER."""
        candidates = defaultdict(list)

        doc = self.nlp(text)

        for ent in doc.ents:
            if ent.label_ != "PERSON":
                continue

            # Normalize name
            name = ' '.join(ent.text.split())

            # Skip false positives
            if not self._is_valid_name(name):
                continue

            # Create mention
            local_pos = ent.start_char
            global_pos = chapter_start + local_pos
            context = self._extract_context(text, local_pos, self.context_window)
            in_dialogue = self._is_in_dialogue(text, local_pos)

            mention = CharacterMention(
                text=name,
                position=global_pos,
                chapter_index=chapter_index,
                context=context,
                in_dialogue=in_dialogue,
            )

            # Use normalized name as key
            normalized = self._normalize_name(name)
            candidates[name].append(mention)  # Keep original case for display

        return dict(candidates)

    def _extract_with_regex(
        self,
        text: str,
        chapter_index: int,
        chapter_start: int,
    ) -> dict[str, list[CharacterMention]]:
        """Extract characters using regex patterns (fallback)."""
        candidates = defaultdict(list)

        patterns = [
            # Title + Name
            r'\b((?:Mr|Mrs|Ms|Miss|Dr|Sir|Lady|Lord)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            # Full name (two capitalized words, not at sentence start)
            r'(?<=[a-z]\s)([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            # Name in dialogue tag
            r'[,""]\s*said\s+([A-Z][a-z]+)',
            r'[,""]\s*asked\s+([A-Z][a-z]+)',
            r'[,""]\s*replied\s+([A-Z][a-z]+)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()

                if not self._is_valid_name(name):
                    continue

                local_pos = match.start(1)
                global_pos = chapter_start + local_pos
                context = self._extract_context(text, local_pos, self.context_window)
                in_dialogue = self._is_in_dialogue(text, local_pos)

                mention = CharacterMention(
                    text=name,
                    position=global_pos,
                    chapter_index=chapter_index,
                    context=context,
                    in_dialogue=in_dialogue,
                )

                candidates[name].append(mention)

        return dict(candidates)

    def _is_valid_name(self, name: str) -> bool:
        """Check if a name is valid (not a false positive)."""
        if len(name) < 2:
            return False

        # Reject names that start or end with non-alphabetic characters
        # This filters out spaCy mis-tags like "--yes" from dialogue
        if not name[0].isalpha() or not name[-1].isalpha():
            return False

        # Check against false positives
        name_lower = name.lower()
        if name_lower in FALSE_POSITIVE_NAMES:
            return False

        # Check for place suffixes
        words = name_lower.split()
        if words and words[-1] in PLACE_SUFFIXES:
            return False

        # Check that it's mostly alphabetic
        alpha_count = sum(1 for c in name if c.isalpha())
        if alpha_count < len(name) * 0.5:
            return False

        return True

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        name = name.lower()
        name = re.sub(r'^(mr|mrs|ms|miss|dr|sir|lady|lord)\s*\.?\s*', '', name)
        name = ' '.join(name.split())
        return name

    def _extract_first_names(self, full_name: str) -> list[str]:
        """
        Extract standalone first name from full name.

        Examples:
        - "Jordan Baker" → ["Jordan"]
        - "Miss Jordan Baker" → ["Jordan"]
        - "Jay Gatsby" → ["Jay"]
        - "Mr. Nick Carraway" → ["Nick"]
        """
        # Remove titles
        titles = ['mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord', 'professor']
        words = full_name.lower().split()

        # Filter out title words
        name_words = [w for w in words if w.rstrip('.') not in titles]

        # If multi-word name, first word is likely first name
        if len(name_words) >= 2:
            return [name_words[0].capitalize()]

        return []

    def _infer_character_type(
        self,
        name: str,
        mentions: list[CharacterMention],
    ) -> CharacterType:
        """
        Infer character type based on context patterns.

        Characters with dialogue or action verb associations are likely STORY characters.
        Returns UNCERTAIN when there's insufficient evidence.
        """
        story_signals = 0
        action_verbs = {
            'said', 'asked', 'replied', 'answered', 'whispered', 'shouted',
            'looked', 'walked', 'turned', 'smiled', 'laughed', 'nodded',
            'sat', 'stood', 'ran', 'came', 'went', 'told', 'thought',
            'felt', 'knew', 'saw', 'heard', 'took', 'put', 'gave',
        }

        for mention in mentions[:10]:  # Check first 10 mentions for efficiency
            # Dialogue is strong signal for story character
            if mention.in_dialogue:
                story_signals += 2

            # Check for action verbs in context
            if mention.context:
                context_lower = mention.context.lower()
                for verb in action_verbs:
                    if verb in context_lower:
                        story_signals += 1
                        break  # Only count once per mention

        # Strong evidence threshold
        if story_signals >= 3:
            return CharacterType.STORY

        # Any dialogue is a good indicator
        if any(m.in_dialogue for m in mentions):
            return CharacterType.STORY

        # Not enough evidence
        return CharacterType.UNCERTAIN
