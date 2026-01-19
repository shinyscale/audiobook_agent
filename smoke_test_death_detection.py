#!/usr/bin/env python3
"""
Smoke test for death relationship detection fix.

This script tests whether the death detection properly blocks merging
"the mummer" with "Prince Prospero" in Masque of the Red Death.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion import get_ingester, refine_extracted_document
from pipeline.character_extraction import extract_characters
from agents.config import create_optimized_config

def main():
    print("=" * 80)
    print("SMOKE TEST: Death Relationship Detection")
    print("=" * 80)
    print()

    # Ingest the Masque of Red Death text
    text_path = Path("Test_Texts/Masque of the Red Death - Poe.txt")
    if not text_path.exists():
        print(f"ERROR: Test text not found at {text_path}")
        return 1

    print(f"Ingesting: {text_path}")
    ingester = get_ingester(str(text_path))
    doc = ingester.extract()
    doc = refine_extracted_document(doc)
    print(f"  - Chapters: {len(doc.chapters)}")
    print(f"  - Total text length: {len(doc.full_text)} chars")
    print()

    # Run character extraction
    print("Running character extraction...")
    print("  (This will take 2-5 minutes)")
    print()

    try:
        # Use default config for speed
        config = create_optimized_config()
        result = extract_characters(doc.chapters, config=config)

        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Characters found: {len(result.characters)}")
        print()

        for char in result.characters:
            print(f"  - {char.canonical_name}")
            if char.aliases:
                print(f"    Aliases: {', '.join(char.aliases)}")
        print()

        # Check the specific issue
        print("=" * 80)
        print("VALIDATION")
        print("=" * 80)
        print()

        # Find Prince Prospero
        prospero = None
        mummer = None

        for char in result.characters:
            if "prospero" in char.canonical_name.lower():
                prospero = char
            if "mummer" in char.canonical_name.lower():
                mummer = char

        # Check if mummer is incorrectly merged with Prospero
        mummer_is_alias = False
        if prospero and prospero.aliases:
            for alias in prospero.aliases:
                if "mummer" in alias.lower():
                    mummer_is_alias = True
                    break

        if mummer_is_alias:
            print("❌ FAIL: 'the mummer' is incorrectly merged with Prince Prospero")
            print(f"   Character: {prospero.canonical_name}")
            print(f"   Aliases: {prospero.aliases}")
            print()
            print("   The fix DID NOT WORK - death detection failed")
            return 1

        # Check if they exist as separate characters
        if prospero and mummer:
            print("✅ PASS: 'the mummer' and 'Prince Prospero' are separate characters")
            print(f"   1. {prospero.canonical_name}")
            if prospero.aliases:
                print(f"      Aliases: {', '.join(prospero.aliases)}")
            print(f"   2. {mummer.canonical_name}")
            if mummer.aliases:
                print(f"      Aliases: {', '.join(mummer.aliases)}")
            print()
            print("   The fix WORKED - death detection successfully blocked merge")
            return 0

        # Mummer should exist separately
        if prospero and not mummer:
            print("⚠️  PARTIAL: Prince Prospero exists, but 'the mummer' not found")
            print("   Checking if mummer aliases exist elsewhere...")

            # Check if any character has mummer-related names
            for char in result.characters:
                name_lower = char.canonical_name.lower()
                if any(word in name_lower for word in ["mummer", "stranger", "figure", "intruder", "death"]):
                    print(f"   Found: {char.canonical_name}")
                    if char.aliases:
                        print(f"     Aliases: {', '.join(char.aliases)}")

            print()
            print("   The fix may have worked, but mummer wasn't detected as separate character")
            return 1

        print("❌ FAIL: Prince Prospero not found in results")
        return 1

    except Exception as e:
        print(f"ERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
