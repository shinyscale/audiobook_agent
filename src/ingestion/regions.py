"""
Document region detection for front/back matter filtering.

Detects non-narrative content (copyright pages, table of contents, author bio, etc.)
so it can be excluded from pronunciation analysis.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Types of document regions."""

    FRONT_MATTER = "front_matter"  # Copyright, dedication, TOC, etc.
    BODY = "body"  # Main story content
    BACK_MATTER = "back_matter"  # About author, also by, etc.


@dataclass
class DocumentRegion:
    """A classified region of the document."""

    region_type: RegionType
    start_position: int
    end_position: int
    label: str  # e.g., "copyright_page", "table_of_contents"
    confidence: float = 0.8

    def __post_init__(self):
        # Ensure positions are valid
        if self.start_position < 0:
            self.start_position = 0
        if self.end_position < self.start_position:
            self.end_position = self.start_position

    def contains(self, position: int) -> bool:
        """Check if a position falls within this region."""
        return self.start_position <= position < self.end_position

    @property
    def length(self) -> int:
        """Length of the region in characters."""
        return self.end_position - self.start_position

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.region_type.value,
            "start": self.start_position,
            "end": self.end_position,
            "label": self.label,
            "confidence": self.confidence,
        }


# Patterns for detecting front matter
# Each tuple: (compiled_pattern, label, confidence)
FRONT_MATTER_PATTERNS = [
    # Project Gutenberg header boilerplate
    (
        re.compile(r"\*\*\*\s*START\s+OF\s+(THE\s+)?PROJECT\s+GUTENBERG", re.IGNORECASE),
        "gutenberg_header",
        0.99,
    ),
    (re.compile(r"The\s+Project\s+Gutenberg\s+eBook", re.IGNORECASE), "gutenberg_header", 0.95),
    # Copyright notices
    (
        re.compile(r"(?im)^\s*(copyright|©|copr\.)\s*(\d{4}|by)", re.MULTILINE),
        "copyright_page",
        0.95,
    ),
    (re.compile(r"(?im)^\s*all\s+rights\s+reserved", re.MULTILINE), "copyright_page", 0.95),
    (re.compile(r"(?im)^\s*ISBN[\s:\-]*[\d\-X]{10,}", re.MULTILINE), "isbn_page", 0.95),
    # TOC
    (
        re.compile(r"(?im)^\s*(table\s+of\s+contents|contents)\s*$", re.MULTILINE),
        "table_of_contents",
        0.95,
    ),
    # Front matter sections
    (re.compile(r"(?im)^\s*dedication\s*$", re.MULTILINE), "dedication", 0.85),
    (re.compile(r"(?im)^\s*for\s+\w+[,\s]*$", re.MULTILINE), "dedication", 0.6),
    (
        re.compile(r"(?im)^\s*(acknowledgements?|acknowledgments?)\s*$", re.MULTILINE),
        "acknowledgements",
        0.9,
    ),
    (re.compile(r"(?im)^\s*(preface|foreword|introduction)\s*$", re.MULTILINE), "preface", 0.8),
    (re.compile(r"(?im)^\s*epigraph\s*$", re.MULTILINE), "epigraph", 0.9),
    (re.compile(r"(?im)^\s*note\s+to\s+(the\s+)?reader", re.MULTILINE), "author_note", 0.9),
    # Publisher info
    (
        re.compile(r"(?im)(first\s+(edition|printing|published)|published\s+by)", re.MULTILINE),
        "publisher_info",
        0.9,
    ),
    (re.compile(r"(?im)(printed\s+in|manufactured\s+in)", re.MULTILINE), "publisher_info", 0.9),
]

# Patterns for detecting back matter
BACK_MATTER_PATTERNS = [
    # Project Gutenberg license boilerplate
    (
        re.compile(r"\*\*\*\s*END\s+OF\s+(THE\s+)?PROJECT\s+GUTENBERG", re.IGNORECASE),
        "gutenberg_license",
        0.99,
    ),
    (re.compile(r"Project\s+Gutenberg.*License", re.IGNORECASE), "gutenberg_license", 0.95),
    # Author info
    (re.compile(r"(?im)^\s*about\s+the\s+author", re.MULTILINE), "about_author", 0.95),
    (re.compile(r"(?im)^\s*author'?s?\s+note", re.MULTILINE), "author_note", 0.9),
    # Also by
    (
        re.compile(r"(?im)^\s*(also\s+by|other\s+(books?|works?)\s+by)", re.MULTILINE),
        "also_by",
        0.95,
    ),
    (re.compile(r"(?im)^\s*books?\s+by\s+\w+", re.MULTILINE), "also_by", 0.85),
    # Extras
    (
        re.compile(
            r"(?im)^\s*(reading\s+group\s+(guide|questions)|book\s+club\s+questions)", re.MULTILINE
        ),
        "reading_guide",
        0.95,
    ),
    (re.compile(r"(?im)^\s*discussion\s+questions", re.MULTILINE), "reading_guide", 0.95),
    (re.compile(r"(?im)^\s*(excerpt|sneak\s+peek|preview)\s+from", re.MULTILINE), "excerpt", 0.95),
    (re.compile(r"(?im)^\s*(appendix|appendices)\s*(:|$)", re.MULTILINE), "appendix", 0.85),
    (re.compile(r"(?im)^\s*glossary(\s+of\s+.+|\s*:|\s*)$", re.MULTILINE), "glossary", 0.9),
    # Glossary-style headings that don't use the word "glossary"
    # (e.g. "<Topic> Lingo, Acronyms, Weapons and Terminology")
    (
        re.compile(
            r"(?im)^\s*[^\n]{0,60}\b(acronyms|terminology|abbreviations)\b[^\n]{0,40}$",
            re.MULTILINE,
        ),
        "glossary",
        0.8,
    ),
    # Acknowledgments commonly appear at the back of modern books; names there
    # are real people, not characters
    (
        re.compile(r"(?im)^\s*(acknowledgements?|acknowledgments?)\s*$", re.MULTILINE),
        "acknowledgements",
        0.9,
    ),
    (re.compile(r"(?im)^\s*index\s*$", re.MULTILINE), "index", 0.9),
    (
        re.compile(
            r"(?im)^\s*(notes|endnotes|references|(annotated\s+)?bibliography)\s*$",
            re.MULTILINE,
        ),
        "endnotes",
        0.85,
    ),
    # Afterword / afterward (author's closing note) — back matter, real people
    (re.compile(r"(?im)^\s*after(word|ward)\s*$", re.MULTILINE), "afterword", 0.8),
]


class RegionDetector:
    """
    Detects front/back matter regions in documents.

    Uses pattern matching and chapter structure to identify non-narrative content.
    """

    def __init__(self):
        self.front_patterns = FRONT_MATTER_PATTERNS
        self.back_patterns = BACK_MATTER_PATTERNS

    # Only look for back-matter headings in the latter portion of the text.
    # Excludes a front-matter Table-of-Contents line ("Acknowledgements ... 459")
    # and any early in-body section that happens to share a back-matter word.
    BACK_MATTER_MIN_FRACTION = 0.55

    def detect_back_matter_start(self, text: str) -> Optional[int]:
        """Find where back matter begins, independent of chapter structure.

        Scans the latter portion of the text for the EARLIEST standalone
        back-matter heading (glossary, afterword, appendix, bibliography,
        acknowledgements, index, about-the-author, also-by, notes). Returns its
        absolute character offset, or None if no such heading is found.

        Chapter-based detection misses back matter whenever the last detected
        chapter runs to EOF (swallowing it); this is the chapter-independent
        backstop.
        """
        if not text:
            return None
        window_start = int(len(text) * self.BACK_MATTER_MIN_FRACTION)
        window = text[window_start:]
        earliest: Optional[int] = None
        for pattern, _label, _conf in self.back_patterns:
            m = pattern.search(window)
            if m:
                pos = window_start + m.start()
                if earliest is None or pos < earliest:
                    earliest = pos
        return earliest

    def detect_regions(
        self,
        text: str,
        chapters: Optional[list[dict]] = None,
    ) -> list[DocumentRegion]:
        """
        Detect document regions based on patterns and chapter structure.

        Args:
            text: Full document text
            chapters: List of chapter dicts with 'start_pos', 'end_pos', 'title'
                     If None, uses heuristics based on patterns only.

        Returns:
            List of DocumentRegion objects
        """
        regions = []
        text_length = len(text)

        if not chapters:
            # No chapter structure - use pattern-based detection only
            return self._detect_without_chapters(text)

        # Sort chapters by position
        sorted_chapters = sorted(chapters, key=lambda c: c.get("start_pos", 0))

        if not sorted_chapters:
            return self._detect_without_chapters(text)

        first_chapter_start = sorted_chapters[0].get("start_pos", 0)
        last_chapter_end = sorted_chapters[-1].get("end_pos", text_length)

        # Chapter-independent back-matter boundary. The last detected chapter
        # often runs to EOF (swallowing back matter), so the chapter gap alone
        # cannot find it; detect the heading directly.
        back_matter_start = self.detect_back_matter_start(text)
        # The body ends at whichever comes first: the last chapter end or the
        # back-matter heading. Only honor a heading that falls before the
        # nominal chapter end (i.e. inside a chapter that over-extends).
        effective_back_start = last_chapter_end
        if back_matter_start is not None and back_matter_start < last_chapter_end:
            effective_back_start = back_matter_start

        # Detect front matter (before first chapter)
        if first_chapter_start > 500:  # Meaningful front matter threshold
            front_text = text[:first_chapter_start]
            front_regions = self._detect_in_section(
                front_text,
                offset=0,
                patterns=self.front_patterns,
                region_type=RegionType.FRONT_MATTER,
            )

            if front_regions:
                regions.extend(front_regions)
            else:
                # Mark entire pre-chapter section as front matter
                regions.append(
                    DocumentRegion(
                        region_type=RegionType.FRONT_MATTER,
                        start_position=0,
                        end_position=first_chapter_start,
                        label="unclassified_front_matter",
                        confidence=0.7,
                    )
                )

        # Body runs from the first chapter to the effective back-matter start.
        regions.append(
            DocumentRegion(
                region_type=RegionType.BODY,
                start_position=first_chapter_start,
                end_position=effective_back_start,
                label="main_content",
                confidence=1.0,
            )
        )

        # Detect back matter (everything after the body ends)
        if effective_back_start < text_length - 500:
            back_text = text[effective_back_start:]
            back_regions = self._detect_in_section(
                back_text,
                offset=effective_back_start,
                patterns=self.back_patterns,
                region_type=RegionType.BACK_MATTER,
            )

            if back_regions:
                regions.extend(back_regions)
            else:
                # Mark entire post-body section as back matter
                regions.append(
                    DocumentRegion(
                        region_type=RegionType.BACK_MATTER,
                        start_position=effective_back_start,
                        end_position=text_length,
                        label="unclassified_back_matter",
                        confidence=0.7,
                    )
                )

        # Log detection summary
        front_count = sum(1 for r in regions if r.region_type == RegionType.FRONT_MATTER)
        back_count = sum(1 for r in regions if r.region_type == RegionType.BACK_MATTER)
        if front_count or back_count:
            logger.info(f"Detected {front_count} front matter and {back_count} back matter regions")

        return regions

    def _detect_without_chapters(self, text: str) -> list[DocumentRegion]:
        """Detect regions when no chapter structure is available."""
        regions = []
        text_length = len(text)

        # Check first 10% for front matter
        front_boundary = min(text_length // 10, 20000)
        front_text = text[:front_boundary]
        front_regions = self._detect_in_section(
            front_text,
            offset=0,
            patterns=self.front_patterns,
            region_type=RegionType.FRONT_MATTER,
        )
        regions.extend(front_regions)

        # Check last 10% for back matter
        back_start = max(text_length - text_length // 10, text_length - 20000)
        back_text = text[back_start:]
        back_regions = self._detect_in_section(
            back_text,
            offset=back_start,
            patterns=self.back_patterns,
            region_type=RegionType.BACK_MATTER,
        )
        regions.extend(back_regions)

        # Mark body as everything in between
        front_end = max((r.end_position for r in front_regions), default=0)
        back_start_pos = min((r.start_position for r in back_regions), default=text_length)

        if front_end < back_start_pos:
            regions.append(
                DocumentRegion(
                    region_type=RegionType.BODY,
                    start_position=front_end,
                    end_position=back_start_pos,
                    label="main_content",
                    confidence=0.8,
                )
            )

        return regions

    def _detect_in_section(
        self,
        section_text: str,
        offset: int,
        patterns: list,
        region_type: RegionType,
    ) -> list[DocumentRegion]:
        """
        Detect specific sections within a portion of text using patterns.

        Args:
            section_text: Text to search within
            offset: Character offset of this section in the full document
            patterns: List of (pattern, label, confidence) tuples
            region_type: Type to assign to detected regions

        Returns:
            List of DocumentRegion objects
        """
        regions = []
        seen_labels = set()

        for pattern, label, confidence in patterns:
            # Skip if we already found this type
            if label in seen_labels:
                continue

            match = pattern.search(section_text)
            if match:
                # Found a match - estimate region boundaries
                # Look for a logical boundary (paragraph break or section end)
                match_start = offset + match.start()

                # Special handling for glossary: extend to end of section
                # since glossaries contain many term/definition pairs separated by newlines
                if label == "glossary":
                    match_end = offset + len(section_text)
                else:
                    # Find end of section (next double newline or end of section)
                    search_start = match.end()
                    next_break = section_text.find("\n\n", search_start)
                    if next_break == -1:
                        match_end = offset + len(section_text)
                    else:
                        # Extend a bit past the break for context
                        match_end = offset + min(next_break + 100, len(section_text))

                regions.append(
                    DocumentRegion(
                        region_type=region_type,
                        start_position=match_start,
                        end_position=match_end,
                        label=label,
                        confidence=confidence,
                    )
                )
                seen_labels.add(label)

        return regions

    def is_in_body(self, position: int, regions: list[DocumentRegion]) -> bool:
        """
        Check if a text position is within the main body.

        Args:
            position: Character position to check
            regions: List of detected regions

        Returns:
            True if position is in BODY region, False otherwise
        """
        for region in regions:
            if region.region_type == RegionType.BODY and region.contains(position):
                return True
        return False

    def get_body_range(self, regions: list[DocumentRegion]) -> tuple[int, int]:
        """
        Get the start and end positions of the body region.

        Args:
            regions: List of detected regions

        Returns:
            Tuple of (start_position, end_position) for body
            Returns (0, 0) if no body region found
        """
        for region in regions:
            if region.region_type == RegionType.BODY:
                return (region.start_position, region.end_position)
        return (0, 0)


def detect_document_regions(
    text: str,
    chapters: Optional[list[dict]] = None,
) -> list[DocumentRegion]:
    """
    Convenience function to detect document regions.

    Args:
        text: Full document text
        chapters: Optional list of chapter dicts

    Returns:
        List of DocumentRegion objects
    """
    detector = RegionDetector()
    return detector.detect_regions(text, chapters)
