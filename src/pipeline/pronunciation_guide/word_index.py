"""
Single-pass word indexing for pronunciation guide performance optimization.

This module provides O(1) word lookups by building a complete word-to-positions
index in a single regex scan of the document, eliminating the need for multiple
full-text scans by individual proposers.
"""

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ParagraphBoundary:
    """A paragraph boundary in the document (Feature F26)."""
    start: int
    end: int
    chapter_index: int


@dataclass
class WordOccurrence:
    """Single occurrence of a word in the document."""
    position: int
    original_form: str
    chapter_index: int
    paragraph_index: Optional[int] = None  # F26: which paragraph this word is in


class WordIndex:
    """
    Pre-built index of all words in document with positions.

    Performs a single regex scan to build a word-to-positions map,
    allowing all proposers to query the index in O(1) time instead
    of each performing their own full-text scan.

    Example:
        >>> text = "The quick brown fox jumps over the lazy dog."
        >>> boundaries = [(1, 0, len(text))]
        >>> index = WordIndex(text, boundaries)
        >>> len(index.get_occurrences("the"))  # case-insensitive
        2
        >>> index.has_word("fox")
        True
    """

    def __init__(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
    ):
        """
        Build word index from document text.

        Args:
            full_text: Complete document text
            chapter_boundaries: List of (chapter_index, start_pos, end_pos)
        """
        self.full_text = full_text
        self.chapter_boundaries = chapter_boundaries
        self.word_positions: dict[str, list[WordOccurrence]] = {}
        self.paragraphs: list[ParagraphBoundary] = []  # F26: paragraph boundaries
        self._build_paragraph_index()  # F26: detect paragraphs first
        self._build_index()

    def _build_paragraph_index(self) -> None:
        """
        F26: Detect and store paragraph boundaries in a single pass.

        Paragraphs are separated by:
        - Two or more newlines
        - Newline followed by indent
        - Chapter boundaries

        This enables paragraph-based context extraction (F27).
        """
        # Pattern for paragraph separators: 2+ newlines or newline + whitespace indent
        para_separator = re.compile(r'\n\s*\n+|\n(?=[ \t]{2,})')

        current_pos = 0
        para_idx = 0

        for match in para_separator.finditer(self.full_text):
            para_start = current_pos
            para_end = match.start()

            # Only add non-empty paragraphs
            if para_end > para_start:
                chapter_idx = self._get_chapter(para_start)
                self.paragraphs.append(ParagraphBoundary(
                    start=para_start,
                    end=para_end,
                    chapter_index=chapter_idx,
                ))
                para_idx += 1

            current_pos = match.end()

        # Handle last paragraph (after last separator)
        if current_pos < len(self.full_text):
            chapter_idx = self._get_chapter(current_pos)
            self.paragraphs.append(ParagraphBoundary(
                start=current_pos,
                end=len(self.full_text),
                chapter_index=chapter_idx,
            ))

    def _get_paragraph_index(self, position: int) -> Optional[int]:
        """F26: Get the paragraph index for a given position."""
        for idx, para in enumerate(self.paragraphs):
            if para.start <= position < para.end:
                return idx
        return None

    def get_paragraph(self, paragraph_index: int) -> Optional[ParagraphBoundary]:
        """F26: Get paragraph boundary by index."""
        if 0 <= paragraph_index < len(self.paragraphs):
            return self.paragraphs[paragraph_index]
        return None

    def get_paragraph_text(self, paragraph_index: int) -> Optional[str]:
        """F26: Get the text of a paragraph by index."""
        para = self.get_paragraph(paragraph_index)
        if para:
            return self.full_text[para.start:para.end].strip()
        return None

    def _build_index(self) -> None:
        """
        Single pass to extract all words with positions.

        Uses regex pattern that handles:
        - Standard words: "hello"
        - Hyphenated words: "well-known" (captured as single word)
        - Apostrophes: "don't", "O'Brien" (captured as single word)

        Note: Accented characters (cafe, naive) may need special handling
        depending on text encoding. Consider Unicode word boundaries if needed.
        """
        # Pattern handles hyphenated words and apostrophes
        pattern = r"\b([a-zA-Z]+(?:[-'][a-zA-Z]+)*)\b"

        for match in re.finditer(pattern, self.full_text):
            word = match.group(1)
            word_lower = word.lower()
            position = match.start()
            chapter_idx = self._get_chapter(position)
            paragraph_idx = self._get_paragraph_index(position)  # F26

            if word_lower not in self.word_positions:
                self.word_positions[word_lower] = []

            self.word_positions[word_lower].append(WordOccurrence(
                position=position,
                original_form=word,
                chapter_index=chapter_idx,
                paragraph_index=paragraph_idx,  # F26
            ))

    def _get_chapter(self, position: int) -> int:
        """Determine which chapter a position falls in (O(n) for n chapters)."""
        for index, start, end in self.chapter_boundaries:
            if start <= position < end:
                return index
        return 1  # Default to chapter 1

    def get_occurrences(self, word: str) -> list[WordOccurrence]:
        """O(1) lookup of word positions."""
        return self.word_positions.get(word.lower(), [])

    def has_word(self, word: str) -> bool:
        """Check if word exists in index."""
        return word.lower() in self.word_positions

    def get_all_words(self) -> set[str]:
        """Get all unique words in document (lowercase)."""
        return set(self.word_positions.keys())

    def filter_by_predicate(
        self,
        predicate: Callable[[str], bool],
    ) -> dict[str, list[WordOccurrence]]:
        """
        Get all words matching a predicate function.

        Args:
            predicate: Function that takes a word (lowercase) and returns True if it matches

        Returns:
            Dict of matching word -> list of occurrences
        """
        return {
            word: occs
            for word, occs in self.word_positions.items()
            if predicate(word)
        }

    def get_unique_word_count(self) -> int:
        """Get count of unique words in document."""
        return len(self.word_positions)

    def get_total_word_count(self) -> int:
        """Get total word count (including duplicates)."""
        return sum(len(occs) for occs in self.word_positions.values())

    def extract_context(
        self,
        position: int,
        word_length: int,
        window: int = 100,
    ) -> str:
        """
        Extract fixed window around word, guaranteeing word is included.

        This is a reliable fixed-window approach that always centers the
        target word in the context. Phase 2 will implement paragraph-based
        context extraction with clickable navigation.

        Args:
            position: Character position of word start
            word_length: Length of the target word
            window: Characters of context on each side (default 100)

        Returns:
            Context string with word guaranteed to be included
        """
        start = max(0, position - window)
        end = min(len(self.full_text), position + word_length + window)
        context = self.full_text[start:end]
        context = ' '.join(context.split())  # Normalize whitespace

        if start > 0:
            context = "..." + context
        if end < len(self.full_text):
            context = context + "..."

        return context

    def extract_paragraph_context(
        self,
        position: int,
        word_length: int,
    ) -> Optional[tuple[str, int, int]]:
        """
        F27: Extract full paragraph containing word, with word position info.

        Returns the complete paragraph text instead of a fixed window,
        providing complete sentence context.

        Args:
            position: Character position of word start
            word_length: Length of the target word

        Returns:
            Tuple of (paragraph_text, word_offset_in_para, word_length) or None
        """
        para_idx = self._get_paragraph_index(position)
        if para_idx is None:
            return None

        para = self.paragraphs[para_idx]
        para_text = self.full_text[para.start:para.end].strip()

        # Calculate word offset within paragraph
        word_offset = position - para.start
        # Adjust for stripped whitespace at start
        leading_ws = len(self.full_text[para.start:para.end]) - len(self.full_text[para.start:para.end].lstrip())
        word_offset -= leading_ws

        return (para_text, max(0, word_offset), word_length)

    def get_paragraph_count(self) -> int:
        """F26: Get total number of paragraphs detected."""
        return len(self.paragraphs)
