"""
Text refinement module for post-ingestion processing.

This module provides deterministic text cleaning and normalization
that runs after document extraction but before analysis.
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional
from dataclasses import replace

from .base import ExtractedDocument
from .pdf_spacing import correct_pdf_spacing, needs_spacing_correction

# Try to import spellchecker for dictionary-based de-hyphenation
try:
    from spellchecker import SpellChecker
    _spell = SpellChecker()
    _HAS_SPELLCHECKER = True
except ImportError:
    _spell = None
    _HAS_SPELLCHECKER = False


def refine_extracted_document(doc: ExtractedDocument) -> ExtractedDocument:
    """
    Apply deterministic text refinement to an extracted document.

    This runs after ingestion and before analysis to normalize text
    across all formats into a canonical representation.

    Args:
        doc: The extracted document to refine

    Returns:
        A new ExtractedDocument with refined text and updated warnings
    """
    text = doc.text
    warnings = list(doc.extraction_warnings)  # Copy to avoid mutation

    # Track refinement stats
    original_len = len(text)

    # === Format-agnostic cleaning ===

    # Unicode normalization (NFKC - compatibility decomposition + canonical composition)
    # This normalizes things like:
    # - fullwidth characters → ASCII
    # - ligatures that weren't caught earlier
    # - various Unicode spaces → regular space
    text = unicodedata.normalize('NFKC', text)

    # Replace non-breaking spaces with regular spaces
    text = text.replace('\u00A0', ' ')  # NBSP
    text = text.replace('\u202F', ' ')  # Narrow NBSP
    text = text.replace('\u2007', ' ')  # Figure space
    text = text.replace('\u2009', ' ')  # Thin space
    text = text.replace('\u200A', ' ')  # Hair space

    # Remove form feeds and other control characters (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Normalize various dash/hyphen characters to ASCII hyphen
    text = text.replace('\u2010', '-')  # Hyphen
    text = text.replace('\u2011', '-')  # Non-breaking hyphen
    text = text.replace('\u2012', '-')  # Figure dash
    text = text.replace('\u2013', '-')  # En dash (for hyphenation context)
    # Note: em-dash (—) is left as-is since it's usually intentional punctuation

    # === PDF-specific cleaning ===
    if doc.source_format == 'pdf':
        text, dehyphen_count = _dehyphenate(text)
        if dehyphen_count > 0:
            warnings.append(f"De-hyphenated {dehyphen_count} line-break word splits")

        # Fix missing word spaces (common in old/scanned PDFs)
        text, spacing_metadata = correct_pdf_spacing(text)
        if spacing_metadata['spacing_correction_applied']:
            warnings.append(f"PDF spacing correction: added {spacing_metadata['spaces_added']} word spaces")

    # === Quality metrics ===
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        avg_chars = sum(len(p) for p in paragraphs) / len(paragraphs)
        empty_ratio = text.count('\n\n\n') / max(len(paragraphs), 1)

        # Flag low quality
        if avg_chars < 50:
            warnings.append(f"Low average paragraph length ({avg_chars:.0f} chars) - may indicate extraction issues")
        if empty_ratio > 0.3:
            warnings.append("High ratio of empty sections detected")

    # Track size change
    refined_len = len(text)
    if abs(refined_len - original_len) > original_len * 0.05:
        warnings.append(f"Text size changed by {((refined_len - original_len) / original_len * 100):.1f}% during refinement")

    # Create new document with refined text
    return replace(
        doc,
        text=text,
        extraction_warnings=warnings
    )


def _dehyphenate(text: str) -> tuple[str, int]:
    """
    Remove line-break hyphenation from text.

    Handles cases like:
        "exam-
        ple" -> "example"

    Uses dictionary validation when available to avoid false positives.

    Args:
        text: The text to de-hyphenate

    Returns:
        Tuple of (dehyphenated text, count of changes made)
    """
    # Pattern: word fragment ending with hyphen, newline(s), then lowercase continuation
    # Captures: (word_start)(hyphen)(whitespace/newlines)(word_end)
    pattern = r'(\b[a-zA-Z]+)-\s*\n\s*([a-z]+\b)'

    count = 0

    def replace_hyphen(match):
        nonlocal count
        word_start = match.group(1)
        word_end = match.group(2)
        combined = word_start + word_end

        # If we have spellchecker, validate the merge
        if _HAS_SPELLCHECKER:
            # Check if combined word is valid
            if combined.lower() in _spell:
                count += 1
                return combined
            # Check if the fragment alone is a valid word (don't merge)
            if word_start.lower() in _spell:
                return match.group(0)  # Keep original
            # Fragment isn't a word, combined isn't recognized - still merge
            # (likely a proper noun or technical term)
            count += 1
            return combined
        else:
            # Without spellchecker, use conservative heuristics
            # Only merge if the result looks reasonable
            if len(word_start) >= 2 and len(word_end) >= 2:
                count += 1
                return combined
            return match.group(0)

    result = re.sub(pattern, replace_hyphen, text)
    return result, count


def to_canonical_markdown(doc: ExtractedDocument) -> str:
    """
    Convert an ExtractedDocument to canonical Markdown format.

    Generates a fully readable artifact with:
    - YAML-ish header with metadata
    - Chapter markers inserted at appropriate positions
    - Full book text under headings

    Args:
        doc: The document to convert

    Returns:
        Markdown string representation of the document
    """
    lines = []

    # === Header section ===
    lines.append("---")
    lines.append(f"title: {doc.title or 'Unknown Title'}")
    if doc.author:
        lines.append(f"author: {doc.author}")
    lines.append(f"source: {doc.source_path.name}")
    lines.append(f"format: {doc.source_format}")
    lines.append(f"word_count: {doc.word_count:,}")
    if doc.page_count:
        lines.append(f"page_count: {doc.page_count}")
    lines.append("---")
    lines.append("")

    # === Title ===
    lines.append(f"# {doc.title or doc.source_path.stem}")
    if doc.author:
        lines.append(f"*by {doc.author}*")
    lines.append("")

    # === Content with chapter markers ===
    if doc.chapters and len(doc.chapters) > 0:
        # Insert chapter headings at appropriate positions
        text = doc.text

        # Sort chapters by start position (descending) to insert from end
        sorted_chapters = sorted(doc.chapters, key=lambda c: c.get('start_pos', 0), reverse=True)

        for i, chapter in enumerate(sorted_chapters):
            start_pos = chapter.get('start_pos', 0)
            title = chapter.get('title', f"Chapter {len(sorted_chapters) - i}")

            # Create chapter heading
            chapter_heading = f"\n\n## {title}\n\n"

            # Insert at position (accounting for shifts would be complex, so we rebuild)
            # Instead, let's do a forward pass

        # Rebuild with forward pass for correctness
        sorted_chapters = sorted(doc.chapters, key=lambda c: c.get('start_pos', 0))
        result_parts = []
        last_pos = 0

        for i, chapter in enumerate(sorted_chapters):
            start_pos = chapter.get('start_pos', 0)
            title = chapter.get('title', f"Chapter {i + 1}")

            # Add text before this chapter
            if start_pos > last_pos:
                result_parts.append(text[last_pos:start_pos].strip())

            # Add chapter heading
            result_parts.append(f"\n\n## {title}\n\n")

            # Move position past the chapter marker in original text
            # (the chapter title might be in the text itself)
            end_pos = chapter.get('end_pos', len(text))
            last_pos = start_pos

        # Add remaining text after last chapter marker
        if last_pos < len(text):
            result_parts.append(text[last_pos:].strip())

        content = ''.join(result_parts)
    else:
        # No chapters - just use the text as-is
        content = doc.text

    lines.append(content)

    # === Warnings section ===
    if doc.extraction_warnings:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Extraction Notes")
        lines.append("")
        for warning in doc.extraction_warnings:
            lines.append(f"- {warning}")

    return '\n'.join(lines)
