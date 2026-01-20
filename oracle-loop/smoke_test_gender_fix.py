#!/usr/bin/env python3
"""
Smoke test for gender conflict detection in epithet resolution.

Tests that:
1. "the old man" is detected as male
2. "the old woman" is detected as female
3. "the sergeant-major" is detected as male
4. Gender conflicts block merges
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.pipeline.character_extraction.consensus import CharacterConsensusBuilder

def test_gender_detection():
    """Test that gender detection works correctly."""
    # Create a minimal consensus builder (no LLM needed for this test)
    builder = CharacterConsensusBuilder(
        llm_client=None,
        use_llm_alias_resolution=False
    )

    test_cases = [
        ("the old man", "male"),
        ("the old woman", "female"),
        ("the sergeant-major", "male"),
        ("his wife", "female"),
        ("the soldier", "male"),
        ("the stranger", None),  # ambiguous
        ("the visitor", None),  # ambiguous
    ]

    print("Testing gender detection:")
    print("-" * 50)

    all_passed = True
    for epithet, expected_gender in test_cases:
        detected = builder._detect_epithet_gender(epithet)
        status = "✓" if detected == expected_gender else "✗"

        if detected != expected_gender:
            all_passed = False

        print(f"{status} '{epithet}' -> {detected} (expected: {expected_gender})")

    print("-" * 50)

    if all_passed:
        print("✓ All gender detection tests PASSED")
        return True
    else:
        print("✗ Some gender detection tests FAILED")
        return False

def test_gender_conflict_scenarios():
    """Test gender conflict blocking scenarios."""
    print("\nTesting gender conflict scenarios:")
    print("-" * 50)

    builder = CharacterConsensusBuilder(
        llm_client=None,
        use_llm_alias_resolution=False
    )

    # Simulate conflict scenarios
    conflicts = [
        ("the old man", "the old woman", True),  # Should conflict
        ("the sergeant-major", "the soldier", False),  # Both male, no conflict
        ("the old man", "the visitor", False),  # One ambiguous, no conflict
        ("his wife", "the old woman", False),  # Both female, no conflict
    ]

    all_passed = True
    for epithet1, epithet2, should_conflict in conflicts:
        gender1 = builder._detect_epithet_gender(epithet1)
        gender2 = builder._detect_epithet_gender(epithet2)

        # Conflict occurs when both genders are detected and they differ
        would_conflict = (
            gender1 is not None and
            gender2 is not None and
            gender1 != gender2
        )

        status = "✓" if would_conflict == should_conflict else "✗"

        if would_conflict != should_conflict:
            all_passed = False

        print(
            f"{status} '{epithet1}' ({gender1}) vs '{epithet2}' ({gender2}) -> "
            f"conflict={would_conflict} (expected: {should_conflict})"
        )

    print("-" * 50)

    if all_passed:
        print("✓ All conflict scenario tests PASSED")
        return True
    else:
        print("✗ Some conflict scenario tests FAILED")
        return False

if __name__ == "__main__":
    test1_passed = test_gender_detection()
    test2_passed = test_gender_conflict_scenarios()

    if test1_passed and test2_passed:
        print("\n✓✓✓ ALL SMOKE TESTS PASSED ✓✓✓")
        sys.exit(0)
    else:
        print("\n✗✗✗ SOME SMOKE TESTS FAILED ✗✗✗")
        sys.exit(1)
