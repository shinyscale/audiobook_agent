"""
Tests for the verification gate (Feature F4).

Verifies that:
1. Pronoun entries are flagged and auto-removed
2. Missing agentive descriptions are flagged
"""

import pytest
from unittest.mock import MagicMock

from src.agents.characters import (
    CharacterAgent,
    PRONOUN_STOPWORDS,
    AGENTIVE_VERBS,
)
from src.agents.base import AgentResult, VerificationIssue, VerificationLevel, AgentContext
from src.pipeline.character_extraction.models import CharacterMap, Character, CharacterMention


def make_character(name: str, aliases: list[str] = None, chapters: list[int] = None,
                   mention_count: int = 10, confidence: float = 0.8) -> Character:
    """Helper to create a Character with required fields."""
    if aliases is None:
        aliases = []
    if chapters is None:
        chapters = [1]

    return Character(
        id=f"char_{name.lower().replace(' ', '_')}",
        canonical_name=name,
        aliases=aliases,
        mentions=[],  # Empty for testing
        first_appearance_chapter=chapters[0] if chapters else 1,
        mention_count=mention_count,
        chapters_present=chapters,
        confidence=confidence,
        supporting_strategies=["test"],
    )


class TestPronounStopwordsDefinition:
    """Test that PRONOUN_STOPWORDS is properly defined."""

    def test_pronouns_included(self):
        """Verify pronouns are in stopwords."""
        expected = {'he', 'she', 'it', 'they', 'we', 'i', 'you'}
        assert expected.issubset(PRONOUN_STOPWORDS)

    def test_determiners_included(self):
        """Verify determiners are in stopwords."""
        expected = {'the', 'a', 'an', 'this', 'that'}
        assert expected.issubset(PRONOUN_STOPWORDS)


class TestAgentiveVerbsDefinition:
    """Test that AGENTIVE_VERBS patterns are properly defined."""

    def test_speech_verbs_included(self):
        """Verify speech verbs are in agentive patterns."""
        combined = ' '.join(AGENTIVE_VERBS)
        for verb in ['said', 'asked', 'replied', 'whispered']:
            assert verb in combined, f"'{verb}' should be in agentive verbs"

    def test_motion_verbs_included(self):
        """Verify motion verbs are in agentive patterns."""
        combined = ' '.join(AGENTIVE_VERBS)
        for verb in ['walked', 'ran', 'stood', 'turned']:
            assert verb in combined, f"'{verb}' should be in agentive verbs"

    def test_action_verbs_included(self):
        """Verify action verbs are in agentive patterns."""
        combined = ' '.join(AGENTIVE_VERBS)
        for verb in ['grabbed', 'took', 'held', 'threw']:
            assert verb in combined, f"'{verb}' should be in agentive verbs"


class TestPronounEntryCheck:
    """Test _check_pronoun_entries() method."""

    @pytest.fixture
    def agent(self):
        """Create a CharacterAgent for testing."""
        return CharacterAgent()

    def test_flags_pronoun_character(self, agent):
        """Verify pronoun characters are flagged as errors."""
        characters = [
            make_character("he", chapters=[1, 2], mention_count=100),
            make_character("Victor", aliases=["Dr. Frankenstein"], chapters=[1, 2, 3], mention_count=50),
        ]

        issues = agent._check_pronoun_entries(characters)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "he" in issues[0].description.lower()
        assert "pronoun/determiner" in issues[0].description.lower()

    def test_flags_multiple_pronouns(self, agent):
        """Verify multiple pronoun characters are all flagged."""
        characters = [
            make_character("he", chapters=[1], mention_count=100),
            make_character("she", chapters=[1], mention_count=80),
            make_character("they", chapters=[1], mention_count=60),
        ]

        issues = agent._check_pronoun_entries(characters)

        assert len(issues) == 3
        for issue in issues:
            assert issue.severity == "error"

    def test_no_issues_for_real_names(self, agent):
        """Verify real character names are not flagged."""
        characters = [
            make_character("Victor Frankenstein", aliases=["Dr. Frankenstein"], chapters=[1, 2], mention_count=50),
            make_character("Elizabeth", chapters=[1, 2], mention_count=30),
        ]

        issues = agent._check_pronoun_entries(characters)

        assert len(issues) == 0


class TestMissingAgentiveDescriptionsCheck:
    """Test _check_missing_agentive_descriptions() method."""

    @pytest.fixture
    def agent(self):
        """Create a CharacterAgent for testing."""
        return CharacterAgent()

    def test_flags_high_frequency_descriptive_handle(self, agent):
        """Verify high-frequency descriptive handles are flagged."""
        # Text with "the creature" appearing with agentive verbs 10+ times
        text = """
        The creature walked through the forest. The creature said nothing.
        The creature turned and fled. The creature walked faster.
        The creature said a word. The creature walked away.
        The creature stood still. The creature looked up.
        The creature smiled grimly. The creature nodded slowly.
        The creature walked toward the light. The creature said goodbye.
        """

        characters = [
            make_character("Victor", chapters=[1], mention_count=50),
        ]

        issues = agent._check_missing_agentive_descriptions(text, characters)

        # Should flag "the creature"
        assert len(issues) >= 1
        creature_issues = [i for i in issues if "creature" in i.description.lower()]
        assert len(creature_issues) >= 1
        assert creature_issues[0].severity == "warning"

    def test_no_flag_for_existing_character(self, agent):
        """Verify no flag when descriptive handle is already in character list."""
        text = """
        The creature walked through the forest. The creature said nothing.
        The creature turned and fled. The creature walked faster.
        The creature said a word. The creature walked away.
        The creature stood still. The creature looked up.
        The creature smiled grimly. The creature nodded slowly.
        The creature walked toward the light. The creature said goodbye.
        """

        characters = [
            make_character("the creature", aliases=["the monster", "the wretch"], chapters=[1, 2], mention_count=100),
        ]

        issues = agent._check_missing_agentive_descriptions(text, characters)

        # Should not flag "the creature" since it's already a character
        creature_issues = [i for i in issues if "creature" in i.description.lower()]
        assert len(creature_issues) == 0

    def test_no_flag_for_low_frequency(self, agent):
        """Verify no flag for low-frequency descriptive handles."""
        text = """
        The stranger walked in. The stranger said hello.
        Victor worked in his lab.
        """

        characters = [
            make_character("Victor", chapters=[1], mention_count=50),
        ]

        issues = agent._check_missing_agentive_descriptions(text, characters)

        # Should not flag "the stranger" (only 2 occurrences, threshold is 10)
        stranger_issues = [i for i in issues if "stranger" in i.description.lower()]
        assert len(stranger_issues) == 0

    def test_skips_common_non_character_phrases(self, agent):
        """Verify common non-character phrases are not flagged."""
        text = """
        The door opened. The door closed. The door stood there.
        The room looked empty. The room turned cold.
        The time came. The day ended. The way seemed clear.
        """ * 10  # Repeat to exceed threshold

        characters = []

        issues = agent._check_missing_agentive_descriptions(text, characters)

        # Should not flag "the door", "the room", etc.
        for issue in issues:
            assert "door" not in issue.description.lower()
            assert "room" not in issue.description.lower()
            assert "time" not in issue.description.lower()


class TestVerificationIntegration:
    """Integration tests for verify() method with new checks."""

    @pytest.fixture
    def agent(self):
        """Create a CharacterAgent for testing."""
        return CharacterAgent()

    def test_verify_catches_pronoun_entries(self, agent):
        """Verify that verify() catches pronoun entries."""
        character_map = CharacterMap(
            characters=[
                make_character("he", chapters=[1], mention_count=100),
                make_character("Victor", chapters=[1, 2], mention_count=50),
            ],
            low_confidence_characters=[],
            total_mentions=150,
            total_chapters=2,
            pipeline_metadata={},
        )

        result = AgentResult(
            data=character_map,
            high_confidence_count=2,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[],
        )

        verification = agent.verify(result)

        # Should not pass due to pronoun entry (error severity)
        assert not verification.passed
        pronoun_issues = [i for i in verification.issues if "pronoun/determiner" in i.description.lower()]
        assert len(pronoun_issues) >= 1


class TestRefineAutoRemoval:
    """Test refine() method auto-removes pronoun entries."""

    @pytest.fixture
    def agent(self):
        """Create a CharacterAgent for testing."""
        return CharacterAgent()

    def test_refine_removes_pronoun_entries(self, agent):
        """Verify refine() removes pronoun entries."""
        character_map = CharacterMap(
            characters=[
                make_character("he", chapters=[1], mention_count=100),
                make_character("Victor", chapters=[1, 2], mention_count=50),
            ],
            low_confidence_characters=[],
            total_mentions=150,
            total_chapters=2,
            pipeline_metadata={},
        )

        result = AgentResult(
            data=character_map,
            high_confidence_count=2,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[],
        )

        issues = [
            VerificationIssue(
                description="Character 'he' is a pronoun/determiner and should not be a character",
                severity="error",
                suggested_fix="Remove this entry",
            )
        ]

        refined = agent.refine(result, issues)

        # Should have removed "he"
        assert len(refined.data.characters) == 1
        assert refined.data.characters[0].canonical_name == "Victor"
        assert refined.data.pipeline_metadata.get("pronoun_entries_removed") == 1

    def test_refine_keeps_real_characters(self, agent):
        """Verify refine() keeps non-pronoun characters."""
        character_map = CharacterMap(
            characters=[
                make_character("Victor", chapters=[1, 2], mention_count=50),
                make_character("Elizabeth", chapters=[1], mention_count=30),
            ],
            low_confidence_characters=[],
            total_mentions=80,
            total_chapters=2,
            pipeline_metadata={},
        )

        result = AgentResult(
            data=character_map,
            high_confidence_count=2,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[],
        )

        # No pronoun issues
        issues = []

        refined = agent.refine(result, issues)

        # Should keep both characters
        assert len(refined.data.characters) == 2


class TestDisjointChapterDistributionCheck:
    """Test _check_disjoint_distributions() method (Feature F1)."""

    @pytest.fixture
    def agent(self):
        """Create a CharacterAgent for testing."""
        return CharacterAgent()

    def test_flags_sequential_disjoint_characters(self, agent):
        """Verify sequential disjoint characters are flagged."""
        # Cathy appears in chapters 1-10, Kate in chapters 15-25
        characters = [
            make_character("Cathy", chapters=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], mention_count=50),
            make_character("Kate", chapters=[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25], mention_count=45),
            make_character("Adam", chapters=[1, 5, 10, 15, 20, 25], mention_count=30),
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=25)

        # Should flag Cathy and Kate as potentially same character
        assert len(issues) == 1
        assert "Cathy" in issues[0].description
        assert "Kate" in issues[0].description
        assert "could be same character" in issues[0].description.lower()
        assert issues[0].severity == "warning"

    def test_no_flag_for_overlapping_chapters(self, agent):
        """Verify characters with overlapping chapters are not flagged."""
        characters = [
            make_character("Tom", chapters=[1, 2, 3, 4, 5], mention_count=50),
            make_character("Daisy", chapters=[3, 4, 5, 6, 7], mention_count=40),
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=10)

        # Should not flag - they have significant overlap
        assert len(issues) == 0

    def test_no_flag_for_non_sequential_disjoint(self, agent):
        """Verify non-sequential disjoint characters are not flagged."""
        # Character A in chapters 5-10, Character B in chapters 1-3
        # Non-sequential because B ends before A begins, but they're interspersed
        characters = [
            make_character("PlotlineA", chapters=[1, 3, 5, 7, 9], mention_count=30),  # Odd chapters
            make_character("PlotlineB", chapters=[2, 4, 6, 8, 10], mention_count=30),  # Even chapters
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=10)

        # Should not flag - these are parallel plots, not sequential
        assert len(issues) == 0

    def test_no_flag_for_low_mention_count(self, agent):
        """Verify characters with low mention counts are not checked."""
        characters = [
            make_character("MinorA", chapters=[1, 2, 3], mention_count=5),  # Below threshold
            make_character("MinorB", chapters=[7, 8, 9], mention_count=5),  # Below threshold
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=10)

        # Should not flag - mention counts below MIN_MENTIONS (10)
        assert len(issues) == 0

    def test_no_flag_when_already_aliases(self, agent):
        """Verify characters that are already aliases don't get flagged."""
        characters = [
            make_character("Cathy", aliases=["Kate", "Catherine"], chapters=[1, 2, 3, 4, 5], mention_count=50),
            make_character("Kate", chapters=[10, 11, 12, 13, 14, 15], mention_count=45),
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=15)

        # Should not flag - Kate is already an alias of Cathy
        assert len(issues) == 0

    def test_correct_order_in_description(self, agent):
        """Verify the earlier character is listed first in the description."""
        # Kate appears first (chapters 1-5), Cathy later (chapters 10-15)
        characters = [
            make_character("Cathy", chapters=[10, 11, 12, 13, 14, 15], mention_count=50),
            make_character("Kate", chapters=[1, 2, 3, 4, 5], mention_count=45),
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=15)

        assert len(issues) == 1
        # Kate should be listed first (earlier chapters)
        desc = issues[0].description
        kate_pos = desc.find("Kate")
        cathy_pos = desc.find("Cathy")
        assert kate_pos < cathy_pos, "Earlier character should appear first in description"

    def test_jaccard_calculation(self, agent):
        """Verify that dominant range heuristic catches characters with disjoint ranges (Feature F4)."""
        # Feature F4: Relaxed Disjoint Distribution Heuristic
        # Uses 80% dominant chapter ranges instead of strict separation
        # CharA dominant range: chapters 1-8 (80% of 10 chapters = 8 chapters)
        # CharB dominant range: chapters 20-27 (80% of 10 chapters = 8 chapters)
        # These are disjoint, so should be flagged
        characters = [
            make_character("CharA", chapters=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], mention_count=50),
            make_character("CharB", chapters=[10, 20, 21, 22, 23, 24, 25, 26, 27, 28], mention_count=45),
        ]

        issues = agent._check_disjoint_distributions(characters, total_chapters=28)

        # Feature F4: Dominant ranges (1-8) and (20-27) are disjoint and sequential
        # This should flag because the 80% dominant ranges don't overlap
        assert len(issues) == 1
        assert "CharA" in issues[0].description
        assert "CharB" in issues[0].description

    def test_integration_with_verify(self, agent):
        """Verify that verify() includes disjoint distribution check."""
        character_map = CharacterMap(
            characters=[
                make_character("Cathy", chapters=[1, 2, 3, 4, 5], mention_count=50),
                make_character("Kate", chapters=[10, 11, 12, 13, 14, 15], mention_count=45),
            ],
            low_confidence_characters=[],
            total_mentions=95,
            total_chapters=15,
            pipeline_metadata={},
        )

        result = AgentResult(
            data=character_map,
            high_confidence_count=2,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[],
        )

        verification = agent.verify(result)

        # Should find disjoint distribution issue
        disjoint_issues = [i for i in verification.issues if "disjoint" in i.description.lower()]
        assert len(disjoint_issues) == 1
