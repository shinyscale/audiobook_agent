"""
Glossary extraction from document back matter.

Parses term/definition pairs from glossary sections detected by region detection.
"""

import re
from dataclasses import dataclass
from typing import Optional
import logging

from .regions import DocumentRegion, RegionType

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntry:
    """A single extracted glossary entry."""
    term: str
    definition: str
    position: int
    confidence: float


@dataclass
class GlossaryExtractionResult:
    """Result of glossary extraction."""
    entries: list[GlossaryEntry]
    region_start: int
    region_end: int
    extraction_method: str


# Patterns for term/definition separation (ordered by confidence)
# Each tuple: (compiled_pattern, confidence, method_name)
GLOSSARY_PATTERNS = [
    # "Term: definition" (most common format)
    # Allow terms starting with uppercase or lowercase, capture multi-line definitions
    (re.compile(r'^([A-Za-z][^:\n]{0,60}):\s*(.+?)(?=\n[A-Za-z][^:\n]{0,60}:|$)', re.MULTILINE | re.DOTALL), 0.9, "colon"),

    # "Term - definition" or "Term — definition" (em-dash or en-dash)
    (re.compile(r'^([A-Za-z][^-—\n]{0,60})\s*[-—]\s*(.+?)(?=\n[A-Za-z][^-—\n]{0,60}\s*[-—]|$)', re.MULTILINE | re.DOTALL), 0.85, "dash"),

    # Bold term: **Term** definition (markdown-style, less common in books)
    (re.compile(r'^\*\*([^*\n]+)\*\*\s*(.+?)(?=\n\*\*|$)', re.MULTILINE | re.DOTALL), 0.8, "bold"),

    # Term on own line, definition indented below
    (re.compile(r'^([A-Z][^\n]{1,40})\n[ \t]{2,}(.+?)(?=\n[A-Z][^\n]{1,40}\n[ \t]{2,}|$)', re.MULTILINE | re.DOTALL), 0.7, "indented"),
]


def _clean_definition(definition: str) -> str:
    """Clean up extracted definition text."""
    # Collapse multiple whitespace/newlines into single space
    definition = re.sub(r'\s+', ' ', definition)
    # Remove leading/trailing whitespace
    definition = definition.strip()
    return definition


def _clean_term(term: str) -> str:
    """Clean up extracted term text."""
    # Remove leading/trailing whitespace
    term = term.strip()
    # Remove trailing punctuation that might have been captured
    term = term.rstrip(':;,.')
    return term


def extract_glossary(
    text: str,
    regions: list[DocumentRegion],
) -> Optional[GlossaryExtractionResult]:
    """
    Extract glossary entries from document.

    Args:
        text: Full document text
        regions: Detected document regions (from region detection)

    Returns:
        GlossaryExtractionResult if glossary found and parsed, None otherwise
    """
    # Find glossary region
    glossary_region = None
    for region in regions:
        if region.label == "glossary":
            glossary_region = region
            break

    if not glossary_region:
        return None

    # Extract glossary text
    glossary_text = text[glossary_region.start_position:glossary_region.end_position]

    # Skip the "Glossary" header line if present
    header_match = re.match(r'^\s*[Gg]lossary\s*\n+', glossary_text)
    if header_match:
        glossary_text = glossary_text[header_match.end():]
        header_offset = header_match.end()
    else:
        header_offset = 0

    # Try each pattern to extract entries
    entries = []
    best_method = None

    for pattern, confidence, method in GLOSSARY_PATTERNS:
        matches = list(pattern.finditer(glossary_text))

        # Need at least 3 entries to confirm this is the right format
        if len(matches) >= 3:
            for match in matches:
                term = _clean_term(match.group(1))
                definition = _clean_definition(match.group(2))

                # Skip entries with empty term or definition
                if not term or not definition:
                    continue

                # Skip if definition is too short (likely a false match)
                if len(definition) < 10:
                    continue

                entries.append(GlossaryEntry(
                    term=term,
                    definition=definition,
                    position=glossary_region.start_position + header_offset + match.start(),
                    confidence=confidence,
                ))

            if entries:
                best_method = method
                break

    if not entries:
        logger.warning("Glossary region detected but could not parse entries")
        return None

    # Sort entries alphabetically by term
    entries.sort(key=lambda e: e.term.lower())

    logger.info(f"Extracted {len(entries)} glossary entries using '{best_method}' pattern")

    return GlossaryExtractionResult(
        entries=entries,
        region_start=glossary_region.start_position,
        region_end=glossary_region.end_position,
        extraction_method=best_method,
    )
