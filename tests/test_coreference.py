"""
Tests for coreference resolution proposer (Feature F5).

Verifies that:
1. Coreference proposer gracefully degrades when not available
2. Pronoun patterns are correctly identified
3. Factory function handles missing dependencies
"""

import pytest
from unittest.mock import MagicMock, patch

from src.pipeline.character_extraction.proposers.coref import (
    CoreferenceProposer,
    create_coreference_proposer,
    COREF_AVAILABLE,
    RESOLVABLE_PRONOUNS,
)


class TestCoreferenceAvailability:
    """Test graceful degradation when coreference is not available."""

    def test_is_available_class_method(self):
        """Verify is_available() reports correct status."""
        # This will be False since coreferee is not installed
        result = CoreferenceProposer.is_available()
        assert result == COREF_AVAILABLE

    def test_propose_returns_empty_when_not_available(self):
        """Verify propose() returns empty list when coreference not available."""
        proposer = CoreferenceProposer(nlp=None)
        result = proposer.propose(
            chapter_text="Victor walked into the room. He looked around.",
            chapter_index=1,
            chapter_start_position=0,
        )
        # Should return empty since coreferee is not available
        assert result == []


class TestResolvablePronouns:
    """Test the resolvable pronouns set."""

    def test_personal_pronouns_included(self):
        """Verify personal pronouns are in resolvable set."""
        expected = {'he', 'him', 'she', 'her', 'they', 'them'}
        assert expected.issubset(RESOLVABLE_PRONOUNS)

    def test_possessive_pronouns_included(self):
        """Verify possessive pronouns are in resolvable set."""
        expected = {'his', 'her', 'their', 'theirs'}
        assert expected.issubset(RESOLVABLE_PRONOUNS)

    def test_reflexive_pronouns_included(self):
        """Verify reflexive pronouns are in resolvable set."""
        expected = {'himself', 'herself', 'themselves'}
        assert expected.issubset(RESOLVABLE_PRONOUNS)

    def test_first_person_not_included(self):
        """Verify first-person pronouns are not in resolvable set."""
        # First-person pronouns typically refer to the narrator, not characters
        first_person = {'i', 'me', 'my', 'myself', 'we', 'us', 'our'}
        for pronoun in first_person:
            assert pronoun not in RESOLVABLE_PRONOUNS


class TestCreateCoreferenceProposer:
    """Test the factory function."""

    def test_returns_none_when_not_available(self):
        """Verify factory returns None when coreferee not installed."""
        if not COREF_AVAILABLE:
            result = create_coreference_proposer()
            assert result is None


class TestCoreferenceProposerAttributes:
    """Test CoreferenceProposer attributes."""

    def test_name_attribute(self):
        """Verify proposer has correct name."""
        proposer = CoreferenceProposer(nlp=None)
        assert proposer.name == "coreference"

    def test_default_context_window(self):
        """Verify default context window."""
        proposer = CoreferenceProposer(nlp=None)
        assert proposer.context_window == 100

    def test_custom_context_window(self):
        """Verify custom context window is respected."""
        proposer = CoreferenceProposer(nlp=None, context_window=200)
        assert proposer.context_window == 200


class TestAgentiveContextDetection:
    """Test _is_agentive_context method."""

    @pytest.fixture
    def proposer(self):
        """Create a proposer for testing."""
        return CoreferenceProposer(nlp=None)

    def test_detects_speech_verbs(self, proposer):
        """Verify speech verbs are detected."""
        assert proposer._is_agentive_context("he said quietly")
        assert proposer._is_agentive_context("she asked him")
        assert proposer._is_agentive_context("they replied with anger")

    def test_detects_motion_verbs(self, proposer):
        """Verify motion verbs are detected."""
        assert proposer._is_agentive_context("he walked away")
        assert proposer._is_agentive_context("she ran quickly")
        assert proposer._is_agentive_context("they stood still")

    def test_detects_action_verbs(self, proposer):
        """Verify action verbs are detected."""
        assert proposer._is_agentive_context("he grabbed the rope")
        assert proposer._is_agentive_context("she took the book")
        assert proposer._is_agentive_context("they held hands")

    def test_non_agentive_context(self, proposer):
        """Verify non-agentive context returns False."""
        assert not proposer._is_agentive_context("the house was old")
        assert not proposer._is_agentive_context("it was a beautiful day")


class TestPipelineIntegration:
    """Test pipeline integration with coreference proposer."""

    def test_pipeline_accepts_enable_coreference(self):
        """Verify pipeline accepts enable_coreference parameter."""
        from src.pipeline.character_extraction.pipeline import CharacterExtractionPipeline

        # Should not raise even when coreference is not available
        pipeline = CharacterExtractionPipeline(enable_coreference=True)
        # Coreference proposer should not be added since coreferee is not installed
        proposer_names = [p.name for p in pipeline.proposers]
        if not COREF_AVAILABLE:
            assert "coreference" not in proposer_names


class TestGracefulDegradation:
    """Test that the system works gracefully without coreference."""

    def test_empty_propose_on_error(self):
        """Verify propose returns empty on any error."""
        proposer = CoreferenceProposer(nlp=None)

        # Even with normal text, should return empty since nlp is None
        result = proposer.propose(
            chapter_text="Elizabeth walked into the room. She looked tired.",
            chapter_index=1,
            chapter_start_position=0,
        )
        assert result == []

    def test_propose_does_not_raise(self):
        """Verify propose doesn't raise exceptions."""
        proposer = CoreferenceProposer(nlp=None)

        # Should not raise
        try:
            result = proposer.propose(
                chapter_text="Some text with pronouns. He said something.",
                chapter_index=1,
                chapter_start_position=0,
            )
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"propose() raised an exception: {e}")
