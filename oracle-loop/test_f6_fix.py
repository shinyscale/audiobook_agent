#!/usr/bin/env python3
"""
Smoke test for F6 alias matching fix.
Tests the specific case from masque_of_red_death.
"""

def test_f6_partial_match():
    """Test that 'the masked figure' matches alias 'the figure'"""

    # Simulate the existing character
    class MockChar:
        def __init__(self):
            self.canonical_name = "the Red Death"
            self.aliases = ["the figure"]

    # Simulate F6 logic
    name = "the masked figure"
    char = MockChar()

    clean_lower = name.lower().strip()
    clean_words = set(clean_lower.split())
    stopwords = {"the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her", "their", "our"}
    adjectives = {"old", "young", "mysterious", "masked", "red", "black", "white", "great", "little", "big", "small"}
    core_words = clean_words - stopwords - adjectives

    print(f"Summary name: {name}")
    print(f"Clean words: {clean_words}")
    print(f"Core words after filtering: {core_words}")

    matched = False
    for alias in char.aliases:
        alias_lower = alias.lower().strip()
        alias_words = set(alias_lower.split())
        alias_core = alias_words - stopwords - adjectives

        print(f"\nChecking alias: {alias}")
        print(f"  Alias words: {alias_words}")
        print(f"  Alias core: {alias_core}")
        print(f"  Is subset of core_words? {alias_core.issubset(core_words)}")

        if alias_core and alias_core.issubset(core_words):
            print(f"  ✓ MATCH! '{name}' contains alias '{alias}' core words")
            matched = True
            break

    if matched:
        print("\n✓ TEST PASSED: Would skip 'the masked figure' (recognized as alias)")
        return True
    else:
        print("\n✗ TEST FAILED: Would create duplicate character")
        return False

if __name__ == "__main__":
    success = test_f6_partial_match()
    exit(0 if success else 1)
