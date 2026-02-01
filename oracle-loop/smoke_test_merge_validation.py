#!/usr/bin/env python3
"""
Smoke test for consolidated Pass 2 merge validation.

Tests that:
1. Semantically incompatible characters are NOT merged (Creature vs magistrate)
2. Compatible characters CAN still be merged (Victor vs "the narrator")
"""

import sys
sys.path.insert(0, '/home/zacharymandrews/Tools/audiobook_agent')

from src.pipeline.character_extraction_v2.main_cast import MainCastProfile

def test_merge_validation():
    """Test the merge validation logic in _process_consolidated_pass2."""

    # Simulated characters from Pass 1
    initial_characters = [
        MainCastProfile(
            canonical_name="the Creature",
            role="antagonist",
            description="Victor's reanimated creation, seeking revenge against his creator"
        ),
        MainCastProfile(
            canonical_name="the magistrate",
            role="supporting",
            description="Local judicial authority who investigates crimes"
        ),
        MainCastProfile(
            canonical_name="Victor Frankenstein",
            role="protagonist",
            description="Ambitious scientist obsessed with creating life"
        ),
        MainCastProfile(
            canonical_name="the narrator",
            role="protagonist",
            description="Recounts his tragic pursuit of forbidden knowledge"
        ),
    ]

    # Simulated LLM response that tries to:
    # 1. Merge "Creature" into "magistrate" (WRONG - should be blocked)
    # 2. Merge "the narrator" into "Victor Frankenstein" (CORRECT - should succeed)
    alias_result = {
        "characters": [
            {
                "canonical_name": "the Creature",
                "aliases": [],
                "uncertain_aliases": [],
                "merge_into": "the magistrate"  # This is WRONG
            },
            {
                "canonical_name": "the magistrate",
                "aliases": [],
                "uncertain_aliases": [],
                "merge_into": None
            },
            {
                "canonical_name": "Victor Frankenstein",
                "aliases": ["Victor"],
                "uncertain_aliases": [],
                "merge_into": None
            },
            {
                "canonical_name": "the narrator",
                "aliases": [],
                "uncertain_aliases": [],
                "merge_into": "Victor Frankenstein"  # This is CORRECT
            },
        ]
    }

    # Import the extractor (we'll call the private method directly for testing)
    from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor
    from src.llm.client import LLMClient, LLMConfig

    # Create a dummy extractor (we don't need real LLM for this test)
    config = LLMConfig(provider="ollama", model="dummy", temperature=0.0)
    llm_client = LLMClient(config)
    extractor = MainCastExtractor(llm_client)

    # Process the Pass 2 results
    result = extractor._process_consolidated_pass2(initial_characters, alias_result)

    # Verify results
    print("=== Smoke Test Results ===\n")

    # Check 1: The Creature should still exist (not merged into magistrate)
    creature = next((c for c in result if "Creature" in c.canonical_name), None)
    if creature:
        print("✓ PASS: 'the Creature' was NOT merged into magistrate (blocked by semantic validation)")
    else:
        print("✗ FAIL: 'the Creature' was incorrectly merged or removed")
        return False

    # Check 2: The magistrate should exist and should NOT have "Creature" as alias
    magistrate = next((c for c in result if "magistrate" in c.canonical_name), None)
    if magistrate:
        if "Creature" in magistrate.aliases or "creature" in [a.lower() for a in magistrate.aliases]:
            print("✗ FAIL: 'the magistrate' has 'Creature' as an alias (merge was not blocked)")
            return False
        else:
            print("✓ PASS: 'the magistrate' does NOT have 'Creature' as alias")
    else:
        print("✗ FAIL: 'the magistrate' was removed")
        return False

    # Check 3: "the narrator" should be merged into Victor
    narrator = next((c for c in result if c.canonical_name == "the narrator"), None)
    if narrator:
        print("✗ FAIL: 'the narrator' still exists (should have been merged into Victor)")
        return False

    victor = next((c for c in result if "Victor" in c.canonical_name), None)
    if victor and "the narrator" in victor.aliases:
        print("✓ PASS: 'the narrator' was correctly merged into 'Victor Frankenstein'")
    else:
        print("✗ FAIL: 'the narrator' merge into Victor did not work")
        return False

    # Check 4: Result should have 3 characters (Creature, magistrate, Victor)
    if len(result) == 3:
        print(f"✓ PASS: Result has correct character count (3)")
    else:
        print(f"✗ FAIL: Expected 3 characters, got {len(result)}")
        return False

    print("\n=== All Smoke Tests Passed ===")
    return True

if __name__ == "__main__":
    success = test_merge_validation()
    sys.exit(0 if success else 1)
