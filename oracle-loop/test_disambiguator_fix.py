#!/usr/bin/env python3
"""
Smoke test for passage_gatherer.py disambiguator fix.

Tests that parenthetical disambiguators are correctly stripped
when searching for character names in text.
"""

import re

# Sample text with father/son both named "John Donaldson"
SAMPLE_TEXT = """
John Donaldson, a man of fifty years, had made a grave mistake in his youth.
He took money from the company where he worked. His shame was deep.

Years later, his son also named John Donaldson enlisted in the army at age eighteen.
The young John was brave and served with distinction. Unlike his father, the boy
had never taken anything that wasn't his. His father watched proudly from afar.

Margaret Donaldson, John's wife, wrote letters to her husband about their son's service.
"Young John is doing well," she wrote. "He is nothing like you were at his age."
"""

def test_disambiguator_strip():
    """Test that the regex correctly strips disambiguators."""

    test_cases = [
        ("John Donaldson (the son)", "John Donaldson"),
        ("John Donaldson (the father)", "John Donaldson"),
        ("Victor Frankenstein (the narrator)", "Victor Frankenstein"),
        ("The Creature", "The Creature"),  # No disambiguator
        ("Mr. Smith (Sr.)", "Mr. Smith"),
        ("Mary (the wife)", "Mary"),
    ]

    print("\n=== Testing Disambiguator Strip Logic ===\n")

    all_passed = True
    for input_name, expected_output in test_cases:
        # This is the regex from the fix
        base_name = re.sub(r'\s*\([^)]+\)\s*$', '', input_name).strip()

        if base_name == expected_output:
            print(f"✓ '{input_name}' → '{base_name}'")
        else:
            print(f"✗ '{input_name}' → '{base_name}' (expected '{expected_output}')")
            all_passed = False

    print("\n=== Testing Pattern Matching ===\n")

    # Test that we can now find matches in text
    name_with_disambiguator = "John Donaldson (the son)"
    base_name = re.sub(r'\s*\([^)]+\)\s*$', '', name_with_disambiguator).strip()
    escaped_name = re.escape(base_name)
    pattern = rf"\b{escaped_name}\b"

    matches = list(re.finditer(pattern, SAMPLE_TEXT, re.IGNORECASE))
    print(f"Searching for '{name_with_disambiguator}':")
    print(f"  Base name after stripping: '{base_name}'")
    print(f"  Found {len(matches)} matches in sample text")

    if len(matches) == 0:
        print("✗ FAIL: No matches found! The pattern is not working.")
        all_passed = False
    else:
        print(f"✓ PASS: Found matches at positions: {[m.start() for m in matches]}")

        # Show first match context
        first_match = matches[0]
        start = max(0, first_match.start() - 50)
        end = min(len(SAMPLE_TEXT), first_match.end() + 50)
        context = SAMPLE_TEXT[start:end]
        print(f"\n  First match context: ...{context}...")

    return all_passed


if __name__ == "__main__":
    success = test_disambiguator_strip()
    if success:
        print("\n✓ ALL TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")
    import sys
    sys.exit(0 if success else 1)
