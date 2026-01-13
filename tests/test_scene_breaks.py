"""Tests for scene break detection utility."""

import pytest

from src.pipeline.chapter_detection.scene_breaks import (
    find_scene_breaks,
    get_scene_break_line_numbers,
    get_scene_break_positions,
    is_near_scene_break,
)


class TestFindSceneBreaks:
    """Test scene break pattern detection."""

    def test_detects_dashes(self):
        """Scene breaks with dashes are detected."""
        text = """Some text here.

------------------------------------------------------------------------

More text after the break."""
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1
        assert text[breaks[0][0] : breaks[0][1]].strip() == "-" * 72

    def test_detects_short_dashes(self):
        """Short dash sequences (3+) are detected."""
        text = "Before\n---\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_detects_asterisks(self):
        """Scene breaks with asterisks are detected."""
        text = "Before\n***\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_detects_spaced_asterisks(self):
        """Spaced asterisks (* * *) are detected."""
        text = "Before\n* * *\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_detects_equals(self):
        """Scene breaks with equals signs are detected."""
        text = "Before\n===\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_detects_tildes(self):
        """Scene breaks with tildes are detected."""
        text = "Before\n~~~\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_detects_dots(self):
        """Scene breaks with dots are detected."""
        text = "Before\n....\nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_multiple_breaks(self):
        """Multiple scene breaks are all detected."""
        text = """Chapter content.

--------

Scene 2 content.

* * *

Scene 3 content.

===

Scene 4 content."""
        breaks = find_scene_breaks(text)
        assert len(breaks) == 3

    def test_no_false_positives_on_regular_text(self):
        """Normal text without scene breaks returns empty list."""
        text = """This is a normal paragraph with no scene breaks.

It has multiple paragraphs but uses standard formatting.

No special characters that look like scene breaks."""
        breaks = find_scene_breaks(text)
        assert len(breaks) == 0

    def test_no_false_positives_on_short_punctuation(self):
        """Short punctuation sequences are not detected."""
        text = "He said -- and I quote -- it was fine."
        breaks = find_scene_breaks(text)
        # This should NOT be detected (not on its own line)
        assert len(breaks) == 0

    def test_centered_with_whitespace(self):
        """Scene breaks centered with whitespace are detected."""
        text = "Before\n     --------     \nAfter"
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1


class TestIsNearSceneBreak:
    """Test position proximity checking."""

    def test_position_at_scene_break(self):
        """Position at scene break start is considered near."""
        scene_breaks = [(100, 150)]
        assert is_near_scene_break(100, scene_breaks)

    def test_position_just_before(self):
        """Position just before scene break is considered near."""
        scene_breaks = [(100, 150)]
        assert is_near_scene_break(50, scene_breaks, threshold=100)

    def test_position_just_after(self):
        """Position just after scene break is considered near."""
        scene_breaks = [(100, 150)]
        assert is_near_scene_break(200, scene_breaks, threshold=100)

    def test_position_far_away(self):
        """Position far from scene break is not considered near."""
        scene_breaks = [(100, 150)]
        assert not is_near_scene_break(500, scene_breaks, threshold=100)

    def test_custom_threshold(self):
        """Custom threshold works correctly."""
        scene_breaks = [(100, 150)]
        # Position 80 is 20 chars from start (100)
        assert is_near_scene_break(80, scene_breaks, threshold=50)
        assert not is_near_scene_break(80, scene_breaks, threshold=10)

    def test_empty_scene_breaks(self):
        """Empty scene breaks list returns False."""
        assert not is_near_scene_break(100, [])

    def test_multiple_scene_breaks(self):
        """Near any scene break returns True."""
        scene_breaks = [(100, 150), (500, 550), (1000, 1050)]
        assert is_near_scene_break(120, scene_breaks)
        assert is_near_scene_break(520, scene_breaks)
        assert is_near_scene_break(980, scene_breaks)
        assert not is_near_scene_break(300, scene_breaks)


class TestGetSceneBreakPositions:
    """Test convenience function for getting positions."""

    def test_returns_start_positions(self):
        """Returns list of start positions only."""
        text = "Before\n---\nMiddle\n***\nAfter"
        positions = get_scene_break_positions(text)
        assert len(positions) == 2
        # All positions should be integers
        assert all(isinstance(p, int) for p in positions)

    def test_empty_text(self):
        """Empty text returns empty list."""
        positions = get_scene_break_positions("")
        assert positions == []


class TestGetSceneBreakLineNumbers:
    """Test line number extraction."""

    def test_returns_line_numbers(self):
        """Returns correct 1-indexed line numbers."""
        text = """Line 1
Line 2
---
Line 4"""
        line_nums = get_scene_break_line_numbers(text)
        assert line_nums == [3]

    def test_multiple_breaks(self):
        """Returns line numbers for all breaks."""
        text = """Line 1
---
Line 3
***
Line 5"""
        line_nums = get_scene_break_line_numbers(text)
        assert line_nums == [2, 4]


class TestGatsbySceneBreaks:
    """Test with patterns found in The Great Gatsby."""

    def test_gatsby_style_dashes(self):
        """Long dash lines like in Gatsby are detected."""
        # Gatsby uses 72 dashes
        gatsby_break = "-" * 72
        text = f"Some text.\n\n{gatsby_break}\n\nMore text."
        breaks = find_scene_breaks(text)
        assert len(breaks) == 1

    def test_gatsby_multiple_breaks(self):
        """Multiple Gatsby-style breaks are all detected."""
        gatsby_break = "-" * 72
        text = f"""Chapter I content.

{gatsby_break}

Scene 2 content.

{gatsby_break}

Scene 3 content."""
        breaks = find_scene_breaks(text)
        assert len(breaks) == 2


class TestConsensusIntegration:
    """Test integration with ConsensusBuilder filtering."""

    def _make_validation_result(
        self, position: int, title: str, confidence: float, strategy: str, evidence: str
    ):
        """Helper to create ValidationResult with all required fields."""
        from src.pipeline.chapter_detection.models import (
            ChapterProposal,
            ValidationResult,
        )

        return ValidationResult(
            proposal=ChapterProposal(
                position=position,
                title=title,
                confidence=confidence,
                strategy=strategy,
                evidence=evidence,
            ),
            ending_score=0.8,
            beginning_score=0.8,
            title_validity=0.9,
            toc_match_score=0.0,
            overall_score=confidence,
            is_valid=True,
            reasoning="Test proposal",
        )

    def _make_profile(self, text: str):
        """Helper to create DocumentProfile with all required fields."""
        from src.pipeline.chapter_detection.models import DocumentProfile

        return DocumentProfile(
            document_type="novel",
            has_explicit_markers=True,
            table_of_contents=None,
            estimated_chapter_count=None,
            structural_conventions=["roman_numerals"],
            front_matter_end=0,
            confidence=0.9,
            reasoning="Test profile",
        )

    def test_filters_proposals_near_scene_breaks(self):
        """Proposals near scene breaks are filtered out by consensus builder."""
        from src.pipeline.chapter_detection.consensus import ConsensusBuilder

        # Create text with a scene break - needs to be long enough to pass size validation
        gatsby_break = "-" * 72
        filler = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50

        text = f"""
                                I

Chapter one content here. This is the beginning of the novel.
{filler}

{gatsby_break}

Still chapter one after scene break.
{filler}

                                II

Chapter two content here. A new chapter begins.
{filler}
"""

        # Find the actual positions of markers
        chapter1_pos = text.find("I\n\nChapter")
        scene_break_pos = text.find(gatsby_break)
        chapter2_pos = text.find("II\n\nChapter")

        # Create proposals - one at a real chapter, one at scene break
        proposals = [
            self._make_validation_result(chapter1_pos, "I", 0.9, "regex", "Roman numeral I"),
            self._make_validation_result(scene_break_pos, None, 0.7, "llm_marker", "Dash line"),
            self._make_validation_result(chapter2_pos, "II", 0.9, "regex", "Roman numeral II"),
        ]

        profile = self._make_profile(text)
        builder = ConsensusBuilder(llm_client=None)
        result = builder.build_consensus(proposals, text, profile)

        # Should have 2 chapters (I and II), not 3 (scene break filtered)
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "I"
        assert result.chapters[1].title == "II"

    def test_no_filtering_without_scene_breaks(self):
        """Text without scene breaks doesn't filter any proposals."""
        from src.pipeline.chapter_detection.consensus import ConsensusBuilder

        # Create text without scene breaks - needs to be long enough to pass size validation
        filler = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50

        text = f"""
                                I

Chapter one content here. This is the beginning of the novel.
{filler}

                                II

Chapter two content here. A new chapter begins.
{filler}

                                III

Chapter three content here.
{filler}
"""

        # Find the actual positions of markers
        chapter1_pos = text.find("I\n\nChapter one")
        chapter2_pos = text.find("II\n\nChapter two")
        chapter3_pos = text.find("III\n\nChapter three")

        # Create proposals for all three chapters
        proposals = [
            self._make_validation_result(chapter1_pos, "I", 0.9, "regex", "Roman numeral I"),
            self._make_validation_result(chapter2_pos, "II", 0.9, "regex", "Roman numeral II"),
            self._make_validation_result(chapter3_pos, "III", 0.9, "regex", "Roman numeral III"),
        ]

        profile = self._make_profile(text)
        builder = ConsensusBuilder(llm_client=None)
        result = builder.build_consensus(proposals, text, profile)

        # All 3 chapters should be preserved
        assert len(result.chapters) == 3


class TestGatsbyChapterDetection:
    """Test that Gatsby's scene breaks don't interfere with chapter detection."""

    def test_gatsby_chapter_markers_not_near_scene_breaks(self):
        """Verify Gatsby's 9 chapter markers are not near any scene breaks."""
        import re
        from pathlib import Path

        gatsby_path = Path("Test_Texts/gatsby.txt")
        if not gatsby_path.exists():
            pytest.skip("gatsby.txt not found in Test_Texts/")

        with open(gatsby_path, "r") as f:
            text = f.read()
            lines = text.splitlines()

        # Find the 9 chapter markers (centered Roman numerals)
        roman_pattern = re.compile(r"^\s+([IVXLC]+)\s*$")
        chapter_positions = []
        current_pos = 0

        for i, line in enumerate(lines, 1):
            if roman_pattern.match(line):
                chapter_positions.append((current_pos, line.strip()))
            current_pos += len(line) + 1

        # Should find exactly 9 chapters
        assert len(chapter_positions) == 9, f"Expected 9 chapters, found {len(chapter_positions)}"

        # Verify expected titles
        expected_titles = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
        actual_titles = [title for _, title in chapter_positions]
        assert actual_titles == expected_titles

        # Check none are near scene breaks
        scene_breaks = find_scene_breaks(text)
        assert len(scene_breaks) > 0, "Should find scene breaks in Gatsby"

        for char_pos, title in chapter_positions:
            is_near = is_near_scene_break(char_pos, scene_breaks, threshold=100)
            assert not is_near, f"Chapter {title} at {char_pos} should not be near scene break"

    def test_gatsby_scene_breaks_count(self):
        """Verify we detect the expected number of scene breaks in Gatsby."""
        from pathlib import Path

        gatsby_path = Path("Test_Texts/gatsby.txt")
        if not gatsby_path.exists():
            pytest.skip("gatsby.txt not found in Test_Texts/")

        with open(gatsby_path, "r") as f:
            text = f.read()

        scene_breaks = find_scene_breaks(text)

        # The PRD mentions 25 scene break lines
        assert len(scene_breaks) == 25, f"Expected 25 scene breaks, found {len(scene_breaks)}"


class TestSceneBreakAwareSummarization:
    """Test scene break-aware chunking in the summarizer."""

    def test_splits_by_scene_breaks(self):
        """Summarizer splits text at scene breaks."""
        from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
        from unittest.mock import MagicMock

        # Create a mock LLM client
        mock_llm = MagicMock()

        summarizer = ChapterSummarizer(llm_client=mock_llm, chunk_size=100)

        # Create text with scene breaks
        gatsby_break = "-" * 72
        text = f"""Scene one content. This is the first scene with some narrative text.
More content in scene one. Characters are introduced and the story begins.

{gatsby_break}

Scene two content. The story continues after the scene break.
New events happen and the plot develops further.

{gatsby_break}

Scene three content. The final scene of this chapter.
Resolution and conclusion of the chapter's events."""

        chunks = summarizer._split_into_chunks(text)

        # Should have 3 chunks (one per scene)
        assert len(chunks) == 3
        assert "Scene one content" in chunks[0]
        assert "Scene two content" in chunks[1]
        assert "Scene three content" in chunks[2]

        # Scene break markers should not appear in chunks
        for chunk in chunks:
            assert "---" not in chunk

    def test_falls_back_to_word_count_without_scene_breaks(self):
        """Without scene breaks, falls back to word count chunking."""
        from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        summarizer = ChapterSummarizer(llm_client=mock_llm, chunk_size=50)

        # Create text without scene breaks that's long enough to need chunking
        text = "This is a sentence. " * 100  # 500 words

        chunks = summarizer._split_into_chunks(text)

        # Should have multiple chunks based on word count
        assert len(chunks) > 1
        # Each chunk should have approximately chunk_size words
        # Allow for overlap (200 words default) and sentence boundary alignment
        for chunk in chunks:
            word_count = len(chunk.split())
            # With overlap and sentence boundary, chunks can exceed target size
            assert word_count <= 300  # chunk_size + overlap + buffer

    def test_long_scenes_are_further_chunked(self):
        """Very long scenes are further chunked by word count."""
        from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        summarizer = ChapterSummarizer(llm_client=mock_llm, chunk_size=50)

        # Create text with one short scene and one very long scene
        gatsby_break = "-" * 72
        short_scene = "Short scene content. Just a few words here."
        long_scene = "This is a long sentence. " * 100  # 500 words

        text = f"""{short_scene}

{gatsby_break}

{long_scene}"""

        chunks = summarizer._split_into_chunks(text)

        # Should have more than 2 chunks because long scene gets subdivided
        assert len(chunks) > 2

        # First chunk should be the short scene
        assert "Short scene" in chunks[0]

    def test_empty_scenes_are_skipped(self):
        """Empty content between scene breaks is skipped."""
        from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        summarizer = ChapterSummarizer(llm_client=mock_llm, chunk_size=100)

        # Create text with empty section between breaks
        gatsby_break = "-" * 72
        text = f"""Scene one content here.

{gatsby_break}

{gatsby_break}

Scene two after empty section."""

        chunks = summarizer._split_into_chunks(text)

        # Should have 2 chunks (empty section skipped)
        assert len(chunks) == 2
        assert "Scene one" in chunks[0]
        assert "Scene two" in chunks[1]
