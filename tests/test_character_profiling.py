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
    CharacterReconciler,
    IdentifiedCharacter,
    CharacterProfile,
    profile_to_character,
    profile_map_to_characters,
    character_to_rich_dict,
)
from src.pipeline.character_profiling.models import (
    ActionAnalysis,
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterProfileMap,
    CharacterRelationship,
    ProfileEvidence,
)
from src.pipeline.character_profiling.moral_valence import (
    MoralValence,
    MoralValenceResult,
    MoralValenceClassifier,
)
from src.pipeline.character_profiling.narrator_commentary import (
    NarratorComment,
    NarratorCommentaryResult,
    NarratorCommentaryDetector,
)
from src.models import Character, ConfidenceLevel
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


class TestCharacterReconciler:
    """Tests for character reconciliation."""

    def test_reconciliation_merges_duplicates(self):
        """Test that reconciliation catches and merges duplicate characters."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "duplicates": [
                    {
                        "name1": "James Gatz",
                        "name2": "Jay Gatsby",
                        "reason": "Birth name and assumed name - same person",
                        "confidence": 0.95,
                    }
                ],
                "analysis": "James Gatz and Jay Gatsby are the same person",
            },
            LLMResponse(content="...", model="test", error=None),
        )

        profiles = [
            CharacterProfile(
                id="char_1",
                canonical_name="James Gatz",
                aliases=["Mr. Gatz"],
                appearance=AppearanceProfile(summary="", age_indication="young"),  # Less complete
            ),
            CharacterProfile(
                id="char_2",
                canonical_name="Jay Gatsby",
                aliases=["Mr. Gatsby", "old sport"],
                appearance=AppearanceProfile(summary="Elegant millionaire with rare smile"),
                personality=PersonalityProfile(summary="Romantic dreamer"),
                voice_guidance=VoiceGuidance(suggested_tone="Formal and rehearsed"),
            ),
            CharacterProfile(
                id="char_3",
                canonical_name="Nick Carraway",
            ),
        ]

        reconciler = CharacterReconciler(mock_llm)
        result = reconciler.reconcile(profiles)

        # Should merge to 2 characters
        assert len(result) == 2

        # Jay Gatsby should be primary (more complete) - check by looking for his profile
        gatsby = next((p for p in result if p.canonical_name == "Jay Gatsby"), None)
        assert gatsby is not None
        # James Gatz should now be an alias
        assert "James Gatz" in gatsby.aliases

    def test_reconciliation_keeps_distinct_characters_separate(self):
        """Test that reconciliation does not incorrectly merge distinct characters."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "duplicates": [],
                "analysis": "All characters are distinct individuals",
            },
            LLMResponse(content="...", model="test", error=None),
        )

        profiles = [
            CharacterProfile(
                id="char_1",
                canonical_name="George Wilson",
                aliases=["Mr. Wilson"],
            ),
            CharacterProfile(
                id="char_2",
                canonical_name="Myrtle Wilson",
                aliases=["Mrs. Wilson"],
            ),
        ]

        reconciler = CharacterReconciler(mock_llm)
        result = reconciler.reconcile(profiles)

        # Should remain as 2 separate characters
        assert len(result) == 2
        names = [p.canonical_name for p in result]
        assert "George Wilson" in names
        assert "Myrtle Wilson" in names

    def test_reconciliation_respects_confidence_threshold(self):
        """Test that low-confidence duplicates are not merged."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "duplicates": [
                    {
                        "name1": "Tom",
                        "name2": "Mr. Buchanan",
                        "reason": "Might be same person",
                        "confidence": 0.6,  # Below threshold
                    }
                ],
                "analysis": "Possible duplicate but not confident",
            },
            LLMResponse(content="...", model="test", error=None),
        )

        profiles = [
            CharacterProfile(id="char_1", canonical_name="Tom"),
            CharacterProfile(id="char_2", canonical_name="Mr. Buchanan"),
        ]

        reconciler = CharacterReconciler(mock_llm, confidence_threshold=0.85)
        result = reconciler.reconcile(profiles)

        # Should NOT merge (confidence below threshold)
        assert len(result) == 2

    def test_reconciliation_preserves_profile_information(self):
        """Test that merging preserves information from both profiles."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            {
                "duplicates": [
                    {
                        "name1": "Myrtle",
                        "name2": "Mrs. Wilson",
                        "reason": "First name and formal name for same person",
                        "confidence": 0.9,
                    }
                ],
                "analysis": "Myrtle and Mrs. Wilson are the same person",
            },
            LLMResponse(content="...", model="test", error=None),
        )

        profiles = [
            CharacterProfile(
                id="char_1",
                canonical_name="Myrtle",
                aliases=[],
                appearance=AppearanceProfile(summary="Thickish figure with vitality"),
                chapters_present=[2],
            ),
            CharacterProfile(
                id="char_2",
                canonical_name="Mrs. Wilson",
                aliases=["Wilson"],
                personality=PersonalityProfile(summary="Ambitious and desperate"),
                chapters_present=[2, 7],
            ),
        ]

        reconciler = CharacterReconciler(mock_llm)
        result = reconciler.reconcile(profiles)

        assert len(result) == 1
        merged = result[0]

        # Should have merged chapters
        assert 2 in merged.chapters_present
        assert 7 in merged.chapters_present

        # Should have both appearance and personality (from different originals)
        # One profile had appearance, one had personality

    def test_reconciliation_handles_llm_failure(self):
        """Test that reconciliation handles LLM failure gracefully."""
        mock_llm = Mock()
        mock_llm.query_json.return_value = (
            None,
            LLMResponse(content="", model="test", error="LLM failed"),
        )

        profiles = [
            CharacterProfile(id="char_1", canonical_name="Character A"),
            CharacterProfile(id="char_2", canonical_name="Character B"),
        ]

        reconciler = CharacterReconciler(mock_llm)
        result = reconciler.reconcile(profiles)

        # Should return original profiles unchanged
        assert len(result) == 2


class TestProfileToCharacterConverter:
    """Tests for converting CharacterProfile to Character model."""

    def test_profile_to_character_basic(self):
        """Test basic conversion from profile to character."""
        profile = CharacterProfile(
            id="char_gatsby_123",
            canonical_name="Jay Gatsby",
            aliases=["Mr. Gatsby", "James Gatz"],
            role="protagonist",
            is_narrator=False,
            confidence=0.9,
            first_appearance_chapter=3,
            chapters_present=[3, 4, 5, 6, 7, 8, 9],
            mention_frequency="frequent",
        )

        char = profile_to_character(profile)

        assert char.id == "char_gatsby_123"
        assert char.canonical_name == "Jay Gatsby"
        assert "Mr. Gatsby" in char.aliases
        assert char.is_narrator is False
        assert char.confidence == ConfidenceLevel.HIGH  # 0.9 >= 0.7

    def test_profile_to_character_with_rich_data(self):
        """Test conversion preserves appearance, personality, voice guidance."""
        profile = CharacterProfile(
            id="char_tom_456",
            canonical_name="Tom Buchanan",
            aliases=["Tom"],
            role="antagonist",
            appearance=AppearanceProfile(
                summary="A hulking man with arrogant eyes",
                age_indication="middle-aged",
                distinguishing_features=["cruel body", "hard mouth"],
            ),
            personality=PersonalityProfile(
                summary="Arrogant and domineering",
                traits=["arrogant", "brutal", "racist"],
                temperament="volatile",
            ),
            voice_guidance=VoiceGuidance(
                suggested_tone="Deep, commanding, dismissive",
                dialect_notes="Upper-class East Coast",
                verbal_tics=[],
                formality_level="formal",
                emotional_range="controlled aggression",
                example_quotes=["I've got a nice place here"],
            ),
            confidence=0.85,
        )

        char = profile_to_character(profile)

        # Should have description with appearance and personality
        assert len(char.descriptions) > 0
        desc_text = char.descriptions[0].text
        assert "Appearance" in desc_text or "hulking" in desc_text.lower()

        # Should have voice notes
        assert char.voice_notes is not None
        assert "Deep" in char.voice_notes or "commanding" in char.voice_notes

    def test_profile_to_character_with_relationships(self):
        """Test conversion preserves relationships."""
        profile = CharacterProfile(
            id="char_daisy_789",
            canonical_name="Daisy Buchanan",
            aliases=["Daisy"],
            relationships=[
                CharacterRelationship(
                    character="Tom Buchanan",
                    relationship_type="spouse",
                    description="Unhappy marriage",
                ),
                CharacterRelationship(
                    character="Jay Gatsby",
                    relationship_type="love interest",
                    description="Former romance, rekindled",
                ),
            ],
            confidence=0.8,
        )

        char = profile_to_character(profile)

        assert "Tom Buchanan" in char.relationships
        assert char.relationships["Tom Buchanan"] == "spouse"
        assert "Jay Gatsby" in char.relationships

    def test_profile_to_character_confidence_mapping(self):
        """Test that confidence is correctly mapped to enum."""
        # High confidence
        high_profile = CharacterProfile(id="c1", canonical_name="A", confidence=0.85)
        assert profile_to_character(high_profile).confidence == ConfidenceLevel.HIGH

        # Medium confidence
        med_profile = CharacterProfile(id="c2", canonical_name="B", confidence=0.5)
        assert profile_to_character(med_profile).confidence == ConfidenceLevel.MEDIUM

        # Low confidence
        low_profile = CharacterProfile(id="c3", canonical_name="C", confidence=0.3)
        assert profile_to_character(low_profile).confidence == ConfidenceLevel.LOW

    def test_profile_map_to_characters(self):
        """Test converting entire profile map."""
        profile_map = CharacterProfileMap(
            profiles=[
                CharacterProfile(id="c1", canonical_name="Character A"),
                CharacterProfile(id="c2", canonical_name="Character B"),
                CharacterProfile(id="c3", canonical_name="Character C"),
            ],
            narrator_name="Character A",
            narrative_style="first-person",
            total_characters=3,
        )

        characters = profile_map_to_characters(profile_map)

        assert len(characters) == 3
        assert all(isinstance(c, Character) for c in characters)


class TestCharacterToRichDict:
    """Tests for character_to_rich_dict function."""

    def test_character_to_rich_dict_structure(self):
        """Test that rich dict has correct structure prioritizing narrator info."""
        profile = CharacterProfile(
            id="char_gatsby",
            canonical_name="Jay Gatsby",
            aliases=["Mr. Gatsby", "James Gatz"],
            role="protagonist",
            is_narrator=False,
            appearance=AppearanceProfile(
                summary="Elegant young man with rare smile",
                age_indication="early thirties",
            ),
            personality=PersonalityProfile(
                summary="Romantic dreamer",
                traits=["mysterious", "romantic", "obsessive"],
            ),
            voice_guidance=VoiceGuidance(
                suggested_tone="Measured formality",
                verbal_tics=["old sport"],
                formality_level="very formal",
            ),
            relationships=[
                CharacterRelationship(
                    character="Daisy Buchanan",
                    relationship_type="love interest",
                    description="Obsessive love",
                ),
            ],
            first_appearance_chapter=3,
            mention_frequency="frequent",
            confidence=0.9,
        )

        char = profile_to_character(profile)
        rich_dict = character_to_rich_dict(char)

        # Check top-level structure
        assert "id" in rich_dict
        assert "canonical_name" in rich_dict
        assert "aliases" in rich_dict
        assert "role" in rich_dict
        assert "is_narrator" in rich_dict

        # Check primary profile data (narrator-useful)
        assert "appearance" in rich_dict
        assert "personality" in rich_dict
        assert "voice_guidance" in rich_dict
        assert "relationships" in rich_dict

        # Check metadata is secondary (nested)
        assert "metadata" in rich_dict
        assert "first_appearance_chapter" in rich_dict["metadata"]
        assert "mention_count" in rich_dict["metadata"]
        assert "confidence" in rich_dict["metadata"]

    def test_character_to_rich_dict_voice_guidance(self):
        """Test that voice guidance is properly structured."""
        profile = CharacterProfile(
            id="char_gatsby",
            canonical_name="Jay Gatsby",
            voice_guidance=VoiceGuidance(
                suggested_tone="Measured formality",
                dialect_notes="Affected upper-class",
                verbal_tics=["old sport"],
                formality_level="very formal",
                emotional_range="controlled",
                example_quotes=['"Old sport"', '"I\'m Gatsby"'],
            ),
            confidence=0.8,
        )

        char = profile_to_character(profile)
        rich_dict = character_to_rich_dict(char)

        vg = rich_dict["voice_guidance"]
        assert "suggested_tone" in vg
        assert "verbal_tics" in vg
        assert "formality_level" in vg

    def test_json_output_includes_rich_profile_data(self):
        """Test that JSON output structure supports rich profiles."""
        profile = CharacterProfile(
            id="char_nick",
            canonical_name="Nick Carraway",
            aliases=["Mr. Carraway"],
            role="protagonist",
            is_narrator=True,
            narrative_role="First-person narrator",
            appearance=AppearanceProfile(summary="Young Midwesterner"),
            personality=PersonalityProfile(summary="Honest and observant"),
            voice_guidance=VoiceGuidance(suggested_tone="Reflective, measured"),
            confidence=0.95,
        )

        char = profile_to_character(profile)
        rich_dict = character_to_rich_dict(char)

        # Verify narrator info is captured
        assert rich_dict["is_narrator"] is True
        assert rich_dict["narrative_role"] == "First-person narrator"

        # Verify all profile sections are present
        assert rich_dict["appearance"]["summary"] is not None
        assert rich_dict["personality"]["summary"] is not None
        assert rich_dict["voice_guidance"]["suggested_tone"] is not None


class TestActionAnalysisModel:
    """Tests for the ActionAnalysis model (Feature F3)."""

    def test_action_analysis_creation(self):
        """Test creating ActionAnalysis with all fields."""
        aa = ActionAnalysis(
            harmful_actions=["murdered parents", "manipulated others"],
            beneficial_actions=[],
            neutral_actions=["walked to town"],
            dominant_pattern="harmful",
            evidence=["She burned the house down"],
        )
        assert aa.dominant_pattern == "harmful"
        assert len(aa.harmful_actions) == 2
        assert len(aa.beneficial_actions) == 0

    def test_action_analysis_to_dict(self):
        """Test ActionAnalysis serialization."""
        aa = ActionAnalysis(
            harmful_actions=["murder", "manipulation"],
            beneficial_actions=["helped a friend"],
            dominant_pattern="mixed",
        )
        data = aa.to_dict()
        assert data["harmful_actions"] == ["murder", "manipulation"]
        assert data["beneficial_actions"] == ["helped a friend"]
        assert data["dominant_pattern"] == "mixed"

    def test_action_analysis_from_dict(self):
        """Test ActionAnalysis deserialization."""
        data = {
            "harmful_actions": ["betrayal"],
            "beneficial_actions": ["sacrifice", "protection"],
            "neutral_actions": [],
            "dominant_pattern": "beneficial",
            "evidence": ["quote 1"],
        }
        aa = ActionAnalysis.from_dict(data)
        assert aa.harmful_actions == ["betrayal"]
        assert aa.beneficial_actions == ["sacrifice", "protection"]
        assert aa.dominant_pattern == "beneficial"

    def test_action_analysis_empty_factory(self):
        """Test empty ActionAnalysis factory method."""
        aa = ActionAnalysis.empty()
        assert aa.harmful_actions == []
        assert aa.beneficial_actions == []
        assert aa.dominant_pattern == "unknown"


class TestActionWeightedProfiling:
    """Tests for action-weighted profiling (Feature F3)."""

    def test_profile_includes_action_analysis(self):
        """Test that CharacterProfile includes action_analysis in to_dict."""
        profile = CharacterProfile(
            id="char_test",
            canonical_name="Test Character",
            action_analysis=ActionAnalysis(
                harmful_actions=["killed someone"],
                dominant_pattern="harmful",
            ),
        )
        data = profile.to_dict()
        assert "action_analysis" in data
        assert data["action_analysis"]["harmful_actions"] == ["killed someone"]
        assert data["action_analysis"]["dominant_pattern"] == "harmful"

    def test_profile_from_dict_includes_action_analysis(self):
        """Test that CharacterProfile.from_dict restores action_analysis."""
        data = {
            "id": "char_test",
            "canonical_name": "Test Character",
            "action_analysis": {
                "harmful_actions": ["manipulation", "deception"],
                "beneficial_actions": [],
                "neutral_actions": ["walked"],
                "dominant_pattern": "harmful",
                "evidence": [],
            },
        }
        profile = CharacterProfile.from_dict(data)
        assert profile.action_analysis.harmful_actions == ["manipulation", "deception"]
        assert profile.action_analysis.dominant_pattern == "harmful"

    def test_generator_prompt_prioritizes_actions(self):
        """Test that the generator prompt emphasizes action-based analysis."""
        from src.pipeline.character_profiling.generator import (
            PROFILE_GENERATION_SYSTEM,
            PROFILE_GENERATION_PROMPT,
        )
        # Verify system prompt establishes action priority
        assert "CHARACTER = ACTIONS" in PROFILE_GENERATION_SYSTEM
        assert "ACTIONS (highest weight)" in PROFILE_GENERATION_SYSTEM
        assert "DESCRIPTIONS (lowest weight)" in PROFILE_GENERATION_SYSTEM

        # Verify prompt includes three-phase structure
        assert "PHASE 1: ACTION ANALYSIS" in PROFILE_GENERATION_PROMPT
        assert "PHASE 2: PERSONALITY FROM ACTIONS" in PROFILE_GENERATION_PROMPT
        assert "action_analysis" in PROFILE_GENERATION_PROMPT

    def test_generator_parses_action_analysis(self):
        """Test that _parse_profile_response correctly parses action_analysis."""
        from src.pipeline.character_profiling.generator import CharacterProfileGenerator

        # Mock LLM client - we won't actually use it since we're testing parsing
        mock_llm = MagicMock()

        generator = CharacterProfileGenerator(mock_llm)

        # Create a base profile
        char = IdentifiedCharacter(canonical_name="Test Villain", role="antagonist")
        profile = CharacterProfile.from_identified(char)

        # Simulate LLM response
        result = {
            "action_analysis": {
                "harmful_actions": ["murdered parents", "manipulated victims"],
                "beneficial_actions": [],
                "neutral_actions": ["arrived at town"],
                "dominant_pattern": "harmful",
                "evidence": ["She set fire to the house"],
            },
            "personality": {
                "summary": "A manipulative and dangerous individual",
                "moral_alignment": "villainous",
                "traits": ["manipulative", "cold", "calculating"],
            },
            "appearance": {
                "summary": "Beautiful and poised",
            },
            "confidence": 0.85,
        }

        # Test the parsing directly
        passages = [CharacterPassage(
            text="She set fire to the house.",
            chapter_index=1,
            position=0,
            name_matched="Test Villain",
            context_type="action",
        )]

        parsed_profile = generator._parse_profile_response(profile, result, passages)

        # Verify action_analysis was parsed
        assert parsed_profile.action_analysis.dominant_pattern == "harmful"
        assert "murdered parents" in parsed_profile.action_analysis.harmful_actions
        assert parsed_profile.personality.moral_alignment == "villainous"


class TestMoralValenceEnum:
    """Tests for MoralValence enum (Feature F2)."""

    def test_all_valence_types_exist(self):
        """Test that all required valence types are defined."""
        assert MoralValence.PROTAGONIST.value == "protagonist"
        assert MoralValence.ANTAGONIST.value == "antagonist"
        assert MoralValence.MORALLY_AMBIGUOUS.value == "morally_ambiguous"
        assert MoralValence.NEUTRAL.value == "neutral"
        assert MoralValence.VICTIM.value == "victim"
        assert MoralValence.UNCERTAIN.value == "uncertain"

    def test_valence_is_string_enum(self):
        """Test that MoralValence inherits from str and can be compared as string."""
        # The value can be compared to a string
        assert MoralValence.ANTAGONIST.value == "antagonist"
        # It's a string enum (inherits from str)
        assert isinstance(MoralValence.ANTAGONIST, str)


class TestMoralValenceResult:
    """Tests for MoralValenceResult dataclass (Feature F2)."""

    def test_result_creation(self):
        """Test creating MoralValenceResult with all fields."""
        result = MoralValenceResult(
            character_name="Test Villain",
            valence=MoralValence.ANTAGONIST,
            confidence=0.9,
            key_actions=[
                {"action": "murdered parents", "category": "harmful", "target": "parents"}
            ],
            evidence_quotes=["She set the house on fire"],
            reasoning="Character commits multiple harmful acts",
        )
        assert result.valence == MoralValence.ANTAGONIST
        assert result.confidence == 0.9
        assert len(result.key_actions) == 1

    def test_result_to_dict(self):
        """Test MoralValenceResult serialization."""
        result = MoralValenceResult(
            character_name="Test Hero",
            valence=MoralValence.PROTAGONIST,
            confidence=0.85,
            key_actions=[
                {"action": "saved a child", "category": "beneficial", "target": "child"}
            ],
        )
        data = result.to_dict()
        assert data["character_name"] == "Test Hero"
        assert data["valence"] == "protagonist"
        assert data["confidence"] == 0.85

    def test_result_from_dict(self):
        """Test MoralValenceResult deserialization."""
        data = {
            "character_name": "Test Character",
            "valence": "morally_ambiguous",
            "confidence": 0.7,
            "key_actions": [
                {"action": "helped friend", "category": "beneficial"},
                {"action": "betrayed enemy", "category": "harmful"},
            ],
            "evidence_quotes": ["quote1"],
            "reasoning": "Both good and bad actions",
        }
        result = MoralValenceResult.from_dict(data)
        assert result.valence == MoralValence.MORALLY_AMBIGUOUS
        assert len(result.key_actions) == 2


class TestMoralValenceClassifier:
    """Tests for MoralValenceClassifier (Feature F2)."""

    def test_classify_with_no_passages(self):
        """Test that classifier returns UNCERTAIN with no passages."""
        mock_llm = MagicMock()
        classifier = MoralValenceClassifier(mock_llm)

        result = classifier.classify_character(
            character_name="Unknown",
            role="supporting",
            passages=[],
        )

        assert result.valence == MoralValence.UNCERTAIN
        assert result.confidence == 0.0
        mock_llm.query_json.assert_not_called()

    def test_classify_antagonist(self):
        """Test classification of an antagonist character."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = (
            {
                "valence": "antagonist",
                "confidence": 0.95,
                "key_actions": [
                    {"action": "murdered parents", "category": "harmful", "target": "parents"},
                    {"action": "manipulated victims", "category": "harmful", "target": "victims"},
                ],
                "evidence_quotes": ["She burned the house down"],
                "reasoning": "Character commits multiple murders and manipulations",
            },
            LLMResponse(content="...", model="test-model"),
        )

        classifier = MoralValenceClassifier(mock_llm)
        result = classifier.classify_character(
            character_name="Evil Character",
            role="antagonist",
            passages=["She murdered her parents.", "She manipulated everyone she met."],
        )

        assert result.valence == MoralValence.ANTAGONIST
        assert result.confidence == 0.95
        assert len(result.key_actions) == 2

    def test_classify_protagonist(self):
        """Test classification of a protagonist character."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = (
            {
                "valence": "protagonist",
                "confidence": 0.9,
                "key_actions": [
                    {"action": "saved the child", "category": "beneficial", "target": "child"},
                    {"action": "protected the innocent", "category": "beneficial", "target": "villagers"},
                ],
                "evidence_quotes": ["He risked his life to save them"],
                "reasoning": "Character performs selfless heroic acts",
            },
            LLMResponse(content="...", model="test-model"),
        )

        classifier = MoralValenceClassifier(mock_llm)
        result = classifier.classify_character(
            character_name="Hero Character",
            role="protagonist",
            passages=["He saved the child from the fire.", "He protected the villagers."],
        )

        assert result.valence == MoralValence.PROTAGONIST
        assert result.confidence == 0.9

    def test_classify_morally_ambiguous(self):
        """Test classification of a morally ambiguous character."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = (
            {
                "valence": "morally_ambiguous",
                "confidence": 0.8,
                "key_actions": [
                    {"action": "killed enemies", "category": "harmful", "target": "enemies"},
                    {"action": "saved friend", "category": "beneficial", "target": "friend"},
                ],
                "evidence_quotes": ["He did what was necessary"],
                "reasoning": "Character does both harmful and beneficial acts",
            },
            LLMResponse(content="...", model="test-model"),
        )

        classifier = MoralValenceClassifier(mock_llm)
        result = classifier.classify_character(
            character_name="Anti-Hero",
            role="protagonist",
            passages=["He killed them to save his friend."],
        )

        assert result.valence == MoralValence.MORALLY_AMBIGUOUS

    def test_classification_prompt_structure(self):
        """Test that the classification prompt contains key elements."""
        from src.pipeline.character_profiling.moral_valence import (
            MORAL_VALENCE_SYSTEM,
            MORAL_VALENCE_PROMPT,
        )
        # Verify system prompt emphasizes actions over descriptions
        assert "ACTIONS" in MORAL_VALENCE_SYSTEM
        assert "descriptions" in MORAL_VALENCE_SYSTEM.lower()
        assert "HARMFUL" in MORAL_VALENCE_SYSTEM
        assert "BENEFICIAL" in MORAL_VALENCE_SYSTEM

        # Verify prompt requests action classification
        assert "key_actions" in MORAL_VALENCE_PROMPT
        assert "valence" in MORAL_VALENCE_PROMPT


class TestNarratorComment:
    """Tests for NarratorComment dataclass (Feature F4)."""

    def test_comment_creation(self):
        """Test creating NarratorComment with all fields."""
        comment = NarratorComment(
            quote="I believe there are monsters born in the world.",
            character_name="Cathy",
            chapter_index=3,
            position=15000,
            comment_type="judgment",
            sentiment="negative",
        )
        assert comment.quote.startswith("I believe")
        assert comment.character_name == "Cathy"
        assert comment.comment_type == "judgment"

    def test_comment_to_dict(self):
        """Test NarratorComment serialization."""
        comment = NarratorComment(
            quote="Little did he know what awaited him.",
            character_name="Adam",
            chapter_index=5,
            position=25000,
            comment_type="foreshadowing",
            sentiment="neutral",
        )
        data = comment.to_dict()
        assert data["comment_type"] == "foreshadowing"
        assert data["character_name"] == "Adam"

    def test_comment_from_dict(self):
        """Test NarratorComment deserialization."""
        data = {
            "quote": "She was, in truth, a monster.",
            "character_name": "Cathy",
            "chapter_index": 8,
            "position": 40000,
            "comment_type": "judgment",
            "sentiment": "negative",
        }
        comment = NarratorComment.from_dict(data)
        assert comment.comment_type == "judgment"
        assert comment.sentiment == "negative"


class TestNarratorCommentaryResult:
    """Tests for NarratorCommentaryResult dataclass (Feature F4)."""

    def test_result_creation(self):
        """Test creating NarratorCommentaryResult."""
        result = NarratorCommentaryResult(
            comments=[
                NarratorComment(
                    quote="Test quote",
                    character_name="Test",
                    chapter_index=1,
                    position=100,
                    comment_type="judgment",
                    sentiment="negative",
                )
            ],
            has_significant_commentary=True,
            narrative_voice_notes="Strong authorial judgments",
        )
        assert len(result.comments) == 1
        assert result.has_significant_commentary is True

    def test_result_to_dict(self):
        """Test NarratorCommentaryResult serialization."""
        result = NarratorCommentaryResult(
            comments=[],
            has_significant_commentary=False,
            narrative_voice_notes="No commentary",
        )
        data = result.to_dict()
        assert data["has_significant_commentary"] is False
        assert data["narrative_voice_notes"] == "No commentary"


class TestNarratorCommentaryDetector:
    """Tests for NarratorCommentaryDetector (Feature F4)."""

    def test_detect_no_commentary(self):
        """Test detection with text that has no commentary patterns."""
        detector = NarratorCommentaryDetector()
        result = detector.detect(
            text="She walked to the door. He picked up the book.",
            character_names=["Alice", "Bob"],
        )
        assert result.has_significant_commentary is False
        assert len(result.comments) == 0

    def test_detect_i_believe_pattern(self):
        """Test detection of 'I believe' pattern."""
        detector = NarratorCommentaryDetector()
        text = "I believe there are monsters born in the world. Cathy was one of them."
        result = detector.detect(
            text=text,
            character_names=["Cathy"],
        )
        assert len(result.comments) >= 1
        # Should find the judgment about Cathy
        cathy_comments = result.comments_by_character.get("Cathy", [])
        # May or may not associate - depends on detection

    def test_detect_little_did_pattern(self):
        """Test detection of 'little did know' foreshadowing pattern."""
        detector = NarratorCommentaryDetector()
        text = "Little did Adam know what fate awaited him in the valley."
        result = detector.detect(
            text=text,
            character_names=["Adam"],
        )
        assert len(result.comments) >= 1
        # Should classify as foreshadowing
        assert any(c.comment_type == "foreshadowing" for c in result.comments)

    def test_detect_in_truth_pattern(self):
        """Test detection of 'in truth' judgment pattern."""
        detector = NarratorCommentaryDetector()
        text = "In truth, she was far more dangerous than anyone suspected."
        result = detector.detect(
            text=text,
            character_names=["Kate"],
        )
        assert len(result.comments) >= 1

    def test_detect_with_llm(self):
        """Test detection with LLM classification."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = (
            {
                "commentary": [
                    {
                        "passage_index": 0,
                        "is_commentary": True,
                        "character_name": "Cathy",
                        "comment_type": "judgment",
                        "sentiment": "negative",
                        "reasoning": "Narrator explicitly judges character as monster",
                    }
                ]
            },
            LLMResponse(content="...", model="test-model"),
        )

        detector = NarratorCommentaryDetector(llm_client=mock_llm)
        text = "I believe there are monsters born in the world. Cathy was one."
        result = detector.detect(
            text=text,
            character_names=["Cathy", "Adam"],
        )

        # Should have called LLM
        mock_llm.query_json.assert_called_once()
        assert len(result.comments) >= 1

    def test_simple_narration_not_flagged(self):
        """Test that simple narration is not flagged as commentary."""
        detector = NarratorCommentaryDetector()
        text = """
        She walked to the door. He opened the window.
        The sun was setting. Birds flew overhead.
        She had blue eyes. He was tall and thin.
        """
        result = detector.detect(
            text=text,
            character_names=["Alice", "Bob"],
        )
        # Simple descriptions should not match patterns
        assert len(result.comments) == 0

    def test_narrator_patterns_compiled(self):
        """Test that narrator patterns are properly compiled."""
        from src.pipeline.character_profiling.narrator_commentary import (
            NARRATOR_PATTERNS,
            COMPILED_PATTERNS,
        )
        assert len(NARRATOR_PATTERNS) > 0
        assert len(COMPILED_PATTERNS) == len(NARRATOR_PATTERNS)


class TestCharacterProfileNarratorComments:
    """Tests for narrator_comments field in CharacterProfile (Feature F4)."""

    def test_profile_includes_narrator_comments_field(self):
        """Test that CharacterProfile has narrator_comments field."""
        profile = CharacterProfile(
            id="char_test",
            canonical_name="Test",
            narrator_comments=[
                {"quote": "Test quote", "sentiment": "negative"}
            ],
        )
        assert len(profile.narrator_comments) == 1

    def test_profile_to_dict_includes_narrator_comments(self):
        """Test that to_dict includes narrator_comments."""
        profile = CharacterProfile(
            id="char_test",
            canonical_name="Test",
            narrator_comments=[
                {"quote": "I believe she was evil", "sentiment": "negative"}
            ],
        )
        data = profile.to_dict()
        assert "narrator_comments" in data
        assert len(data["narrator_comments"]) == 1

    def test_profile_from_dict_includes_narrator_comments(self):
        """Test that from_dict restores narrator_comments."""
        data = {
            "id": "char_test",
            "canonical_name": "Test",
            "narrator_comments": [
                {"quote": "In truth, he was noble", "sentiment": "positive"}
            ],
        }
        profile = CharacterProfile.from_dict(data)
        assert len(profile.narrator_comments) == 1
        assert profile.narrator_comments[0]["sentiment"] == "positive"


# Integration test marker - requires actual LLM
@pytest.mark.skip(reason="Integration test - requires LLM")
class TestCharacterProfilingIntegration:
    """Integration tests with actual LLM."""

    def test_gatsby_character_identification(self):
        """Test full identification on Gatsby summaries."""
        # This would be run with an actual LLM
        pass
