#!/usr/bin/env python3
"""
Smoke test for death-based character splitting.

Tests the _split_on_death_evidence function with the Masque of the Red Death scenario.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.characters import CharacterAgent
from src.pipeline.character_extraction.models import CharacterMap, Character, CharacterMention, CharacterType


def create_test_character():
    """Create a test character with Prince Prospero and the mummer merged."""
    # Create mentions for "Prince Prospero"
    prospero_mentions = [
        CharacterMention(
            text="Prince Prospero",
            position=100,
            chapter_index=1,
            context="Prince Prospero was happy and dauntless and sagacious",
            in_dialogue=False,
        ),
        CharacterMention(
            text="the prince",
            position=500,
            chapter_index=1,
            context="the prince had provided all the appliances of pleasure",
            in_dialogue=False,
        ),
    ]

    # Create mentions for "the mummer" with death context
    mummer_mentions = [
        CharacterMention(
            text="the mummer",
            position=2000,
            chapter_index=1,
            context="seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock",
            in_dialogue=False,
        ),
        CharacterMention(
            text="the figure",
            position=2100,
            chapter_index=1,
            context="And now was acknowledged the presence of the Red Death. He had come like a thief in the night",
            in_dialogue=False,
        ),
    ]

    # Add CRITICAL death context
    death_mention = CharacterMention(
        text="Prince Prospero",
        position=1900,
        chapter_index=1,
        context="the Prince Prospero, maddening with rage and the shame of his own momentary cowardice, rushed hurriedly through the six chambers, while none followed him on account of a deadly terror that had seized upon all. He bore aloft a drawn dagger, and had approached, in rapid impetuosity, to within three or four feet of the retreating figure, when the latter, having attained the extremity of the velvet apartment, turned suddenly and confronted his pursuer. There was a sharp cry—and the dagger dropped gleaming upon the sable carpet, upon which, instantly afterwards, fell prostrate in death the Prince Prospero. Then, summoning the wild courage of despair, a throng of the revellers at once threw themselves into the black apartment, and, seizing the mummer whose tall figure stood erect and motionless within the shadow of the ebony clock, gasped in unutterable horror at finding the grave-cerements and corpse-like mask which they handled with so violent a rudeness, untenanted by any tangible form",
        in_dialogue=False,
    )

    all_mentions = prospero_mentions + mummer_mentions + [death_mention]

    char = Character(
        id="char-1",
        canonical_name="Prince Prospero",
        aliases=["the prince", "the mummer", "the figure"],
        mentions=all_mentions,
        first_appearance_chapter=1,
        mention_count=len(all_mentions),
        chapters_present=[1],
        confidence=0.85,
        supporting_strategies=["ner", "llm"],
        character_type=CharacterType.STORY,
    )

    return char


def test_split_on_death_evidence():
    """Test that the split function correctly identifies and splits merged characters."""
    print("Testing death-based character splitting...")
    print("=" * 70)

    # Create test data
    test_char = create_test_character()
    character_map = CharacterMap(
        characters=[test_char],
        low_confidence_characters=[],
        total_mentions=test_char.mention_count,
        total_chapters=1,
        pipeline_metadata={},
    )

    print(f"\nBEFORE SPLIT:")
    print(f"  Number of characters: {len(character_map.characters)}")
    print(f"  Character 1: {character_map.characters[0].canonical_name}")
    print(f"    Aliases: {', '.join(character_map.characters[0].aliases)}")
    print(f"    Mention count: {character_map.characters[0].mention_count}")

    # Create agent and run split
    agent = CharacterAgent()
    result_map = agent._split_on_death_evidence(character_map)

    print(f"\nAFTER SPLIT:")
    print(f"  Number of characters: {len(result_map.characters)}")
    for i, char in enumerate(result_map.characters, 1):
        print(f"  Character {i}: {char.canonical_name}")
        print(f"    Aliases: {', '.join(char.aliases) if char.aliases else 'none'}")
        print(f"    Mention count: {char.mention_count}")

    # Verify results
    print(f"\n{'='*70}")
    if len(result_map.characters) == 2:
        print("✓ SUCCESS: Characters were split into 2 separate entries")

        # Check that we have both Prince Prospero and the mummer/figure
        names = {c.canonical_name.lower() for c in result_map.characters}
        has_prospero = any("prospero" in name for name in names)
        has_mummer = any("mummer" in name or "figure" in name for name in names)

        if has_prospero and has_mummer:
            print("✓ SUCCESS: Both 'Prince Prospero' and 'the mummer/figure' are present")
            return True
        else:
            print(f"✗ FAIL: Missing expected characters. Found: {names}")
            return False
    elif len(result_map.characters) == 1:
        print("✗ FAIL: Characters were NOT split (still 1 character)")
        print(f"  This means death evidence was not detected")
        return False
    else:
        print(f"? UNEXPECTED: Got {len(result_map.characters)} characters")
        return False


if __name__ == "__main__":
    success = test_split_on_death_evidence()
    sys.exit(0 if success else 1)
