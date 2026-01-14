"""
Coreference-based character proposer.

Uses spaCy coreference resolution to link pronouns back to character names,
boosting mention counts and providing pronoun-to-character mappings.
"""

import logging
from typing import Optional
import re

from .base import BaseCharacterProposer
from ..models import CharacterProposal, CharacterMention, CharacterType

logger = logging.getLogger(__name__)

# Try to import coreference library
COREF_AVAILABLE = False
try:
    import coreferee
    COREF_AVAILABLE = True
    logger.info("Coreference resolution available via coreferee")
except ImportError:
    logger.debug("coreferee not available - coreference resolution disabled")

# Pronouns that we want to resolve
RESOLVABLE_PRONOUNS = {
    'he', 'him', 'his', 'himself',
    'she', 'her', 'hers', 'herself',
    'they', 'them', 'their', 'theirs', 'themselves',
}


class CoreferenceProposer(BaseCharacterProposer):
    """
    Proposes characters using coreference resolution.

    Links pronouns back to their antecedent noun phrases (character names)
    to boost mention counts. Gracefully degrades if coreference library
    is not available.
    """

    name = "coreference"

    def __init__(
        self,
        nlp=None,
        context_window: int = 100,
        min_confidence: float = 0.7,
    ):
        """
        Args:
            nlp: spaCy nlp object with coreference pipeline component
            context_window: Characters of context to extract around mentions
            min_confidence: Minimum confidence for coreference links
        """
        self.nlp = nlp
        self.context_window = context_window
        self.min_confidence = min_confidence
        self._coref_available = COREF_AVAILABLE and nlp is not None

        if self._coref_available:
            # Check if nlp has coreference component
            try:
                if 'coreferee' not in nlp.pipe_names:
                    nlp.add_pipe('coreferee')
            except Exception as e:
                logger.warning(f"Could not add coreference component: {e}")
                self._coref_available = False

    @classmethod
    def is_available(cls) -> bool:
        """Check if coreference resolution is available."""
        return COREF_AVAILABLE

    def propose(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_start_position: int,
    ) -> list[CharacterProposal]:
        """
        Extract character proposals using coreference resolution.

        Args:
            chapter_text: The text of the chapter
            chapter_index: The chapter number (1-indexed)
            chapter_start_position: Character offset where this chapter starts

        Returns:
            List of character proposals with pronoun-linked mentions
        """
        if not self._coref_available:
            logger.debug("Coreference not available - returning empty proposals")
            return []

        try:
            return self._extract_with_coreference(
                chapter_text, chapter_index, chapter_start_position
            )
        except Exception as e:
            logger.warning(f"Coreference extraction failed: {e}")
            return []

    def _extract_with_coreference(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_start_position: int,
    ) -> list[CharacterProposal]:
        """
        Extract character proposals using coreference resolution.

        Links pronouns to their antecedent character names.
        """
        doc = self.nlp(chapter_text)

        # Track proposals by canonical name
        proposals = {}

        # Process coreference chains
        if hasattr(doc._, 'coref_chains') and doc._.coref_chains:
            for chain in doc._.coref_chains:
                # Find the best antecedent (typically a proper noun or NP)
                antecedent = self._find_best_antecedent(chain, doc)
                if not antecedent:
                    continue

                antecedent_text = antecedent.text

                # Collect all mentions in this chain
                mentions = []
                for mention_idx in chain:
                    span = doc[mention_idx[0]:mention_idx[1]]
                    mention_text = span.text

                    # Calculate global position
                    start_char = span.start_char
                    global_pos = chapter_start_position + start_char

                    # Get context
                    context = self._extract_context(
                        chapter_text, start_char, self.context_window
                    )

                    # Check if in dialogue
                    in_dialogue = self._is_in_dialogue(chapter_text, start_char)

                    mentions.append(CharacterMention(
                        text=mention_text,
                        position=global_pos,
                        chapter_index=chapter_index,
                        context=context,
                        in_dialogue=in_dialogue,
                        is_agentive=self._is_agentive_context(context),
                    ))

                if mentions:
                    if antecedent_text not in proposals:
                        proposals[antecedent_text] = CharacterProposal(
                            strategy=self.name,
                            name=antecedent_text,
                            mentions=[],
                            confidence=0.7,  # Base confidence for coreference
                            chapter_index=chapter_index,
                            reasoning="Coreference resolution linked pronouns to this name",
                            character_type=CharacterType.STORY,
                        )
                    proposals[antecedent_text].mentions.extend(mentions)

        return list(proposals.values())

    def _find_best_antecedent(self, chain, doc) -> Optional:
        """
        Find the best antecedent in a coreference chain.

        Prefers proper nouns and definite noun phrases over pronouns.
        """
        best = None
        best_score = -1

        for mention_idx in chain:
            span = doc[mention_idx[0]:mention_idx[1]]

            # Skip pronouns - we want the actual name
            if span.text.lower() in RESOLVABLE_PRONOUNS:
                continue

            # Score based on token types
            score = 0
            for token in span:
                if token.pos_ == 'PROPN':  # Proper noun
                    score += 3
                elif token.pos_ == 'NOUN':  # Common noun
                    score += 1
                if token.ent_type_ == 'PERSON':
                    score += 2

            if score > best_score:
                best_score = score
                best = span

        return best

    def _is_agentive_context(self, context: str) -> bool:
        """Check if the context indicates agentive behavior."""
        agentive_patterns = [
            r'\b(said|asked|replied|whispered|shouted|called|cried|muttered|exclaimed)\b',
            r'\b(walked|ran|stood|turned|looked|smiled|laughed|nodded|frowned)\b',
            r'\b(grabbed|took|held|threw|placed|opened|closed|pushed|pulled)\b',
            r'\b(sat|came|went|entered|left|arrived|departed|approached|retreated)\b',
        ]
        return any(re.search(p, context.lower()) for p in agentive_patterns)


def create_coreference_proposer(
    nlp=None,
    context_window: int = 100,
) -> Optional[CoreferenceProposer]:
    """
    Factory function to create a CoreferenceProposer if available.

    Returns None if coreference resolution is not available.
    """
    if not CoreferenceProposer.is_available():
        logger.info("Coreference proposer not available - skipping")
        return None

    if nlp is None:
        try:
            import spacy
            nlp = spacy.load("en_core_web_lg")
        except Exception as e:
            logger.warning(f"Could not load spacy model: {e}")
            return None

    return CoreferenceProposer(nlp=nlp, context_window=context_window)
