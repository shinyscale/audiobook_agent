#!/usr/bin/env python3
"""
Smoke test for main_cast extraction fix.
Tests if Gatsby and Daisy are now extracted correctly.
"""
import json
import sys

# Load the analysis to get summaries
with open('../output/gatsby/analysis.json', 'r') as f:
    analysis = json.load(f)

# Extract summaries from structure
summaries_text = []
for chapter in analysis['structure']:
    if chapter.get('summary'):
        summaries_text.append(f"Chapter {chapter.get('chapter_number', '?')}: {chapter['summary']}")

summaries_combined = "\n\n".join(summaries_text[:5])  # First 5 chapters for quick test

print("=" * 80)
print("SMOKE TEST: Main Cast Extraction")
print("=" * 80)
print(f"\nTesting with first 5 chapter summaries ({len(summaries_combined)} chars)\n")

# Import the extraction module
sys.path.insert(0, '../src')
from pipeline.character_extraction_v2.main_cast import MainCastExtractor
from llm.client import LLMClient, LLMConfig

# Create LLM client (using same config as actual run)
# Check what model was used
config = analysis.get('_config', {})
model_name = config.get('model', 'qwen2.5:14b')
print(f"Using model: {model_name}")

llm_config = LLMConfig.ollama(model=model_name)
llm_client = LLMClient(llm_config)

# Create extractor and run
extractor = MainCastExtractor()
result = extractor.extract_from_summaries(
    summaries=summaries_combined,
    llm_client=llm_client,
)

print(f"\n✓ Extraction completed: {len(result.characters)} characters found\n")
print("Characters extracted:")
print("-" * 80)

# Check for Gatsby and Daisy specifically
found_gatsby = False
found_daisy = False

for char in result.characters:
    print(f"\n{char.canonical_name}")
    print(f"  Role: {char.role}")
    print(f"  Aliases: {char.aliases}")

    if 'gatsby' in char.canonical_name.lower():
        found_gatsby = True
    if 'daisy' in char.canonical_name.lower():
        found_daisy = True

print("\n" + "=" * 80)
print("SMOKE TEST RESULTS:")
print("=" * 80)
print(f"✓ Found Gatsby: {'YES ✓' if found_gatsby else 'NO ✗ FAILED'}")
print(f"✓ Found Daisy: {'YES ✓' if found_daisy else 'NO ✗ FAILED'}")
print(f"✓ Eckleburg filtered: {'YES ✓' if not any('eckleburg' in c.canonical_name.lower() for c in result.characters) else 'NO ✗ FAILED'}")

if found_gatsby and found_daisy:
    print("\n✓✓✓ SMOKE TEST PASSED ✓✓✓")
    sys.exit(0)
else:
    print("\n✗✗✗ SMOKE TEST FAILED ✗✗✗")
    sys.exit(1)
