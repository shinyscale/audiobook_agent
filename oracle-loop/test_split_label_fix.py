#!/usr/bin/env python3
"""
Smoke test for split character label disambiguation fix.

Tests that passages containing label-specific aliases (e.g., "the father")
are correctly assigned to the corresponding split character, preventing
profile cross-contamination.
"""

import sys
sys.path.insert(0, "../src")

from src.pipeline.character_profiling.name_disambiguator import (
    NameAmbiguityMap,
    ContextDisambiguator,
)


class MockCharacter:
    """Mock IdentifiedCharacter for testing."""
    def __init__(self, canonical_name, aliases):
        self.canonical_name = canonical_name
        self.aliases = aliases


def test_split_character_label_detection():
    """Test that label-specific aliases correctly disambiguate split characters."""

    # Simulate split characters with overlapping aliases
    father = MockCharacter(
        canonical_name="John Donaldson (the father)",
        aliases=["the father", "John Donaldson", "John"]
    )
    son = MockCharacter(
        canonical_name="John Donaldson (the son)",
        aliases=["John Donaldson", "John"]  # No "the son" in aliases (it's in canonical)
    )

    characters = [father, son]

    # Build disambiguator
    ambiguity_map = NameAmbiguityMap(characters)

    # DEBUG: Print what the ambiguity map detected
    print("DEBUG: Ambiguous names detected:")
    for name, ambig in ambiguity_map.get_ambiguous_names().items():
        print(f"  '{name}' -> {ambig.possible_characters}")
    print()

    disambiguator = ContextDisambiguator(
        ambiguity_map=ambiguity_map,
        summary_map=None,
        llm_client=None,
        characters=characters,
    )

    # Test 1: Passage contains "the father" - should strongly assign to father
    father_passage = "John Donaldson, the father, was fifty-five years old and grizzled."
    father_target_names = ["John Donaldson (the father)", "the father", "John Donaldson", "John"]

    result = disambiguator.disambiguate(
        name="John Donaldson",
        sentence=father_passage,
        target_character_names=father_target_names,
    )

    print(f"Test 1: Passage with 'the father'")
    print(f"  Resolved to: {result.resolved_character}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
    print(f"  Reason: {result.reason}")

    assert result.resolved_character == "John Donaldson (the father)", \
        f"Expected father, got {result.resolved_character}"
    assert result.confidence >= 0.99, \
        f"Expected high confidence (>= 0.99), got {result.confidence}"
    assert result.method == "split_label", \
        f"Expected split_label method, got {result.method}"
    print("  ✓ PASS\n")

    # Test 2: Passage about father when profiling son - should reject
    son_target_names = ["John Donaldson (the son)", "John Donaldson", "John"]

    result = disambiguator.disambiguate(
        name="John Donaldson",
        sentence=father_passage,  # Contains "the father"
        target_character_names=son_target_names,
    )

    print(f"Test 2: Father passage when profiling son")
    print(f"  Resolved to: {result.resolved_character}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
    print(f"  Reason: {result.reason}")

    # Should detect mismatch and return low confidence
    assert result.confidence < 0.5, \
        f"Expected low confidence (< 0.5) for mismatched label, got {result.confidence}"
    print("  ✓ PASS\n")

    # Test 3: Passage with no label - should use other signals
    neutral_passage = "John Donaldson was brave and dutiful."

    result = disambiguator.disambiguate(
        name="John",
        sentence=neutral_passage,
        target_character_names=son_target_names,
    )

    print(f"Test 3: Neutral passage (no label)")
    print(f"  Resolved to: {result.resolved_character}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
    print(f"  Reason: {result.reason}")

    # Should NOT use split_label method (no label in passage)
    assert result.method != "split_label", \
        f"Expected non-split_label method for neutral passage, got {result.method}"
    print("  ✓ PASS\n")

    print("=" * 60)
    print("All smoke tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_split_character_label_detection()
