"""
Structure analysis module.
Detects and classifies structural elements in book text.
"""

import re
from typing import Optional
from dataclasses import dataclass

from ..models import (
    StructuralElement, 
    StructureType, 
    ConfidenceLevel,
)
from ..ingestion.base import ExtractedDocument


@dataclass
class StructurePattern:
    """A pattern for detecting structural elements."""
    pattern: str
    structure_type: StructureType
    confidence: ConfidenceLevel
    flags: int = re.MULTILINE | re.IGNORECASE
    requires_blank_before: bool = False  # Must have blank line before
    requires_blank_after: bool = False   # Must have blank line after


# Patterns ordered by specificity (most specific first)
STRUCTURE_PATTERNS = [
    # Prologue/Epilogue (high confidence - explicit labels)
    StructurePattern(
        r'^(?P<title>PROLOGUE|Prologue)(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.PROLOGUE,
        ConfidenceLevel.HIGH,
    ),
    StructurePattern(
        r'^(?P<title>EPILOGUE|Epilogue)(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.EPILOGUE,
        ConfidenceLevel.HIGH,
    ),
    
    # Part headers
    StructurePattern(
        r'^(?P<title>(?:PART|Part)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten))(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.PART,
        ConfidenceLevel.HIGH,
    ),
    
    # Chapter headers (various formats)
    StructurePattern(
        r'^(?P<title>Chapter\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Twenty[- ]?(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine)))(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.CHAPTER,
        ConfidenceLevel.HIGH,
    ),
    StructurePattern(
        r'^(?P<title>CHAPTER\s+(?:\d+|[IVXLC]+))(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.CHAPTER,
        ConfidenceLevel.HIGH,
    ),
    
    # Scene breaks
    StructurePattern(
        r'^(?P<title>\*\s*\*\s*\*|\*{3,}|#\s*#\s*#|#{3,}|-\s*-\s*-|-{3,}|~\s*~\s*~|~{3,})$',
        StructureType.SCENE_BREAK,
        ConfidenceLevel.HIGH,
    ),
    
    # Journal entries / dated sections
    StructurePattern(
        r'^(?P<title>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4})',
        StructureType.JOURNAL_ENTRY,
        ConfidenceLevel.MEDIUM,
    ),
    StructurePattern(
        r'^(?P<title>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        StructureType.JOURNAL_ENTRY,
        ConfidenceLevel.MEDIUM,
    ),
    StructurePattern(
        r'^(?P<title>Dear\s+(?:Diary|Journal))',
        StructureType.JOURNAL_ENTRY,
        ConfidenceLevel.HIGH,
    ),
    
    # Letters
    StructurePattern(
        r'^(?P<title>Dear\s+(?:Mr\.|Mrs\.|Ms\.|Miss|Dr\.|[A-Z][a-z]+)(?:\s+[A-Z][a-z]+)?)',
        StructureType.LETTER,
        ConfidenceLevel.MEDIUM,
    ),
    
    # Epigraphs (often italicized quotes at chapter starts - harder to detect without formatting)
    # This is a medium confidence pattern - may need LLM refinement
    StructurePattern(
        r'^(?P<title>"[^"]{20,200}"\s*\n\s*[-–—]\s*[A-Z][^\n]+)',
        StructureType.EPIGRAPH,
        ConfidenceLevel.MEDIUM,
    ),
    
    # Appendix
    StructurePattern(
        r'^(?P<title>(?:APPENDIX|Appendix)(?:\s+[A-Z\d]+)?)(?:\s*[:\-–—]\s*(?P<subtitle>[^\n]+))?',
        StructureType.APPENDIX,
        ConfidenceLevel.HIGH,
    ),
]


class StructureAnalyzer:
    """Analyzes text to detect structural elements."""
    
    def __init__(
        self,
        words_per_minute: int = 150,
        include_scene_breaks: bool = True,
        min_chapter_words: int = 100,  # Minimum words to consider a valid chapter
    ):
        self.words_per_minute = words_per_minute
        self.include_scene_breaks = include_scene_breaks
        self.min_chapter_words = min_chapter_words
    
    def analyze(self, doc: ExtractedDocument) -> list[StructuralElement]:
        """
        Analyze document structure.
        
        Uses pre-detected chapters from ingestion if available,
        then enhances with pattern detection.
        """
        text = doc.text
        elements = []
        
        # Start with chapters from ingestion (if available and usable)
        if doc.chapters:
            elements = self._convert_ingested_chapters(doc.chapters, text)
        
        # Run pattern detection
        pattern_elements = self._detect_patterns(text)
        
        # Merge pattern results with ingested chapters
        elements = self._merge_elements(elements, pattern_elements)
        
        # Calculate metrics for each element
        elements = self._calculate_metrics(elements, text)
        
        # Sort by position
        elements.sort(key=lambda e: e.start_position)
        
        # Assign indices
        self._assign_indices(elements)
        
        return elements
    
    def _convert_ingested_chapters(
        self, 
        chapters: list[dict], 
        text: str
    ) -> list[StructuralElement]:
        """Convert ingested chapter info to StructuralElement objects."""
        elements = []
        
        for ch in chapters:
            # Determine type from title
            title = ch.get('title', '')
            structure_type = self._infer_type_from_title(title)
            
            elements.append(StructuralElement(
                type=structure_type,
                title=title,
                index=0,  # Will be assigned later
                start_position=ch.get('start_pos', 0),
                end_position=ch.get('end_pos', len(text)),
                confidence=ConfidenceLevel.HIGH,  # Came from document structure
            ))
        
        return elements
    
    def _infer_type_from_title(self, title: str) -> StructureType:
        """Infer structure type from a title string."""
        title_lower = title.lower().strip()
        
        if title_lower.startswith('prologue'):
            return StructureType.PROLOGUE
        elif title_lower.startswith('epilogue'):
            return StructureType.EPILOGUE
        elif title_lower.startswith('part'):
            return StructureType.PART
        elif title_lower.startswith('appendix'):
            return StructureType.APPENDIX
        elif title_lower.startswith('chapter') or re.match(r'^[ivxlc]+$', title_lower):
            return StructureType.CHAPTER
        else:
            return StructureType.SECTION
    
    def _detect_patterns(self, text: str) -> list[StructuralElement]:
        """Detect structural elements using regex patterns."""
        elements = []
        
        for pattern_def in STRUCTURE_PATTERNS:
            if not self.include_scene_breaks and pattern_def.structure_type == StructureType.SCENE_BREAK:
                continue
            
            pattern = re.compile(pattern_def.pattern, pattern_def.flags)
            
            for match in pattern.finditer(text):
                title = match.group('title')
                
                # Check for subtitle if captured
                try:
                    subtitle = match.group('subtitle')
                    if subtitle:
                        title = f"{title}: {subtitle.strip()}"
                except IndexError:
                    pass
                
                # Validate context if required
                if pattern_def.requires_blank_before:
                    before_text = text[max(0, match.start()-3):match.start()]
                    if '\n\n' not in before_text and match.start() > 2:
                        continue
                
                elements.append(StructuralElement(
                    type=pattern_def.structure_type,
                    title=title.strip(),
                    index=0,
                    start_position=match.start(),
                    end_position=match.end(),  # Will be adjusted
                    confidence=pattern_def.confidence,
                ))
        
        return elements
    
    def _merge_elements(
        self,
        primary: list[StructuralElement],
        secondary: list[StructuralElement],
    ) -> list[StructuralElement]:
        """Merge two lists of elements, preferring primary on conflicts."""
        if not primary:
            return secondary
        if not secondary:
            return primary
        
        # Build position set from primary elements
        primary_positions = set()
        for elem in primary:
            # Consider positions within 50 chars as the same location
            for offset in range(-50, 51):
                primary_positions.add(elem.start_position + offset)
        
        # Add non-conflicting secondary elements
        result = list(primary)
        for elem in secondary:
            if elem.start_position not in primary_positions:
                # Also add scene breaks even if near chapter markers
                if elem.type == StructureType.SCENE_BREAK:
                    result.append(elem)
                elif elem.type not in (StructureType.CHAPTER, StructureType.PART):
                    # Add non-chapter structural elements
                    result.append(elem)
        
        return result
    
    def _calculate_metrics(
        self,
        elements: list[StructuralElement],
        text: str,
    ) -> list[StructuralElement]:
        """Calculate word counts and duration estimates."""
        # Sort by position first
        elements.sort(key=lambda e: e.start_position)

        # Adjust end positions based on next element
        for i, elem in enumerate(elements):
            if i < len(elements) - 1:
                elem.end_position = elements[i + 1].start_position
            else:
                elem.end_position = len(text)

            # Calculate word count
            section_text = text[elem.start_position:elem.end_position]
            elem.word_count = len(section_text.split())

            # Calculate estimated duration
            elem.estimated_duration_minutes = elem.word_count / self.words_per_minute

        # Filter out TOC entries - chapters with very low word counts
        # This handles Project Gutenberg files that have a TOC at the start
        elements = self._filter_toc_entries(elements)

        return elements

    def _filter_toc_entries(
        self,
        elements: list[StructuralElement],
    ) -> list[StructuralElement]:
        """
        Filter out probable table of contents entries.

        TOC entries are detected as chapters but have minimal word counts
        because they're just listings like "I", "II", "III" etc.
        """
        # Find chapters that are likely TOC entries
        # Criteria: CHAPTER type with word_count < min_chapter_words
        # But only filter if there are also "real" chapters with substantial content

        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        other_elements = [e for e in elements if e.type != StructureType.CHAPTER]

        if not chapters:
            return elements

        # Check if we have a mix of tiny and substantial chapters
        tiny_chapters = [c for c in chapters if c.word_count < self.min_chapter_words]
        substantial_chapters = [c for c in chapters if c.word_count >= self.min_chapter_words]

        # Only filter if:
        # 1. There are both tiny and substantial chapters
        # 2. Tiny chapters appear at the start (typical TOC position)
        # 3. There are multiple tiny chapters in a row (TOC pattern)
        if not tiny_chapters or not substantial_chapters:
            return elements

        # Check if tiny chapters are clustered at the beginning
        chapters_sorted = sorted(chapters, key=lambda c: c.start_position)

        # Count consecutive tiny chapters at the start
        consecutive_tiny = 0
        for ch in chapters_sorted:
            if ch.word_count < self.min_chapter_words:
                consecutive_tiny += 1
            else:
                break

        # If we have 3+ consecutive tiny chapters at start, it's likely a TOC
        if consecutive_tiny >= 3:
            # Filter out the tiny chapters at the start
            filtered_chapters = []
            for ch in chapters_sorted:
                if ch.word_count >= self.min_chapter_words:
                    filtered_chapters.append(ch)
                elif ch.start_position > chapters_sorted[consecutive_tiny - 1].start_position:
                    # Keep tiny chapters that appear after the TOC section
                    filtered_chapters.append(ch)

            # Re-index the remaining chapters
            for i, ch in enumerate(filtered_chapters):
                ch.index = i + 1

            return other_elements + filtered_chapters

        return elements
    
    def _assign_indices(self, elements: list[StructuralElement]) -> None:
        """Assign sequential indices within each type."""
        type_counters = {}
        
        for elem in elements:
            if elem.type not in type_counters:
                type_counters[elem.type] = 0
            type_counters[elem.type] += 1
            elem.index = type_counters[elem.type]


def analyze_structure(
    doc: ExtractedDocument,
    words_per_minute: int = 150,
) -> list[StructuralElement]:
    """
    Convenience function to analyze document structure.
    
    Args:
        doc: Extracted document to analyze
        words_per_minute: Narration pace for duration estimates
        
    Returns:
        List of detected structural elements
    """
    analyzer = StructureAnalyzer(words_per_minute=words_per_minute)
    return analyzer.analyze(doc)
