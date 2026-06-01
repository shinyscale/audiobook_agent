"""
Pronunciation enricher using LLM.

Generates IPA notation and phonetic spellings for flagged words.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from ..llm import LLMClient
from .models import PronunciationEnrichment, PronunciationProposal

logger = logging.getLogger(__name__)


def _is_valid_ipa(ipa: str) -> bool:
    """Return True if the IPA string contains only valid IPA Unicode codepoints.

    IPA notation uses characters from Latin/IPA-extension blocks (up to U+02FF)
    plus combining diacritics (U+0300–U+036F) and Phonetic Extensions (U+1D00–U+1DBF).
    Characters in CJK / Hiragana / Katakana blocks (U+2E80+) indicate LLM corruption.
    """
    for ch in ipa:
        cp = ord(ch)
        # Allow: ASCII (0x20–0x7E), Latin+IPA extensions (0x00A0–0x02FF),
        #        combining marks (0x0300–0x036F), Phonetic Extensions (0x1D00–0x1DBF)
        if cp < 0x0080:
            continue  # ASCII — always fine
        if 0x00A0 <= cp <= 0x02FF:
            continue  # Latin Extended / IPA Extensions / Spacing Modifiers
        if 0x0300 <= cp <= 0x036F:
            continue  # Combining Diacritical Marks
        if 0x1D00 <= cp <= 0x1DBF:
            continue  # Phonetic Extensions
        return False  # Anything else (CJK, Hiragana, Katakana, etc.) is invalid
    return True


# Static IPA lookup for common English homographs.
# Provides both pronunciation variants so narrators know context-dependent choices.
# This is a universal reference lexicon (not a filter/deny-list).
HOMOGRAPH_IPA_MAP: dict[str, str] = {
    "minute": "/ˈmɪnɪt/ (time unit) or /maɪˈnjuːt/ (tiny)",
    "live": "/lɪv/ (to exist, present) or /laɪv/ (in real time, alive)",
    "close": "/kloʊs/ (nearby, adj) or /kloʊz/ (to shut, verb)",
    "wind": "/wɪnd/ (moving air, noun) or /waɪnd/ (to coil/turn, verb)",
    "read": "/riːd/ (present tense) or /rɛd/ (past tense)",
    "does": "/dʌz/ (verb: he does) or /doʊz/ (female deer, plural)",
    "subject": "/ˈsʌbdʒɪkt/ (noun/adj: topic) or /səbˈdʒɛkt/ (verb: to expose)",
    "row": "/roʊ/ (a line or to row a boat) or /raʊ/ (a noisy argument, British)",
    "excuse": "/ɪkˈskjuːs/ (noun: a reason) or /ɪkˈskjuːz/ (verb: to pardon)",
    "elaborate": "/ɪˈlæbərɪt/ (adj: detailed) or /ɪˈlæbəreɪt/ (verb: to expand on)",
    "intimate": "/ˈɪntɪmɪt/ (adj/noun: close) or /ˈɪntɪmeɪt/ (verb: to hint)",
    "content": "/ˈkɒntɛnt/ (noun: material) or /kənˈtɛnt/ (adj: satisfied)",
    "bow": "/boʊ/ (bow and arrow; ribbon bow) or /baʊ/ (ship's bow; to bow one's head)",
    "refuse": "/ˈrɛfjuːs/ (noun: garbage) or /rɪˈfjuːz/ (verb: to decline)",
    "bass": "/bæs/ (musical bass; bass guitar) or /beɪs/ (bass fish)",
    "entrance": "/ˈɛntrəns/ (noun: doorway) or /ɪnˈtræns/ (verb: to enchant)",
    "polish": "/ˈpoʊlɪʃ/ (from Poland; Polish language) or /ˈpɒlɪʃ/ (to shine; shoe polish)",
    "separate": "/ˈsɛpərɪt/ (adj: apart) or /ˈsɛpəreɪt/ (verb: to divide)",
    "moderate": "/ˈmɒdərɪt/ (adj: middle, not extreme) or /ˈmɒdəreɪt/ (verb: to oversee)",
    "object": "/ˈɒbdʒɪkt/ (noun: a thing) or /əbˈdʒɛkt/ (verb: to protest)",
    "permit": "/ˈpɜːrmɪt/ (noun: authorization) or /pərˈmɪt/ (verb: to allow)",
    "present": "/ˈprɛzənt/ (noun/adj: gift; here) or /prɪˈzɛnt/ (verb: to introduce)",
    "record": "/ˈrɛkərd/ (noun: a recording) or /rɪˈkɔːrd/ (verb: to record)",
    "wound": "/wuːnd/ (past tense of wind) or /wuːnd/ (an injury) — context: injury=wuːnd; wound up=waʊnd",
    "tear": "/tɪər/ (from the eye) or /tɛər/ (to rip)",
    "lead": "/liːd/ (verb: to guide) or /lɛd/ (noun: the heavy metal)",
    "desert": "/ˈdɛzərt/ (noun: arid region) or /dɪˈzɜːrt/ (verb: to abandon)",
    "produce": "/ˈproʊ.duːs/ (noun: fresh food, esp. vegetables) or /prəˈduːs/ (verb: to make/create)",
}


# Static IPA for words with well-known but non-intuitive pronunciations.
# These override LLM output to prevent systematic errors on common irregular spellings.
# Universal reference lexicon: applies to any book containing these words.
KNOWN_IRREGULAR_IPA: dict[str, PronunciationEnrichment] = {
    # Nautical terms often misread letter-by-letter when spelled out
    "gunwale": PronunciationEnrichment(
        word="gunwale",
        ipa="/ˈɡʌn.əl/",
        phonetic_spelling="GUN-ul",
        notes='Despite the spelling, pronounced "GUN-ul" (rhymes with "funnel"). Not "gun-wail".',
        confidence=1.0,
    ),
    "gunwhale": PronunciationEnrichment(
        word="gunwhale",
        ipa="/ˈɡʌn.əl/",
        phonetic_spelling="GUN-ul",
        notes='Variant spelling of "gunwale". Pronounced "GUN-ul" (rhymes with "funnel"). Not "gun-whale".',
        confidence=1.0,
    ),
    # "-fanged" compounds: LLMs often produce /feɪnd/ (silent-g, like "feigned") instead
    # of the correct /fæŋd/. Add overrides for likely encountered forms.
    "sharp-fanged": PronunciationEnrichment(
        word="sharp-fanged",
        ipa="/ˈʃɑːrp.fæŋd/",
        phonetic_spelling="SHARP-fangd",
        notes='"Fanged" rhymes with "banged" — the g is pronounced. Not "faned" (do not treat as silent g).',
        confidence=1.0,
    ),
    "fanged": PronunciationEnrichment(
        word="fanged",
        ipa="/fæŋd/",
        phonetic_spelling="FANGD",
        notes='"Fanged" rhymes with "banged". The g is pronounced, not silent.',
        confidence=1.0,
    ),
    # "cogito" (Latin: "I think") from "cogito ergo sum"; LLMs often use soft g /dʒ/ → wrong.
    # Standard Latin: hard g, stress on first syllable: KOG-ih-toh.
    "cogito": PronunciationEnrichment(
        word="cogito",
        ipa="/ˈkɒɡɪtoʊ/",
        phonetic_spelling="KOG-ih-toh",
        notes='Latin philosophical term ("I think" from "cogito ergo sum"). Hard g, not soft. KOG-ih-toh.',
        confidence=1.0,
    ),
    # "bolo" is an unfamiliar word (Filipino knife); LLMs often give garbled IPA for
    # hyphenated compounds. Standard phonetics: BOH-loh.
    "bolo-toothed": PronunciationEnrichment(
        word="bolo-toothed",
        ipa="/ˈboʊ.loʊ.tuːθt/",
        phonetic_spelling="BOH-loh-TOOTHT",
        notes='"Bolo" rhymes with "solo"; "toothed" = /tuːθt/ (clear th, then t). '
              'Bolo is a large single-edged Filipino knife.',
        confidence=1.0,
    ),
}


ENRICHER_SYSTEM_PROMPT = """You are an expert phonetician helping audiobook narrators with pronunciation.

Use whatever phonological knowledge you have, including knowledge of how words from
non-English languages (German, French, Italian, Latin, etc.) are pronounced. If a word
comes from a famous literary work and you know how it is conventionally pronounced,
you may use that knowledge — the goal is precision, not philosophical purity.

For each word, provide:
1. IPA transcription using International Phonetic Alphabet notation
2. A phonetic spelling using common English syllables that a narrator can easily read
3. Any helpful notes about the pronunciation

Be precise with IPA. For phonetic spelling, use intuitive uppercase representations like:
- "MILL-er" for Miller (simple surname)
- "AN-der-son" for Anderson (compound surname)
- "ZHAHN" for Jean (French pronunciation)

Use hyphens to separate syllables and CAPS to indicate stressed syllables."""


ENRICHER_BATCH_PROMPT = """Generate pronunciation guidance for these words from a novel.

WORDS TO PRONOUNCE:
{word_list}

CONTEXT EXAMPLES:
{context_examples}

CRITICAL: Your response must be a JSON array containing one object per word.
- Even if there is only ONE word, wrap it in an array: [object]
- Do NOT return a bare object

Required format:
[
  {{
    "word": "the word",
    "ipa": "/IPA transcription/",
    "phonetic_spelling": "PHONETIC-SPELLING",
    "notes": "any helpful notes or null"
  }}
]

Return ONLY the JSON array, no other text."""


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
        batch_size: int = 30,
        max_workers: int = 4,
        max_retries: int = 3,
        retry_backoff_base: int = 2,
    ):
        """
        Args:
            llm_client: LLM client for generating pronunciations
            batch_size: Number of words to process per LLM call (default 30)
            max_workers: Maximum concurrent LLM enrichment workers (default 4)
            max_retries: Maximum retry attempts for failed batches (default 3)
            retry_backoff_base: Base seconds for exponential backoff (default 2)
        """
        self.llm = llm_client
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base

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

        # Check static irregular IPA lookup first — these are known-correct and override LLM
        enrichments: dict[str, PronunciationEnrichment] = {}
        llm_proposals = []
        for p in proposals:
            static = KNOWN_IRREGULAR_IPA.get(p.word.lower())
            if static:
                enrichments[p.word.lower()] = static
            else:
                llm_proposals.append(p)

        if not llm_proposals:
            return enrichments
        proposals = llm_proposals

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
                context_examples.append(f'- {p.word}: "{context}"')

        prompt = ENRICHER_BATCH_PROMPT.format(
            word_list="\n".join(word_list),
            context_examples="\n".join(context_examples) if context_examples else "(no context)",
        )

        result, response = self.llm.query_json(prompt, system=ENRICHER_SYSTEM_PROMPT)

        llm_enrichments: dict[str, PronunciationEnrichment] = {}

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM batch enrichment failed: {response.error}")
            # Fallback to single enrichment
            return self._fallback_to_single_enrichment(proposals)

        if result is None:
            # JSON parsing failure
            logger.warning("LLM batch enrichment failed: failed to parse JSON")
            # Fallback to single enrichment
            return self._fallback_to_single_enrichment(proposals)

        # Check if result is an error dict from Ollama json_mode validation
        if isinstance(result, dict) and "error" in result and "word" not in result:
            logger.warning(f"Ollama json_mode validation error: {result.get('error')}")
            logger.info("Falling back to single-word enrichment")
            # Fallback to single enrichment
            return self._fallback_to_single_enrichment(proposals)

        # Parse results - handle both list and single dict
        if isinstance(result, list):
            for item in result:
                word = item.get("word", "")
                if word:  # Only add if word is not empty
                    raw_ipa = item.get("ipa")
                    llm_enrichments[word.lower()] = PronunciationEnrichment(
                        word=word,
                        ipa=raw_ipa if (raw_ipa and _is_valid_ipa(raw_ipa)) else None,
                        phonetic_spelling=item.get("phonetic_spelling"),
                        notes=item.get("notes"),
                        confidence=0.8,
                    )
        elif isinstance(result, dict) and "word" in result:
            # LLM returned a single object instead of an array (common with 1 word)
            word = result.get("word", "")
            if word:  # Only add if word is not empty
                raw_ipa = result.get("ipa")
                llm_enrichments[word.lower()] = PronunciationEnrichment(
                    word=word,
                    ipa=raw_ipa if (raw_ipa and _is_valid_ipa(raw_ipa)) else None,
                    phonetic_spelling=result.get("phonetic_spelling"),
                    notes=result.get("notes"),
                    confidence=0.8,
                )

        # Fill in any missing words with single enrichment
        for p in proposals:
            if p.word.lower() not in llm_enrichments:
                logger.debug(f"Word '{p.word}' missing from batch result, enriching individually")
                llm_enrichments[p.word.lower()] = self.enrich_single(p)

        # Merge: static results take precedence (they're known-correct).
        # Update LLM results first, then overwrite with static — this ensures
        # static overrides win even if the LLM returned a result for a word
        # that should have been filtered (e.g., batch models sometimes return
        # extra words that weren't in the request).
        llm_enrichments.update(enrichments)
        return llm_enrichments

    def _fallback_to_single_enrichment(
        self,
        proposals: list[PronunciationProposal],
    ) -> dict[str, PronunciationEnrichment]:
        """Fallback to single-word enrichment when batch fails."""
        logger.info(f"Falling back to single enrichment for {len(proposals)} words")
        enrichments = {}
        for p in proposals:
            try:
                enrichments[p.word.lower()] = self.enrich_single(p)
            except Exception as e:
                logger.error(f"Single enrichment failed for '{p.word}': {e}")
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
        # Check static lookup first — overrides LLM for known irregular pronunciations
        static = KNOWN_IRREGULAR_IPA.get(proposal.word.lower())
        if static:
            return static

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

        raw_ipa = result.get("ipa")
        return PronunciationEnrichment(
            word=result.get("word", proposal.word),
            ipa=raw_ipa if (raw_ipa and _is_valid_ipa(raw_ipa)) else None,
            phonetic_spelling=result.get("phonetic_spelling"),
            notes=result.get("notes"),
            confidence=0.8,
        )

    def enrich_homograph(
        self,
        proposal: PronunciationProposal,
    ) -> PronunciationEnrichment:
        """
        Special handling for homographs - provide both IPA variants.

        Uses a static IPA lookup table for common English homographs so
        narrators see the full phonetic options for context-dependent words.
        Falls back to a note when the word is not in the lookup table.
        """
        word_lower = proposal.word.lower()
        ipa_variants = HOMOGRAPH_IPA_MAP.get(word_lower)

        if ipa_variants:
            # IPA from static lookup - reliable and consistent
            notes = f"Context-dependent: {ipa_variants}"
            return PronunciationEnrichment(
                word=proposal.word,
                ipa=ipa_variants,
                notes=notes,
                confidence=0.95,
            )

        if proposal.homograph_options:
            notes = "Multiple pronunciations: " + "; ".join(proposal.homograph_options)
        else:
            notes = "Homograph with context-dependent pronunciation"

        return PronunciationEnrichment(
            word=proposal.word,
            notes=notes,
            confidence=0.9,
        )

    def enrich_batch_with_retry(
        self,
        proposals: list[PronunciationProposal],
    ) -> dict[str, PronunciationEnrichment]:
        """
        Enrich a batch with exponential backoff retry.

        Args:
            proposals: List of pronunciation proposals

        Returns:
            Dictionary mapping word (lowercase) to enrichment
        """
        for attempt in range(self.max_retries):
            try:
                return self.enrich_batch(proposals)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_backoff_base**attempt
                    logger.warning(
                        f"Enrichment batch attempt {attempt + 1} failed: {e}, "
                        f"retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Enrichment batch failed after {self.max_retries} attempts: {e}")
                    # Return empty enrichments for all words
                    enrichments = {}
                    for p in proposals:
                        enrichments[p.word.lower()] = PronunciationEnrichment(
                            word=p.word,
                            confidence=0.0,
                        )
                    return enrichments

        # Should not reach here, but return empty dict just in case
        return {}

    def enrich_parallel(
        self,
        proposals: list[PronunciationProposal],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, PronunciationEnrichment]:
        """
        Process enrichment batches concurrently using ThreadPoolExecutor.

        Args:
            proposals: List of all pronunciation proposals to enrich
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            Dictionary mapping word (lowercase) to enrichment
        """
        if not proposals:
            return {}

        # Split into batches
        batches = [
            proposals[i : i + self.batch_size] for i in range(0, len(proposals), self.batch_size)
        ]
        total_batches = len(batches)
        completed_batches = 0

        logger.info(
            f"Starting parallel enrichment: {len(proposals)} words in "
            f"{total_batches} batches, {self.max_workers} workers"
        )

        all_enrichments = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {
                executor.submit(self.enrich_batch_with_retry, batch): i
                for i, batch in enumerate(batches)
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                completed_batches += 1

                try:
                    batch_enrichments = future.result()
                    all_enrichments.update(batch_enrichments)
                    logger.debug(
                        f"Batch {batch_idx + 1}/{total_batches} completed: "
                        f"{len(batch_enrichments)} enrichments"
                    )
                except Exception as e:
                    logger.error(f"Batch {batch_idx + 1} failed: {e}")
                    # Fill in empty enrichments for this batch
                    for p in batches[batch_idx]:
                        all_enrichments[p.word.lower()] = PronunciationEnrichment(
                            word=p.word,
                            confidence=0.0,
                        )

                if progress_callback:
                    progress_callback(completed_batches, total_batches)

        logger.info(f"Parallel enrichment complete: {len(all_enrichments)} words enriched")

        return all_enrichments
