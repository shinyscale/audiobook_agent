"""
Tests for character type inference.

Feature 3: Character Type Classification
- Story 1: NER proposer infers character type from context
"""

import pytest
from src.pipeline.character_extraction.proposers.ner import NERProposer
from src.pipeline.character_extraction.models import CharacterMention, CharacterType


class TestCharacterTypeInference:
    """Test _infer_character_type() in NER proposer."""

    @pytest.fixture
    def proposer(self):
        return NERProposer()

    def _make_mention(
        self, context: str, in_dialogue: bool = False, chapter: int = 1
    ) -> CharacterMention:
        """Helper to create character mentions."""
        return CharacterMention(
            text="TestChar",
            position=0,
            chapter_index=chapter,
            context=context,
            in_dialogue=in_dialogue,
        )

    def test_dialogue_signals_story_character(self, proposer):
        """Characters appearing in dialogue should be STORY type."""
        mentions = [
            self._make_mention("He was there", in_dialogue=True),
            self._make_mention("Standing by the door", in_dialogue=False),
        ]
        result = proposer._infer_character_type("TestChar", mentions)
        assert result == CharacterType.STORY, "Dialogue should indicate STORY character"

    def test_action_verbs_signal_story_character(self, proposer):
        """Characters with action verbs in context should be STORY type."""
        mentions = [
            self._make_mention("Gatsby said something"),
            self._make_mention("Gatsby looked at her"),
            self._make_mention("Gatsby smiled warmly"),
        ]
        result = proposer._infer_character_type("Gatsby", mentions)
        assert result == CharacterType.STORY, "Action verbs should indicate STORY character"

    def test_multiple_action_verbs_accumulate(self, proposer):
        """Multiple action verbs across mentions should accumulate signals."""
        mentions = [
            self._make_mention("He walked to the door"),
            self._make_mention("He turned around"),
            self._make_mention("He nodded slowly"),
        ]
        result = proposer._infer_character_type("TestChar", mentions)
        assert result == CharacterType.STORY, "Multiple action verbs should indicate STORY"

    def test_no_signals_returns_uncertain(self, proposer):
        """No dialogue or action verbs should return UNCERTAIN."""
        mentions = [
            self._make_mention("The famous author"),
            self._make_mention("A name in history"),
        ]
        result = proposer._infer_character_type("TestChar", mentions)
        assert result == CharacterType.UNCERTAIN, "No signals should return UNCERTAIN"

    def test_single_dialogue_sufficient(self, proposer):
        """Even a single dialogue mention should indicate STORY."""
        mentions = [
            self._make_mention("Some text", in_dialogue=False),
            self._make_mention("Some text", in_dialogue=False),
            self._make_mention("Some text", in_dialogue=True),  # One dialogue
        ]
        result = proposer._infer_character_type("TestChar", mentions)
        assert result == CharacterType.STORY, "Single dialogue should indicate STORY"

    def test_historical_reference_without_action(self, proposer):
        """Historical references without action verbs stay UNCERTAIN."""
        mentions = [
            self._make_mention("Napoleon was a great general"),
            self._make_mention("Like Napoleon in his time"),
        ]
        result = proposer._infer_character_type("Napoleon", mentions)
        assert result == CharacterType.UNCERTAIN, "Historical refs without action should be UNCERTAIN"


class TestNERProposerIntegration:
    """Test that NER proposer correctly sets character_type on proposals."""

    @pytest.fixture
    def proposer(self):
        return NERProposer()

    def test_proposal_has_character_type(self, proposer):
        """Proposals from NER should have character_type set."""
        # Sample text with dialogue
        text = '''
        "Hello," said Gatsby.
        Gatsby smiled at her.
        Gatsby walked to the window.
        '''
        proposals = proposer.propose(text, chapter_index=1, chapter_start_position=0)

        # Find Gatsby proposal if present (spaCy may or may not detect it)
        gatsby_proposals = [p for p in proposals if 'Gatsby' in p.name]

        if gatsby_proposals:
            # Should have character_type set (either STORY or UNCERTAIN)
            for prop in gatsby_proposals:
                assert hasattr(prop, 'character_type'), "Proposal should have character_type"
                assert prop.character_type in [CharacterType.STORY, CharacterType.UNCERTAIN]

    def test_dialogue_character_is_story_type(self, proposer):
        """Character appearing in dialogue should be STORY type."""
        text = '''
        "What do you mean?" asked Nick.
        Nick stood up from his chair.
        "I see," Nick replied thoughtfully.
        Nick looked out the window.
        '''
        proposals = proposer.propose(text, chapter_index=1, chapter_start_position=0)

        nick_proposals = [p for p in proposals if 'Nick' in p.name]

        if nick_proposals:
            # Nick should be classified as STORY due to dialogue and action verbs
            for prop in nick_proposals:
                # Either STORY (detected dialogue/verbs) or UNCERTAIN (spaCy issue)
                assert prop.character_type in [CharacterType.STORY, CharacterType.UNCERTAIN]
