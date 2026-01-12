"""
Tests for the character profiling pipeline.

Tests the summary-driven character identification and profiling.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.pipeline.character_profiling import (
    SummaryDrivenCharacterIdentifier,
    CharacterProfilingPipeline,
    CharacterProfileGenerator,
    CharacterPassageGatherer,
    CharacterPassage,
    NarratorDetector,
    NarratorInfo,
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
from src.pipeline.chapter_detection.models import ChapterMap, Chapter
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


# Sample text for testing passage gathering
SAMPLE_TEXT = """Chapter 1

Nick Carraway moved to West Egg in the summer of 1922. He was a young man from
the Midwest, tall and thin with an earnest expression. His cousin Daisy Buchanan
lived across the bay in East Egg with her husband Tom.

Tom Buchanan was a hulking man with a cruel body. His eyes were arrogant and he
spoke with a commanding voice. "I've got a nice place here," Tom said, gesturing
at his mansion.

Daisy Buchanan was beautiful with a voice full of money. She had bright eyes and
a passionate mouth. "I'm paralyzed with happiness," Daisy whispered dramatically.

Chapter 2

In the Valley of Ashes, George Wilson ran a garage. He was a spiritless man,
anemic and faintly handsome. His wife Myrtle Wilson was thickish but had vitality.

Tom's mistress Myrtle Wilson changed her costume three times that afternoon.
"I married him because I thought he was a gentleman," Myrtle said about George.

Chapter 3

Jay Gatsby threw magnificent parties at his mansion. He was an elegant young man
with a rare smile. "I'm Gatsby," he said with an extraordinary smile.
"Old sport, I understand you're looking for me."

Nick noticed that Gatsby chose his words with care. He spoke formally, almost
rehearsed. "Old sport" was his constant phrase, used with everyone he met.
"""


class TestCharacterPassageGatherer:
    """Tests for the passage gatherer."""

    def test_gather_passages_finds_mentions(self):
        """Test that gatherer finds passages containing character name."""
        chapters = [
            Chapter(index=1, title="Chapter 1", start_position=0, end_position=500, word_count=100, confidence=0.9),
            Chapter(index=2, title="Chapter 2", start_position=500, end_position=900, word_count=80, confidence=0.9),
            Chapter(index=3, title="Chapter 3", start_position=900, end_position=1400, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        character = IdentifiedCharacter(
            canonical_name="Tom Buchanan",
            aliases=["Tom"],
            role="antagonist",
        )

        gatherer = CharacterPassageGatherer(context_window=200)
        passages = gatherer.gather_passages(character, SAMPLE_TEXT, chapter_map)

        assert len(passages) > 0
        # Should find passages mentioning Tom or Tom Buchanan
        assert any("Tom" in p.text for p in passages)

    def test_gather_passages_includes_aliases(self):
        """Test that gatherer finds passages for all name variants."""
        chapters = [
            Chapter(index=1, title="Chapter 1", start_position=0, end_position=500, word_count=100, confidence=0.9),
            Chapter(index=2, title="Chapter 2", start_position=500, end_position=900, word_count=80, confidence=0.9),
            Chapter(index=3, title="Chapter 3", start_position=900, end_position=1400, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        character = IdentifiedCharacter(
            canonical_name="Jay Gatsby",
            aliases=["Gatsby"],
            role="protagonist",
        )

        gatherer = CharacterPassageGatherer(context_window=200)
        passages = gatherer.gather_passages(character, SAMPLE_TEXT, chapter_map)

        assert len(passages) > 0
        # Should find passages mentioning Gatsby
        assert any("Gatsby" in p.text for p in passages)

    def test_passage_scoring_prefers_descriptions(self):
        """Test that passages with descriptions score higher."""
        chapters = [
            Chapter(index=1, title="Chapter 1", start_position=0, end_position=500, word_count=100, confidence=0.9),
            Chapter(index=2, title="Chapter 2", start_position=500, end_position=900, word_count=80, confidence=0.9),
            Chapter(index=3, title="Chapter 3", start_position=900, end_position=1400, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        character = IdentifiedCharacter(
            canonical_name="Tom Buchanan",
            aliases=["Tom"],
            role="antagonist",
        )

        gatherer = CharacterPassageGatherer(context_window=300)
        passages = gatherer.gather_passages(character, SAMPLE_TEXT, chapter_map)

        # Passages with "hulking", "cruel", "arrogant", "eyes" should score higher
        description_passages = [p for p in passages if p.context_type == "description"]
        assert len(description_passages) > 0

    def test_classify_dialogue_context(self):
        """Test that dialogue passages are classified correctly."""
        gatherer = CharacterPassageGatherer()

        dialogue_text = 'Tom said, "I have got a nice place here."'
        context_type = gatherer._classify_context(dialogue_text, "Tom")
        assert context_type == "dialogue"

        description_text = "Tom was tall with blue eyes and a commanding presence."
        context_type = gatherer._classify_context(description_text, "Tom")
        assert context_type == "description"


class TestCharacterProfileGenerator:
    """Tests for the profile generator."""

    def test_generate_profile_parses_llm_response(self):
        """Test that generator correctly parses LLM response into profile."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "appearance": {
                    "summary": "A hulking man with arrogant eyes",
                    "details": {"build": "hulking", "eyes": "arrogant"},
                    "age_indication": "middle-aged",
                    "distinguishing_features": ["cruel body"],
                    "evidence": ["His eyes were arrogant"],
                },
                "personality": {
                    "summary": "Arrogant and commanding",
                    "traits": ["arrogant", "cruel", "domineering"],
                    "temperament": "volatile",
                    "speech_patterns": ["commanding", "dismissive"],
                    "evidence": ["spoke with a commanding voice"],
                },
                "voice_guidance": {
                    "suggested_tone": "Deep, commanding, dismissive",
                    "dialect_notes": "Upper-class East Coast",
                    "verbal_tics": [],
                    "formality_level": "formal",
                    "emotional_range": "controlled aggression",
                    "example_quotes": ["I've got a nice place here"],
                },
                "relationships": [
                    {
                        "character": "Daisy Buchanan",
                        "type": "spouse",
                        "description": "Unhappy marriage",
                    },
                    {
                        "character": "Myrtle Wilson",
                        "type": "mistress",
                        "description": "Affair",
                    },
                ],
                "confidence": 0.85,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        chapters = [
            Chapter(index=1, title="Chapter 1", start_position=0, end_position=500, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        character = IdentifiedCharacter(
            canonical_name="Tom Buchanan",
            aliases=["Tom"],
            role="antagonist",
        )

        generator = CharacterProfileGenerator(mock_llm)
        profile = generator.generate_profile(
            character=character,
            full_text=SAMPLE_TEXT,
            chapter_map=chapter_map,
        )

        assert profile.canonical_name == "Tom Buchanan"
        assert profile.appearance.summary == "A hulking man with arrogant eyes"
        assert "arrogant" in profile.personality.traits
        assert profile.voice_guidance.suggested_tone == "Deep, commanding, dismissive"
        assert len(profile.relationships) == 2
        assert profile.confidence == 0.85

    def test_generate_profile_handles_empty_passages(self):
        """Test that generator handles characters with no passages gracefully."""
        mock_llm = Mock()

        chapters = [
            Chapter(index=1, title="Chapter 1", start_position=0, end_position=500, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        # Character not in text
        character = IdentifiedCharacter(
            canonical_name="Unknown Character",
            aliases=[],
            role="minor",
        )

        generator = CharacterProfileGenerator(mock_llm)
        profile = generator.generate_profile(
            character=character,
            full_text=SAMPLE_TEXT,
            chapter_map=chapter_map,
        )

        # Should return basic profile without LLM call
        assert profile.canonical_name == "Unknown Character"
        # LLM should not have been called since no passages
        mock_llm.query_json.assert_not_called()

    def test_profile_includes_voice_guidance(self):
        """Test that profiles include actionable voice guidance."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "appearance": {"summary": "An elegant young man"},
                "personality": {"summary": "Mysterious and romantic"},
                "voice_guidance": {
                    "suggested_tone": "Measured, almost rehearsed formality",
                    "dialect_notes": "Affected upper-class",
                    "verbal_tics": ["old sport"],
                    "formality_level": "very formal",
                    "emotional_range": "controlled with occasional intensity",
                    "example_quotes": [
                        '"Old sport, I understand you\'re looking for me."',
                        '"I\'m Gatsby."',
                    ],
                },
                "relationships": [],
                "confidence": 0.9,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        chapters = [
            Chapter(index=3, title="Chapter 3", start_position=900, end_position=1400, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        character = IdentifiedCharacter(
            canonical_name="Jay Gatsby",
            aliases=["Gatsby"],
            role="protagonist",
        )

        generator = CharacterProfileGenerator(mock_llm)
        profile = generator.generate_profile(
            character=character,
            full_text=SAMPLE_TEXT,
            chapter_map=chapter_map,
        )

        assert "old sport" in profile.voice_guidance.verbal_tics
        assert profile.voice_guidance.formality_level == "very formal"
        assert len(profile.voice_guidance.example_quotes) > 0


class TestRichProfilingPipeline:
    """Tests for the full pipeline with rich profiling enabled."""

    def test_pipeline_generates_rich_profiles(self):
        """Test that pipeline generates rich profiles with LLM."""
        mock_llm = Mock()
        # First call: identification
        mock_llm.query_json.side_effect = [
            (
                {
                    "characters": [
                        {
                            "canonical_name": "Jay Gatsby",
                            "aliases": ["Gatsby"],
                            "role": "protagonist",
                            "chapters_present": [3],
                            "brief_description": "Mysterious millionaire",
                        },
                    ],
                    "narrator": None,
                },
                LLMResponse(content="...", model="test", error=None),
            ),
            # Second call: profile generation
            (
                {
                    "appearance": {"summary": "Elegant young man with rare smile"},
                    "personality": {"summary": "Mysterious romantic"},
                    "voice_guidance": {
                        "suggested_tone": "Measured formality",
                        "verbal_tics": ["old sport"],
                    },
                    "relationships": [],
                    "confidence": 0.9,
                },
                LLMResponse(content="...", model="test", error=None),
            ),
        ]

        summary_map = ChapterSummaryMap(
            summaries=GATSBY_SUMMARIES[2:3],  # Just chapter 3
            total_chapters=1,
            total_word_count=5500,
            total_duration_minutes=37,
            overall_tones={"mysterious": 1},
            character_appearances={"Jay Gatsby": [3]},
        )

        chapters = [
            Chapter(index=3, title="Chapter 3", start_position=900, end_position=1400, word_count=100, confidence=0.9),
        ]
        chapter_map = Mock()
        chapter_map.chapters = chapters

        pipeline = CharacterProfilingPipeline(
            llm_client=mock_llm,
            generate_rich_profiles=True,
        )
        result = pipeline.run(
            full_text=SAMPLE_TEXT,
            chapter_map=chapter_map,
            summary_map=summary_map,
            plot_summary="Sample plot",
        )

        assert len(result.profiles) == 1
        profile = result.profiles[0]
        assert profile.canonical_name == "Jay Gatsby"
        # Rich profile should have appearance populated
        assert profile.appearance.summary == "Elegant young man with rare smile"


class TestNarratorDetector:
    """Tests for narrator detection from summaries."""

    def test_first_person_narrator_detected(self):
        """Test that first-person narrator is correctly identified."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "narrative_style": "first-person",
                "narrator_name": "Nick Carraway",
                "narrator_role": "First-person narrator and participant in events",
                "confidence": 0.95,
                "reasoning": "The plot summary states 'through the eyes of Nick Carraway'",
            },
            LLMResponse(content="...", model="test", error=None),
        )

        characters = [
            IdentifiedCharacter(canonical_name="Nick Carraway", aliases=["Mr. Carraway"]),
            IdentifiedCharacter(canonical_name="Jay Gatsby", aliases=["Gatsby"]),
        ]

        detector = NarratorDetector(mock_llm)
        result = detector.detect_narrator(GATSBY_PLOT_SUMMARY, characters)

        assert result.narrative_style == "first-person"
        assert result.narrator_name == "Nick Carraway"
        assert result.confidence >= 0.9

    def test_narrator_detection_uses_plot_summary_intelligence(self):
        """Test that narrator is detected from summary, not mention count."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "narrative_style": "first-person",
                "narrator_name": "Nick Carraway",
                "narrator_role": "Observer and participant",
                "confidence": 0.9,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        # Characters with narrator having LOW mention count
        characters = [
            IdentifiedCharacter(
                canonical_name="Nick Carraway",
                aliases=["Mr. Carraway"],
                chapters_present=[1],  # Appears rarely by name
            ),
            IdentifiedCharacter(
                canonical_name="Jay Gatsby",
                aliases=["Gatsby"],
                chapters_present=[1, 2, 3, 4, 5, 6, 7, 8, 9],  # Appears frequently
            ),
        ]

        detector = NarratorDetector(mock_llm)
        result = detector.detect_narrator(GATSBY_PLOT_SUMMARY, characters)

        # Should still identify Nick as narrator despite low mentions
        assert result.narrator_name == "Nick Carraway"

    def test_third_person_narrative_no_narrator_character(self):
        """Test that third-person narratives have no narrator character."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "narrative_style": "third-person",
                "narrator_name": None,
                "narrator_role": "External omniscient narrator",
                "confidence": 0.95,
            },
            LLMResponse(content="...", model="test", error=None),
        )

        third_person_summary = """
        Elizabeth Bennet navigates the complex social world of Regency England.
        She encounters Mr. Darcy, a proud and wealthy gentleman, at a local ball.
        Their initial dislike gradually transforms into mutual respect and love.
        """

        characters = [
            IdentifiedCharacter(canonical_name="Elizabeth Bennet"),
            IdentifiedCharacter(canonical_name="Mr. Darcy"),
        ]

        detector = NarratorDetector(mock_llm)
        result = detector.detect_narrator(third_person_summary, characters)

        assert result.narrative_style == "third-person"
        assert result.narrator_name is None

    def test_mark_narrator_in_characters(self):
        """Test that narrator flag is set on the correct character."""
        mock_llm = Mock()

        characters = [
            IdentifiedCharacter(canonical_name="Nick Carraway", aliases=["Mr. Carraway"]),
            IdentifiedCharacter(canonical_name="Jay Gatsby", aliases=["Gatsby"]),
        ]

        narrator_info = NarratorInfo(
            narrative_style="first-person",
            narrator_name="Nick Carraway",
            narrator_role="First-person narrator",
            confidence=0.95,
        )

        detector = NarratorDetector(mock_llm)
        detector.mark_narrator_in_characters(characters, narrator_info)

        # Nick should be marked as narrator
        nick = next(c for c in characters if c.canonical_name == "Nick Carraway")
        assert nick.is_narrator is True
        assert nick.narrative_role == "First-person narrator"

        # Gatsby should NOT be marked as narrator
        gatsby = next(c for c in characters if c.canonical_name == "Jay Gatsby")
        assert gatsby.is_narrator is False

    def test_mark_narrator_by_alias(self):
        """Test that narrator is found even when using alias."""
        mock_llm = Mock()

        characters = [
            IdentifiedCharacter(canonical_name="Nick Carraway", aliases=["Mr. Carraway"]),
        ]

        # LLM returns alias instead of canonical name
        narrator_info = NarratorInfo(
            narrative_style="first-person",
            narrator_name="Mr. Carraway",  # Alias
            narrator_role="First-person narrator",
            confidence=0.9,
        )

        detector = NarratorDetector(mock_llm)
        detector.mark_narrator_in_characters(characters, narrator_info)

        nick = characters[0]
        assert nick.is_narrator is True

    def test_fallback_detection_first_person(self):
        """Test fallback detection for first-person narratives."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            None,
            LLMResponse(content="", model="test", error="LLM failed"),
        )

        # Plot summary with clear first-person indicator
        summary = "The story unfolds through the eyes of Nick Carraway, who narrates the events."

        detector = NarratorDetector(mock_llm)
        result = detector.detect_narrator(summary, [])

        assert result.narrative_style == "first-person"

    def test_fallback_detection_third_person(self):
        """Test fallback detection defaults to third-person."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            None,
            LLMResponse(content="", model="test", error="LLM failed"),
        )

        # Plot summary with no clear narrator
        summary = "Elizabeth meets Darcy at a ball. They fall in love."

        detector = NarratorDetector(mock_llm)
        result = detector.detect_narrator(summary, [])

        assert result.narrative_style == "third-person"


# Integration test marker - requires actual LLM
@pytest.mark.skip(reason="Integration test - requires LLM")
class TestCharacterProfilingIntegration:
    """Integration tests with actual LLM."""

    def test_gatsby_character_identification(self):
        """Test full identification on Gatsby summaries."""
        # This would be run with an actual LLM
        pass
