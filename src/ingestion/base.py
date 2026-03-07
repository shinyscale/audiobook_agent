"""
Base class for document ingestion.
All format-specific parsers inherit from this.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..utils.debug_log import append_debug_event

if TYPE_CHECKING:
    from .glossary import GlossaryExtractionResult
    from .regions import DocumentRegion


@dataclass
class ExtractedDocument:
    """Raw extracted content from a document."""

    text: str
    source_path: Path
    source_format: str

    # Optional structured info if the format provides it
    title: Optional[str] = None
    author: Optional[str] = None
    chapters: Optional[list[dict]] = None  # [{title, start_pos, end_pos}, ...]

    # Metadata
    page_count: Optional[int] = None
    has_images: bool = False
    extraction_warnings: list[str] = None

    # Document regions (front/back matter detection)
    regions: Optional[list["DocumentRegion"]] = None

    # Extracted glossary (if present)
    glossary: Optional["GlossaryExtractionResult"] = None

    def __post_init__(self):
        if self.extraction_warnings is None:
            self.extraction_warnings = []
        if self.regions is None:
            self.regions = []

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.text.split())

    @property
    def character_count(self) -> int:
        """Character count."""
        return len(self.text)

    def is_in_body(self, position: int) -> bool:
        """
        Check if a text position is within the main body (not front/back matter).

        Args:
            position: Character position to check

        Returns:
            True if position is in body, False if in front/back matter.
            Returns True if no regions detected (assume all is body).
        """
        if not self.regions:
            return True  # No regions = assume all body

        from .regions import RegionType

        for region in self.regions:
            if region.region_type == RegionType.BODY and region.contains(position):
                return True

        # Check if position is before body start or after body end
        body_regions = [r for r in self.regions if r.region_type == RegionType.BODY]
        if not body_regions:
            return True  # No body region defined = assume all body

        # If we have body regions but position doesn't fall in any, it's front/back matter
        return False


class DocumentIngester(ABC):
    """Abstract base class for document ingesters."""

    SUPPORTED_EXTENSIONS: list[str] = []

    def __init__(self, normalize_whitespace: bool = True):
        self.normalize_whitespace = normalize_whitespace

    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text and metadata from the document."""
        pass

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this ingester can handle the given file."""
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS

    def _normalize_text(self, text: str) -> str:
        """Clean up extracted text."""
        if not self.normalize_whitespace:
            return text

        # region agent log (chapter-v-bug) - hypothesis A/B
        try:
            _raw_centered = re.findall(r"(?m)^[ \t]{10,}([IVXLC]+)[ \t]*$", text)
            _raw_standalone_1 = re.findall(r"(?m)^[ \t]*([IVXLC])[ \t]*$", text)
            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "chapter-v-bug-pre",
                    "hypothesisId": "A",
                    "location": "src/ingestion/base.py:_normalize_text:pre",
                    "message": "Pre-normalization roman numeral line stats",
                    "data": {
                        "text_len": len(text),
                        "centered_roman_count": len(_raw_centered),
                        "centered_has_I": ("I" in set(_raw_centered)),
                        "centered_has_V": ("V" in set(_raw_centered)),
                        "standalone_single_roman_count": len(_raw_standalone_1),
                        "standalone_has_I": ("I" in set(_raw_standalone_1)),
                        "standalone_has_V": ("V" in set(_raw_standalone_1)),
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiple blank lines into two (preserving paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize spaces (but preserve newlines)
        lines = text.split("\n")
        # Preserve leading indentation (important for centered headings like roman numerals),
        # but still normalize internal whitespace and remove trailing whitespace.
        normalized_lines = []
        for line in lines:
            # Keep leading whitespace exactly; normalize the rest.
            m = re.match(r"^([ \t]*)(.*)$", line)
            if not m:
                normalized_lines.append(line.rstrip())
                continue
            indent, rest = m.group(1), m.group(2)
            # If the line is only whitespace, treat it as blank.
            if rest.strip() == "":
                normalized_lines.append("")
                continue
            rest = re.sub(r"[ \t]+", " ", rest).strip()
            normalized_lines.append(indent + rest)
        lines = normalized_lines
        text = "\n".join(lines)

        # Remove leading/trailing whitespace
        text = text.strip()

        # region agent log (chapter-v-bug) - hypothesis A/B
        try:
            _norm_centered = re.findall(r"(?m)^[ \t]{10,}([IVXLC]+)[ \t]*$", text)
            _norm_standalone_1 = re.findall(r"(?m)^[ \t]*([IVXLC])[ \t]*$", text)
            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "chapter-v-bug-pre",
                    "hypothesisId": "A",
                    "location": "src/ingestion/base.py:_normalize_text:post",
                    "message": "Post-normalization roman numeral line stats",
                    "data": {
                        "text_len": len(text),
                        "centered_roman_count": len(_norm_centered),
                        "centered_has_I": ("I" in set(_norm_centered)),
                        "centered_has_V": ("V" in set(_norm_centered)),
                        "standalone_single_roman_count": len(_norm_standalone_1),
                        "standalone_has_I": ("I" in set(_norm_standalone_1)),
                        "standalone_has_V": ("V" in set(_norm_standalone_1)),
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        return text

    def _clean_extracted_title(self, title: Optional[str]) -> Optional[str]:
        """Clean up an extracted title."""
        if not title:
            return None

        # Strip BOM (U+FEFF) that can appear at the start of text files
        title = title.lstrip("\ufeff")

        # Remove common suffixes
        title = re.sub(r"\.(pdf|docx|epub|txt)$", "", title, flags=re.IGNORECASE)

        # Clean whitespace
        title = " ".join(title.split())

        return title if title else None


def get_ingester(path: Path, ocr_fallback: bool = False) -> DocumentIngester:
    """
    Factory function to get the appropriate ingester for a file.

    Args:
        path: Path to the file to ingest
        ocr_fallback: Enable OCR fallback for PDFs with low text extraction

    Returns:
        Appropriate DocumentIngester instance for the file type
    """
    from .docx import DOCXIngester
    from .epub import EPUBIngester
    from .pdf import PDFIngester
    from .txt import TXTIngester

    ingesters = [PDFIngester, DOCXIngester, EPUBIngester, TXTIngester]

    for ingester_class in ingesters:
        if ingester_class.can_handle(path):
            # Pass ocr_fallback to PDFIngester
            if ingester_class == PDFIngester:
                return ingester_class(ocr_fallback=ocr_fallback)
            return ingester_class()

    raise ValueError(f"No ingester available for file type: {path.suffix}")
