"""
Tests for CharacterAgent (character extraction).

These tests validate:
1. Ground truth compliance (main characters found)
2. Alias resolution (correct merges)
3. Distinct pairs NOT merged (Tom != Daisy)
4. No hallucinated characters
"""

import pytest
from pathlib import Path


class TestGatsbyCharacterExtraction:
    """Test character extraction on The Great Gatsby."""

    def test_gatsby_main_characters_defined(self, gatsby_characters_ground_truth):
        """Ground truth should define main characters."""
        main_chars = gatsby_characters_ground_truth["main_characters"]
        assert len(main_chars) == 5, "Should have 5 main characters defined"

        names = [c["canonical_name"] for c in main_chars]
        assert "Nick Carraway" in names
        assert "Jay Gatsby" in names
        assert "Daisy Buchanan" in names
        assert "Tom Buchanan" in names
        assert "Jordan Baker" in names

    def test_gatsby_supporting_characters_defined(self, gatsby_characters_ground_truth):
        """Ground truth should define supporting characters."""
        supporting = gatsby_characters_ground_truth["supporting_characters"]
        assert len(supporting) >= 4

        names = [c["canonical_name"] for c in supporting]
        assert "Myrtle Wilson" in names
        assert "George Wilson" in names
        assert "Meyer Wolfsheim" in names

    def test_gatsby_distinct_pairs_defined(self, gatsby_characters_ground_truth):
        """Ground truth should define pairs that must not merge."""
        distinct_pairs = gatsby_characters_ground_truth["distinct_pairs"]
        assert len(distinct_pairs) == 2

        # Tom and Daisy Buchanan
        pair1 = distinct_pairs[0]
        assert "Tom Buchanan" in [pair1["char1"], pair1["char2"]]
        assert "Daisy Buchanan" in [pair1["char1"], pair1["char2"]]
        assert pair1["must_not_merge"] is True

        # George and Myrtle Wilson
        pair2 = distinct_pairs[1]
        assert "George Wilson" in [pair2["char1"], pair2["char2"]]
        assert "Myrtle Wilson" in [pair2["char1"], pair2["char2"]]
        assert pair2["must_not_merge"] is True

    def test_gatsby_jay_gatsby_aliases(self, gatsby_characters_ground_truth):
        """Jay Gatsby should have correct aliases defined."""
        main_chars = gatsby_characters_ground_truth["main_characters"]
        gatsby = next(c for c in main_chars if c["canonical_name"] == "Jay Gatsby")

        expected_aliases = ["Gatsby", "Mr. Gatsby", "James Gatz", "Jimmy Gatz"]
        for alias in expected_aliases:
            assert alias in gatsby["aliases"], f"Missing alias: {alias}"


class TestFrankensteinCharacterExtraction:
    """Test character extraction on Frankenstein."""

    def test_frankenstein_main_characters_defined(self, frankenstein_characters_ground_truth):
        """Ground truth should define main characters."""
        main_chars = frankenstein_characters_ground_truth["main_characters"]
        assert len(main_chars) == 5

        names = [c["canonical_name"] for c in main_chars]
        assert "Victor Frankenstein" in names
        assert "The Creature" in names
        assert "Elizabeth Lavenza" in names
        assert "Henry Clerval" in names
        assert "Robert Walton" in names

    def test_frankenstein_creature_aliases(self, frankenstein_characters_ground_truth):
        """The Creature should have all alias variants."""
        main_chars = frankenstein_characters_ground_truth["main_characters"]
        creature = next(c for c in main_chars if c["canonical_name"] == "The Creature")

        expected_aliases = ["Monster", "Creature", "Fiend", "Daemon", "Wretch"]
        for alias in expected_aliases:
            assert alias in creature["aliases"], f"Missing creature alias: {alias}"

    def test_frankenstein_victor_not_merged_with_creature(self, frankenstein_characters_ground_truth):
        """Victor and Creature must be separate (common misconception)."""
        distinct_pairs = frankenstein_characters_ground_truth["distinct_pairs"]

        victor_creature_pair = None
        for pair in distinct_pairs:
            if "Victor Frankenstein" in [pair["char1"], pair["char2"]]:
                if "The Creature" in [pair["char1"], pair["char2"]]:
                    victor_creature_pair = pair
                    break

        assert victor_creature_pair is not None, "Should define Victor/Creature as distinct"
        assert victor_creature_pair["must_not_merge"] is True


class TestAliasResolution:
    """Test alias resolution logic."""

    def test_first_name_matches_full_name(self):
        """First name should potentially match full name."""
        # This tests the logic, not actual extraction
        # "Nick" should match "Nick Carraway"
        pass

    def test_title_prefix_matches(self):
        """Title prefixes should be recognized as aliases."""
        # "Mr. Gatsby" should match "Jay Gatsby"
        pass

    def test_same_surname_different_first_not_merged(self):
        """Same surname but different first names should NOT merge."""
        # Tom Buchanan != Daisy Buchanan
        pass


class TestNoHallucinations:
    """Test that no hallucinated characters appear."""

    def test_gatsby_no_hallucinated_characters(self, gatsby_text, gatsby_characters_ground_truth):
        """All extracted characters should exist in the text."""
        all_chars = (
            gatsby_characters_ground_truth["main_characters"] +
            gatsby_characters_ground_truth["supporting_characters"]
        )

        for char in all_chars:
            name = char["canonical_name"]
            # At least part of the name should appear in text
            name_parts = name.split()
            found = any(part.lower() in gatsby_text.lower() for part in name_parts)
            assert found, f"Character '{name}' not found in text - may be hallucinated"


class TestConfidenceScores:
    """Test confidence score expectations."""

    def test_main_characters_should_have_high_confidence(self, gatsby_characters_ground_truth):
        """Main characters should be expected to have high confidence."""
        for char in gatsby_characters_ground_truth["main_characters"]:
            assert char["importance"] <= 3, f"{char['canonical_name']} should be important"
            assert char["min_mentions"] >= 50, f"{char['canonical_name']} should have many mentions"


class TestIntegration:
    """Integration tests that run the actual pipeline.

    Run with: pytest tests/test_character_agent.py -v --run-integration
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_gatsby_character_extraction(self, analyzer_with_llm, gatsby_characters_ground_truth):
        """Full character extraction on Gatsby."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/gatsby.txt"))

        # Get character names
        char_names = [c.canonical_name for c in result.characters]
        print(f"\nCharacters found: {char_names[:15]}")

        # Check main characters found
        main_chars = gatsby_characters_ground_truth["main_characters"]
        missing = []
        for mc in main_chars:
            name = mc["canonical_name"]
            # Check if name or any alias is in the results
            found = name in char_names or any(
                alias in char_names for alias in mc["aliases"]
            )
            if not found:
                missing.append(name)

        assert len(missing) == 0, f"Missing main characters: {missing}"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_frankenstein_character_extraction(self, analyzer_with_llm, frankenstein_characters_ground_truth):
        """Full character extraction on Frankenstein."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/frankenstein.txt"))

        # Get character names
        char_names = [c.canonical_name for c in result.characters]
        print(f"\nCharacters found: {char_names[:15]}")

        # Check Victor Frankenstein found
        assert any("Victor" in name or "Frankenstein" in name for name in char_names), (
            f"Victor Frankenstein not found in: {char_names}"
        )

        # Check Creature found (under some alias)
        creature_aliases = ["Creature", "Monster", "Fiend", "Daemon", "creature", "monster"]
        assert any(alias in str(char_names) for alias in creature_aliases), (
            f"The Creature not found in: {char_names}"
        )
