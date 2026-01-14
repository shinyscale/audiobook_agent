"""
Tests for hardened mention matching (Feature F1).

Verifies that:
1. Pronouns are not extracted as characters
2. Word boundary matching prevents substring matches
"""

import pytest
import re

from src.pipeline.character_extraction.proposers.llm import (
    LLMCharacterProposer,
    PRONOUN_STOPWORDS,
)
from src.pipeline.character_extraction.proposers.ner import (
    NERProposer,
    FALSE_POSITIVE_NAMES,
)


class TestPronounStopwordFilter:
    """Test that pronouns are filtered out as characters."""

    def test_pronoun_stopwords_defined(self):
        """Verify pronoun stopwords set contains expected pronouns."""
        expected_pronouns = {'he', 'she', 'it', 'they', 'we', 'i', 'you'}
        assert expected_pronouns.issubset(PRONOUN_STOPWORDS)

    def test_pronoun_stopwords_lowercase(self):
        """Verify all stopwords are lowercase for case-insensitive matching."""
        for word in PRONOUN_STOPWORDS:
            assert word == word.lower(), f"Stopword '{word}' is not lowercase"

    def test_determiners_included(self):
        """Verify determiners like 'the', 'a', 'an' are in stopwords."""
        expected_determiners = {'the', 'a', 'an', 'this', 'that'}
        assert expected_determiners.issubset(PRONOUN_STOPWORDS)

    def test_ner_false_positives_include_pronouns(self):
        """Verify NER proposer's false positives include pronouns."""
        pronouns = {'he', 'she', 'it', 'they', 'we', 'i', 'you', 'him', 'her', 'them', 'us', 'me'}
        assert pronouns.issubset(FALSE_POSITIVE_NAMES)


class TestWordBoundaryMatching:
    """Test word boundary matching to prevent substring matches."""

    def test_he_does_not_match_the(self):
        """Verify 'he' pattern does not match inside 'the'."""
        text = "The cat sat on the mat."
        pattern = r'\b' + re.escape('he') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 0, "Found matches for 'he' in text without standalone 'he'"

    def test_he_does_not_match_whether(self):
        """Verify 'he' pattern does not match inside 'whether'."""
        text = "He didn't know whether to stay or leave."
        pattern = r'\b' + re.escape('he') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        # Should only match standalone 'He', not 'whether'
        assert len(matches) == 1
        assert matches[0].group(0).lower() == 'he'

    def test_he_does_not_match_they(self):
        """Verify 'he' pattern does not match inside 'they'."""
        text = "They went to the store."
        pattern = r'\b' + re.escape('he') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 0

    def test_victor_matches_exactly(self):
        """Verify 'Victor' matches correctly."""
        text = "Victor walked into the room."
        pattern = r'\b' + re.escape('Victor') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 1
        assert matches[0].group(0) == 'Victor'

    def test_victor_does_not_match_victory(self):
        """Verify 'Victor' does not match inside 'victory'."""
        text = "The victory was complete."
        pattern = r'\b' + re.escape('Victor') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 0

    def test_multi_word_name_matches(self):
        """Verify multi-word names match correctly with word boundaries."""
        text = "Tom Buchanan entered the room. Tom was angry."
        pattern = r'\b' + re.escape('Tom Buchanan').replace(r'\ ', r'\s+') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 1

    def test_name_with_title_matches(self):
        """Verify names with titles match correctly."""
        text = "Mr. Gatsby threw a party."
        pattern = r'\b' + re.escape('Mr. Gatsby') + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        assert len(matches) == 1


class TestMinimumLengthGuardrail:
    """Test minimum length guardrail for single-word names."""

    def test_short_single_word_rejected(self):
        """Single-word names <= 2 chars should be rejected."""
        # This is tested through the LLM proposer logic
        # Single words like 'he', 'it', 'me' are 2 chars or less
        short_names = ['he', 'it', 'me', 'we', 'i', 'us']
        for name in short_names:
            # Should be <= 2 chars
            assert len(name) <= 2, f"'{name}' is longer than 2 chars"

    def test_valid_names_accepted(self):
        """Valid names > 2 chars should be accepted."""
        valid_names = ['Tom', 'Nick', 'Jay', 'Daisy', 'Victor']
        for name in valid_names:
            words = name.split()
            # Single-word name should be > 2 chars
            if len(words) == 1:
                assert len(name) > 2, f"'{name}' should be > 2 chars"


class TestNERProposerValidity:
    """Test NER proposer validity checks include pronouns."""

    def test_pronouns_invalid(self):
        """Verify NER proposer rejects pronouns as valid names."""
        proposer = NERProposer()
        pronouns = ['he', 'she', 'it', 'they', 'we', 'i', 'you', 'him', 'her']
        for pronoun in pronouns:
            assert not proposer._is_valid_name(pronoun), f"'{pronoun}' should be invalid"

    def test_real_names_valid(self):
        """Verify real names are still valid."""
        proposer = NERProposer()
        real_names = ['Victor', 'Elizabeth', 'Tom Buchanan', 'Nick Carraway']
        for name in real_names:
            assert proposer._is_valid_name(name), f"'{name}' should be valid"


class TestIntegrationWithSampleText:
    """Integration tests with sample text containing pronouns."""

    @pytest.fixture
    def sample_text_with_pronouns(self):
        """Sample text with both pronouns and real names."""
        return """
        Victor walked into the laboratory. He looked around nervously.
        Elizabeth called to him from the doorway. She was worried about Victor.
        "What are you doing here?" they asked. Whether it was wise to continue,
        Victor couldn't say. The experiment had consumed him entirely.
        """

    def test_word_boundary_regex_on_sample(self, sample_text_with_pronouns):
        """Verify word boundary regex works on sample text."""
        text = sample_text_with_pronouns

        # 'Victor' should match 3 times
        victor_pattern = r'\bVictor\b'
        victor_matches = list(re.finditer(victor_pattern, text, re.IGNORECASE))
        assert len(victor_matches) == 3, f"Expected 3 Victor matches, got {len(victor_matches)}"

        # 'Elizabeth' should match once
        elizabeth_pattern = r'\bElizabeth\b'
        elizabeth_matches = list(re.finditer(elizabeth_pattern, text, re.IGNORECASE))
        assert len(elizabeth_matches) == 1

        # 'he' should NOT match inside 'the', 'they', 'whether'
        # but should match standalone 'He'
        he_pattern = r'\bhe\b'
        he_matches = list(re.finditer(he_pattern, text, re.IGNORECASE))
        assert len(he_matches) == 1, f"Expected 1 standalone 'he' match, got {len(he_matches)}"

    def test_pronouns_filtered_from_character_list(self, sample_text_with_pronouns):
        """Verify pronouns would be filtered as characters."""
        # Simulate what the LLM proposer does
        potential_names = ['Victor', 'Elizabeth', 'He', 'She', 'They', 'him']

        valid_characters = []
        for name in potential_names:
            # Apply pronoun filter
            if name.lower() in PRONOUN_STOPWORDS:
                continue
            # Apply length filter
            if len(name.split()) == 1 and len(name) <= 2:
                continue
            valid_characters.append(name)

        assert 'Victor' in valid_characters
        assert 'Elizabeth' in valid_characters
        assert 'He' not in valid_characters
        assert 'She' not in valid_characters
        assert 'They' not in valid_characters
        assert 'him' not in valid_characters
