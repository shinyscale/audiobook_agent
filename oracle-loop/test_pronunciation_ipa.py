#!/usr/bin/env python3
"""
Smoke test for pronunciation IPA generation.
Tests if the enricher is properly generating IPA data.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.pronunciation_guide.enricher import PronunciationEnricher
from src.pipeline.pronunciation_guide.models import PronunciationProposal, PronunciationFlag, PronunciationMention

# Create a minimal proposal
proposal = PronunciationProposal(
    word="Lincoln",
    strategy="character",
    flag_reason=PronunciationFlag.PROPER_NOUN,
    confidence=0.8,
    mentions=[
        PronunciationMention(
            word_form="Lincoln",
            position=100,
            context="Lincoln Stewart was riding a plow",
            chapter_index=1,
        )
    ]
)

# Create LLM client
print("Creating LLM client...")
config = LLMConfig.ollama(model="qwen3-next:80b-a3b-instruct-q8_0")
llm = LLMClient(config)

# Create enricher
print("Creating enricher...")
enricher = PronunciationEnricher(llm, batch_size=30)

# Test batch enrichment
print("\nTesting batch enrichment with 1 word...")

# Add debugging - call the LLM directly to see what it returns
from src.pipeline.pronunciation_guide.enricher import ENRICHER_SYSTEM_PROMPT, ENRICHER_BATCH_PROMPT

word_list = f"- Lincoln [proper_noun]"
context_examples = '- Lincoln: "Lincoln Stewart was riding a plow"'
prompt = ENRICHER_BATCH_PROMPT.format(
    word_list=word_list,
    context_examples=context_examples
)

print("\n--- Direct LLM call ---")
result, response = llm.query_json(prompt, system=ENRICHER_SYSTEM_PROMPT)
print(f"Response success: {response.success}")
print(f"Result type: {type(result)}")
print(f"Result value: {result}")
print("--- End direct LLM call ---\n")

enrichments = enricher.enrich_batch([proposal])

print(f"\nResults:")
for word, enrichment in enrichments.items():
    print(f"  Word: {word}")
    print(f"  IPA: {enrichment.ipa}")
    print(f"  Phonetic: {enrichment.phonetic_spelling}")
    print(f"  Notes: {enrichment.notes}")
    print(f"  Confidence: {enrichment.confidence}")

# Test single enrichment
print("\n\nTesting single enrichment...")
enrichment = enricher.enrich_single(proposal)
print(f"  Word: {enrichment.word}")
print(f"  IPA: {enrichment.ipa}")
print(f"  Phonetic: {enrichment.phonetic_spelling}")
print(f"  Notes: {enrichment.notes}")
print(f"  Confidence: {enrichment.confidence}")
