"""
Back matter detection for audiobook prep.

Feature F11: Detect boilerplate/license/metadata blocks and exclude from
chapter detection, summaries, and character extraction.

Common back matter includes:
- Project Gutenberg license and metadata
- Copyright notices
- About the author sections
- Advertisements for other books
- Transcriber notes
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BackMatterRegion:
    """A region of text identified as back matter (non-content)."""

    start_position: int
    end_position: int
    region_type: str  # "project_gutenberg", "copyright", "advertisement", etc.
    confidence: float  # 0.0 - 1.0
    matched_pattern: str  # The pattern that triggered detection

    def __contains__(self, position: int) -> bool:
        """Check if a position is within this region."""
        return self.start_position <= position < self.end_position


# Project Gutenberg patterns
GUTENBERG_START_PATTERNS = [
    # License section start markers
    re.compile(r"\*{3,}\s*START OF (THE )?PROJECT GUTENBERG (EBOOK|LICENSE|ETEXT)", re.IGNORECASE),
    re.compile(r"End of (the )?Project Gutenberg", re.IGNORECASE),
    re.compile(r"\*{3,}\s*END OF (THE )?PROJECT GUTENBERG (EBOOK|LICENSE|ETEXT)", re.IGNORECASE),
    re.compile(r"This eBook is for the use of anyone", re.IGNORECASE),
    re.compile(r"Project Gutenberg.{0,50}(License|Terms|Trademark)", re.IGNORECASE),
    re.compile(r"The Project Gutenberg Literary Archive Foundation", re.IGNORECASE),
    re.compile(r"Professor Michael S\. Hart", re.IGNORECASE),
    re.compile(
        r"Produced by .{10,100}(Project Gutenberg|PG|Distributed Proofreaders)", re.IGNORECASE
    ),
    re.compile(r"www\.gutenberg\.org", re.IGNORECASE),
]

# Generic back matter patterns
BACK_MATTER_PATTERNS = [
    # Copyright and legal
    (re.compile(r"^\s*COPYRIGHT\s*$", re.MULTILINE | re.IGNORECASE), "copyright"),
    (re.compile(r"All rights reserved", re.IGNORECASE), "copyright"),
    (re.compile(r"ISBN[\s:-]*[\dX-]{10,}", re.IGNORECASE), "metadata"),
    (re.compile(r"Library of Congress", re.IGNORECASE), "metadata"),
    (
        re.compile(
            r"Printed in (the )?(United States|USA|America|UK|Great Britain)", re.IGNORECASE
        ),
        "metadata",
    ),
    # Publisher/publication info
    (re.compile(r"Published by .{5,50}(Press|Publishing|Books)", re.IGNORECASE), "metadata"),
    (re.compile(r"First (published|edition|printing)", re.IGNORECASE), "metadata"),
    # Advertisements
    (re.compile(r"(Other|More) books by (the )?same author", re.IGNORECASE), "advertisement"),
    (
        re.compile(r"Also (available|by) (the same author|this author)", re.IGNORECASE),
        "advertisement",
    ),
    (re.compile(r"(Visit|Check out) (our |the )?(website|online)", re.IGNORECASE), "advertisement"),
    # Transcriber notes
    (
        re.compile(
            r"^\s*\[?(Transcriber'?s?|Editor'?s?) (Note|Comment)", re.MULTILINE | re.IGNORECASE
        ),
        "transcriber_note",
    ),
    (re.compile(r"Transcribed (by|from)", re.IGNORECASE), "transcriber_note"),
    # About the author
    (re.compile(r"^\s*About the Author\s*$", re.MULTILINE | re.IGNORECASE), "about_author"),
    (re.compile(r"^\s*About the Translator\s*$", re.MULTILINE | re.IGNORECASE), "about_author"),
    (
        re.compile(r"^\s*Author's? (Note|Bio|Biography)\s*$", re.MULTILINE | re.IGNORECASE),
        "about_author",
    ),
    # Appendices and indices
    (
        re.compile(
            r"^\s*(Appendix|Index|Bibliography|Glossary|Notes)\s*$", re.MULTILINE | re.IGNORECASE
        ),
        "appendix",
    ),
    # End markers
    (re.compile(r"^\s*(THE END|FINIS|FIN)\s*$", re.MULTILINE), "end_marker"),
]


class BackMatterDetector:
    """
    Detects back matter regions in a document.

    Back matter is content that should be excluded from analysis because it's
    not part of the narrative (licenses, copyright notices, advertisements, etc.)
    """

    def __init__(self, min_region_size: int = 100):
        """
        Args:
            min_region_size: Minimum character size for a back matter region
        """
        self.min_region_size = min_region_size

    def detect(self, text: str) -> list[BackMatterRegion]:
        """
        Detect all back matter regions in the text.

        Args:
            text: Full document text

        Returns:
            List of BackMatterRegion objects, sorted by position
        """
        regions = []

        # Detect Project Gutenberg content
        pg_regions = self._detect_project_gutenberg(text)
        regions.extend(pg_regions)

        # Detect generic back matter (only in last 20% of document)
        doc_length = len(text)
        back_section_start = int(doc_length * 0.8)
        generic_regions = self._detect_generic_back_matter(text, back_section_start)
        regions.extend(generic_regions)

        # Merge overlapping regions
        regions = self._merge_regions(regions)

        # Sort by position
        regions.sort(key=lambda r: r.start_position)

        logger.info(f"BackMatterDetector: found {len(regions)} back matter regions")
        for region in regions:
            logger.debug(
                f"  [{region.start_position}-{region.end_position}] "
                f"{region.region_type} (conf={region.confidence:.2f})"
            )

        return regions

    def _detect_project_gutenberg(self, text: str) -> list[BackMatterRegion]:
        """Detect Project Gutenberg license and metadata regions."""
        regions = []

        for pattern in GUTENBERG_START_PATTERNS:
            for match in pattern.finditer(text):
                # Project Gutenberg content is typically in blocks
                # Find the extent of the block
                start = match.start()
                end = self._find_block_end(text, start)

                # Ensure minimum size
                if end - start < self.min_region_size:
                    end = min(len(text), start + self.min_region_size)

                regions.append(
                    BackMatterRegion(
                        start_position=start,
                        end_position=end,
                        region_type="project_gutenberg",
                        confidence=0.95,
                        matched_pattern=pattern.pattern[:50],
                    )
                )

        return regions

    def _detect_generic_back_matter(self, text: str, search_start: int) -> list[BackMatterRegion]:
        """Detect generic back matter patterns."""
        regions = []
        search_text = text[search_start:]

        for pattern, region_type in BACK_MATTER_PATTERNS:
            for match in pattern.finditer(search_text):
                abs_start = search_start + match.start()
                abs_end = self._find_block_end(text, abs_start)

                # More conservative confidence for generic patterns
                confidence = 0.7 if region_type in ["metadata", "copyright"] else 0.6

                regions.append(
                    BackMatterRegion(
                        start_position=abs_start,
                        end_position=abs_end,
                        region_type=region_type,
                        confidence=confidence,
                        matched_pattern=pattern.pattern[:50],
                    )
                )

        return regions

    def _find_block_end(self, text: str, start: int) -> int:
        """
        Find the end of a back matter block.

        Back matter blocks typically end with:
        - Multiple blank lines
        - A chapter heading
        - End of document
        """
        # Look for multiple blank lines
        double_blank = re.search(r"\n\s*\n\s*\n\s*\n", text[start : start + 5000])
        if double_blank:
            return start + double_blank.start()

        # Look for chapter heading
        chapter_heading = re.search(
            r"^\s*(Chapter|CHAPTER|\d+\.|[IVXLC]+\.)\s", text[start : start + 5000], re.MULTILINE
        )
        if chapter_heading:
            return start + chapter_heading.start()

        # Default: extend to a reasonable boundary (paragraph end)
        para_end = re.search(r"\n\s*\n", text[start : start + 2000])
        if para_end:
            return start + para_end.end()

        # Ultimate fallback: 1000 chars or end of doc
        return min(len(text), start + 1000)

    def _merge_regions(self, regions: list[BackMatterRegion]) -> list[BackMatterRegion]:
        """Merge overlapping or adjacent regions."""
        if not regions:
            return regions

        # Sort by start position
        sorted_regions = sorted(regions, key=lambda r: r.start_position)
        merged = [sorted_regions[0]]

        for region in sorted_regions[1:]:
            last = merged[-1]
            # Check for overlap or adjacency (within 100 chars)
            if region.start_position <= last.end_position + 100:
                # Merge: extend the last region
                last.end_position = max(last.end_position, region.end_position)
                # Keep higher confidence
                if region.confidence > last.confidence:
                    last.confidence = region.confidence
                    last.region_type = region.region_type
            else:
                merged.append(region)

        return merged


def detect_back_matter(text: str) -> list[BackMatterRegion]:
    """
    Convenience function to detect back matter in a document.

    Args:
        text: Full document text

    Returns:
        List of BackMatterRegion objects
    """
    detector = BackMatterDetector()
    return detector.detect(text)


def is_in_back_matter(
    position: int,
    regions: list[BackMatterRegion],
) -> Optional[BackMatterRegion]:
    """
    Check if a position falls within a back matter region.

    Args:
        position: Character position to check
        regions: List of back matter regions

    Returns:
        The BackMatterRegion containing the position, or None
    """
    for region in regions:
        if position in region:
            return region
    return None
