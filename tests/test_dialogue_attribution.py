"""
Tests for CRF dialogue attribution module.

Tests feature extraction, dialogue turn extraction, and integration patterns.
CRF model tests are skipped when the model or sklearn-crfsuite is unavailable.
"""

import pytest

from src.pipeline.dialogue_attribution import (
    extract_dialogue_turns,
    extract_features,
    _find_speech_verb,
    _find_character_in_context,
    _detect_pronoun_gender,
    crf_available,
    _crfsuite_available,
    SPEECH_VERBS,
)


class TestDialogueTurnExtraction:
    """Test quote/dialogue extraction from raw text."""

    def test_basic_quote_extraction(self):
        text = 'Tom looked at her. "I love New York," he said. Daisy smiled.'
        turns = extract_dialogue_turns(text)
        assert len(turns) == 1
        assert "I love New York" in turns[0]["quote"]

    def test_multiple_quotes(self):
        text = (
            '"Hello," said Tom. "How are you?" '
            'Daisy paused. "I am well, thank you," she replied.'
        )
        turns = extract_dialogue_turns(text)
        assert len(turns) >= 2

    def test_short_quotes_filtered(self):
        text = 'He said "no" and left. Then he said "I disagree with that entirely."'
        turns = extract_dialogue_turns(text)
        # "no" is only 2 chars, should be filtered (minimum 3)
        assert all(len(t["quote"]) >= 3 for t in turns)

    def test_context_captured(self):
        text = "A" * 300 + '"Hello there friend," said Tom.' + "B" * 300
        turns = extract_dialogue_turns(text)
        assert len(turns) == 1
        assert "said Tom" in turns[0]["post_context"]

    def test_empty_text(self):
        assert extract_dialogue_turns("") == []
        assert extract_dialogue_turns("No dialogue here.") == []


class TestSpeechVerbDetection:

    def test_common_verbs(self):
        assert _find_speech_verb("said Tom") == "said"
        assert _find_speech_verb("she whispered softly") == "whispered"
        assert _find_speech_verb("he asked her") == "asked"

    def test_no_verb(self):
        assert _find_speech_verb("Tom walked away") is None
        assert _find_speech_verb("") is None

    def test_multiple_verbs(self):
        # Should return first match
        result = _find_speech_verb("she said and then asked")
        assert result in SPEECH_VERBS


class TestCharacterDetection:

    def test_full_name_match(self):
        chars = ["Tom Buchanan", "Daisy Buchanan", "Jay Gatsby"]
        assert _find_character_in_context("Tom Buchanan smiled", chars) == "Tom Buchanan"

    def test_partial_name_match(self):
        chars = ["Tom Buchanan", "Daisy Buchanan"]
        assert _find_character_in_context("said Tom", chars) == "Tom Buchanan"

    def test_no_match(self):
        chars = ["Tom Buchanan"]
        assert _find_character_in_context("Jordan walked away", chars) is None

    def test_short_name_parts_ignored(self):
        chars = ["Mr. Li"]
        # "Li" is only 2 chars, should not match on its own
        result = _find_character_in_context("He liked it", chars)
        # "Mr. Li" doesn't appear, and "Li" is too short
        assert result is None


class TestPronounGender:

    def test_male(self):
        assert _detect_pronoun_gender("he said to his friend") == "male"

    def test_female(self):
        assert _detect_pronoun_gender("she told her mother") == "female"

    def test_neutral(self):
        assert _detect_pronoun_gender("the person walked away") == "neutral"


class TestFeatureExtraction:

    def test_basic_features(self):
        turn = {
            "quote": "I love New York",
            "position": 100,
            "pre_context": "Tom looked at her. ",
            "post_context": " he said quietly.",
        }
        chars = ["Tom Buchanan", "Daisy Buchanan"]
        feats = extract_features(turn, 0, 5, chars)

        assert "pre_speech_verb" in feats
        assert "post_speech_verb" in feats
        assert "pre_character" in feats
        assert "post_character" in feats
        assert "quote_length" in feats
        assert "chapter_position" in feats
        assert "prev_speaker" in feats
        assert feats["post_speech_verb"] == "said"

    def test_all_features_are_strings(self):
        turn = {
            "quote": "Hello there",
            "position": 50,
            "pre_context": "She smiled. ",
            "post_context": " he replied.",
        }
        feats = extract_features(turn, 2, 10, ["Alice", "Bob"])
        for key, value in feats.items():
            assert isinstance(value, str), f"Feature {key} is {type(value)}, expected str"

    def test_quote_length_buckets(self):
        short_turn = {"quote": "Yes", "position": 0, "pre_context": "", "post_context": ""}
        medium_turn = {"quote": "x" * 100, "position": 0, "pre_context": "", "post_context": ""}
        long_turn = {"quote": "x" * 300, "position": 0, "pre_context": "", "post_context": ""}

        assert extract_features(short_turn, 0, 1, [])["quote_length"] == "very_short"
        assert extract_features(medium_turn, 0, 1, [])["quote_length"] == "medium"
        assert extract_features(long_turn, 0, 1, [])["quote_length"] == "long"


class TestCRFAvailability:

    def test_unavailable_without_model(self):
        # Model file shouldn't exist in test environment
        if not _crfsuite_available():
            assert crf_available() is False

    def test_crfsuite_check(self):
        # Just verify the check doesn't crash
        result = _crfsuite_available()
        assert isinstance(result, bool)


@pytest.mark.skipif(
    not _crfsuite_available(),
    reason="sklearn-crfsuite not installed"
)
@pytest.mark.skipif(
    not crf_available(),
    reason="CRF model not available"
)
class TestCRFIntegration:
    """Integration tests when CRF model is available."""

    def test_attribute_basic_dialogue(self):
        from src.pipeline.dialogue_attribution import CRFDialogueAttributor

        attributor = CRFDialogueAttributor()
        text = (
            'Tom walked into the room. "Hello everyone," said Tom. '
            'Daisy looked up. "Oh, you are here," she replied. '
            '"Yes, I just arrived," Tom answered.'
        )
        characters = ["Tom Buchanan", "Daisy Buchanan"]
        results = attributor.attribute(text, characters)
        # Should get some attributions
        assert isinstance(results, list)
        for r in results:
            assert "quote" in r
            assert "speaker" in r
            assert "confidence" in r
            assert "position" in r

    def test_empty_characters(self):
        from src.pipeline.dialogue_attribution import CRFDialogueAttributor

        attributor = CRFDialogueAttributor()
        results = attributor.attribute("Some text", [])
        assert results == []

    def test_no_dialogue(self):
        from src.pipeline.dialogue_attribution import CRFDialogueAttributor

        attributor = CRFDialogueAttributor()
        results = attributor.attribute("No dialogue here.", ["Tom"])
        assert results == []
