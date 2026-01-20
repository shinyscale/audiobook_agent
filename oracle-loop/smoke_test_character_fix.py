#!/usr/bin/env python3
"""
Smoke test for character canonical name selection fix.

Tests that:
1. "Herbert White" does NOT merge into bare "White"
2. "Mr. White" and "White" DO merge (after Herbert is correctly separated)
"""

import sys
sys.path.insert(0, '/home/zacharymandrews/Tools/audiobook_agent/src')

from ingestion import get_ingester, refine_extracted_document
from pipeline.character_extraction import build_character_consensus
from pipeline.character_extraction.proposers.llm_proposer import LLMCharacterProposer
from pipeline.character_extraction.validator import CharacterValidator
from pipeline.llm import LLMClient, LLMConfig
from agents.config import OrchestratorConfig, create_optimized_config
import logging

logging.basicConfig(level=logging.INFO)

# Load the test text
ingester = get_ingester('../Test_Texts/The_Monkey\'s_Paw.txt')
raw_doc = ingester.ingest()
doc = refine_extracted_document(raw_doc)
print(f"Loaded document: {doc.metadata.title}")
print(f"Chapters: {len(doc.chapters)}")

# Use first 3 chapters for smoke test
test_chapters = doc.chapters[:3]
print(f"Testing with {len(test_chapters)} chapters")

# Set up LLM and pipeline components
config = create_optimized_config()
character_config = config.get_agent_config("characters")
llm = LLMClient(LLMConfig.ollama(
    model=character_config.model,
    temperature=character_config.temperature
))

proposer = LLMCharacterProposer(llm=llm)
validator = CharacterValidator(llm=llm)

print("\n=== Running character extraction ===")
result = build_character_consensus(
    chapters=test_chapters,
    proposer=proposer,
    validator=validator,
    llm=llm
)

print(f"\n=== Results: {len(result.characters)} characters found ===\n")

# Check results
errors = []
warnings = []

for char in result.characters:
    print(f"Character: {char.canonical_name}")
    if char.aliases:
        print(f"  Aliases: {char.aliases}")
    print(f"  Mentions: {char.mention_count}")
    print()

    # TEST 1: "White" should NOT have "Herbert White" or "Herbert" as aliases
    if char.canonical_name.lower() == "white":
        if "Herbert White" in char.aliases or "Herbert" in char.aliases:
            errors.append(
                f"FAIL: 'White' has Herbert aliases: {char.aliases}\n"
                f"      Herbert should be separate from the father!"
            )

    # TEST 2: "Mr. White" should either:
    #   - Be merged with "White" (canonical could be either), OR
    #   - "White" should have "Mr. White" as alias
    # We'll check after processing all characters

# Check for proper merging
white_entries = [c for c in result.characters if 'white' in c.canonical_name.lower()]
print(f"=== White family entries: {len(white_entries)} ===")

has_mr_white = any(c.canonical_name == "Mr. White" for c in white_entries)
has_white = any(c.canonical_name == "White" for c in white_entries)
has_herbert_white = any(c.canonical_name == "Herbert White" or c.canonical_name == "Herbert" for c in white_entries)

# Find if Mr. White and White are merged
mr_white_merged_with_white = False
for char in white_entries:
    if char.canonical_name == "Mr. White" and "White" in char.aliases:
        mr_white_merged_with_white = True
        print(f"✓ 'Mr. White' merged with 'White' (Mr. White is canonical)")
    elif char.canonical_name == "White" and "Mr. White" in char.aliases:
        mr_white_merged_with_white = True
        print(f"✓ 'White' merged with 'Mr. White' (White is canonical)")

if has_mr_white and has_white and not mr_white_merged_with_white:
    warnings.append(
        "WARNING: 'Mr. White' and 'White' exist separately.\n"
        "         These should be merged (they're the same person - the father)."
    )

if has_herbert_white:
    print(f"✓ Herbert White/Herbert is separate from 'White'")
else:
    errors.append(
        "FAIL: Herbert White not found as separate character.\n"
        "      He should exist separately from his father."
    )

# Summary
print("\n" + "="*60)
print("SMOKE TEST SUMMARY")
print("="*60)

if errors:
    print("❌ FAILED")
    for error in errors:
        print(f"\n{error}")
else:
    print("✅ PASSED - Herbert is correctly separated from 'White'")

if warnings:
    print("\n⚠ WARNINGS:")
    for warning in warnings:
        print(f"\n{warning}")

print("\nExpected correct state:")
print("  - 'Mr. White' + 'White' → MERGED (same person, the father)")
print("  - 'Herbert White' + 'Herbert' → MERGED (same person, the son)")
print("  - 'Mrs. White' → SEPARATE (the mother)")
print("  - Father ≠ Son ≠ Mother (three different people)")

sys.exit(1 if errors else 0)
