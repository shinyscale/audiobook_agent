#!/usr/bin/env python3
"""
Smoke test for disambiguation label guard in _process_consolidated_pass2().

Tests that characters with the same base name but different disambiguation labels
(e.g., "John Donaldson (the father)" and "John Donaldson (the son)") are NOT merged.
"""

import sys
import os

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor, MainCastProfile
from src.llm.client import LLMClient, LLMConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_disambiguation_label_protection():
    """Test that disambiguation labels prevent merges."""

    # Enable debug logging
    logging.getLogger().setLevel(logging.DEBUG)

    # Create extractor (need LLMClient for instantiation, won't actually use it)
    llm = LLMClient(LLMConfig.ollama(model="qwen2.5:7b"))
    extractor = MainCastExtractor(llm)

    # Create initial characters with disambiguation labels
    initial_characters = [
        MainCastProfile(
            canonical_name="John Donaldson (the father)",
            aliases=[],
            uncertain_aliases=[],
            role="supporting",
            is_symbolic=False,
            description="The older John, father of the young John",
        ),
        MainCastProfile(
            canonical_name="John Donaldson (the son)",
            aliases=[],
            uncertain_aliases=[],
            role="protagonist",
            is_symbolic=False,
            description="The younger John, son of the older John",
        ),
    ]

    # Simulate LLM response that tries to merge them (nondeterministic failure case)
    alias_result = {
        "characters": [
            {
                "canonical_name": "John Donaldson (the father)",
                "aliases": ["John Donaldson", "John"],
                "uncertain_aliases": [],
                "merge_into": None,
            },
            {
                "canonical_name": "John Donaldson (the son)",
                "aliases": [],
                "uncertain_aliases": [],
                "merge_into": "John Donaldson (the father)",  # LLM incorrectly tries to merge them
            },
        ]
    }

    # Process with the deterministic guard
    print("\n=== Before processing ===")
    for c in initial_characters:
        print(f"  {c.canonical_name}: aliases={c.aliases}")

    print("\n=== Processing with alias_result ===")
    print(f"  alias_result = {alias_result}")

    result = extractor._process_consolidated_pass2(initial_characters, alias_result)

    print("\n=== After processing ===")
    # Verify both characters still exist
    canonical_names = [c.canonical_name for c in result]
    print(f"Result: {len(result)} characters")
    for c in result:
        print(f"  - {c.canonical_name} (aliases: {c.aliases})")

    # Assert both still exist
    assert len(result) == 2, f"Expected 2 characters, got {len(result)}"
    assert "John Donaldson (the father)" in canonical_names, "Father character missing!"
    assert "John Donaldson (the son)" in canonical_names, "Son character missing!"

    # Verify son was NOT added as alias of father
    father = [c for c in result if c.canonical_name == "John Donaldson (the father)"][0]
    assert "John Donaldson (the son)" not in father.aliases, \
        "Son was incorrectly added as alias of father!"

    # Verify father's aliases were still applied (even though merge was blocked)
    assert "John Donaldson" in father.aliases, "Father should have 'John Donaldson' alias"
    assert "John" in father.aliases, "Father should have 'John' alias"

    print("\n✓ SUCCESS: Disambiguation label guard correctly prevented invalid merge")
    print("✓ Father's aliases were still applied correctly")
    return True


if __name__ == "__main__":
    try:
        test_disambiguation_label_protection()
        print("\nAll smoke tests PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
