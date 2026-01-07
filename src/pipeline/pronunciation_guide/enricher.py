"""
Pronunciation enricher using LLM.

Generates IPA notation and phonetic spellings for flagged words.
"""

from typing import Optional
import logging

from .models import PronunciationProposal, PronunciationEnrichment, PronunciationFlag
from ..llm import LLMClient

logger = logging.getLogger(__name__)


ENRICHER_SYSTEM_PROMPT = """You are an expert phonetician helping audiobook narrators with pronunciation.

CRITICAL: Base your pronunciation guidance ONLY on standard phonetic rules.
Do NOT use any prior knowledge about how specific characters in famous novels are pronounced.
If you recognize a character name from a famous work, provide standard phonetic guidance based on spelling alone.

For each word, provide:
1. IPA transcription using International Phonetic Alphabet notation
2. A phonetic spelling using common English syllables that a narrator can easily read
3. Any helpful notes about the pronunciation

Be precise with IPA. For phonetic spelling, use intuitive uppercase representations like:
- "GAT-sbee" for Gatsby
- "KWAH-zee-MOH-doh" for Quasimodo
- "ZHAHN" for Jean (French)

Use hyphens to separate syllables and CAPS to indicate stressed syllables."""


ENRICHER_BATCH_PROMPT = """Generate pronunciation guidance for these words from a novel.

WORDS TO PRONOUNCE:
{word_list}

CONTEXT EXAMPLES:
{context_examples}

Return a JSON array with one object per word:
[
  {{
    "word": "the word",
    "ipa": "/IPA transcription/",
    "phonetic_spelling": "PHONETIC-SPELLING",
    "notes": "any helpful notes or null"
  }}
]

Return ONLY valid JSON, no other text."""


ENRICHER_SINGLE_PROMPT = """Generate pronunciation guidance for this word from a novel.

WORD: {word}
TYPE: {word_type}
CONTEXT: {context}

Return JSON:
{{
  "word": "{word}",
  "ipa": "/IPA transcription/",
  "phonetic_spelling": "PHONETIC-SPELLING",
  "notes": "any helpful notes or null"
}}

Return ONLY valid JSON."""


class PronunciationEnricher:
    """Generates pronunciation guidance using LLM."""

    def __init__(
        self,
        llm_client: LLMClient,
        batch_size: int = 10,
    ):
        """
        Args:
            llm_client: LLM client for generating pronunciations
            batch_size: Number of words to process per LLM call
        """
        self.llm = llm_client
        self.batch_size = batch_size

    def enrich_batch(
        self,
        proposals: list[PronunciationProposal],
    ) -> dict[str, PronunciationEnrichment]:
        """
        Generate pronunciation data for a batch of words.

        Args:
            proposals: List of pronunciation proposals

        Returns:
            Dictionary mapping word (lowercase) to enrichment
        """
        if not proposals:
            return {}

        # Build word list
        word_list = []
        for p in proposals:
            word_type = p.flag_reason.value
            if p.language_hint:
                word_type = f"{word_type} ({p.language_hint})"
            word_list.append(f"- {p.word} [{word_type}]")

        # Build context examples
        context_examples = []
        for p in proposals[:5]:  # Limit context examples
            if p.mentions:
                context = p.mentions[0].context[:100]
                context_examples.append(f"- {p.word}: \"{context}\"")

        prompt = ENRICHER_BATCH_PROMPT.format(
            word_list="\n".join(word_list),
            context_examples="\n".join(context_examples) if context_examples else "(no context)",
        )

        result, response = self.llm.query_json(prompt, system=ENRICHER_SYSTEM_PROMPT)

        enrichments = {}

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM batch enrichment failed: {response.error}")
            # Return empty enrichments for all words
            for p in proposals:
                enrichments[p.word.lower()] = PronunciationEnrichment(
                    word=p.word,
                    confidence=0.0,
                )
            return enrichments

        if result is None:
            # JSON parsing failure
            logger.warning("LLM batch enrichment failed: failed to parse JSON")
            # Return empty enrichments for all words
            for p in proposals:
                enrichments[p.word.lower()] = PronunciationEnrichment(
                    word=p.word,
                    confidence=0.0,
                )
            return enrichments

        # Parse results
        if isinstance(result, list):
            for item in result:
                word = item.get("word", "")
                enrichments[word.lower()] = PronunciationEnrichment(
                    word=word,
                    ipa=item.get("ipa"),
                    phonetic_spelling=item.get("phonetic_spelling"),
                    notes=item.get("notes"),
                    confidence=0.8,
                )

        # Fill in any missing words
        for p in proposals:
            if p.word.lower() not in enrichments:
                enrichments[p.word.lower()] = PronunciationEnrichment(
                    word=p.word,
                    confidence=0.0,
                )

        return enrichments

    def enrich_single(
        self,
        proposal: PronunciationProposal,
    ) -> PronunciationEnrichment:
        """
        Generate pronunciation data for a single word.

        Args:
            proposal: Single pronunciation proposal

        Returns:
            Enrichment data
        """
        context = ""
        if proposal.mentions:
            context = proposal.mentions[0].context[:150]

        word_type = proposal.flag_reason.value
        if proposal.language_hint:
            word_type = f"{word_type} ({proposal.language_hint})"

        prompt = ENRICHER_SINGLE_PROMPT.format(
            word=proposal.word,
            word_type=word_type,
            context=context or "(no context)",
        )

        result, response = self.llm.query_json(prompt, system=ENRICHER_SYSTEM_PROMPT)

        if result is None:
            logger.warning(f"LLM enrichment failed for '{proposal.word}'")
            return PronunciationEnrichment(
                word=proposal.word,
                confidence=0.0,
            )

        return PronunciationEnrichment(
            word=result.get("word", proposal.word),
            ipa=result.get("ipa"),
            phonetic_spelling=result.get("phonetic_spelling"),
            notes=result.get("notes"),
            confidence=0.8,
        )

    def enrich_homograph(
        self,
        proposal: PronunciationProposal,
    ) -> PronunciationEnrichment:
        """
        Special handling for homographs - note the multiple pronunciations.

        For homographs, we don't generate a single pronunciation but rather
        return the known options as notes.
        """
        if proposal.homograph_options:
            notes = "Multiple pronunciations: " + "; ".join(proposal.homograph_options)
        else:
            notes = "Homograph with context-dependent pronunciation"

        return PronunciationEnrichment(
            word=proposal.word,
            notes=notes,
            confidence=0.9,
        )
