#!/usr/bin/env python3
"""Diagnostic script to trace main_cast grounding failure for Gatsby."""
import json
import sys
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '.')

# Load analysis.json to get summaries
with open('output/gatsby/analysis.json') as f:
    data = json.load(f)

# Extract summaries with characters_present (simulating _get_chapter_summaries)
structure = data.get('structure', [])
summaries = []
for ch in structure:
    summary = ch.get('summary', '')
    if not summary:
        continue
    chars = ch.get('characters_present', []) or []
    if chars:
        text = f"[Characters present: {', '.join(chars)}]\n{summary}"
    else:
        text = summary
    summaries.append(text)

print(f"Loaded {len(summaries)} chapter summaries")
print(f"First summary preview: {summaries[0][:200]!r}")
print(f"Total summary chars: {sum(len(s) for s in summaries)}")

# Load the raw text
with open('Test_Texts/gatsby.txt') as f:
    raw_text = f.read()

print(f"\nRaw text length: {len(raw_text)} chars")

# Test mention search for expected characters
from src.pipeline.character_extraction_v2.mention_search import MentionSearcher
from src.models import Character, ConfidenceLevel

searcher = MentionSearcher(raw_text)

test_chars = [
    Character(id='test_0', canonical_name='Nick Carraway', aliases=['Nick', 'Carraway', 'Nick Carraway'], confidence=ConfidenceLevel.MEDIUM),
    Character(id='test_1', canonical_name='Jay Gatsby', aliases=['Gatsby', 'Jay'], confidence=ConfidenceLevel.MEDIUM),
    Character(id='test_2', canonical_name='Daisy Buchanan', aliases=['Daisy'], confidence=ConfidenceLevel.MEDIUM),
    Character(id='test_3', canonical_name='Tom Buchanan', aliases=['Tom'], confidence=ConfidenceLevel.MEDIUM),
    Character(id='test_4', canonical_name='Jordan Baker', aliases=['Jordan'], confidence=ConfidenceLevel.MEDIUM),
]

print("\n--- Mention Search Results ---")
mention_results = searcher.search_all(test_chars)
for char in test_chars:
    result = mention_results[char.id]
    print(f"{char.canonical_name}: {result.total_mentions} total mentions, by_alias={result.mentions_by_alias}")

# Now apply grounding gate
from src.pipeline.character_extraction_v2.grounding import GroundingGate

gate = GroundingGate(min_mentions=3)
report = gate.apply(test_chars, mention_results)
print(f"\n--- Grounding Gate ---")
print(f"Grounded: {report.total_grounded}, Ungrounded: {report.total_ungrounded}")
for r in report.grounding_results:
    status = "GROUNDED" if r.is_grounded else "UNGROUNDED"
    print(f"  [{status}] {r.canonical_name}: {r.total_mentions} mentions, reason={r.reason}")

print("\n--- Test Complete ---")
print("If the above characters are grounded, the mention search works fine.")
print("The issue is likely that the LLM returns wrong names in Pass 1.")
