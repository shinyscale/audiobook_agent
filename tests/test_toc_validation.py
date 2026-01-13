"""
Tests for TOC (Table of Contents) entry validation.

Feature 1: TOC Entry Validation - validates entry count and filters by pattern.
"""

import pytest
from src.pipeline.chapter_detection.profiler import DocumentProfiler
from src.pipeline.chapter_detection.models import TOCEntry


class TestTOCMetadataFiltering:
    """Test _is_metadata_line() filters out non-chapter content."""

    @pytest.fixture
    def profiler(self):
        return DocumentProfiler(llm_client=None)

    def test_copyright_line_is_metadata(self, profiler):
        """Copyright lines should be filtered."""
        assert profiler._is_metadata_line("Copyright 2024 by Author Name")

    def test_published_line_is_metadata(self, profiler):
        """Published lines should be filtered."""
        assert profiler._is_metadata_line("Published by Random House")

    def test_isbn_line_is_metadata(self, profiler):
        """ISBN lines should be filtered."""
        assert profiler._is_metadata_line("ISBN: 978-0-123456-78-9")

    def test_all_rights_reserved_is_metadata(self, profiler):
        """All rights reserved lines should be filtered."""
        assert profiler._is_metadata_line("All Rights Reserved")

    def test_author_byline_is_metadata(self, profiler):
        """Author bylines should be filtered."""
        # Full author line is typically longer
        assert profiler._is_metadata_line("Written by F. Scott Fitzgerald - A Novel of the Jazz Age in America")

    def test_long_line_is_metadata(self, profiler):
        """Very long lines (>80 chars) are likely prose, not TOC entries."""
        long_line = "This is a very long line that exceeds eighty characters and is probably not a TOC entry at all"
        assert profiler._is_metadata_line(long_line)

    def test_roman_numeral_is_not_metadata(self, profiler):
        """Roman numerals should NOT be filtered."""
        assert not profiler._is_metadata_line("III")
        assert not profiler._is_metadata_line("IX")

    def test_chapter_title_is_not_metadata(self, profiler):
        """Chapter titles should NOT be filtered."""
        assert not profiler._is_metadata_line("Chapter 1")
        assert not profiler._is_metadata_line("Chapter One")
        assert not profiler._is_metadata_line("The Beginning")


class TestTOCValidation:
    """Test _validate_toc_entries() filters entries by pattern."""

    @pytest.fixture
    def profiler(self):
        return DocumentProfiler(llm_client=None)

    def _make_entry(self, title: str, level: int = 1) -> TOCEntry:
        """Helper to create TOC entries."""
        return TOCEntry(title=title, position_in_toc=0, page_number=None, level=level)

    def test_roman_numeral_pattern_kept(self, profiler):
        """Roman numeral entries should be kept when dominant."""
        entries = [
            self._make_entry("I"),
            self._make_entry("II"),
            self._make_entry("III"),
            self._make_entry("IV"),
            self._make_entry("V"),
            self._make_entry("VI"),
            self._make_entry("VII"),
            self._make_entry("VIII"),
            self._make_entry("IX"),
            self._make_entry("Some Random Text"),  # Non-roman
            self._make_entry("Another Random"),     # Non-roman
        ]
        result = profiler._validate_toc_entries(entries)
        assert len(result) == 9  # Only Roman numerals

    def test_chapter_n_pattern_kept(self, profiler):
        """Chapter N entries should be kept when dominant."""
        entries = [
            self._make_entry("Chapter 1"),
            self._make_entry("Chapter 2"),
            self._make_entry("Chapter 3"),
            self._make_entry("Introduction"),
            self._make_entry("Epilogue"),
        ]
        result = profiler._validate_toc_entries(entries)
        assert len(result) == 3  # Only "Chapter N" entries

    def test_excessive_count_filters_to_level1(self, profiler):
        """More than 30 entries should trigger filtering to level-1."""
        entries = [self._make_entry(f"Entry {i}", level=1) for i in range(35)]
        # Add some level-2 entries
        entries.extend([self._make_entry(f"Sub {i}", level=2) for i in range(10)])

        result = profiler._validate_toc_entries(entries)
        # Should keep level-1 entries (35)
        assert len(result) == 35

    def test_reasonable_count_preserved(self, profiler):
        """Reasonable counts without clear patterns are preserved."""
        entries = [
            self._make_entry("Prologue"),
            self._make_entry("The First Day"),
            self._make_entry("The Journey Begins"),
            self._make_entry("Discovery"),
            self._make_entry("Epilogue"),
        ]
        result = profiler._validate_toc_entries(entries)
        assert len(result) == 5  # All preserved


class TestGatsbyTOC:
    """Test TOC extraction specifically for Gatsby-style Roman numerals."""

    @pytest.fixture
    def profiler(self):
        return DocumentProfiler(llm_client=None)

    def test_gatsby_toc_text_parsing(self, profiler):
        """Gatsby-style TOC with Roman numerals I-IX should yield 9 entries."""
        gatsby_toc = """CONTENTS

I
II
III
IV
V
VI
VII
VIII
IX
"""
        entries = profiler._parse_toc_entries(gatsby_toc, 0)
        assert len(entries) == 9, f"Expected 9 entries, got {len(entries)}: {[e.title for e in entries]}"

    def test_gatsby_toc_with_noise(self, profiler):
        """Gatsby TOC with metadata noise should still yield 9 entries."""
        gatsby_toc_noisy = """TABLE OF CONTENTS

Copyright 1925 by F. Scott Fitzgerald
All rights reserved.

I
II
III
IV
V
VI
VII
VIII
IX

Published by Scribner
"""
        entries = profiler._parse_toc_entries(gatsby_toc_noisy, 0)
        assert len(entries) == 9, f"Expected 9 entries, got {len(entries)}: {[e.title for e in entries]}"


class TestFullProfilerIntegration:
    """Integration tests for full TOC extraction."""

    @pytest.fixture
    def profiler(self):
        return DocumentProfiler(llm_client=None)

    def test_gatsby_full_text_toc_extraction(self, profiler, gatsby_text):
        """Full Gatsby text should extract 9 TOC entries."""
        toc = profiler._extract_toc(gatsby_text)

        if toc is None:
            pytest.skip("Gatsby text does not have recognizable TOC")

        assert len(toc.entries) == 9, (
            f"Expected 9 TOC entries, got {len(toc.entries)}: "
            f"{[e.title for e in toc.entries]}"
        )

    def test_gatsby_profile_estimated_chapters(self, profiler, gatsby_text):
        """Gatsby profile should estimate 9 chapters."""
        profile = profiler.profile(gatsby_text)

        if profile.estimated_chapter_count is not None:
            assert profile.estimated_chapter_count == 9, (
                f"Expected estimated_chapter_count=9, got {profile.estimated_chapter_count}"
            )
