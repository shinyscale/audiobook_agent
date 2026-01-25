#!/usr/bin/env python3
"""
Smoke test for Gutenberg boilerplate filtering fix.

Tests that the regions.py fix correctly identifies Project Gutenberg license text as back matter.
"""

import sys
from pathlib import Path
sys.path.insert(0, '../src')

from ingestion.regions import RegionDetector, RegionType
from ingestion.base import get_ingester
from ingestion.refine import refine_extracted_document

def test_gutenberg_detection():
    """Test that Gutenberg boilerplate is stripped during refinement."""

    # Load the monkey's paw text
    print("Loading The Monkey's Paw...")
    text_path = Path('../Test_Texts/The_Monkey\'s_Paw.txt')
    ingester = get_ingester(text_path)
    doc = ingester.extract(text_path)

    print("Before refinement:")
    print(f"  Text length: {len(doc.text)} chars")
    gutenberg_before = doc.text.find('*** END OF THE PROJECT GUTENBERG')
    if gutenberg_before >= 0:
        print(f"  Gutenberg license found at position: {gutenberg_before}")
    else:
        print("  Gutenberg license NOT found (unexpected!)")

    # Apply refinement (this should strip Gutenberg boilerplate)
    print("\nApplying refinement...")
    doc = refine_extracted_document(doc)

    print("\nAfter refinement:")
    print(f"  Text length: {len(doc.text)} chars")
    gutenberg_after = doc.text.find('*** END OF THE PROJECT GUTENBERG')
    if gutenberg_after >= 0:
        print(f"  ❌ FAIL: Gutenberg license STILL found at position: {gutenberg_after}")
        return False
    else:
        print(f"  ✅ SUCCESS: Gutenberg license removed!")

    # Verify no problematic terms remain in the text
    full_text = doc.text
    problematic = ['GutenbergTM', 'eBooks', 'PGLAF', 'MERCHANTABILITY']
    found_terms = [term for term in problematic if term in full_text]

    if found_terms:
        print(f"\n❌ WARNING: Some problematic terms still in text: {', '.join(found_terms)}")
        print("  (These may be in the story content itself)")

    # Check refinement warnings
    print("\nRefinement warnings:")
    for warning in doc.extraction_warnings:
        if 'Gutenberg' in warning or 'gutenberg' in warning:
            print(f"  {warning}")

    return True

if __name__ == '__main__':
    success = test_gutenberg_detection()
    sys.exit(0 if success else 1)
