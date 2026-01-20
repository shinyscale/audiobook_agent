#!/usr/bin/env python3
"""
Smoke test for character extraction fix.
Tests the specific "Mr. White" vs "White" merge issue.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion import get_ingester, refine_extracted_document
from src.pipeline.character_extraction import extract_characters
from src.agents.config import OrchestratorConfig, AgentConfig

def main():
    # Load The Monkey's Paw
    text_path = "/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The_Monkey's_Paw.txt"
    if not os.path.exists(text_path):
        print(f"ERROR: Test text not found at {text_path}")
        sys.exit(1)

    print("Loading The Monkey's Paw...")
    ingester = get_ingester(text_path)
    doc = ingester.ingest()
    doc = refine_extracted_document(doc)
    print(f"Loaded {len(doc.chapters)} chapters, {len(doc.text)} characters")

    # Configure to use a fast model for testing
    config = OrchestratorConfig(default_model="qwen3:30b-instruct")
    config.set_agent_config("characters", AgentConfig(
        model="qwen3:30b-instruct",
        temperature=0.3,
        max_tokens=4096
    ))

    # Extract characters
    print("\nExtracting characters...")
    result = extract_characters(doc, config)

    # Check results
    print("\n=== CHARACTER EXTRACTION RESULTS ===")
    print(f"Total characters found: {len(result.characters)}")

    # Check for specific issues
    issues = []

    mr_white = None
    white = None
    herbert_white = None

    for char in result.characters:
        print(f"\n{char.name} ({char.mention_count} mentions)")
        if char.aliases:
            print(f"  Aliases: {char.aliases}")

        if char.name == "Mr. White":
            mr_white = char
        elif char.name == "White":
            white = char
        elif char.name == "Herbert White":
            herbert_white = char

    # Check Issue #1: "Mr. White" vs "White" split
    if mr_white and white:
        issues.append("❌ ISSUE #1: 'Mr. White' and 'White' are still separate characters")
    elif mr_white and "White" not in mr_white.aliases:
        issues.append("⚠️  Issue #1: 'Mr. White' exists but doesn't have 'White' as alias")
    elif white and "Mr. White" not in white.aliases:
        issues.append("⚠️  Issue #1: 'White' exists but doesn't have 'Mr. White' as alias")
    else:
        print("\n✓ Issue #1 FIXED: 'Mr. White' and 'White' are merged")

    # Check Issue #2: Herbert wrongly aliased to "White"
    if white and ("Herbert White" in white.aliases or "Herbert" in white.aliases):
        issues.append("❌ ISSUE #2: 'Herbert' is still wrongly aliased to 'White' (father)")
    elif mr_white and ("Herbert White" in mr_white.aliases or "Herbert" in mr_white.aliases):
        issues.append("❌ ISSUE #2: 'Herbert' is wrongly aliased to 'Mr. White' (father)")
    elif not herbert_white and not any("Herbert" in c.name or "Herbert" in c.aliases for c in result.characters):
        issues.append("⚠️  Issue #2: Herbert White is completely missing")
    else:
        print("✓ Issue #2 FIXED: Herbert is separate from his father")

    # Summary
    print("\n=== SMOKE TEST SUMMARY ===")
    if issues:
        print("❌ SMOKE TEST FAILED:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("✓ SMOKE TEST PASSED: All issues fixed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
