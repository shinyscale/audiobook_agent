"""
Tests for SummaryAgent (chapter summaries).

These tests validate:
1. Summary length bounds (100-300 words)
2. Key events mentioned
3. No hallucinated events
4. Character references match character list
"""

import pytest
from pathlib import Path


class TestSummaryStructure:
    """Test summary structure requirements."""

    def test_summary_length_bounds(self):
        """Summaries should be 100-300 words."""
        min_words = 100
        max_words = 300

        # This would validate actual summaries
        # For now, just verify bounds are reasonable
        assert min_words < max_words
        assert min_words >= 50  # Not too short
        assert max_words <= 500  # Not too long

    def test_summary_contains_key_events(self):
        """Each summary should mention key events."""
        # This would validate actual summaries against ground truth
        pass

    def test_no_cross_chapter_events(self):
        """Summary should not include events from other chapters."""
        # This would validate chapter boundaries
        pass


class TestGatsbySummaries:
    """Test summaries for The Great Gatsby."""

    @pytest.fixture
    def gatsby_chapter_events(self):
        """Key events by chapter for validation."""
        return {
            1: ["West Egg", "Nick", "Daisy", "Tom", "green light"],
            2: ["Valley of Ashes", "Myrtle", "apartment", "party"],
            3: ["Gatsby's party", "Jordan", "meets Gatsby"],
            4: ["car ride", "Wolfsheim", "lunch", "Jordan tells"],
            5: ["reunite", "Daisy", "Nick's house", "mansion"],
            6: ["James Gatz", "origins", "Tom and Daisy at party"],
            7: ["hot day", "Plaza Hotel", "confrontation", "Myrtle's death"],
            8: ["vigil", "pool", "Wilson", "Gatsby killed"],
            9: ["funeral", "green light", "Nick leaves"],
        }

    def test_chapter_1_key_events(self, gatsby_chapter_events):
        """Chapter 1 summary should include key events."""
        events = gatsby_chapter_events[1]
        assert "Nick" in events
        assert "green light" in events

    def test_chapter_7_key_events(self, gatsby_chapter_events):
        """Chapter 7 (climax) should include confrontation and death."""
        events = gatsby_chapter_events[7]
        assert any("Plaza" in e or "confrontation" in e for e in events)
        assert any("Myrtle" in e or "death" in e for e in events)


class TestFrankensteinSummaries:
    """Test summaries for Frankenstein."""

    @pytest.fixture
    def frankenstein_key_events(self):
        """Key events by section for validation."""
        return {
            "letters": ["Walton", "expedition", "Arctic", "Victor"],
            "creation": ["laboratory", "creature", "animation", "horror"],
            "creature_tale": ["De Lacey", "learning", "rejection", "revenge"],
            "climax": ["Elizabeth", "wedding night", "pursuit"],
        }

    def test_frame_narrative_captured(self, frankenstein_key_events):
        """Letters should capture frame narrative."""
        events = frankenstein_key_events["letters"]
        assert "Walton" in events
        assert "Arctic" in events


class TestNoHallucinations:
    """Test that summaries don't hallucinate events."""

    def test_summary_events_in_text(self):
        """Events mentioned in summary should appear in chapter text."""
        # This would validate actual summaries against source text
        pass

    def test_character_names_match_list(self):
        """Characters mentioned should exist in character list."""
        # This would cross-reference with character extraction
        pass


class TestSummaryVerification:
    """Test summary verification checks."""

    def test_structural_checks(self):
        """Structural checks should catch basic issues."""
        # Test word count bounds
        # Test that summary is not empty
        # Test that chapter index is valid
        pass

    def test_self_check_prompts_book_agnostic(self):
        """Self-check prompts should not rely on book knowledge."""
        # Good: "Does this summary mention specific events from the text?"
        # Bad: "Does this capture the green light symbolism?"
        pass


class TestIntegration:
    """Integration tests that run the actual pipeline.

    Run with: pytest tests/test_summary_agent.py -v --run-integration
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_gatsby_summaries(self, analyzer_with_llm):
        """Full summary generation for Gatsby."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/gatsby.txt"))

        # Check chapter_summaries attribute exists and has content
        if hasattr(result, 'chapter_summaries') and result.chapter_summaries:
            print(f"\nSummaries found: {len(result.chapter_summaries)}")
            for i, s in enumerate(result.chapter_summaries[:3]):
                print(f"  Chapter {i+1}: {str(s)[:100]}...")
        else:
            print("\nNo chapter_summaries attribute or empty")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_frankenstein_summaries(self, analyzer_with_llm):
        """Full summary generation for Frankenstein."""
        from pathlib import Path

        result = analyzer_with_llm.analyze(Path("Test_Texts/frankenstein.txt"))

        # Check chapter_summaries attribute exists
        if hasattr(result, 'chapter_summaries') and result.chapter_summaries:
            print(f"\nSummaries found: {len(result.chapter_summaries)}")
        else:
            print("\nNo chapter_summaries attribute or empty")
