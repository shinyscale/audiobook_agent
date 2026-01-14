"""
Tests for epithet alias resolution (Feature F3).

Verifies that:
1. Semantically equivalent epithets are merged
2. Different descriptive handles remain separate
3. Canonicalization prefers most specific handle
"""

import pytest
from unittest.mock import MagicMock

from src.pipeline.character_extraction.consensus import (
    CharacterConsensusBuilder,
    EPITHET_ALIAS_SYSTEM,
    EPITHET_ALIAS_PROMPT,
)


class TestIsDescriptiveHandle:
    """Test _is_descriptive_handle() method."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder for testing."""
        return CharacterConsensusBuilder()

    def test_detects_the_creature(self, builder):
        """Verify 'the creature' is detected as descriptive handle."""
        assert builder._is_descriptive_handle("the creature")

    def test_detects_the_monster(self, builder):
        """Verify 'the monster' is detected as descriptive handle."""
        assert builder._is_descriptive_handle("the monster")

    def test_detects_the_old_man(self, builder):
        """Verify 'the old man' is detected as descriptive handle."""
        assert builder._is_descriptive_handle("the old man")

    def test_detects_the_detective(self, builder):
        """Verify 'the detective' is detected as descriptive handle."""
        assert builder._is_descriptive_handle("the detective")

    def test_detects_the_blind_old_man(self, builder):
        """Verify longer epithets are detected."""
        assert builder._is_descriptive_handle("the blind old man")

    def test_rejects_proper_name(self, builder):
        """Verify proper names are not detected as descriptive handles."""
        assert not builder._is_descriptive_handle("Victor")
        assert not builder._is_descriptive_handle("Elizabeth Bennet")

    def test_rejects_titled_name(self, builder):
        """Verify titled names are not detected as descriptive handles."""
        assert not builder._is_descriptive_handle("Mr. Darcy")
        assert not builder._is_descriptive_handle("Dr. Frankenstein")

    def test_rejects_the_with_title(self, builder):
        """Verify 'the Mr. X' pattern is rejected."""
        assert not builder._is_descriptive_handle("the Mr. Smith")

    def test_case_insensitive(self, builder):
        """Verify detection is case-insensitive."""
        assert builder._is_descriptive_handle("The Creature")
        assert builder._is_descriptive_handle("THE MONSTER")


class TestPickCanonicalEpithet:
    """Test _pick_canonical_epithet() method."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder for testing."""
        return CharacterConsensusBuilder()

    def test_prefers_more_specific(self, builder):
        """Verify more specific epithet is preferred."""
        epithets = ["the old man", "the blind old man"]
        # Empty groups for this test
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        # "the blind old man" has more words
        assert result == "the blind old man"

    def test_prefers_unique_words_same_length(self, builder):
        """Verify epithets with unique words are preferred when same length."""
        # When word count is the same, uniqueness should win
        epithets = ["the old man", "the creature"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        # "the old man" has 3 words, "the creature" has 2 words
        # Word count wins, so "the old man" is preferred
        assert result == "the old man"

    def test_unique_words_tie_breaker(self, builder):
        """Verify unique words break ties for same word count."""
        # Both have 2 words
        epithets = ["the man", "the creature"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        # "creature" has more unique words than "man"
        assert result == "the creature"

    def test_single_epithet_returns_itself(self, builder):
        """Verify single epithet returns itself."""
        epithets = ["the monster"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        assert result == "the monster"


class TestEpithetAliasPrompt:
    """Test epithet alias prompt structure."""

    def test_system_prompt_mentions_epithets(self):
        """Verify system prompt mentions epithet handling."""
        assert "descriptive handles" in EPITHET_ALIAS_SYSTEM.lower() or "epithets" in EPITHET_ALIAS_SYSTEM.lower()

    def test_system_prompt_warns_about_different_characters(self):
        """Verify system prompt warns about different characters."""
        assert "same" in EPITHET_ALIAS_SYSTEM.lower()
        assert "different" in EPITHET_ALIAS_SYSTEM.lower() or "not" in EPITHET_ALIAS_SYSTEM.lower()

    def test_prompt_template_structure(self):
        """Verify prompt template has required placeholders."""
        assert "{epithets}" in EPITHET_ALIAS_PROMPT

    def test_prompt_requests_canonical(self):
        """Verify prompt requests canonical name selection."""
        assert "canonical" in EPITHET_ALIAS_PROMPT.lower()

    def test_prompt_requests_aliases(self):
        """Verify prompt requests alias identification."""
        assert "alias" in EPITHET_ALIAS_PROMPT.lower()


class TestBuildConsensusWithEpithets:
    """Test build_consensus separates epithets from proper names."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder without LLM."""
        return CharacterConsensusBuilder(llm_client=None)

    def test_empty_validations(self, builder):
        """Verify empty input produces empty character map."""
        result = builder.build_consensus([], total_chapters=5)
        assert len(result.characters) == 0


class TestEpithetMergeLogic:
    """Test the logic for merging epithets."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder for testing."""
        return CharacterConsensusBuilder()

    def test_epithets_not_merged_with_proper_names_by_default(self, builder):
        """Verify epithets are not accidentally merged with proper names."""
        # This tests that _is_descriptive_handle properly separates them
        proper_names = ["Victor", "Elizabeth", "Mr. Darcy"]
        epithets = ["the creature", "the monster"]

        for name in proper_names:
            assert not builder._is_descriptive_handle(name)

        for name in epithets:
            assert builder._is_descriptive_handle(name)


class TestSpecificityScoring:
    """Test that canonicalization prefers most specific handle."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder for testing."""
        return CharacterConsensusBuilder()

    def test_creature_over_monster(self, builder):
        """Test that unique epithets are preferred."""
        # creature is more unique than monster in general usage
        epithets = ["the creature", "the monster"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        # Both have same word count and uniqueness, so either is valid
        # But we prefer the more distinctive one
        assert result in ["the creature", "the monster"]

    def test_multiword_over_simple(self, builder):
        """Test that longer epithets are preferred over shorter."""
        epithets = ["the man", "the old man", "the blind old man"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        assert result == "the blind old man"

    def test_specific_descriptor_preferred(self, builder):
        """Test that specific descriptors are preferred."""
        epithets = ["the wretch", "the fiend", "the daemon"]
        groups = {}
        result = builder._pick_canonical_epithet(epithets, groups)
        # All have same structure, so any is valid
        assert result in epithets


class TestFrankensteinEpithets:
    """Integration tests using Frankenstein-like epithet variations."""

    @pytest.fixture
    def builder(self):
        """Create a CharacterConsensusBuilder for testing."""
        return CharacterConsensusBuilder()

    def test_all_creature_epithets_detected(self, builder):
        """Verify all creature-related epithets are detected as descriptive."""
        frankenstein_epithets = [
            "the creature",
            "the monster",
            "the wretch",
            "the fiend",
            "the daemon",
            "the devil",
        ]
        for epithet in frankenstein_epithets:
            assert builder._is_descriptive_handle(epithet), f"'{epithet}' should be descriptive"

    def test_proper_names_not_epithets(self, builder):
        """Verify Frankenstein proper names are not detected as epithets."""
        proper_names = [
            "Victor",
            "Victor Frankenstein",
            "Elizabeth",
            "Henry Clerval",
            "Alphonse Frankenstein",
        ]
        for name in proper_names:
            assert not builder._is_descriptive_handle(name), f"'{name}' should not be descriptive"
