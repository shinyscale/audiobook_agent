"""
Tests for the character profiling pipeline.

Tests the summary-driven character identification and profiling.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.pipeline.character_profiling import (
    SummaryDrivenCharacterIdentifier,
    CharacterProfilingPipeline,
    IdentifiedCharacter,
    CharacterProfile,
)
from src.pipeline.character_profiling.models import (
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterProfileMap,
)
from src.pipeline.chapter_summary.models import ChapterSummary, ChapterSummaryMap
from src.pipeline.llm import LLMResponse


# Sample chapter summaries simulating The Great Gatsby
GATSBY_SUMMARIES = [
    ChapterSummary(
        chapter_index=1,
        chapter_title="Chapter 1",
        summary="Nick Carraway, the narrator, moves to West Egg and visits his cousin Daisy Buchanan and her husband Tom. He learns about their troubled marriage and meets Jordan Baker.",
        key_events=["Nick arrives in West Egg", "Visits the Buchanans", "Meets Jordan Baker"],
        primary_tone="reflective",
        secondary_tones=["mysterious"],
        dialogue_density="medium",
        characters_present=["Nick Carraway", "Daisy Buchanan", "Tom Buchanan", "Jordan Baker"],
        pov_character="Nick Carraway",
        word_count=5000,
        estimated_duration_minutes=33,
        confidence=0.9,
    ),
    ChapterSummary(
        chapter_index=2,
        chapter_title="Chapter 2",
        summary="Tom takes Nick to meet his mistress Myrtle Wilson in the Valley of Ashes. They attend a party at Myrtle's apartment where Tom breaks her nose.",
        key_events=["Visit to Valley of Ashes", "Meet Myrtle Wilson", "Party at apartment"],
        primary_tone="dark",
        secondary_tones=["dramatic"],
        dialogue_density="high",
        characters_present=["Nick Carraway", "Tom Buchanan", "Myrtle Wilson", "George Wilson"],
        pov_character="Nick Carraway",
        word_count=4500,
        estimated_duration_minutes=30,
        confidence=0.9,
    ),
    ChapterSummary(
        chapter_index=3,
        chapter_title="Chapter 3",
        summary="Nick attends one of Jay Gatsby's lavish parties and finally meets the mysterious host. Gatsby's smile is remarkable and reassuring.",
        key_events=["Gatsby's party", "Nick meets Gatsby", "Gatsby's mysterious past discussed"],
        primary_tone="mysterious",
        secondary_tones=["hopeful"],
        dialogue_density="high",
        characters_present=["Nick Carraway", "Jay Gatsby", "Jordan Baker"],
        pov_character="Nick Carraway",
        word_count=5500,
        estimated_duration_minutes=37,
        confidence=0.9,
    ),
    ChapterSummary(
        chapter_index=4,
        chapter_title="Chapter 4",
        summary="Gatsby reveals his past to Nick, including his real name James Gatz and his humble origins. Jordan tells Nick about Gatsby's history with Daisy.",
        key_events=["Gatsby's backstory", "James Gatz revealed", "Gatsby and Daisy's history"],
        primary_tone="reflective",
        secondary_tones=["romantic"],
        dialogue_density="medium",
        characters_present=["Nick Carraway", "Jay Gatsby", "Jordan Baker"],
        pov_character="Nick Carraway",
        word_count=6000,
        estimated_duration_minutes=40,
        confidence=0.9,
    ),
]

GATSBY_PLOT_SUMMARY = """The story unfolds through the eyes of Nick Carraway, a young Midwesterner who moves to West Egg
and becomes entangled in the lives of his enigmatic neighbor, Jay Gatsby, and his cousin Daisy Buchanan.
Gatsby, a self-made millionaire known for his lavish parties, is revealed to be deeply in love with Daisy,
whom he met years earlier as a young officer named James Gatz. His entire fortune is built around the dream
of rekindling their lost romance. Tom Buchanan's affair with Myrtle Wilson, the wife of garage owner George Wilson,
creates a parallel storyline of betrayal. The tragic climax involves Myrtle's death and Gatsby's murder by the grieving George Wilson."""


class TestIdentifiedCharacterModel:
    """Tests for IdentifiedCharacter data model."""

    def test_create_basic(self):
        char = IdentifiedCharacter(
            canonical_name="Jay Gatsby",
            aliases=["Mr. Gatsby", "James Gatz"],
            role="protagonist",
        )
        assert char.canonical_name == "Jay Gatsby"
        assert "James Gatz" in char.aliases
        assert char.role == "protagonist"
        assert char.is_narrator is False

    def test_to_dict_roundtrip(self):
        char = IdentifiedCharacter(
            canonical_name="Nick Carraway",
            aliases=["Mr. Carraway"],
            role="protagonist",
            is_narrator=True,
            narrative_role="First-person narrator",
            chapters_present=[1, 2, 3, 4],
        )
        data = char.to_dict()
        restored = IdentifiedCharacter.from_dict(data)
        assert restored.canonical_name == char.canonical_name
        assert restored.is_narrator == char.is_narrator
        assert restored.narrative_role == char.narrative_role


class TestCharacterProfileModel:
    """Tests for CharacterProfile data model."""

    def test_from_identified(self):
        identified = IdentifiedCharacter(
            canonical_name="Jay Gatsby",
            aliases=["Mr. Gatsby"],
            role="protagonist",
            chapters_present=[3, 4, 5],
        )
        profile = CharacterProfile.from_identified(identified)
        assert profile.canonical_name == "Jay Gatsby"
        assert profile.role == "protagonist"
        assert "char_" in profile.id

    def test_to_dict_structure(self):
        profile = CharacterProfile(
            id="char_test_123",
            canonical_name="Test Character",
            aliases=["Test"],
            role="supporting",
            appearance=AppearanceProfile(
                summary="A tall figure",
                age_indication="middle-aged",
            ),
            personality=PersonalityProfile(
                summary="Quiet and reserved",
                traits=["introverted", "thoughtful"],
            ),
            voice_guidance=VoiceGuidance(
                suggested_tone="soft-spoken",
                verbal_tics=["hmm"],
            ),
        )
        data = profile.to_dict()
        assert "appearance" in data
        assert "personality" in data
        assert "voice_guidance" in data
        assert data["appearance"]["summary"] == "A tall figure"


class TestCharacterProfileMap:
    """Tests for CharacterProfileMap."""

    def test_get_profile_by_name(self):
        profiles = [
            CharacterProfile(
                id="char_gatsby",
                canonical_name="Jay Gatsby",
                aliases=["Mr. Gatsby", "James Gatz"],
            ),
            CharacterProfile(
                id="char_nick",
                canonical_name="Nick Carraway",
                aliases=["Mr. Carraway"],
            ),
        ]
        profile_map = CharacterProfileMap(
            profiles=profiles,
            narrator_name="Nick Carraway",
            total_characters=2,
        )

        # Find by canonical name
        gatsby = profile_map.get_profile("Jay Gatsby")
        assert gatsby is not None
        assert gatsby.canonical_name == "Jay Gatsby"

        # Find by alias
        gatsby_by_alias = profile_map.get_profile("James Gatz")
        assert gatsby_by_alias is not None
        assert gatsby_by_alias.canonical_name == "Jay Gatsby"

        # Case insensitive
        nick = profile_map.get_profile("nick carraway")
        assert nick is not None


class TestSummaryDrivenCharacterIdentifier:
    """Tests for the character identifier."""

    def test_identify_characters_parses_response(self):
        """Test that identifier correctly parses LLM response."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "characters": [
                    {
                        "canonical_name": "Jay Gatsby",
                        "aliases": ["Mr. Gatsby", "James Gatz"],
                        "role": "protagonist",
                        "chapters_present": [3, 4, 5],
                        "brief_description": "A mysterious millionaire",
                    },
                    {
                        "canonical_name": "Nick Carraway",
                        "aliases": ["Mr. Carraway"],
                        "role": "protagonist",
                        "chapters_present": [1, 2, 3, 4],
                        "brief_description": "The narrator",
                    },
                ],
                "narrator": {
                    "name": "Nick Carraway",
                    "narrative_style": "first-person",
                    "role": "First-person narrator",
                },
            },
            LLMResponse(content="...", model="test", error=None),
        )

        identifier = SummaryDrivenCharacterIdentifier(mock_llm)
        characters, narrator, style = identifier.identify_characters(
            GATSBY_SUMMARIES[:2],
            GATSBY_PLOT_SUMMARY,
        )

        assert len(characters) == 2
        assert any(c.canonical_name == "Jay Gatsby" for c in characters)
        assert narrator == "Nick Carraway"
        assert style == "first-person"

        # Check narrator flag is set
        nick = next(c for c in characters if c.canonical_name == "Nick Carraway")
        assert nick.is_narrator is True

    def test_birth_name_unification(self):
        """Test that birth name and assumed name are unified."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "characters": [
                    {
                        "canonical_name": "Jay Gatsby",
                        "aliases": ["Mr. Gatsby", "James Gatz", "Mr. Gatz"],
                        "role": "protagonist",
                        "chapters_present": [3, 4, 5, 6, 7, 8, 9],
                        "brief_description": "Born James Gatz, reinvented himself as Jay Gatsby",
                    },
                ],
                "narrator": None,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        identifier = SummaryDrivenCharacterIdentifier(mock_llm)
        characters, _, _ = identifier.identify_characters(
            GATSBY_SUMMARIES,
            GATSBY_PLOT_SUMMARY,
        )

        # Should be ONE character with both names
        gatsby_chars = [c for c in characters if "Gatsby" in c.canonical_name or "Gatz" in c.canonical_name]
        assert len(gatsby_chars) == 1
        assert "James Gatz" in gatsby_chars[0].aliases

    def test_family_members_kept_separate(self):
        """Test that family members with same last name are kept separate."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "characters": [
                    {
                        "canonical_name": "George Wilson",
                        "aliases": ["Mr. Wilson", "Wilson"],
                        "role": "supporting",
                        "chapters_present": [2, 7, 8],
                        "brief_description": "Garage owner, Myrtle's husband",
                    },
                    {
                        "canonical_name": "Myrtle Wilson",
                        "aliases": ["Mrs. Wilson", "Myrtle"],
                        "role": "supporting",
                        "chapters_present": [2, 7],
                        "brief_description": "George's wife, Tom's mistress",
                    },
                ],
                "narrator": None,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        identifier = SummaryDrivenCharacterIdentifier(mock_llm)
        characters, _, _ = identifier.identify_characters(
            GATSBY_SUMMARIES,
            GATSBY_PLOT_SUMMARY,
        )

        # Should be TWO separate characters
        wilson_chars = [c for c in characters if "Wilson" in c.canonical_name]
        assert len(wilson_chars) == 2

        george = next(c for c in wilson_chars if "George" in c.canonical_name)
        myrtle = next(c for c in wilson_chars if "Myrtle" in c.canonical_name)
        assert george.canonical_name != myrtle.canonical_name

    def test_fallback_extraction_on_llm_failure(self):
        """Test fallback extraction when LLM fails."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            None,
            LLMResponse(content="", model="test", error="LLM failed"),
        )

        identifier = SummaryDrivenCharacterIdentifier(mock_llm)
        characters, narrator, style = identifier.identify_characters(
            GATSBY_SUMMARIES[:2],
            GATSBY_PLOT_SUMMARY,
        )

        # Should still get characters from summaries
        assert len(characters) > 0
        # Characters from summaries: Nick, Daisy, Tom, Jordan, Myrtle, George
        char_names = {c.canonical_name for c in characters}
        assert "Nick Carraway" in char_names or any("Nick" in n for n in char_names)


class TestCharacterProfilingPipeline:
    """Tests for the full pipeline."""

    def test_pipeline_runs_identification(self):
        """Test that pipeline runs identification stage."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "characters": [
                    {
                        "canonical_name": "Test Character",
                        "aliases": [],
                        "role": "protagonist",
                        "chapters_present": [1],
                        "brief_description": "A test character",
                    },
                ],
                "narrator": None,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        summary_map = ChapterSummaryMap(
            summaries=GATSBY_SUMMARIES[:1],
            total_chapters=1,
            total_word_count=5000,
            total_duration_minutes=33,
            overall_tones={"reflective": 1},
            character_appearances={"Nick Carraway": [1]},
        )

        pipeline = CharacterProfilingPipeline(llm_client=mock_llm)
        result = pipeline.run(
            full_text="Sample text",
            chapter_map=Mock(),
            summary_map=summary_map,
            plot_summary="Sample plot",
        )

        assert isinstance(result, CharacterProfileMap)
        assert len(result.profiles) == 1
        assert result.profiles[0].canonical_name == "Test Character"


# Integration test marker - requires actual LLM
@pytest.mark.skip(reason="Integration test - requires LLM")
class TestCharacterProfilingIntegration:
    """Integration tests with actual LLM."""

    def test_gatsby_character_identification(self):
        """Test full identification on Gatsby summaries."""
        # This would be run with an actual LLM
        pass
