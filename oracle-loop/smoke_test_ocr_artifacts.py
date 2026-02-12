#!/usr/bin/env python3
"""Smoke test for OCR artifact detection in pronunciation guide."""

import sys
sys.path.insert(0, '../src')

from src.pipeline.pronunciation_guide.proposers.cmu_proposer import CMUProposer

def test_ocr_artifacts():
    """Test that concatenation artifacts are detected."""
    proposer = CMUProposer()

    # Test cases: (word, should_be_artifact)
    test_cases = [
        ("himselfin", True),    # himself + in
        ("beliefin", True),     # belief + in
        ("tothe", True),        # to + the
        ("fakir", False),       # real word, not artifact
        ("antimacassar", False),# real word, not artifact
        ("flambeaux", False),   # real word (though obscure), not artifact
    ]

    print("Testing OCR artifact detection:")
    print("-" * 60)

    all_passed = True
    for word, expected_artifact in test_cases:
        is_artifact = proposer._is_ocr_artifact(word)
        status = "✓" if is_artifact == expected_artifact else "✗"
        result = "ARTIFACT" if is_artifact else "REAL WORD"
        expected = "ARTIFACT" if expected_artifact else "REAL WORD"

        print(f"{status} {word:20s} → {result:12s} (expected: {expected})")

        if is_artifact != expected_artifact:
            all_passed = False

    print("-" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_ocr_artifacts())
