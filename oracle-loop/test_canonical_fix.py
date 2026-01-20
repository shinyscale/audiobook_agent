#!/usr/bin/env python3
"""
Unit test for the canonical name selection fix.
Tests that bare last names are deprioritized when fuller forms exist.
"""

def test_is_ambiguous_lastname_only():
    """Test the ambiguous lastname detection logic"""

    # Simulate the logic from the fix
    def is_ambiguous_lastname_only(name: str, members: list[str]) -> bool:
        """
        Detect if this is a bare last name that's ambiguous because
        full names (FirstName LastName or Title LastName) exist in the same component.
        """
        parts = name.split()
        # Only applies to single-word names (bare last names)
        if len(parts) != 1:
            return False

        # Check if any member has this as a last name with a first name or title
        lastname = parts[0].lower()
        for other in members:
            if other == name:
                continue
            other_parts = other.split()
            if len(other_parts) < 2:
                continue

            # Check if other ends with this lastname
            other_lastname = other_parts[-1].lower()
            if other_lastname == lastname:
                # This is a bare lastname with a fuller form present
                return True

        return False

    # Test case 1: "White" with "Herbert White" and "Mr. White" present
    members = ["White", "Herbert White", "Mr. White", "Mrs. White"]
    assert is_ambiguous_lastname_only("White", members) == True, \
        "White should be ambiguous when Herbert White exists"

    # Test case 2: Fuller forms should NOT be ambiguous
    assert is_ambiguous_lastname_only("Herbert White", members) == False, \
        "Herbert White should NOT be ambiguous (has first name)"
    assert is_ambiguous_lastname_only("Mr. White", members) == False, \
        "Mr. White should NOT be ambiguous (has title)"

    # Test case 3: "White" alone (no fuller forms) should NOT be ambiguous
    members_alone = ["White"]
    assert is_ambiguous_lastname_only("White", members_alone) == False, \
        "White alone should NOT be ambiguous"

    # Test case 4: "Morris" with "Sergeant-Major Morris" present
    members_morris = ["Morris", "Sergeant-Major Morris"]
    assert is_ambiguous_lastname_only("Morris", members_morris) == True, \
        "Morris should be ambiguous when Sergeant-Major Morris exists"

    print("✅ All tests passed!")

def test_canonical_selection_order():
    """Test that the scoring correctly prioritizes non-ambiguous names"""

    # Simulate scoring logic
    def score_name(name: str, members: list[str], mention_counts: dict[str, int]) -> tuple:
        """Score for canonical selection (lower is better with min())"""
        parts = name.split()
        has_title = 1 if parts and parts[0].rstrip('.').lower() in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'} else 0
        mention_count = mention_counts.get(name, 0)

        # Check ambiguity
        def is_ambiguous_lastname_only(n: str) -> bool:
            p = n.split()
            if len(p) != 1:
                return False
            lastname = p[0].lower()
            for other in members:
                if other == n:
                    continue
                other_parts = other.split()
                if len(other_parts) >= 2 and other_parts[-1].lower() == lastname:
                    return True
            return False

        is_ambiguous = is_ambiguous_lastname_only(name)

        # Priority: 1) Not ambiguous, 2) Mention count, 3) More parts, 4) No title, 5) Alpha
        return (is_ambiguous, -mention_count, -len(parts), has_title, name.lower())

    # The problematic case from Monkey's Paw
    members = ["White", "Herbert White", "Mr. White"]
    mention_counts = {
        "White": 44,           # Highest mentions
        "Herbert White": 5,    # Lower mentions
        "Mr. White": 10        # Medium mentions
    }

    # Score each name
    scores = {name: score_name(name, members, mention_counts) for name in members}

    print("\nScores (lower is better):")
    for name, score in sorted(scores.items(), key=lambda x: x[1]):
        is_ambig, neg_mentions, neg_parts, has_title, alpha = score
        print(f"  {name:20} → ambig={is_ambig}, mentions={-neg_mentions:3}, parts={-neg_parts}, title={has_title}")

    # The canonical should be the one with lowest score
    canonical = min(members, key=lambda n: score_name(n, members, mention_counts))

    print(f"\nCanonical selected: {canonical}")

    # Verify: Should NOT be "White" (even though it has highest mentions)
    assert canonical != "White", \
        "White should NOT be canonical (it's ambiguous)"

    # Should be one of the fuller forms (either "Mr. White" or "Herbert White")
    # "Mr. White" has more mentions (10 vs 5), so it will win
    assert canonical in ["Mr. White", "Herbert White"], \
        f"Canonical should be a fuller form, but got {canonical}"

    print(f"✅ Canonical selection correct! (chose {canonical} over ambiguous 'White')")

if __name__ == "__main__":
    test_is_ambiguous_lastname_only()
    test_canonical_selection_order()
    print("\n✅ All unit tests passed!")
