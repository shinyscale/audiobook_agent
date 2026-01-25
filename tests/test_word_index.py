"""Tests for WordIndex single-pass word indexing."""

import pytest
from src.pipeline.pronunciation_guide.word_index import WordIndex, WordOccurrence
from src.pipeline.pronunciation_guide.proposers import (
    CMUProposer, HomographProposer, CharacterProposer
)


class TestWordIndexBasics:
    """Basic WordIndex functionality tests."""

    def test_builds_index_in_single_pass(self):
        """WordIndex builds complete word-to-positions map in single pass."""
        text = "The quick brown fox jumps over the lazy dog. The fox was quick."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Verify all unique words are indexed
        all_words = index.get_all_words()
        expected_words = {"the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "was"}
        assert expected_words.issubset(all_words)

    def test_word_counts_correct(self):
        """WordIndex correctly counts word occurrences."""
        text = "The quick brown fox jumps over the lazy dog. The fox was quick."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Verify occurrence counts
        assert len(index.get_occurrences("the")) == 3  # "The" appears 3 times
        assert len(index.get_occurrences("fox")) == 2
        assert len(index.get_occurrences("quick")) == 2
        assert len(index.get_occurrences("lazy")) == 1

    def test_positions_are_correct(self):
        """WordIndex stores correct character positions."""
        text = "Hello world. Hello again."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Check positions for "Hello"
        hello_occurrences = index.get_occurrences("hello")
        assert len(hello_occurrences) == 2
        assert hello_occurrences[0].position == 0
        assert hello_occurrences[1].position == 13

    def test_has_word(self):
        """has_word correctly identifies present and absent words."""
        text = "The quick brown fox"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        assert index.has_word("quick")
        assert index.has_word("QUICK")  # Case insensitive
        assert index.has_word("fox")
        assert not index.has_word("nonexistent")
        assert not index.has_word("lazy")

    def test_preserves_original_form(self):
        """WordIndex preserves original capitalization in original_form."""
        text = "The THE the"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        occurrences = index.get_occurrences("the")
        forms = [occ.original_form for occ in occurrences]
        assert "The" in forms
        assert "THE" in forms
        assert "the" in forms


class TestWordIndexChapters:
    """Tests for chapter boundary assignment."""

    def test_chapter_indices_correctly_assigned(self):
        """Words are assigned to correct chapters."""
        text = "Chapter one content. Chapter two content. Chapter three content."
        # Chapter 1: 0-20, Chapter 2: 20-42, Chapter 3: 42-64
        boundaries = [
            (1, 0, 20),
            (2, 20, 42),
            (3, 42, 64),
        ]

        index = WordIndex(text, boundaries)

        # "Chapter" appears in each chapter
        chapter_occurrences = index.get_occurrences("chapter")
        chapters = [occ.chapter_index for occ in chapter_occurrences]
        assert 1 in chapters
        assert 2 in chapters
        assert 3 in chapters

    def test_default_chapter_for_position_outside_boundaries(self):
        """Positions outside defined boundaries default to chapter 1."""
        text = "Some text here"
        boundaries = [(5, 100, 200)]  # Boundaries don't cover text

        index = WordIndex(text, boundaries)

        occurrences = index.get_occurrences("some")
        assert occurrences[0].chapter_index == 1


class TestWordIndexSpecialWords:
    """Tests for hyphenated words and apostrophes."""

    def test_hyphenated_words(self):
        """Hyphenated words are captured as single words."""
        text = "This is a well-known fact. State-of-the-art technology."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        assert index.has_word("well-known")
        assert index.has_word("state-of-the-art")

    def test_apostrophe_words(self):
        """Words with apostrophes are captured correctly."""
        text = "Don't worry, it's O'Brien's idea."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        assert index.has_word("don't")
        assert index.has_word("it's")
        assert index.has_word("o'brien's")


class TestWordIndexFiltering:
    """Tests for predicate-based filtering."""

    def test_filter_by_predicate(self):
        """filter_by_predicate returns matching words."""
        text = "apple banana cherry date elderberry fig grape"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Filter words starting with specific letters
        def starts_with_vowel(word: str) -> bool:
            return word[0] in "aeiou"

        filtered = index.filter_by_predicate(starts_with_vowel)
        filtered_words = set(filtered.keys())
        assert "apple" in filtered_words
        assert "elderberry" in filtered_words
        assert "banana" not in filtered_words

    def test_filter_by_length(self):
        """Filter words by length."""
        text = "a ab abc abcd abcde"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        def longer_than_3(word: str) -> bool:
            return len(word) > 3

        filtered = index.filter_by_predicate(longer_than_3)
        assert "abcd" in filtered
        assert "abcde" in filtered
        assert "abc" not in filtered


class TestWordIndexContext:
    """Tests for context extraction."""

    def test_context_includes_target_word(self):
        """Context extraction always includes the target word."""
        text = "This is a test sentence with the word pronunciation in the middle of it."
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        position = text.index("pronunciation")
        word_length = len("pronunciation")
        context = index.extract_context(position, word_length)

        assert "pronunciation" in context

    def test_context_at_start(self):
        """Context at document start has no leading ellipsis."""
        text = "Hello world this is a test"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        context = index.extract_context(0, 5, window=10)
        assert not context.startswith("...")
        assert "Hello" in context

    def test_context_at_end(self):
        """Context at document end has no trailing ellipsis."""
        text = "This is a test world Hello"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        position = text.rindex("Hello")
        context = index.extract_context(position, 5, window=10)
        assert not context.endswith("...")
        assert "Hello" in context

    def test_context_in_middle(self):
        """Context in middle has both ellipses."""
        text = "A" * 200 + " target " + "B" * 200
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        position = text.index("target")
        context = index.extract_context(position, 6, window=50)

        assert context.startswith("...")
        assert context.endswith("...")
        assert "target" in context


class TestWordIndexStats:
    """Tests for statistics methods."""

    def test_unique_word_count(self):
        """get_unique_word_count returns correct count."""
        text = "the the the quick brown fox"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Unique words: the, quick, brown, fox
        assert index.get_unique_word_count() == 4

    def test_total_word_count(self):
        """get_total_word_count returns correct count."""
        text = "the the the quick brown fox"
        boundaries = [(1, 0, len(text))]

        index = WordIndex(text, boundaries)

        # Total words: 6
        assert index.get_total_word_count() == 6


class TestProposersWithWordIndex:
    """Tests that proposers work correctly with WordIndex."""

    def test_homograph_proposer_with_index(self):
        """HomographProposer finds homographs using WordIndex."""
        text = "I read the book yesterday. I will read another book today. The lead singer took the lead."
        boundaries = [(1, 0, len(text))]
        word_index = WordIndex(text, boundaries)

        proposer = HomographProposer()

        # With WordIndex
        proposals_with_index = proposer.propose(
            text, boundaries, None, word_index=word_index
        )

        # Without WordIndex
        proposals_without_index = proposer.propose(
            text, boundaries, None, word_index=None
        )

        # Results should be equivalent
        words_with = {p.word for p in proposals_with_index}
        words_without = {p.word for p in proposals_without_index}
        assert words_with == words_without
        assert "read" in words_with
        assert "lead" in words_with

    def test_character_proposer_with_index(self):
        """CharacterProposer finds character names using WordIndex."""
        text = "Gatsby threw a party. Nick met Gatsby at the party. Daisy was there too."
        boundaries = [(1, 0, len(text))]
        word_index = WordIndex(text, boundaries)
        character_names = ["Gatsby", "Nick", "Daisy"]

        proposer = CharacterProposer()

        # With WordIndex
        proposals_with_index = proposer.propose(
            text, boundaries, character_names, word_index=word_index
        )

        # Without WordIndex
        proposals_without_index = proposer.propose(
            text, boundaries, character_names, word_index=None
        )

        # Results should be equivalent
        words_with = {p.word for p in proposals_with_index}
        words_without = {p.word for p in proposals_without_index}
        assert words_with == words_without
        # "Gatsby" is flagged; "Nick" and "Daisy" are in COMMON_WORDS_WHITELIST
        assert "Gatsby" in words_with
        assert "Nick" not in words_with  # Common word, whitelisted
        assert "Daisy" not in words_with  # Common word, whitelisted

    def test_cmu_proposer_with_index(self):
        """CMUProposer finds unknown words using WordIndex."""
        text = "The Frankenstein monster walked through Geneva. Dr. Krempe was there."
        boundaries = [(1, 0, len(text))]
        word_index = WordIndex(text, boundaries)

        proposer = CMUProposer()

        # With WordIndex
        proposals_with_index = proposer.propose(
            text, boundaries, None, word_index=word_index
        )

        # Without WordIndex
        proposals_without_index = proposer.propose(
            text, boundaries, None, word_index=None
        )

        # Results should be equivalent (same words found)
        words_with = {p.word.lower() for p in proposals_with_index}
        words_without = {p.word.lower() for p in proposals_without_index}
        assert words_with == words_without
