#!/usr/bin/env python3
"""
Test pronunciation IPA generation with multiple words.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.pronunciation_guide.enricher import PronunciationEnricher
from src.pipeline.pronunciation_guide.models import PronunciationProposal, PronunciationFlag, PronunciationMention

# Create proposals
proposals = [
    PronunciationProposal(
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
    ),
    PronunciationProposal(
        word="Rance",
        strategy="character",
        flag_reason=PronunciationFlag.PROPER_NOUN,
        confidence=0.8,
        mentions=[
            PronunciationMention(
                word_form="Rance",
                position=200,
                context="Rance was a sailor",
                chapter_index=1,
            )
        ]
    ),
    PronunciationProposal(
        word="Milton",
        strategy="character",
        flag_reason=PronunciationFlag.PROPER_NOUN,
        confidence=0.8,
        mentions=[
            PronunciationMention(
                word_form="Milton",
                position=300,
                context="Milton Jennings shouted",
                chapter_index=1,
            )
        ]
    ),
]

# Create LLM client
print("Creating LLM client...")
config = LLMConfig.ollama(model="qwen3-next:80b-a3b-instruct-q8_0")
llm = LLMClient(config)

# Create enricher
print("Creating enricher...")
enricher = PronunciationEnricher(llm, batch_size=30)

# Test batch enrichment with multiple words
print("\nTesting batch enrichment with 3 words...")

# Add debugging
from src.pipeline.pronunciation_guide.enricher import ENRICHER_SYSTEM_PROMPT, ENRICHER_BATCH_PROMPT

word_list = "- Lincoln [proper_noun]\n- Rance [proper_noun]\n- Milton [proper_noun]"
context_examples = '- Lincoln: "Lincoln Stewart was riding a plow"\n- Rance: "Rance was a sailor"\n- Milton: "Milton Jennings shouted"'
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

enrichments = enricher.enrich_batch(proposals)

print(f"\nResults ({len(enrichments)} words):")
for word, enrichment in enrichments.items():
    print(f"\n  Word: {word}")
    print(f"  IPA: {enrichment.ipa}")
    print(f"  Phonetic: {enrichment.phonetic_spelling}")
    print(f"  Confidence: {enrichment.confidence}")
