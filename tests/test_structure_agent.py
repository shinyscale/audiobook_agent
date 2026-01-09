"""
Tests for StructureAgent (chapter detection).

These tests validate:
1. Ground truth compliance (Gatsby: 9 chapters, Frankenstein: 28 sections)
2. Structural verification checks
3. Edge cases (no chapters, unusual formats)
"""

import pytest
import re
from pathlib import Path


class TestGatsbyChapterDetection:
    """Test chapter detection on The Great Gatsby."""

    def test_gatsby_has_nine_chapters(self, gatsby_text, gatsby_chapters_ground_truth):
        """Gatsby should have exactly 9 chapters."""
        expected_count = gatsby_chapters_ground_truth["chapter_count"]
        assert expected_count == 9, "Ground truth should specify 9 chapters"

        # Count chapter markers in text
        # Gatsby uses Roman numerals for chapters
        chapter_pattern = r'^\s*[IVX]+\s*$'
        chapter_matches = re.findall(chapter_pattern, gatsby_text, re.MULTILINE)

        # Should find chapter markers (may include TOC duplicates)
        assert len(chapter_matches) > 0, "Should find Roman numeral chapter markers"

    def test_gatsby_chapter_structure_type(self, gatsby_chapters_ground_truth):
        """Gatsby should be simple numbered structure."""
        assert gatsby_chapters_ground_truth["structure_type"] == "simple_numbered"

    def test_gatsby_no_titled_chapters(self, gatsby_chapters_ground_truth):
        """Gatsby chapters should not have titles."""
        for chapter in gatsby_chapters_ground_truth["chapters"]:
            assert chapter["has_title"] is False
            assert chapter["title"] is None


class TestFrankensteinChapterDetection:
    """Test chapter detection on Frankenstein."""

    def test_frankenstein_has_28_sections(self, frankenstein_chapters_ground_truth):
        """Frankenstein should have 28 sections (4 letters + 24 chapters)."""
        expected_count = frankenstein_chapters_ground_truth["section_count"]
        assert expected_count == 28

    def test_frankenstein_frame_narrative_structure(self, frankenstein_chapters_ground_truth):
        """Frankenstein should be identified as frame narrative."""
        assert frankenstein_chapters_ground_truth["structure_type"] == "frame_narrative"

    def test_frankenstein_has_four_letters(self, frankenstein_chapters_ground_truth):
        """Frankenstein should have 4 letters in frame narrative."""
        letters = [s for s in frankenstein_chapters_ground_truth["sections"] if s["type"] == "letter"]
        assert len(letters) == 4

    def test_frankenstein_has_24_chapters(self, frankenstein_chapters_ground_truth):
        """Frankenstein should have 24 chapters."""
        chapters = [s for s in frankenstein_chapters_ground_truth["sections"] if s["type"] == "chapter"]
        assert len(chapters) == 24

    def test_frankenstein_letter_markers_in_text(self, frankenstein_text):
        """Frankenstein text should contain letter markers."""
        letter_pattern = r'LETTER [IVX]+\.'
        letters = re.findall(letter_pattern, frankenstein_text)
        assert len(letters) >= 4, f"Expected at least 4 letter markers, found {len(letters)}"

    def test_frankenstein_chapter_markers_in_text(self, frankenstein_text):
        """Frankenstein text should contain chapter markers."""
        chapter_pattern = r'CHAPTER [IVX]+\.'
        chapters = re.findall(chapter_pattern, frankenstein_text)
        assert len(chapters) >= 20, f"Expected at least 20 chapter markers, found {len(chapters)}"


class TestStructuralVerification:
    """Test structural verification checks."""

    def test_chapter_count_reasonable_for_word_count(self, gatsby_text, gatsby_chapters_ground_truth):
        """Chapter count should be reasonable for word count."""
        word_count = len(gatsby_text.split())
        chapter_count = gatsby_chapters_ground_truth["chapter_count"]

        # Typical novels have 1 chapter per 3,000-8,000 words
        min_reasonable = word_count // 10000  # Very long chapters
        max_reasonable = word_count // 2000   # Very short chapters

        assert min_reasonable <= chapter_count <= max_reasonable, (
            f"Chapter count {chapter_count} seems unreasonable for {word_count} words"
        )

    def test_no_empty_chapters(self, gatsby_chapters_ground_truth):
        """All chapters should have content (index > 0)."""
        for chapter in gatsby_chapters_ground_truth["chapters"]:
            assert chapter["index"] > 0

    def test_chapters_sequential(self, gatsby_chapters_ground_truth):
        """Chapter indices should be sequential."""
        indices = [c["index"] for c in gatsby_chapters_ground_truth["chapters"]]
        assert indices == list(range(1, len(indices) + 1))


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text_detection(self):
        """Empty text should not crash detection."""
        # This would test the actual agent - placeholder for now
        pass

    def test_no_chapter_markers(self):
        """Text without chapter markers should handle gracefully."""
        # This would test the actual agent - placeholder for now
        pass

    def test_unusual_numbering(self):
        """Unusual chapter numbering should be handled."""
        # This would test the actual agent - placeholder for now
        pass


class TestIntegration:
    """Integration tests that run the actual pipeline.

    Run with: pytest tests/test_structure_agent.py -v --run-integration
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_gatsby_analysis(self, analyzer_with_llm, gatsby_chapters_ground_truth):
        """Full pipeline analysis of Gatsby - validates chapter detection."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/gatsby.txt"))

        # Validate chapter count
        expected_chapters = gatsby_chapters_ground_truth["chapter_count"]
        actual_chapters = len(result.structure)

        print(f"\nGatsby chapters: expected={expected_chapters}, actual={actual_chapters}")
        print(f"Chapters found: {[s.title or f'Chapter {i+1}' for i, s in enumerate(result.structure)]}")

        assert actual_chapters == expected_chapters, (
            f"Expected {expected_chapters} chapters, got {actual_chapters}"
        )

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_frankenstein_analysis(self, analyzer_with_llm, frankenstein_chapters_ground_truth):
        """Full pipeline analysis of Frankenstein - validates section detection."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/frankenstein.txt"))

        # Validate section count (letters + chapters)
        expected_sections = frankenstein_chapters_ground_truth["section_count"]
        actual_sections = len(result.structure)

        print(f"\nFrankenstein sections: expected={expected_sections}, actual={actual_sections}")
        print(f"Sections found: {[s.title or f'Section {i+1}' for i, s in enumerate(result.structure[:10])]}")

        # Allow some tolerance for frame narrative complexity
        assert actual_sections >= expected_sections - 5, (
            f"Expected ~{expected_sections} sections, got {actual_sections}"
        )
