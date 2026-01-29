#!/usr/bin/env python3
"""
Smoke test for relationship extraction fix.
Tests profile generation for Uncle Bill character.
"""

import json
import sys
sys.path.insert(0, '/home/zacharymandrews/Tools/audiobook_agent')

from src.analyzer import AudiobookAnalyzer
from src.ingestion.base import ingest_document
from src.agents.config import OrchestratorConfig

def test_relationship_extraction():
    """Test that relationships are now being extracted."""

    print("=" * 60)
    print("SMOKE TEST: Relationship Extraction Fix")
    print("=" * 60)

    # Load the text
    doc = ingest_document('../test_texts/american_sir.txt')
    print(f"\n✓ Loaded document ({len(doc.text)} chars)")

    # Create analyzer
    config = OrchestratorConfig()
    analyzer = AudiobookAnalyzer(
        llm_model="qwen2.5:32b",
        llm_provider="ollama",
        orchestrator_config=config
    )
    print(f"✓ Created analyzer with model: qwen2.5:32b")

    # Run analysis
    print("\n📊 Running analysis...")
    result = analyzer.analyze(doc)

    # Check relationships
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    found_relationships = False
    for char in result.characters:
        rel_count = len(char.relationships) if char.relationships else 0
        status = "✓" if rel_count > 0 else "✗"
        print(f"\n{status} {char.canonical_name}:")
        print(f"   Mention count: {char.mention_count}")
        print(f"   Evidence items: {len(char.evidence) if char.evidence else 0}")
        print(f"   Relationships: {rel_count}")
        if char.relationships:
            for other_char, rel_type in char.relationships.items():
                print(f"      → {other_char}: {rel_type}")
            found_relationships = True
        else:
            print(f"      (empty)")

    # Final verdict
    print("\n" + "=" * 60)
    if found_relationships:
        print("✓ SMOKE TEST PASSED: At least one character has relationships")
        return 0
    else:
        print("✗ SMOKE TEST FAILED: No relationships extracted")
        return 1

if __name__ == "__main__":
    sys.exit(test_relationship_extraction())
