#!/usr/bin/env python3
"""Diagnostic: Run Pass 1 character extraction with actual Gatsby summaries."""
import json
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.insert(0, '.')

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.character_extraction_v2.main_cast import CHARACTER_IDENTIFICATION_PROMPT, MainCastExtractor

# Load summaries from analysis.json
with open('output/gatsby/analysis.json') as f:
    data = json.load(f)

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

summaries_text = "\n\n".join(f"Chapter {i+1}:\n{s}" for i, s in enumerate(summaries))

# Build the prompt
prompt = CHARACTER_IDENTIFICATION_PROMPT.format(
    summaries=summaries_text,
    plot_summary_section="",
)

print(f"Prompt length: {len(prompt)} chars")
print(f"Prompt preview (first 200): {prompt[:200]!r}")
print(f"Prompt preview (last 200): {prompt[-200:]!r}")

# Initialize LLM
config = LLMConfig.ollama(model='qwen3-next:80b-a3b-instruct-q8_0')
config.temperature = 0.7
config.context_length = 32768
config.max_tokens = 32768
config.think = False

client = LLMClient(config)

print("\n--- Querying LLM (this may take a while)... ---")
result, response = client.query_json(prompt)

print(f"\n--- LLM Response ---")
print(f"success: {response.success}")
print(f"error: {response.error}")
print(f"content length: {len(response.content) if response.content else 0}")
if response.content:
    print(f"content preview (first 500): {response.content[:500]!r}")
    print(f"content preview (last 200): {response.content[-200:]!r}")

print(f"\n--- Parsed Result ---")
print(f"type: {type(result).__name__ if result is not None else 'None'}")
if isinstance(result, list):
    print(f"items: {len(result)}")
    for i, item in enumerate(result[:3]):
        print(f"  [{i}]: {item}")
elif isinstance(result, dict):
    print(f"keys: {list(result.keys())}")

# Now parse it
extractor = MainCastExtractor(client)
if result is not None:
    profiles = extractor._parse_pass1_results(result)
    print(f"\n--- Parsed Profiles ---")
    print(f"count: {len(profiles)}")
    for p in profiles[:5]:
        print(f"  - {p.canonical_name} ({p.role})")
