"""
Tests for character alias merging improvements.

Feature 2: Birth Name / Alias Merging
- Story 1: Birth name patterns are detected and merged
- Story 2: Hyphenation and spacing variants are merged
"""

import pytest
from src.pipeline.character_extraction.consensus import CharacterConsensusBuilder
from src.pipeline.character_extraction.models import (
    CharacterProposal,
    CharacterValidationResult,
    CharacterMention,
    CharacterType,
)


class TestAggressiveAliasPatterns:
    """Test _check_aggressive_alias_patterns() for hyphenation/spacing variants."""

    @pytest.fixture
    def builder(self):
        return CharacterConsensusBuilder(llm_client=None)

    def test_hyphenation_variant_merges(self, builder):
        """'Owl Eyes' and 'Owl-eyes' should merge."""
        is_match, conf = builder._check_aggressive_alias_patterns("Owl Eyes", "Owl-eyes")
        assert is_match, "Hyphenation variants should merge"
        assert conf >= 0.90

    def test_spacing_variant_merges(self, builder):
        """'Mc Donald' and 'McDonald' should merge."""
        is_match, conf = builder._check_aggressive_alias_patterns("Mc Donald", "McDonald")
        assert is_match, "Spacing variants should merge"
        assert conf >= 0.90

    def test_case_insensitive_matching(self, builder):
        """Case should not matter."""
        is_match, conf = builder._check_aggressive_alias_patterns("OWL EYES", "owl-eyes")
        assert is_match, "Case-insensitive matching should work"

    def test_different_names_dont_merge(self, builder):
        """Completely different names should not merge."""
        is_match, _ = builder._check_aggressive_alias_patterns("Tom", "Nick")
        assert not is_match, "Different names should not merge"

    def test_similar_but_different_names(self, builder):
        """Similar but different names should not merge."""
        is_match, _ = builder._check_aggressive_alias_patterns("Tom Buchanan", "Daisy Buchanan")
        assert not is_match, "Different first names should not merge"


class TestBirthNamePattern:
    """Test _check_birth_name_pattern() for birth name/alias detection."""

    @pytest.fixture
    def builder(self):
        return CharacterConsensusBuilder(llm_client=None)

    def _make_validation_result(
        self, name: str, contexts: list[str], chapter: int = 1
    ) -> CharacterValidationResult:
        """Helper to create validation results with contexts."""
        mentions = [
            CharacterMention(
                text=name,
                position=i * 100,
                chapter_index=chapter,
                context=ctx,
                in_dialogue=False,
            )
            for i, ctx in enumerate(contexts)
        ]
        proposal = CharacterProposal(
            strategy="test",
            name=name,
            mentions=mentions,
            confidence=0.9,
            chapter_index=chapter,
        )
        return CharacterValidationResult(
            proposal=proposal,
            is_person_score=0.9,
            context_score=0.9,
            alias_candidates=[],
            overall_score=0.9,
            is_valid=True,
            reasoning="Test validation",
        )

    def test_born_as_pattern(self, builder):
        """Context with 'born as' should trigger merge."""
        name_groups = {
            "Jay Gatsby": [
                self._make_validation_result(
                    "Jay Gatsby",
                    ["He was born as James Gatz in North Dakota."],
                )
            ],
            "James Gatz": [
                self._make_validation_result(
                    "James Gatz",
                    ["James Gatz, that was his real name."],
                )
            ],
        }
        is_match, conf = builder._check_birth_name_pattern(
            "Jay Gatsby", "James Gatz", name_groups
        )
        assert is_match, "Birth name pattern 'born as' should trigger merge"
        assert conf >= 0.80

    def test_real_name_pattern(self, builder):
        """Context with 'real name' should trigger merge."""
        name_groups = {
            "Gatsby": [
                self._make_validation_result(
                    "Gatsby",
                    ["His real name was James Gatz."],
                )
            ],
            "James Gatz": [
                self._make_validation_result(
                    "James Gatz",
                    ["James Gatz had changed his name."],
                )
            ],
        }
        is_match, conf = builder._check_birth_name_pattern(
            "Gatsby", "James Gatz", name_groups
        )
        assert is_match, "Birth name pattern 'real name' should trigger merge"

    def test_changed_name_pattern(self, builder):
        """Context with 'changed his name' should trigger merge."""
        name_groups = {
            "Jay Gatsby": [
                self._make_validation_result(
                    "Jay Gatsby",
                    ["He changed his name from James Gatz at seventeen."],
                )
            ],
            "James Gatz": [
                self._make_validation_result(
                    "James Gatz",
                    ["James Gatz was his original name."],
                )
            ],
        }
        is_match, conf = builder._check_birth_name_pattern(
            "Jay Gatsby", "James Gatz", name_groups
        )
        assert is_match, "Birth name pattern 'changed his name' should trigger merge"

    def test_no_birth_name_pattern_without_indicators(self, builder):
        """Names without birth name indicators should not merge."""
        name_groups = {
            "Tom Buchanan": [
                self._make_validation_result(
                    "Tom Buchanan",
                    ["Tom Buchanan was standing on the porch."],
                )
            ],
            "Daisy Buchanan": [
                self._make_validation_result(
                    "Daisy Buchanan",
                    ["Daisy Buchanan laughed softly."],
                )
            ],
        }
        is_match, _ = builder._check_birth_name_pattern(
            "Tom Buchanan", "Daisy Buchanan", name_groups
        )
        assert not is_match, "Different people should not merge without birth name evidence"


class TestValidateMergeIntegration:
    """Test _validate_merge() integrates the new patterns correctly."""

    @pytest.fixture
    def builder(self):
        return CharacterConsensusBuilder(llm_client=None)

    def _make_validation_result(
        self, name: str, contexts: list[str], chapter: int = 1
    ) -> CharacterValidationResult:
        """Helper to create validation results with contexts."""
        mentions = [
            CharacterMention(
                text=name,
                position=i * 100,
                chapter_index=chapter,
                context=ctx,
                in_dialogue=False,
            )
            for i, ctx in enumerate(contexts)
        ]
        proposal = CharacterProposal(
            strategy="test",
            name=name,
            mentions=mentions,
            confidence=0.9,
            chapter_index=chapter,
        )
        return CharacterValidationResult(
            proposal=proposal,
            is_person_score=0.9,
            context_score=0.9,
            alias_candidates=[],
            overall_score=0.9,
            is_valid=True,
            reasoning="Test validation",
        )

    def test_hyphenation_merges_via_validate(self, builder):
        """Hyphenation variants should merge through _validate_merge."""
        name_groups = {
            "Owl Eyes": [self._make_validation_result("Owl Eyes", ["He was called Owl Eyes."])],
            "Owl-eyes": [self._make_validation_result("Owl-eyes", ["Owl-eyes looked surprised."])],
        }
        is_valid, conf = builder._validate_merge("Owl Eyes", "Owl-eyes", name_groups)
        assert is_valid, "Hyphenation variants should merge"
        assert conf >= 0.90

    def test_birth_name_merges_via_validate(self, builder):
        """Birth name patterns should merge through _validate_merge."""
        name_groups = {
            "Jay Gatsby": [
                self._make_validation_result(
                    "Jay Gatsby",
                    ["His real name was James Gatz, but he changed it."],
                )
            ],
            "James Gatz": [
                self._make_validation_result(
                    "James Gatz",
                    ["James Gatz had been born in North Dakota."],
                )
            ],
        }
        is_valid, conf = builder._validate_merge("Jay Gatsby", "James Gatz", name_groups)
        assert is_valid, "Birth name patterns should merge"
        assert conf >= 0.80

    def test_family_members_dont_merge(self, builder):
        """Different family members should not merge."""
        name_groups = {
            "Tom Buchanan": [
                self._make_validation_result(
                    "Tom Buchanan",
                    ["Tom Buchanan stood on the porch."],
                    chapter=1,
                ),
                self._make_validation_result(
                    "Tom Buchanan",
                    ["Tom was getting impatient."],
                    chapter=2,
                ),
                self._make_validation_result(
                    "Tom Buchanan",
                    ["Tom drove the car."],
                    chapter=3,
                ),
            ],
            "Daisy Buchanan": [
                self._make_validation_result(
                    "Daisy Buchanan",
                    ["Daisy Buchanan laughed."],
                    chapter=1,
                ),
                self._make_validation_result(
                    "Daisy Buchanan",
                    ["Daisy sat on the couch."],
                    chapter=2,
                ),
                self._make_validation_result(
                    "Daisy Buchanan",
                    ["Daisy looked away."],
                    chapter=3,
                ),
            ],
        }
        is_valid, _ = builder._validate_merge("Tom Buchanan", "Daisy Buchanan", name_groups)
        assert not is_valid, "Different family members should not merge"
