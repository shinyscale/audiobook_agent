#!/usr/bin/env python3
"""
Smoke test for disambiguation label fix.

Verifies that the _apply_disambiguation_labels_from_constraints() method
correctly extracts and applies labels from constraint edges.
"""

import sys
sys.path.insert(0, "/home/zacharymandrews/Tools/audiobook_agent")

from src.agents.characters import CharacterAgent
from src.pipeline.character_extraction.models import Character as PipelineCharacter


def test_extract_labels():
    """Test label extraction from different reason formats."""
    agent = CharacterAgent(llm_client=None, config=None)

    # Test format 1: labels array
    reason1 = "Summary disambiguates 'John Donaldson': 2 distinct people with labels ['the father', 'the son']"
    labels1 = agent._extract_labels_from_reason(reason1)
    assert labels1 == ["the father", "the son"], f"Expected ['the father', 'the son'], got {labels1}"
    print(f"✓ Format 1 (labels array): {labels1}")

    # Test format 2: parenthetical
    reason2 = "Generational conflict: 'John' (the son of john) vs 'John' (the father of john)"
    labels2 = agent._extract_labels_from_reason(reason2)
    print(f"✓ Format 2 (parenthetical): {labels2}")

    print("\n✓ All label extraction tests passed!")


def test_apply_labels():
    """Test applying labels to characters with same name."""
    agent = CharacterAgent(llm_client=None, config=None)

    # Create two characters with the same name
    char1 = PipelineCharacter(
        id="main_cast_1",
        canonical_name="John Donaldson",
        aliases=[],
        mentions=[],
        first_appearance_chapter=0,
        mention_count=9,
        chapters_present=[],
        confidence=0.8,
        supporting_strategies=[],
        description="",
        is_narrator=True,
        narrative_role="Secondary narrator",
        role="protagonist",
    )

    char2 = PipelineCharacter(
        id="main_cast_2",
        canonical_name="John Donaldson",
        aliases=["the father"],
        mentions=[],
        first_appearance_chapter=0,
        mention_count=29,
        chapters_present=[],
        confidence=0.9,
        supporting_strategies=[],
        description="",
        is_narrator=False,
        narrative_role=None,
        role="supporting",
    )

    # Create identity graph data matching the actual format from american_sir
    identity_graph_data = {
        "graph": {
            "constraint_edges": [
                {
                    "source": "main_cast_1",
                    "target": "main_cast_2",
                    "type": "role_conflict",
                    "strength": 1.0,
                    "reason": "Summary disambiguates 'John Donaldson': 2 distinct people with labels ['the father', 'the son']"
                }
            ]
        }
    }

    # Apply labels
    characters = [char1, char2]
    updated_chars = agent._apply_disambiguation_labels_from_constraints(
        characters, identity_graph_data
    )

    # Check results
    print(f"\nBefore:")
    print(f"  char1: {char1.canonical_name} (is_narrator={char1.is_narrator})")
    print(f"  char2: {char2.canonical_name} (is_narrator={char2.is_narrator})")

    print(f"\nAfter:")
    print(f"  char1: {updated_chars[0].canonical_name}")
    print(f"  char2: {updated_chars[1].canonical_name}")

    # Verify labels were applied
    assert "(" in updated_chars[0].canonical_name, f"Expected label in char1 name: {updated_chars[0].canonical_name}"
    assert "(" in updated_chars[1].canonical_name, f"Expected label in char2 name: {updated_chars[1].canonical_name}"

    # Verify they have different labels
    assert updated_chars[0].canonical_name != updated_chars[1].canonical_name, "Characters should have different labels"

    # The narrator (char1) should get "the son" label
    assert "son" in updated_chars[0].canonical_name.lower(), f"Narrator should have 'son' label: {updated_chars[0].canonical_name}"
    assert "father" in updated_chars[1].canonical_name.lower(), f"Non-narrator should have 'father' label: {updated_chars[1].canonical_name}"

    print("\n✓ All label application tests passed!")


if __name__ == "__main__":
    print("Testing disambiguation label fix...\n")
    test_extract_labels()
    test_apply_labels()
    print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
