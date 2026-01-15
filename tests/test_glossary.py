"""Tests for glossary extraction."""

import pytest
from src.ingestion.glossary import extract_glossary, GlossaryEntry, GlossaryExtractionResult
from src.ingestion.regions import DocumentRegion, RegionType


class TestGlossaryExtraction:
    """Test the glossary extraction functionality."""

    def test_extract_colon_format(self):
        """Test extraction of colon-separated glossary entries."""
        text = """
Chapter 1

Story content here...

Glossary

Aardvark: A nocturnal mammal native to Africa that feeds primarily on ants and termites.
Baroque: An ornate artistic style from the 17th century characterized by elaborate detail.
Cadence: The rhythm or flow of sounds in music or speech, often marking the end of a phrase.
Django: A high-level Python web framework that encourages rapid development.
"""
        regions = [
            DocumentRegion(
                region_type=RegionType.BACK_MATTER,
                start_position=text.index("Glossary"),
                end_position=len(text),
                label="glossary",
            )
        ]

        result = extract_glossary(text, regions)

        assert result is not None
        assert len(result.entries) == 4
        assert result.extraction_method == "colon"

        # Check first entry
        aardvark = next(e for e in result.entries if e.term == "Aardvark")
        assert "nocturnal mammal" in aardvark.definition

        # Check entries are sorted alphabetically
        terms = [e.term for e in result.entries]
        assert terms == sorted(terms)

    def test_extract_dash_format(self):
        """Test extraction of dash-separated glossary entries."""
        text = """
Glossary

Alpha - The first letter of the Greek alphabet, used to denote the first in a series.
Beta - The second letter of the Greek alphabet, often used for testing versions.
Gamma - The third letter of the Greek alphabet, representing a specific type of radiation.
Delta - The fourth letter of the Greek alphabet, symbolizing change in mathematics.
"""
        regions = [
            DocumentRegion(
                region_type=RegionType.BACK_MATTER,
                start_position=0,
                end_position=len(text),
                label="glossary",
            )
        ]

        result = extract_glossary(text, regions)

        assert result is not None
        assert len(result.entries) == 4
        assert result.extraction_method == "dash"

    def test_no_glossary_region(self):
        """Test behavior when no glossary region exists."""
        text = "Just some regular text without a glossary"
        regions = []

        result = extract_glossary(text, regions)

        assert result is None

    def test_glossary_region_with_non_glossary_label(self):
        """Test that non-glossary regions are ignored."""
        text = """
About the Author

Some author biography text here.
"""
        regions = [
            DocumentRegion(
                region_type=RegionType.BACK_MATTER,
                start_position=0,
                end_position=len(text),
                label="about_author",
            )
        ]

        result = extract_glossary(text, regions)

        assert result is None

    def test_glossary_with_few_entries_not_extracted(self):
        """Test that glossaries with fewer than 3 entries are not extracted."""
        text = """
Glossary

Alpha: First letter only.
Beta: Second letter only.
"""
        regions = [
            DocumentRegion(
                region_type=RegionType.BACK_MATTER,
                start_position=0,
                end_position=len(text),
                label="glossary",
            )
        ]

        result = extract_glossary(text, regions)

        # Should return None because we need at least 3 entries to confirm format
        assert result is None

    def test_glossary_skips_short_definitions(self):
        """Test that entries with very short definitions are skipped."""
        text = """
Glossary

Valid: This is a valid definition that has enough content to be useful.
Short: Yes.
Another: This is another valid definition with sufficient content to be useful.
Third: This has enough content to make it a valid entry for the glossary.
"""
        regions = [
            DocumentRegion(
                region_type=RegionType.BACK_MATTER,
                start_position=0,
                end_position=len(text),
                label="glossary",
            )
        ]

        result = extract_glossary(text, regions)

        if result:
            # Short definitions (< 10 chars) should be skipped
            terms = [e.term for e in result.entries]
            assert "Short" not in terms


class TestGlossaryModels:
    """Test glossary model classes."""

    def test_glossary_entry_creation(self):
        """Test creating a GlossaryEntry."""
        entry = GlossaryEntry(
            term="Test",
            definition="A test definition",
            position=100,
            confidence=0.9
        )
        assert entry.term == "Test"
        assert entry.definition == "A test definition"
        assert entry.position == 100
        assert entry.confidence == 0.9

    def test_glossary_extraction_result_creation(self):
        """Test creating a GlossaryExtractionResult."""
        entries = [
            GlossaryEntry(term="A", definition="First", position=0, confidence=0.9),
            GlossaryEntry(term="B", definition="Second", position=50, confidence=0.9),
        ]
        result = GlossaryExtractionResult(
            entries=entries,
            region_start=0,
            region_end=100,
            extraction_method="colon"
        )
        assert len(result.entries) == 2
        assert result.region_start == 0
        assert result.region_end == 100
        assert result.extraction_method == "colon"


class TestGlossaryMap:
    """Test the GlossaryMap model from models.py."""

    def test_entries_by_letter(self):
        """Test grouping entries by first letter."""
        from src.models import GlossaryEntry as ModelEntry, GlossaryMap

        entries = [
            ModelEntry(term="Apple", definition="A fruit"),
            ModelEntry(term="Banana", definition="Another fruit"),
            ModelEntry(term="Apricot", definition="Yet another fruit"),
            ModelEntry(term="Cherry", definition="A red fruit"),
        ]
        glossary = GlossaryMap(entries=entries)

        by_letter = glossary.entries_by_letter()

        assert "A" in by_letter
        assert "B" in by_letter
        assert "C" in by_letter
        assert len(by_letter["A"]) == 2
        assert len(by_letter["B"]) == 1
        assert len(by_letter["C"]) == 1

    def test_entries_by_letter_with_special_chars(self):
        """Test that non-alphabetic first chars are grouped under '#'."""
        from src.models import GlossaryEntry as ModelEntry, GlossaryMap

        entries = [
            ModelEntry(term="123Test", definition="Numeric start"),
            ModelEntry(term="Apple", definition="Normal"),
        ]
        glossary = GlossaryMap(entries=entries)

        by_letter = glossary.entries_by_letter()

        assert "#" in by_letter
        assert "A" in by_letter

    def test_is_empty(self):
        """Test the is_empty property."""
        from src.models import GlossaryMap, GlossaryEntry as ModelEntry

        empty_glossary = GlossaryMap()
        assert empty_glossary.is_empty is True

        non_empty = GlossaryMap(entries=[ModelEntry(term="Test", definition="Def")])
        assert non_empty.is_empty is False
