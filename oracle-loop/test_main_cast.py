#!/usr/bin/env python3
"""Diagnostic script to test main cast extraction on monkeys_paw."""

import json
import sys
sys.path.insert(0, "/home/zacharymandraws/Tools/audiobook_agent")

from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor
from src.llm.client import LLMClient, LLMConfig

# Load analysis.json to get summaries
with open("../output/monkeys_paw/analysis.json") as f:
    analysis = json.load(f)

# Extract chapter summaries
summaries = [ch["summary"] for ch in analysis["structure"] if ch["summary"]]
print(f"Loaded {len(summaries)} chapter summaries")
print(f"\nFirst summary preview:")
print(summaries[0][:200] + "...")

# Check if Mrs. White is mentioned
for i, summary in enumerate(summaries):
    if "Mrs. White" in summary or "mrs. white" in summary.lower():
        print(f"\n✓ Mrs. White mentioned in chapter {i+1}")

# Initialize LLM client (use same config as analysis used)
actual_model = analysis["_config"]["agents"]["characters"]["model"]
print(f"\nUsing model from config: {actual_model}")

llm_config = LLMConfig(
    provider="ollama",
    model=actual_model,
    base_url="http://localhost:11434",
    temperature=0.3,
)

llm = LLMClient(llm_config)

# Run main cast extraction
print(f"\n{'='*60}")
print("Running main cast extraction...")
print(f"{'='*60}\n")

extractor = MainCastExtractor(llm)
profiles = extractor.extract(summaries, use_two_pass=False)

print(f"\n{'='*60}")
print(f"RESULT: Extracted {len(profiles)} main cast profiles")
print(f"{'='*60}\n")

if profiles:
    for profile in profiles:
        print(f"  - {profile.canonical_name}")
        if profile.aliases:
            print(f"    Aliases: {', '.join(profile.aliases)}")
        print(f"    Role: {profile.role}")
        print()

    # Check specifically for Mrs. White and Mr. White aliases
    mr_white = next((p for p in profiles if "Mr. White" in p.canonical_name), None)
    mrs_white = next((p for p in profiles if "Mrs. White" in p.canonical_name), None)

    print(f"\n{'='*60}")
    print("VERIFICATION:")
    print(f"{'='*60}")
    print(f"✓ Mrs. White extracted: {mrs_white is not None}")
    if mr_white:
        print(f"✓ Mr. White has aliases: {mr_white.aliases}")
        print(f"  - 'father' in aliases: {'father' in mr_white.aliases}")
        print(f"  - 'the old man' in aliases: {'the old man' in mr_white.aliases}")
else:
    print("  ⚠️  NO PROFILES EXTRACTED!")
    print("\nThis is the bug - main cast extraction returned 0 characters.")
