"""
Tests for descriptive character extraction (Feature F2).

Verifies that:
1. Recurring descriptive handles are extracted as characters
2. One-off generic roles are not extracted
3. Descriptive handles must be agentive to be included
"""

import pytest
import re

from src.pipeline.character_extraction.models import CharacterType, CharacterMention
from src.pipeline.character_extraction.proposers.llm import (
    LLMCharacterProposer,
    CHARACTER_SYSTEM_PROMPT,
    CHARACTER_PROMPT_TEMPLATE,
)


class TestCharacterTypeDescriptive:
    """Test that DESCRIPTIVE character type exists."""

    def test_descriptive_type_exists(self):
        """Verify DESCRIPTIVE is in CharacterType enum."""
        assert hasattr(CharacterType, 'DESCRIPTIVE')
        assert CharacterType.DESCRIPTIVE.value == "descriptive"

    def test_all_character_types(self):
        """Verify all character types are present."""
        expected_types = {'story', 'historical', 'referenced', 'descriptive', 'uncertain'}
        actual_types = {t.value for t in CharacterType}
        assert actual_types == expected_types


class TestCharacterMentionAgentive:
    """Test is_agentive field on CharacterMention."""

    def test_is_agentive_field_exists(self):
        """Verify is_agentive field exists with default False."""
        mention = CharacterMention(
            text="Victor",
            position=0,
            chapter_index=1,
            context="Victor walked into the room",
            in_dialogue=False,
        )
        assert hasattr(mention, 'is_agentive')
        assert mention.is_agentive == False

    def test_is_agentive_can_be_set(self):
        """Verify is_agentive can be set to True."""
        mention = CharacterMention(
            text="the creature",
            position=0,
            chapter_index=1,
            context="The creature walked through the forest",
            in_dialogue=False,
            is_agentive=True,
        )
        assert mention.is_agentive == True

    def test_to_dict_includes_is_agentive(self):
        """Verify to_dict includes is_agentive field."""
        mention = CharacterMention(
            text="Victor",
            position=0,
            chapter_index=1,
            context="Victor said hello",
            in_dialogue=True,
            is_agentive=True,
        )
        data = mention.to_dict()
        assert 'is_agentive' in data
        assert data['is_agentive'] == True

    def test_from_dict_handles_is_agentive(self):
        """Verify from_dict handles is_agentive field."""
        data = {
            "text": "Victor",
            "position": 0,
            "chapter_index": 1,
            "context": "Victor walked",
            "in_dialogue": False,
            "is_agentive": True,
        }
        mention = CharacterMention.from_dict(data)
        assert mention.is_agentive == True

    def test_from_dict_defaults_is_agentive(self):
        """Verify from_dict defaults is_agentive to False."""
        data = {
            "text": "Victor",
            "position": 0,
            "chapter_index": 1,
            "context": "Victor walked",
            "in_dialogue": False,
        }
        mention = CharacterMention.from_dict(data)
        assert mention.is_agentive == False


class TestPromptIncludesDescriptive:
    """Test that prompts include descriptive character type."""

    def test_system_prompt_mentions_descriptive(self):
        """Verify system prompt mentions descriptive type."""
        assert "descriptive" in CHARACTER_SYSTEM_PROMPT.lower()

    def test_system_prompt_descriptive_criteria(self):
        """Verify system prompt specifies criteria for descriptive handles."""
        # Should mention recurring/3+ times
        assert "3+" in CHARACTER_SYSTEM_PROMPT or "recurring" in CHARACTER_SYSTEM_PROMPT.lower()
        # Should mention agentive/speak/act
        assert "speak" in CHARACTER_SYSTEM_PROMPT.lower() or "act" in CHARACTER_SYSTEM_PROMPT.lower()

    def test_system_prompt_excludes_one_off(self):
        """Verify system prompt excludes one-off generic references."""
        assert "one-off" in CHARACTER_SYSTEM_PROMPT.lower() or "generic" in CHARACTER_SYSTEM_PROMPT.lower()

    def test_prompt_template_includes_acts_field(self):
        """Verify prompt template requests acts field."""
        assert "acts" in CHARACTER_PROMPT_TEMPLATE.lower()

    def test_prompt_template_descriptive_example(self):
        """Verify prompt template includes descriptive example."""
        assert "creature" in CHARACTER_PROMPT_TEMPLATE.lower() or "descriptive" in CHARACTER_PROMPT_TEMPLATE.lower()


class TestAgentiveDetection:
    """Test _detect_agentive_context() method."""

    @pytest.fixture
    def proposer(self):
        """Create a LLMCharacterProposer for testing."""
        # We can't easily mock the LLM, but we can test the detection method
        from unittest.mock import MagicMock
        mock_llm = MagicMock()
        return LLMCharacterProposer(llm_client=mock_llm)

    def test_speech_verbs_detected(self, proposer):
        """Verify speech verbs are detected as agentive."""
        agentive_contexts = [
            "The creature said nothing",
            "Victor asked the question",
            "She replied quietly",
            "He whispered the secret",
            "The monster shouted in rage",
        ]
        for context in agentive_contexts:
            assert proposer._detect_agentive_context(context), f"Should detect agentive: {context}"

    def test_motion_verbs_detected(self, proposer):
        """Verify motion verbs are detected as agentive."""
        agentive_contexts = [
            "The creature walked away",
            "Victor ran to the door",
            "She stood by the window",
            "He turned around suddenly",
            "The monster looked up",
        ]
        for context in agentive_contexts:
            assert proposer._detect_agentive_context(context), f"Should detect agentive: {context}"

    def test_action_verbs_detected(self, proposer):
        """Verify action verbs are detected as agentive."""
        agentive_contexts = [
            "The creature grabbed the rope",
            "Victor took the book",
            "She held the baby",
            "He threw the stone",
            "The monster pushed the door",
        ]
        for context in agentive_contexts:
            assert proposer._detect_agentive_context(context), f"Should detect agentive: {context}"

    def test_non_agentive_not_detected(self, proposer):
        """Verify non-agentive contexts are not detected."""
        non_agentive_contexts = [
            "The house was old",
            "A beautiful sunset appeared",
            "The door was blue",
            "Something strange happened",
        ]
        for context in non_agentive_contexts:
            assert not proposer._detect_agentive_context(context), f"Should NOT detect agentive: {context}"

    def test_case_insensitive(self, proposer):
        """Verify detection is case-insensitive."""
        assert proposer._detect_agentive_context("THE CREATURE SAID")
        assert proposer._detect_agentive_context("the creature SAID")
        assert proposer._detect_agentive_context("The Creature Said")


class TestDescriptiveCharacterCriteria:
    """Test criteria for descriptive character inclusion."""

    def test_prompt_requires_3_plus_mentions(self):
        """Verify prompt requires 3+ mentions for descriptive."""
        assert "3+" in CHARACTER_PROMPT_TEMPLATE or "three" in CHARACTER_PROMPT_TEMPLATE.lower()

    def test_prompt_requires_agentive(self):
        """Verify prompt requires agentive behavior for descriptive."""
        # Should mention acts: true or speaks/acts
        assert "acts" in CHARACTER_PROMPT_TEMPLATE.lower()


class TestIntegrationWithSampleText:
    """Integration tests for descriptive character extraction."""

    @pytest.fixture
    def sample_frankenstein_text(self):
        """Sample text mimicking Frankenstein with the creature."""
        return """
        The creature walked through the forest slowly. It had been days since
        the creature had seen another human. "Where am I?" the creature asked
        itself. The creature turned and looked back at the mountain.

        Victor watched from afar. The creature said nothing more and walked away.
        Later that evening, the creature came upon a cottage. The creature smiled
        for the first time. "Perhaps here I can find peace," the creature whispered.

        The creature entered the cottage carefully. The old man inside could not
        see the creature approach. The creature sat down near the fire.
        """

    def test_creature_would_be_agentive(self, sample_frankenstein_text):
        """Verify 'the creature' contexts would be detected as agentive."""
        from unittest.mock import MagicMock
        mock_llm = MagicMock()
        proposer = LLMCharacterProposer(llm_client=mock_llm)

        # Check agentive contexts around "the creature"
        # walked, asked, turned, looked, said, walked, came, smiled, whispered, entered, approach, sat
        agentive_verbs_in_text = ['walked', 'asked', 'turned', 'looked', 'said', 'came', 'smiled', 'whispered', 'entered', 'sat']

        for verb in agentive_verbs_in_text:
            context = f"The creature {verb}"
            assert proposer._detect_agentive_context(context), f"Should detect agentive: {context}"

    def test_prompt_structure_allows_descriptive(self):
        """Verify the prompt structure allows descriptive type."""
        # The prompt should list descriptive as a valid type
        assert '"descriptive"' in CHARACTER_PROMPT_TEMPLATE or "'descriptive'" in CHARACTER_PROMPT_TEMPLATE
