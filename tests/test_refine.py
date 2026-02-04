"""
Tests for text refinement functionality.

Tests the dehyphenation and word rejoining logic in src/ingestion/refine.py.
"""

import pytest
from src.ingestion.refine import (
    _dehyphenate,
    _rejoin_split_words,
    _should_merge,
)


class TestDehyphenate:
    """Tests for the _dehyphenate() function."""

    def test_basic_dehyphenation(self):
        """Test basic hyphenated word rejoining."""
        text = "This is an exam-\nple of text"
        result, count = _dehyphenate(text)
        assert "example" in result
        assert count == 1

    def test_dehyphenate_proper_noun(self):
        """Test dehyphenation of proper nouns (Clerval case)."""
        text = "Henry Cler-\nval was a friend"
        result, count = _dehyphenate(text)
        assert "Clerval" in result
        assert count == 1

    def test_dehyphenate_uppercase_continuation(self):
        """Test that uppercase continuations are now handled."""
        text = "Franken-\nStein was the doctor"
        result, count = _dehyphenate(text)
        # Should join even with uppercase S
        assert "FrankenStein" in result or "Frankenstein" in result.lower()

    def test_dehyphenate_multiple(self):
        """Test multiple dehyphenations in same text."""
        text = "The exam-\nple and sam-\nple are similar"
        result, count = _dehyphenate(text)
        assert "example" in result
        assert "sample" in result
        assert count == 2

    def test_dehyphenate_preserves_valid_hyphen(self):
        """Test that intentional hyphens within lines are preserved."""
        text = "This is a self-aware robot"
        result, count = _dehyphenate(text)
        assert "self-aware" in result
        assert count == 0

    def test_dehyphenate_with_extra_whitespace(self):
        """Test dehyphenation with extra whitespace after hyphen."""
        text = "exam-\n   ple"
        result, count = _dehyphenate(text)
        assert "example" in result
        assert count == 1

    def test_no_dehyphenation_paragraph_boundary(self):
        """Test that hyphen at paragraph boundary is preserved."""
        # Pattern requires single newline, not double
        text = "word-\n\nother"
        result, count = _dehyphenate(text)
        # Should NOT merge across paragraph break
        assert count == 0


class TestRejoinSplitWords:
    """Tests for the _rejoin_split_words() function."""

    def test_basic_rejoin(self):
        """Test basic word rejoining at line break."""
        text = "Henry Cler\nval was a friend"
        result, count = _rejoin_split_words(text)
        assert "Clerval" in result
        assert count == 1

    def test_rejoin_proper_noun_variant(self):
        """Test rejoining with mixed case proper noun."""
        # Use a fragment that is NOT a valid word on its own
        # "Parac" (from Paracelsus) is not a valid word
        text = "The alchemist Parac\nelsus studied"
        result, count = _rejoin_split_words(text)
        assert "Paracelsus" in result
        assert count == 1

    def test_no_rejoin_paragraph_break(self):
        """Test that words are not rejoined across paragraph breaks."""
        text = "End of paragraph.\n\nNew paragraph starts"
        result, count = _rejoin_split_words(text)
        assert result == text
        assert count == 0

    def test_no_rejoin_uppercase_continuation(self):
        """Test that uppercase continuations are not rejoined (conservative)."""
        text = "Hello\nWorld"
        result, count = _rejoin_split_words(text)
        # Should NOT merge - both are valid words and continuation is uppercase
        assert result == text
        assert count == 0

    def test_rejoin_with_leading_whitespace(self):
        """Test rejoining with leading whitespace on continuation."""
        text = "Cler\n  val was there"
        result, count = _rejoin_split_words(text)
        assert "Clerval" in result
        assert count == 1

    def test_no_rejoin_valid_words(self):
        """Test that valid standalone words are not rejoined."""
        text = "the\ndog ran"
        result, count = _rejoin_split_words(text)
        # "the" is a valid word, should not merge
        assert "thedog" not in result
        assert count == 0

    def test_no_rejoin_single_char_fragment(self):
        """Test that single character fragments are not rejoined."""
        text = "a\npart"
        result, count = _rejoin_split_words(text)
        # "a" is too short to be a fragment
        assert "apart" not in result
        assert count == 0

    def test_rejoin_mid_text(self):
        """Test rejoining in the middle of a longer text."""
        text = "The character Cler\nval appeared often in the story."
        result, count = _rejoin_split_words(text)
        assert "Clerval" in result
        assert "appeared" in result


class TestShouldMerge:
    """Tests for the _should_merge() helper function."""

    def test_merge_valid_combined_word(self):
        """Test that valid combined words are merged."""
        # "example" is a valid word
        assert _should_merge("exam", "ple") is True

    def test_no_merge_valid_first_fragment(self):
        """Test that valid first fragments prevent merging when combined is invalid."""
        # "book" is a valid word and "xyz" makes invalid combination
        assert _should_merge("book", "xyz") is False

    def test_merge_proper_noun_fragments(self):
        """Test that proper noun fragments are merged."""
        # Neither "Cler" nor "val" is a valid word, combined isn't either
        # But continuation is lowercase, so should merge
        result = _should_merge("Cler", "val")
        assert result is True

    def test_short_valid_word_still_merges(self):
        """Test that very short valid words (<=2 chars) still allow merging."""
        # "re" is 2 chars, should still allow merge even if valid
        # The function checks len(word_start) > 2 for the rejection
        result = _should_merge("re", "mark")
        assert result is True  # "remark" is valid

    def test_two_letter_words_prevent_merge(self):
        """Test that 2-letter valid words prevent incorrect merging.

        This was a bug where words like "to", "no", "us" at line endings
        would incorrectly merge with the next word because the check was
        `len(word_start) > 2` instead of `>= 2`.

        Regression test for: "attached to\\nthe" becoming "attached tothe"
        """
        # These 2-letter words should NOT merge when combined is invalid
        assert _should_merge("to", "the") is False
        assert _should_merge("no", "blood") is False
        assert _should_merge("us", "followed") is False
        assert _should_merge("on", "top") is False

        # Note: "in" + "side" -> "inside" IS valid, so merge is allowed
        # Same with "an" + "other" -> "another"
        # This is correct behavior - we only block merge when combined is invalid


class TestIntegration:
    """Integration tests combining dehyphenation and rejoining."""

    def test_frankenstein_style_text(self):
        """Test text similar to what we see from old PDF extraction."""
        text = """
Henry Cler-
val was the son of a merchant of Geneva. He
was a boy of singular talent and fancy.

Meanwhile Cler
val occupied himself with the moral relations of things.

My dear Frank-
enstein, exclaimed he, how glad I am to see you!
"""
        # Run dehyphenation first
        text, dehyphen_count = _dehyphenate(text)
        # Then rejoin
        text, rejoin_count = _rejoin_split_words(text)

        # Check results
        assert "Clerval" in text
        assert "Frankenstein" in text
        # Should have caught at least 2 dehyphenations
        assert dehyphen_count >= 2
        # And at least 1 rejoin
        assert rejoin_count >= 1

    def test_does_not_break_valid_text(self):
        """Test that valid text is not corrupted."""
        text = """
The quick brown fox jumps over the lazy dog.
This is a normal paragraph with proper spacing.

A new paragraph starts here with no issues.
The text should remain unchanged.
"""
        original = text
        text, dehyphen_count = _dehyphenate(text)
        text, rejoin_count = _rejoin_split_words(text)

        # Valid text should not be changed
        assert dehyphen_count == 0
        assert rejoin_count == 0
        assert text == original
