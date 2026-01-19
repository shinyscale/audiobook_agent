#!/usr/bin/env python3
"""
Test script for the chapter detection pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline.chapter_detection import ChapterDetectionPipeline
from ingestion import get_ingester, refine_extracted_document


def extract_text(file_path: Path) -> str:
    """Extract text from any supported file format."""
    ingester = get_ingester(file_path)
    doc = ingester.extract(file_path)
    # Apply refinement (includes PDF spacing correction)
    doc = refine_extracted_document(doc)
    return doc.text


def test_document(file_path: Path, name: str):
    """Test chapter detection on a document."""
    print("=" * 70)
    print(f"Testing: {name}")
    print("=" * 70)

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return None

    # Extract text
    print(f"\nExtracting text from: {file_path.name}")
    text = extract_text(file_path)
    print(f"Text length: {len(text):,} characters")
    print(f"Word count: {len(text.split()):,} words")

    # Run pipeline
    print("\n" + "-" * 70)
    print("Running DETERMINISTIC pipeline (no LLM)...")
    print("-" * 70)

    pipeline = ChapterDetectionPipeline.deterministic_only()
    result = pipeline.run(text, source_file=str(file_path))

    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(result.summary())

    # Print detailed chapter info
    print("\n" + "-" * 70)
    print("CHAPTER DETAILS")
    print("-" * 70)
    for ch in result.chapters:
        preview = text[ch.start_position:ch.start_position + 100].strip()
        preview = " ".join(preview.split())[:70]
        print(f"\nChapter {ch.index}: {ch.title or '(no title)'}")
        print(f"  Words: {ch.word_count:,} | Confidence: {ch.confidence:.0%}")
        print(f"  Preview: \"{preview}...\"")

    # Print low confidence boundaries if any
    if result.low_confidence_boundaries:
        print("\n" + "-" * 70)
        print(f"LOW CONFIDENCE BOUNDARIES ({len(result.low_confidence_boundaries)} need review)")
        print("-" * 70)
        for b in result.low_confidence_boundaries[:5]:  # Show first 5
            print(f"  - {b.title or '(untitled)'} @ {b.position:,} ({b.confidence:.0%})")

    # Print document profile
    print("\n" + "-" * 70)
    print("DOCUMENT PROFILE")
    print("-" * 70)
    profile = result.document_profile
    print(f"  Type: {profile.document_type}")
    print(f"  Has explicit markers: {profile.has_explicit_markers}")
    print(f"  Has TOC: {profile.has_table_of_contents}")
    print(f"  Conventions: {', '.join(profile.structural_conventions) or 'none detected'}")

    if profile.table_of_contents:
        entries = profile.table_of_contents.entries
        print(f"\n  TOC Entries ({len(entries)}):")
        for entry in entries[:12]:
            print(f"    - {entry.title}")
        if len(entries) > 12:
            print(f"    ... and {len(entries) - 12} more")

    print("\n")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test chapter detection pipeline")
    parser.add_argument("file", nargs="?", help="File to test (default: all test files)")
    args = parser.parse_args()

    test_dir = Path("Test_Texts")

    if args.file:
        # Test specific file
        file_path = Path(args.file)
        if not file_path.exists():
            file_path = test_dir / args.file
        test_document(file_path, file_path.name)
    else:
        # Test all files
        test_files = [
            (test_dir / "gatsby.txt", "The Great Gatsby"),
            (test_dir / "Shelley_1888_Frankenstein.pdf", "Frankenstein (1888 PDF)"),
            (test_dir / "See the Light V-15 11-11-25.docx", "See the Light (DOCX)"),
        ]

        for file_path, name in test_files:
            if file_path.exists():
                test_document(file_path, name)
            else:
                print(f"Skipping {name}: file not found")


if __name__ == "__main__":
    main()
