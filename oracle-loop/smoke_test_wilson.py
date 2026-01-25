#!/usr/bin/env python3
"""
Smoke test for Wilson merge fix.
Tests that "Wilson" (bare last name) merges with "George Wilson" when "Myrtle Wilson" has "Mrs. Wilson" as alias.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import Character
from src.agents.characters import CharacterAgent

def test_wilson_merge():
    """Test that Wilson merges with George Wilson, not Myrtle Wilson."""

    # Create mock characters
    george = Character(
        id="george",
        canonical_name="George Wilson",
        aliases=["George"],
        role="supporting",
        mention_count=14,
    )

    myrtle = Character(
        id="myrtle",
        canonical_name="Myrtle Wilson",
        aliases=["Myrtle", "Mrs. Wilson"],  # Has Mrs. Wilson as alias
        role="supporting",
        mention_count=24,
    )

    wilson_bare = Character(
        id="wilson",
        canonical_name="Wilson",
        aliases=[],
        role="minor",
        mention_count=65,
    )

    # Create agent
    agent = CharacterAgent()

    # Test the merge logic
    main_cast = [george, myrtle]
    supporting_cast = [wilson_bare]

    main_cast_updated, supporting_updated, _ = agent._merge_lastname_aliases(
        main_cast, supporting_cast
    )

    # Check results
    print("Main cast after merge:")
    for char in main_cast_updated:
        print(f"  {char.canonical_name}: {char.aliases}")

    print(f"\nSupporting cast after merge: {len(supporting_updated)} characters")
    for char in supporting_updated:
        print(f"  {char.canonical_name}: {char.aliases}")

    # Verify expectations
    george_after = next(c for c in main_cast_updated if c.canonical_name == "George Wilson")
    myrtle_after = next(c for c in main_cast_updated if c.canonical_name == "Myrtle Wilson")

    print("\n=== VERIFICATION ===")
    print(f"George Wilson aliases: {george_after.aliases}")
    print(f"Myrtle Wilson aliases: {myrtle_after.aliases}")
    print(f"Supporting cast count: {len(supporting_updated)}")

    # Check if Wilson was added to George's aliases
    if "Wilson" in george_after.aliases:
        print("\n✓ SUCCESS: 'Wilson' merged with 'George Wilson'")
        return True
    else:
        print("\n✗ FAIL: 'Wilson' NOT in George Wilson's aliases")
        if "Wilson" in myrtle_after.aliases:
            print("  (ERROR: 'Wilson' was merged with Myrtle Wilson instead)")
        return False

if __name__ == "__main__":
    success = test_wilson_merge()
    sys.exit(0 if success else 1)
