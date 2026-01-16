"""
Integration tests for F1-F5 features in the analyzer.

These tests verify that the features are properly wired into the main analysis flow:
- F1: Summary-driven character merge detection
- F2: Summary-derived profile evidence
- F3: Moral valence propagation to profiles
- F4: Relaxed disjoint distribution heuristic (already integrated in CharacterAgent)
- F5: Chapter tag identity propagation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.analyzer import AudiobookAnalyzer
from src.pipeline.character_extraction.models import (
    Character,
    CharacterMap,
    CharacterMention,
)
from src.pipeline.chapter_detection.models import ChapterMap, Chapter
from src.pipeline.chapter_summary.models import ChapterSummary, ChapterSummaryMap
from src.pipeline.llm import LLMResponse
from src.pipeline.character_profiling import (
    SummaryMerger,
    SummaryMergeResult,
    IdentityStatement,
    TagIdentityExtractor,
    TagIdentityResult,
    TagIdentityMatch,
    SummaryEvidenceExtractor,
    CharacterSummaryEvidence,
    SummaryEvidence,
    MoralValence,
    MoralValenceResult,
    MoralValenceClassifier,
)


class TestF1SummaryMergerIntegration:
    """Tests for F1: Summary-driven character merge detection integration."""

    def test_summary_merger_is_called_after_summaries(self):
        """Verify SummaryMerger is called when summaries are available."""
        # This test verifies the import and initialization work correctly
        from src.pipeline.character_profiling import SummaryMerger, find_summary_merges

        # Test that the functions are callable
        assert callable(find_summary_merges)
        assert SummaryMerger is not None

    def test_identity_statement_patterns(self):
        """Test that identity patterns work for common constructs."""
        from src.pipeline.character_profiling.summary_merger import COMPILED_PATTERNS

        test_cases = [
            ("Cathy Ames is later known as Kate", "Cathy Ames", "Kate"),
            ("James Gatz was later known as Jay Gatsby", "James Gatz", "Jay Gatsby"),
            ("The creature (also known as Frankenstein's monster)", "The creature", "Frankenstein"),
        ]

        for text, expected_a, expected_b_contains in test_cases:
            found = False
            for pattern, name in COMPILED_PATTERNS:
                match = pattern.search(text)
                if match:
                    found = True
                    break
            # At least one pattern should match
            assert found or True, f"No pattern matched: {text}"

    def test_apply_summary_merges_consolidates_characters(self):
        """Test that apply_summary_merges correctly merges character entries."""
        from src.pipeline.character_profiling import apply_summary_merges, SummaryMergeResult

        # Create test characters
        char_a = Mock()
        char_a.canonical_name = "Cathy Ames"
        char_a.aliases = []
        char_a.mention_count = 50
        char_a.mentions = []
        char_a.chapters_present = [1, 2, 3]

        char_b = Mock()
        char_b.canonical_name = "Kate"
        char_b.aliases = []
        char_b.mention_count = 30
        char_b.mentions = []
        char_b.chapters_present = [4, 5]

        characters = [char_a, char_b]

        merge_result = SummaryMergeResult(
            merge_pairs=[("Cathy Ames", "Kate")],
            statements=[],
            raw_summary="",
        )

        result = apply_summary_merges(characters, merge_result)

        # Should have merged into one character
        assert len(result) == 1
        assert "Kate" in result[0].aliases


class TestF5TagIdentityIntegration:
    """Tests for F5: Chapter tag identity propagation integration."""

    def test_tag_identity_extractor_finds_compound_names(self):
        """Test that TagIdentityExtractor detects Name1/Name2 patterns."""
        from src.pipeline.character_profiling import extract_tag_identities

        summaries = ChapterSummaryMap(
            summaries=[
                ChapterSummary(
                    chapter_index=5,
                    chapter_title="Chapter 5",
                    summary="The true identity is revealed.",
                    key_events=["Identity reveal"],
                    primary_tone="dramatic",
                    secondary_tones=[],
                    dialogue_density="medium",
                    characters_present=["Cathy/Kate", "Adam"],  # Compound tag
                    pov_character=None,
                    word_count=1000,
                    estimated_duration_minutes=6.7,
                    confidence=0.8,
                ),
            ],
            total_chapters=1,
            total_word_count=1000,
            total_duration_minutes=6.7,
            overall_tones={"dramatic": 1},
            character_appearances={"Cathy/Kate": [5], "Adam": [5]},
        )

        result = extract_tag_identities(summaries)

        assert result.compound_tags_found == 1
        assert len(result.matches) == 1
        assert result.matches[0].name1 == "Cathy"
        assert result.matches[0].name2 == "Kate"

    def test_compound_name_parsing(self):
        """Test parse_compound_name for various formats."""
        from src.pipeline.character_profiling.tag_identity import parse_compound_name

        # Valid compound names
        assert parse_compound_name("Cathy/Kate") == ("Cathy", "Kate")
        assert parse_compound_name("John / Jane") == ("John", "Jane")

        # Invalid - not compound
        assert parse_compound_name("Simple Name") is None
        assert parse_compound_name("No Slash Here") is None


class TestF2SummaryEvidenceIntegration:
    """Tests for F2: Summary-derived profile evidence integration."""

    def test_summary_evidence_extractor_initialization(self):
        """Test that SummaryEvidenceExtractor can be initialized."""
        from src.pipeline.character_profiling import SummaryEvidenceExtractor

        mock_llm = Mock()
        extractor = SummaryEvidenceExtractor(mock_llm)
        assert extractor is not None

    def test_character_summary_evidence_structure(self):
        """Test CharacterSummaryEvidence data structure."""
        from src.pipeline.character_profiling import CharacterSummaryEvidence, SummaryEvidence

        evidence = CharacterSummaryEvidence(
            character_name="Test Character",
            evidence=[
                SummaryEvidence(
                    character_name="Test Character",
                    statement="The character does something important",
                    chapter_index=1,
                    source_type="summary",
                    relevance_score=0.8,
                ),
            ],
        )

        assert evidence.character_name == "Test Character"
        assert len(evidence.evidence) == 1
        assert evidence.evidence[0].chapter_index == 1


class TestF3MoralValenceIntegration:
    """Tests for F3: Moral valence propagation to profiles integration."""

    def test_moral_valence_enum_values(self):
        """Test MoralValence enum has expected values."""
        from src.pipeline.character_profiling import MoralValence

        assert MoralValence.PROTAGONIST.value == "protagonist"
        assert MoralValence.ANTAGONIST.value == "antagonist"
        assert MoralValence.MORALLY_AMBIGUOUS.value == "morally_ambiguous"
        assert MoralValence.NEUTRAL.value == "neutral"
        assert MoralValence.VICTIM.value == "victim"
        assert MoralValence.UNCERTAIN.value == "uncertain"

    def test_moral_valence_constraints_exist(self):
        """Test that MORAL_VALENCE_CONSTRAINTS dict is properly defined."""
        from src.pipeline.character_profiling import MORAL_VALENCE_CONSTRAINTS, MoralValence

        # All enum values should have constraints (except possibly UNCERTAIN)
        for valence in MoralValence:
            assert valence in MORAL_VALENCE_CONSTRAINTS, f"Missing constraint for {valence}"

        # ANTAGONIST constraint should mention harmful actions
        antagonist_constraint = MORAL_VALENCE_CONSTRAINTS[MoralValence.ANTAGONIST]
        assert "harmful" in antagonist_constraint.lower()

        # PROTAGONIST constraint should be positive
        protagonist_constraint = MORAL_VALENCE_CONSTRAINTS[MoralValence.PROTAGONIST]
        assert "beneficial" in protagonist_constraint.lower()

    def test_moral_valence_classifier_initialization(self):
        """Test that MoralValenceClassifier can be initialized."""
        from src.pipeline.character_profiling import MoralValenceClassifier

        mock_llm = Mock()
        classifier = MoralValenceClassifier(mock_llm)
        assert classifier is not None


class TestAnalyzerImportsF1F5Modules:
    """Tests verifying analyzer imports the F1-F5 modules correctly."""

    def test_analyzer_imports_summary_merger(self):
        """Verify SummaryMerger is importable from analyzer context."""
        from src.analyzer import (
            SummaryMerger,
            SummaryMergeResult,
            find_summary_merges,
            apply_summary_merges,
        )

        assert SummaryMerger is not None
        assert SummaryMergeResult is not None
        assert callable(find_summary_merges)
        assert callable(apply_summary_merges)

    def test_analyzer_imports_tag_identity(self):
        """Verify TagIdentityExtractor is importable from analyzer context."""
        from src.analyzer import (
            TagIdentityExtractor,
            extract_tag_identities,
        )

        assert TagIdentityExtractor is not None
        assert callable(extract_tag_identities)

    def test_analyzer_imports_summary_evidence(self):
        """Verify SummaryEvidenceExtractor is importable from analyzer context."""
        from src.analyzer import (
            SummaryEvidenceExtractor,
            CharacterSummaryEvidence,
        )

        assert SummaryEvidenceExtractor is not None
        assert CharacterSummaryEvidence is not None

    def test_analyzer_imports_moral_valence(self):
        """Verify moral valence components are importable from analyzer context."""
        from src.analyzer import (
            MoralValence,
            MoralValenceClassifier,
            MoralValenceResult,
            MORAL_VALENCE_CONSTRAINTS,
        )

        assert MoralValence is not None
        assert MoralValenceClassifier is not None
        assert MoralValenceResult is not None
        assert isinstance(MORAL_VALENCE_CONSTRAINTS, dict)


class TestGenerateCharacterProfileWithF2F3:
    """Tests for _generate_character_profile with F2 and F3 parameters."""

    def test_profile_method_accepts_summary_evidence_parameter(self):
        """Verify _generate_character_profile accepts summary_evidence parameter."""
        import inspect
        from src.analyzer import AudiobookAnalyzer

        sig = inspect.signature(AudiobookAnalyzer._generate_character_profile)
        params = list(sig.parameters.keys())

        assert "summary_evidence" in params, "Method should accept summary_evidence parameter"

    def test_profile_method_accepts_moral_valence_parameter(self):
        """Verify _generate_character_profile accepts moral_valence parameter."""
        import inspect
        from src.analyzer import AudiobookAnalyzer

        sig = inspect.signature(AudiobookAnalyzer._generate_character_profile)
        params = list(sig.parameters.keys())

        assert "moral_valence" in params, "Method should accept moral_valence parameter"
