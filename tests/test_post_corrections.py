"""
Tests for post-processing character corrections.

Tests PipelineCharacterCorrector and OutputCharacterCorrector from
src/pipeline/character_profiling/post_corrections.py.
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock

from src.pipeline.character_profiling.post_corrections import (
    PipelineCharacterCorrector,
    OutputCharacterCorrector,
    RELATIONSHIP_REVERSES,
    FAMILY_TERMS,
    _physical_descriptor_score,
)


# ---------------------------------------------------------------------------
# Mock dataclasses (pipeline Character)
# ---------------------------------------------------------------------------

@dataclass
class MockPipelineCharacter:
    """Mock of pipeline Character (from character_extraction/models.py)."""
    canonical_name: str
    aliases: list = field(default_factory=list)
    is_narrator: bool = False
    appearance: Optional[dict] = None
    personality: Optional[dict] = None
    description: str = ""
    profile_evidence: list = field(default_factory=list)
    relationships: Optional[dict] = None


# ---------------------------------------------------------------------------
# Mock Pydantic-like output Character
# ---------------------------------------------------------------------------

@dataclass
class MockDescription:
    text: str
    source_position: int = 0


@dataclass
class MockOutputCharacter:
    """Mock of output Character (Pydantic, from models.py)."""
    canonical_name: str
    aliases: list = field(default_factory=list)
    is_narrator: bool = False
    appearance: Optional[dict] = None
    descriptions: list = field(default_factory=list)
    relationships: Optional[dict] = None


# ===========================================================================
# PipelineCharacterCorrector tests
# ===========================================================================

class TestInjectNarratorAppearance:
    """Tests for PipelineCharacterCorrector.inject_narrator_appearance."""

    def test_injects_direct_self_description(self):
        """'I am an elderly, grizzled man' -> injected."""
        char = MockPipelineCharacter(
            canonical_name="Montresor",
            is_narrator=True,
            appearance={"summary": "Unknown", "age_indication": "unknown"},
        )
        text = "I am an elderly, grizzled man with a thin frame and bald head."
        corrector = PipelineCharacterCorrector()
        corrector.inject_narrator_appearance([char], text)
        assert "elderly" in char.appearance["summary"].lower()
        assert "grizzled" in char.appearance["summary"].lower()
        assert char.appearance["age_indication"] == "elderly"

    def test_skips_when_appearance_already_set(self):
        char = MockPipelineCharacter(
            canonical_name="Narrator",
            is_narrator=True,
            appearance={"summary": "A tall man with blue eyes", "age_indication": "middle-aged"},
        )
        text = "I am a short fat woman."
        corrector = PipelineCharacterCorrector()
        corrector.inject_narrator_appearance([char], text)
        assert char.appearance["summary"] == "A tall man with blue eyes"

    def test_skips_non_narrators(self):
        char = MockPipelineCharacter(
            canonical_name="Fortunato",
            is_narrator=False,
            appearance={"summary": "Unknown"},
        )
        text = "I am an elderly man."
        corrector = PipelineCharacterCorrector()
        corrector.inject_narrator_appearance([char], text)
        assert char.appearance["summary"] == "Unknown"

    def test_requires_minimum_score_of_2(self):
        """Single physical word should not trigger injection."""
        char = MockPipelineCharacter(
            canonical_name="Narrator",
            is_narrator=True,
            appearance={"summary": "Unknown", "age_indication": "unknown"},
        )
        text = "I am happy today."  # no physical descriptors
        corrector = PipelineCharacterCorrector()
        corrector.inject_narrator_appearance([char], text)
        assert char.appearance["summary"] == "Unknown"

    def test_young_age_detection(self):
        char = MockPipelineCharacter(
            canonical_name="Narrator",
            is_narrator=True,
            appearance={"summary": "Unknown", "age_indication": "unknown"},
        )
        text = "I was a young, thin man in those days."
        corrector = PipelineCharacterCorrector()
        corrector.inject_narrator_appearance([char], text)
        assert char.appearance["age_indication"] == "young"


class TestInferBidirectionalRelationships:
    """Tests for PipelineCharacterCorrector.infer_bidirectional_relationships."""

    def test_father_implies_son(self):
        char_a = MockPipelineCharacter(
            canonical_name="John Sr",
            relationships={"John Jr": "father"},
        )
        char_b = MockPipelineCharacter(
            canonical_name="John Jr",
            relationships={},
        )
        corrector = PipelineCharacterCorrector()
        corrector.infer_bidirectional_relationships([char_a, char_b])
        assert char_b.relationships["John Sr"] == "son"

    def test_does_not_overwrite_correct_existing(self):
        char_a = MockPipelineCharacter(
            canonical_name="John Sr",
            relationships={"John Jr": "father"},
        )
        char_b = MockPipelineCharacter(
            canonical_name="John Jr",
            relationships={"John Sr": "son"},
        )
        corrector = PipelineCharacterCorrector()
        corrector.infer_bidirectional_relationships([char_a, char_b])
        assert char_b.relationships["John Sr"] == "son"

    def test_overrides_unknown(self):
        char_a = MockPipelineCharacter(
            canonical_name="Alice",
            relationships={"Bob": "wife"},
        )
        char_b = MockPipelineCharacter(
            canonical_name="Bob",
            relationships={"Alice": "unknown"},
        )
        corrector = PipelineCharacterCorrector()
        corrector.infer_bidirectional_relationships([char_a, char_b])
        assert char_b.relationships["Alice"] == "husband"

    def test_cousin_is_symmetric(self):
        char_a = MockPipelineCharacter(
            canonical_name="Amy",
            relationships={"Beth": "cousin"},
        )
        char_b = MockPipelineCharacter(
            canonical_name="Beth",
            relationships={},
        )
        corrector = PipelineCharacterCorrector()
        corrector.infer_bidirectional_relationships([char_a, char_b])
        assert char_b.relationships["Amy"] == "cousin"

    def test_matches_within_longer_description(self):
        """'cousin and former associate' should still match 'cousin'."""
        char_a = MockPipelineCharacter(
            canonical_name="A",
            relationships={"B": "cousin and former associate"},
        )
        char_b = MockPipelineCharacter(
            canonical_name="B",
            relationships={},
        )
        corrector = PipelineCharacterCorrector()
        corrector.infer_bidirectional_relationships([char_a, char_b])
        assert char_b.relationships["A"] == "cousin"


class TestFixSameNameContamination:
    """Tests for PipelineCharacterCorrector.fix_same_name_contamination."""

    def test_skips_without_llm(self):
        char = MockPipelineCharacter(
            canonical_name="John",
            personality={"traits": ["brave"]},
        )
        corrector = PipelineCharacterCorrector(llm_client=None, evidence_store={})
        corrector.fix_same_name_contamination([char])
        assert char.personality["traits"] == ["brave"]

    def test_applies_llm_correction(self):
        char_short = MockPipelineCharacter(
            canonical_name="John",
            personality={"traits": ["brave", "old"], "summary": "An old warrior"},
            appearance={"age_indication": "elderly", "summary": "An old man"},
            description="John is an old warrior who died in battle.",
        )
        char_long = MockPipelineCharacter(
            canonical_name="John Donaldson",
            personality={"traits": ["cowardly", "young"], "summary": "A young farmer"},
        )

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"contamination_detected": true, "reason": "Old warrior traits belong to John Donaldson", "corrected_personality": {"summary": "A simple man", "traits": ["brave"], "temperament": "calm", "emotional_range": "limited"}, "corrected_age_indication": "unknown", "corrected_description": "John is a simple man.", "corrected_appearance_summary": "A man of average build"}'
        mock_llm.query.return_value = mock_response

        corrector = PipelineCharacterCorrector(llm_client=mock_llm, evidence_store={"John": MagicMock(evidence=[]), "John Donaldson": MagicMock(evidence=[])})
        corrector.fix_same_name_contamination([char_short, char_long])

        assert char_short.personality["traits"] == ["brave"]
        assert char_short.appearance["age_indication"] == "unknown"
        assert char_short.description == "John is a simple man."
        assert char_short.appearance["summary"] == "A man of average build"

    def test_no_contamination_detected(self):
        char_short = MockPipelineCharacter(
            canonical_name="John",
            personality={"traits": ["brave"], "summary": "Brave man"},
        )
        char_long = MockPipelineCharacter(
            canonical_name="John Donaldson",
            personality={"traits": ["cowardly"], "summary": "Coward"},
        )

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"contamination_detected": false, "reason": "No overlap"}'
        mock_llm.query.return_value = mock_response

        corrector = PipelineCharacterCorrector(llm_client=mock_llm, evidence_store={"John": MagicMock(evidence=[]), "John Donaldson": MagicMock(evidence=[])})
        corrector.fix_same_name_contamination([char_short, char_long])

        assert char_short.personality["traits"] == ["brave"]


class TestRemoveUnsupportedDeathClaims:
    """Tests for PipelineCharacterCorrector.remove_unsupported_death_claims."""

    def test_removes_unsupported_death(self):
        char = MockPipelineCharacter(
            canonical_name="Fortunato",
            description="A jester who united people in death.",
            profile_evidence=[{"quote": "He wore a cap and bells."}],
        )
        corrector = PipelineCharacterCorrector()
        corrector.remove_unsupported_death_claims([char])
        assert "in death" not in char.description

    def test_keeps_supported_death(self):
        char = MockPipelineCharacter(
            canonical_name="Fortunato",
            description="A jester who united people in death.",
            profile_evidence=[{"quote": "He died behind the wall."}],
        )
        corrector = PipelineCharacterCorrector()
        corrector.remove_unsupported_death_claims([char])
        assert "in death" in char.description

    def test_no_death_phrase_unchanged(self):
        char = MockPipelineCharacter(
            canonical_name="Alice",
            description="A curious girl.",
            profile_evidence=[],
        )
        corrector = PipelineCharacterCorrector()
        corrector.remove_unsupported_death_claims([char])
        assert char.description == "A curious girl."


class TestCorrectDescriptionRelationships:
    """Tests for PipelineCharacterCorrector.correct_description_relationships."""

    def test_corrects_possessive_family_term(self):
        char = MockPipelineCharacter(
            canonical_name="Fortunato",
            description="Fortunato's brother's legacy lives on.",
            aliases=["Fortunato"],
        )
        # Text uses "cousin" near Fortunato, not "brother"
        text = "Fortunato was his cousin and they drank wine together. Fortunato laughed."
        corrector = PipelineCharacterCorrector()
        corrector.correct_description_relationships([char], text)
        assert "cousin's" in char.description.lower()
        assert "brother's" not in char.description.lower()

    def test_non_possessive_not_corrected(self):
        char = MockPipelineCharacter(
            canonical_name="Alice",
            description="Alice saw her brother in the garden.",
            aliases=[],
        )
        text = "Alice met her cousin at the party. Alice waved."
        corrector = PipelineCharacterCorrector()
        corrector.correct_description_relationships([char], text)
        # "brother" is NOT in possessive form, so should not be corrected
        assert "brother" in char.description


# ===========================================================================
# OutputCharacterCorrector tests
# ===========================================================================

class TestInjectNarratorAppearanceFinal:
    """Tests for OutputCharacterCorrector.inject_narrator_appearance_final."""

    def test_injects_for_narrator(self):
        char = MockOutputCharacter(
            canonical_name="Montresor",
            is_narrator=True,
            appearance={"summary": "Unknown", "age_indication": "unknown"},
        )
        text = "I was an elderly, grizzled man with a lean frame."
        corrector = OutputCharacterCorrector()
        corrector.inject_narrator_appearance_final([char], text)
        assert "elderly" in char.appearance["summary"].lower()

    def test_no_injection_without_description(self):
        char = MockOutputCharacter(
            canonical_name="Montresor",
            is_narrator=True,
            appearance={"summary": "Unknown"},
        )
        text = "The weather was fine that day."
        corrector = OutputCharacterCorrector()
        corrector.inject_narrator_appearance_final([char], text)
        assert char.appearance["summary"] == "Unknown"


class TestExtractDeterministicAge:
    """Tests for OutputCharacterCorrector.extract_deterministic_age."""

    def test_extracts_numeric_age(self):
        char = MockOutputCharacter(
            canonical_name="Alice",
            appearance={"age_indication": "unknown"},
        )
        text = "Alice was 22 years old when she arrived."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert "22" in char.appearance["age_indication"]

    def test_extracts_written_age(self):
        char = MockOutputCharacter(
            canonical_name="Bob",
            appearance={"age_indication": "unknown"},
        )
        text = "Bob was twenty-two years old at the time."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert "twenty-two" in char.appearance["age_indication"].lower()

    def test_skips_already_known_age(self):
        char = MockOutputCharacter(
            canonical_name="Alice",
            appearance={"age_indication": "elderly"},
        )
        text = "Alice was 22 years old when she arrived."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert char.appearance["age_indication"] == "elderly"

    def test_uses_alias_for_matching(self):
        char = MockOutputCharacter(
            canonical_name="Elizabeth Bennet",
            aliases=["Lizzy"],
            appearance={"age_indication": "unknown"},
        )
        text = "Lizzy was aged 20 at the start of the season."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert "20" in char.appearance["age_indication"]


class TestFixSamePersonRelationships:
    """Tests for OutputCharacterCorrector.fix_same_person_relationships."""

    def test_clears_same_person_relationship(self):
        char_a = MockOutputCharacter(
            canonical_name="John",
            relationships={"John Donaldson": "same person as John Donaldson"},
        )
        char_b = MockOutputCharacter(
            canonical_name="John Donaldson",
            relationships={},
        )
        corrector = OutputCharacterCorrector()
        corrector.fix_same_person_relationships([char_a, char_b])
        assert char_a.relationships["John Donaldson"] == "unknown"

    def test_keeps_non_same_person(self):
        char_a = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Bob": "husband"},
        )
        char_b = MockOutputCharacter(
            canonical_name="Bob",
            relationships={},
        )
        corrector = OutputCharacterCorrector()
        corrector.fix_same_person_relationships([char_a, char_b])
        assert char_a.relationships["Bob"] == "husband"

    def test_matches_alias(self):
        char_a = MockOutputCharacter(
            canonical_name="John",
            relationships={"JD": "the same as JD"},
        )
        char_b = MockOutputCharacter(
            canonical_name="John Donaldson",
            aliases=["JD"],
            relationships={},
        )
        corrector = OutputCharacterCorrector()
        corrector.fix_same_person_relationships([char_a, char_b])
        assert char_a.relationships["JD"] == "unknown"


class TestVerifyRelationshipsFromText:
    """Tests for OutputCharacterCorrector.verify_relationships_from_text."""

    def test_text_overrides_llm_relationship(self):
        char_a = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Bob": "brother"},
        )
        char_b = MockOutputCharacter(
            canonical_name="Bob",
            relationships={},
        )
        # Text explicitly says "cousin" when both co-appear
        text = "Alice met her cousin Bob at the fountain. Alice and Bob talked."
        corrector = OutputCharacterCorrector()
        corrector.verify_relationships_from_text([char_a, char_b], text)
        assert char_a.relationships["Bob"] == "cousin"

    def test_downgrades_hallucinated_family_rel(self):
        char_a = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Bob": "sister"},
        )
        char_b = MockOutputCharacter(
            canonical_name="Bob",
            relationships={},
        )
        # Characters never co-appear in text (must be >500 chars apart)
        padding = "The wind blew through the trees. " * 30
        text = "Alice was in the garden. " + padding + "Bob was at the market far away."
        corrector = OutputCharacterCorrector()
        corrector.verify_relationships_from_text([char_a, char_b], text)
        assert char_a.relationships["Bob"] == "acquaintance"


class TestEnforceGenderConsistency:
    """Tests for OutputCharacterCorrector.enforce_gender_consistency."""

    def test_male_cannot_be_mother(self):
        char = MockOutputCharacter(
            canonical_name="John",
            descriptions=[MockDescription("He is a gentleman of great stature.")],
            relationships={"Alice": "mother"},
        )
        corrector = OutputCharacterCorrector()
        corrector.enforce_gender_consistency([char])
        # Male character with "mother" label → corrected to gender-appropriate "father"
        assert char.relationships["Alice"] == "father"

    def test_female_cannot_be_father(self):
        char = MockOutputCharacter(
            canonical_name="Mary",
            descriptions=[MockDescription("She is a lady of distinction.")],
            relationships={"Tom": "father"},
        )
        corrector = OutputCharacterCorrector()
        corrector.enforce_gender_consistency([char])
        # Female character with "father" label → corrected to gender-appropriate "mother"
        assert char.relationships["Tom"] == "mother"

    def test_correct_gender_unchanged(self):
        char = MockOutputCharacter(
            canonical_name="John",
            descriptions=[MockDescription("He is a gentleman.")],
            relationships={"Alice": "father"},
        )
        corrector = OutputCharacterCorrector()
        corrector.enforce_gender_consistency([char])
        assert char.relationships["Alice"] == "father"

    def test_ambiguous_gender_unchanged(self):
        """When gender is not determinable, don't correct."""
        char = MockOutputCharacter(
            canonical_name="Pat",
            descriptions=[MockDescription("A quiet, thoughtful individual.")],
            relationships={"Alice": "mother"},
        )
        corrector = OutputCharacterCorrector()
        corrector.enforce_gender_consistency([char])
        assert char.relationships["Alice"] == "mother"


# ===========================================================================
# Shared helper tests
# ===========================================================================

class TestPhysicalDescriptorScore:
    def test_multiple_descriptors(self):
        assert _physical_descriptor_score("an elderly, grizzled man") >= 3

    def test_no_descriptors(self):
        assert _physical_descriptor_score("a happy person walking") == 1  # "person" counts

    def test_empty_string(self):
        assert _physical_descriptor_score("") == 0


class TestCleanOrphanedRelationships:
    """Tests for OutputCharacterCorrector.clean_orphaned_relationships."""

    def test_removes_relationship_to_missing_character(self):
        char = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Jesus": "unknown", "Bob": "friend"},
        )
        bob = MockOutputCharacter(canonical_name="Bob", relationships={})
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char, bob])
        assert "Jesus" not in char.relationships
        assert "Bob" in char.relationships

    def test_keeps_relationships_to_existing_chars(self):
        char_a = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Bob": "husband"},
        )
        char_b = MockOutputCharacter(canonical_name="Bob", relationships={})
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char_a, char_b])
        assert char_a.relationships["Bob"] == "husband"

    def test_matches_by_alias(self):
        char_a = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"Robbie": "friend"},
        )
        char_b = MockOutputCharacter(
            canonical_name="Robert",
            aliases=["Robbie"],
            relationships={},
        )
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char_a, char_b])
        # "Robbie" is an alias of Robert, so relationship should be kept
        assert "Robbie" in char_a.relationships

    def test_case_insensitive_matching(self):
        char = MockOutputCharacter(
            canonical_name="Alice",
            relationships={"bob": "friend"},
        )
        bob = MockOutputCharacter(canonical_name="Bob", relationships={})
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char, bob])
        # "bob" (lowercase) matches "Bob" (canonical)
        assert "bob" in char.relationships

    def test_empty_relationships_unchanged(self):
        char = MockOutputCharacter(canonical_name="Alice", relationships={})
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char])
        assert char.relationships == {}

    def test_none_relationships_unchanged(self):
        char = MockOutputCharacter(canonical_name="Alice", relationships=None)
        corrector = OutputCharacterCorrector()
        corrector.clean_orphaned_relationships([char])  # Should not raise
        assert char.relationships is None


class TestExtractDeterministicAgeValidation:
    """Tests for the age validation in OutputCharacterCorrector.extract_deterministic_age."""

    def test_rejects_count_word_as_age(self):
        """'five years' (from 'five survivors') should be reset, then real age extracted."""
        char = MockOutputCharacter(
            canonical_name="Benny",
            appearance={"age_indication": "five years"},
        )
        # No real age in the text — should reset to unknown but not find anything
        text = "There were five survivors. Benny was tall and muscular."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert char.appearance["age_indication"] == "unknown"

    def test_rejects_count_word_when_no_real_age_in_text(self):
        """'five years' (from 'five survivors') should reset to unknown when text has no real age."""
        char = MockOutputCharacter(
            canonical_name="Ted",
            appearance={"age_indication": "nine years"},
        )
        # Text has character name but no age-like phrase nearby
        text = "Ted shouted into the void. There was no answer. Ted fell silent."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        # "nine years" invalid → reset. No real age found in text → stays "unknown"
        assert char.appearance["age_indication"] == "unknown"

    def test_replaces_invalid_age_with_text_age(self):
        """After resetting invalid age, real age from text is extracted."""
        char = MockOutputCharacter(
            canonical_name="Ellen",
            appearance={"age_indication": "five years"},
        )
        text = "Ellen was 28 years old before the war."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert "28" in char.appearance["age_indication"]

    def test_keeps_valid_category_age(self):
        """'elderly', 'young', etc. are valid and should not be reset."""
        for valid_age in ("elderly", "young", "middle-aged", "adult"):
            char = MockOutputCharacter(
                canonical_name="Char",
                appearance={"age_indication": valid_age},
            )
            text = "Char was five years a servant."
            corrector = OutputCharacterCorrector()
            corrector.extract_deterministic_age([char], text)
            assert char.appearance["age_indication"] == valid_age

    def test_keeps_valid_numeric_age(self):
        """'22 years old' is a valid age and should not be reset."""
        char = MockOutputCharacter(
            canonical_name="Alice",
            appearance={"age_indication": "22 years old"},
        )
        text = "Alice was five years married."
        corrector = OutputCharacterCorrector()
        corrector.extract_deterministic_age([char], text)
        assert char.appearance["age_indication"] == "22 years old"


class TestRunAllOrdering:
    """Integration tests for run_all methods."""

    def test_pipeline_corrector_run_all(self):
        """Verify run_all executes without error on simple data."""
        narrator = MockPipelineCharacter(
            canonical_name="Narrator",
            is_narrator=True,
            appearance={"summary": "Unknown", "age_indication": "unknown"},
            personality={"traits": ["observant"], "summary": "An observer"},
            description="The narrator tells the story.",
            relationships={"Friend": "cousin"},
        )
        friend = MockPipelineCharacter(
            canonical_name="Friend",
            relationships={},
        )
        corrector = PipelineCharacterCorrector()
        corrector.run_all([narrator, friend], "I was an elderly, grizzled man. The narrator met his cousin Friend nearby.")
        # Just verify no exceptions and bidirectional rel was created
        assert friend.relationships.get("Narrator") == "cousin"

    def test_output_corrector_run_all(self):
        """Verify run_all executes without error on simple data."""
        char = MockOutputCharacter(
            canonical_name="Alice",
            appearance={"age_indication": "unknown"},
            descriptions=[MockDescription("She is a lady.")],
            relationships={"Bob": "friend"},
        )
        bob = MockOutputCharacter(
            canonical_name="Bob",
            descriptions=[],
            relationships={},
        )
        corrector = OutputCharacterCorrector()
        corrector.run_all([char, bob], "Alice was 30 years old. Bob knew Alice well.")
        assert "30" in char.appearance["age_indication"]
