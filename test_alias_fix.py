#!/usr/bin/env python3
"""
Smoke test for the misplaced alias fix.
Tests the _fix_misplaced_aliases method directly.
"""

from src.pipeline.character_extraction.models import Character, CharacterMap, CharacterMention

# Create a mock CharacterMap similar to the Masque of the Red Death issue
def create_mock_character_map():
    # Character 1: "the Prince Prospero" with NO aliases (should have "Prospero")
    prince_char = Character(
        id="char_prince",
        canonical_name="the Prince Prospero",
        aliases=[],  # Empty - this is the problem!
        mentions=[
            CharacterMention(
                text="Prince Prospero",
                context="the Prince Prospero was happy and dauntless",
                chapter_index=1,
                position=100,
                in_dialogue=False,
                is_agentive=True
            )
        ],
        first_appearance_chapter=1,
        mention_count=3,
        chapters_present=[1],
        confidence=0.9,
        supporting_strategies=["ner", "llm_character"],
    )

    # Character 2: "the mummer" with "Prospero" as alias (WRONG!)
    mummer_char = Character(
        id="char_mummer",
        canonical_name="the mummer",
        aliases=["Prospero"],  # This should be moved to prince_char
        mentions=[
            CharacterMention(
                text="the mummer",
                context="the mummer had gone so far",
                chapter_index=1,
                position=500,
                in_dialogue=False,
                is_agentive=True
            )
        ],
        first_appearance_chapter=1,
        mention_count=4,
        chapters_present=[1],
        confidence=0.9,
        supporting_strategies=["ner"],
    )

    character_map = CharacterMap(
        characters=[prince_char, mummer_char],
        low_confidence_characters=[],
        total_mentions=7,
        total_chapters=1,
        pipeline_metadata={}
    )

    return character_map


def test_fix_misplaced_aliases():
    """Test that the fix correctly moves 'Prospero' to 'the Prince Prospero'"""
    from src.agents.characters import CharacterAgent

    # Create the agent (we don't need LLM for this test)
    agent = CharacterAgent(llm_client=None, config=None, tuning=None)

    # Create mock data
    character_map = create_mock_character_map()

    # Print BEFORE state
    print("=" * 60)
    print("BEFORE FIX:")
    print("=" * 60)
    for char in character_map.characters:
        print(f"  {char.canonical_name}: aliases={char.aliases}")

    # Apply the fix
    fixed_map = agent._fix_misplaced_aliases(character_map)

    # Print AFTER state
    print("\n" + "=" * 60)
    print("AFTER FIX:")
    print("=" * 60)
    for char in fixed_map.characters:
        print(f"  {char.canonical_name}: aliases={char.aliases}")

    # Verify the fix worked
    print("\n" + "=" * 60)
    print("VERIFICATION:")
    print("=" * 60)

    prince_char = next(c for c in fixed_map.characters if "Prince" in c.canonical_name)
    mummer_char = next(c for c in fixed_map.characters if "mummer" in c.canonical_name)

    success = True

    # Check: Prince Prospero should now have "Prospero" as an alias
    if "Prospero" in prince_char.aliases:
        print("✓ PASS: 'Prospero' is now an alias of 'the Prince Prospero'")
    else:
        print("✗ FAIL: 'Prospero' is NOT an alias of 'the Prince Prospero'")
        success = False

    # Check: the mummer should NO LONGER have "Prospero" as an alias
    if "Prospero" not in mummer_char.aliases:
        print("✓ PASS: 'Prospero' is no longer an alias of 'the mummer'")
    else:
        print("✗ FAIL: 'Prospero' is still an alias of 'the mummer'")
        success = False

    # Check: metadata was updated
    if "post_processing_alias_moves" in fixed_map.pipeline_metadata:
        moves = fixed_map.pipeline_metadata["post_processing_alias_moves"]
        print(f"✓ PASS: Metadata shows {moves} alias move(s)")
    else:
        print("✗ FAIL: No metadata about alias moves")
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓✓✓ ALL CHECKS PASSED ✓✓✓")
    else:
        print("✗✗✗ SOME CHECKS FAILED ✗✗✗")
    print("=" * 60)

    return success


if __name__ == "__main__":
    import sys
    success = test_fix_misplaced_aliases()
    sys.exit(0 if success else 1)
