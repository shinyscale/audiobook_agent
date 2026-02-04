"""
OCR repair module for fixing common optical character recognition errors.

This module handles errors that occur when text is extracted from scanned
documents or PDFs with poor text layers. Common issues include:

1. Roman numeral corruption (II → IT, III → ITI)
2. Character substitution (rn → m, l → 1, O → 0)
3. Ligature breakage (fi → f i, fl → f l)

These repairs are context-sensitive to avoid false positives.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Roman Numeral Repair
# ============================================================================

# Valid Roman numerals (up to 50 should cover most chapter numbering)
VALID_ROMAN_NUMERALS = {
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII", "XXIX", "XXX",
    "XXXI", "XXXII", "XXXIII", "XXXIV", "XXXV", "XXXVI", "XXXVII", "XXXVIII", "XXXIX", "XL",
    "XLI", "XLII", "XLIII", "XLIV", "XLV", "XLVI", "XLVII", "XLVIII", "XLIX", "L",
}

# Common OCR corruptions of Roman numerals
# Maps corrupted form → correct form
# These happen when vertical strokes (I) get misread as other letters
ROMAN_NUMERAL_CORRUPTIONS = {
    # II corruptions (two vertical strokes)
    "IT": "II",
    "TI": "II",
    "Il": "II",
    "lI": "II",
    "ll": "II",
    "1I": "II",
    "I1": "II",
    "11": "II",
    # III corruptions (three vertical strokes)
    "ITI": "III",
    "IIT": "III",
    "TII": "III",
    "TTI": "III",
    "TIT": "III",
    "ITT": "III",
    "Ill": "III",
    "IIl": "III",
    "Ilt": "III",
    "lII": "III",
    "llI": "III",
    "lll": "III",
    "111": "III",
    # IV corruptions
    "1V": "IV",
    "lV": "IV",
    # VI corruptions
    "V1": "VI",
    "Vl": "VI",
    # VII corruptions
    "V1I": "VII",
    "VI1": "VII",
    "VIl": "VII",
    "VlI": "VII",
    "Vll": "VII",
    "V11": "VII",
    # VIII corruptions
    "V1II": "VIII",
    "VI1I": "VIII",
    "VII1": "VIII",
    "VIIl": "VIII",
    "VIlI": "VIII",
    "VlII": "VIII",
    "Vlll": "VIII",
    "V111": "VIII",
    # IX corruptions
    "1X": "IX",
    "lX": "IX",
    # XI corruptions
    "X1": "XI",
    "Xl": "XI",
    # XII corruptions
    "X1I": "XII",
    "XI1": "XII",
    "XIl": "XII",
    "XlI": "XII",
    "Xll": "XII",
    "X11": "XII",
    # XIII corruptions
    "X1II": "XIII",
    "XI1I": "XIII",
    "XII1": "XIII",
    "XIIl": "XIII",
    "XIlI": "XIII",
    "XlII": "XIII",
    "Xlll": "XIII",
    "X111": "XIII",
    # Add more as needed...
}

# Patterns that indicate we're in a chapter heading context
CHAPTER_HEADING_PATTERNS = [
    # "Chapter IT" or "CHAPTER ITI"
    r"(?i)\bchapter\s+",
    # "Part IT" or "PART ITI"
    r"(?i)\bpart\s+",
    # "Book IT" or "BOOK ITI"
    r"(?i)\bbook\s+",
    # "Letter IT" (for epistolary novels like Frankenstein)
    r"(?i)\bletter\s+",
    # "Act IT" or "Scene ITI" (for plays)
    r"(?i)\b(?:act|scene)\s+",
    # Centered text (10+ leading spaces) - common for chapter markers
    r"^\s{10,}",
    # Line starts with the numeral (possibly after whitespace)
    r"^\s*",
]


def repair_roman_numerals(text: str) -> tuple[str, int]:
    """
    Repair OCR-corrupted Roman numerals in chapter headings.

    This function is context-aware - it only repairs Roman numerals that
    appear in chapter heading contexts to avoid false positives.

    Args:
        text: The text to repair

    Returns:
        Tuple of (repaired text, count of repairs made)
    """
    repairs = 0
    lines = text.split('\n')
    repaired_lines = []

    for line in lines:
        repaired_line, line_repairs = _repair_roman_numerals_in_line(line)
        repaired_lines.append(repaired_line)
        repairs += line_repairs

    return '\n'.join(repaired_lines), repairs


def _repair_roman_numerals_in_line(line: str) -> tuple[str, int]:
    """Repair Roman numerals in a single line if it looks like a heading."""
    repairs = 0

    # Check if this line looks like a chapter heading
    is_heading_context = _is_chapter_heading_context(line)

    if not is_heading_context:
        return line, 0

    # Try to repair each known corruption (case-insensitive matching)
    for corrupted, correct in ROMAN_NUMERAL_CORRUPTIONS.items():
        # Use word boundary matching to avoid partial matches
        # Case-insensitive to catch "It", "IT", "it" etc.
        pattern = rf'(?<![A-Za-z0-9])({re.escape(corrupted)})(?![A-Za-z0-9])'

        def replace_preserving_case(match):
            nonlocal repairs
            original = match.group(1)
            repairs += 1
            logger.debug(f"Repaired Roman numeral: '{original}' → '{correct}'")
            # Preserve case pattern: if original is title case, return title case
            if original.isupper():
                return correct.upper()
            elif original.istitle() or (original[0].isupper() and not original.isupper()):
                return correct.capitalize()
            else:
                return correct.lower()

        line = re.sub(pattern, replace_preserving_case, line, flags=re.IGNORECASE)

    return line, repairs


def _is_chapter_heading_context(line: str) -> bool:
    """
    Determine if a line is likely a chapter heading context.

    We want to be conservative and only repair in clear heading contexts.
    """
    line_stripped = line.strip()

    if not line_stripped:
        return False

    # Check for explicit chapter markers
    if re.match(r'(?i)^(chapter|part|book|letter|act|scene)\s+', line_stripped):
        return True

    # Check for centered text (significant leading whitespace)
    if len(line) - len(line.lstrip()) >= 10:
        # Centered text that's short (likely a heading)
        if len(line_stripped) < 50:
            return True

    # Check if the line is ONLY a potential Roman numeral (possibly corrupted)
    # This catches standalone centered numerals like "   ITI   "
    if len(line_stripped) <= 10:
        # Could be a Roman numeral or corrupted version
        upper_stripped = line_stripped.upper()
        if upper_stripped in VALID_ROMAN_NUMERALS:
            return True
        if upper_stripped in ROMAN_NUMERAL_CORRUPTIONS:
            return True
        # Check for patterns like "I.", "II.", "III." with period
        if re.match(r'^[IVXLCDMTl1]+\.?$', line_stripped, re.IGNORECASE):
            return True

    return False


# ============================================================================
# Character Substitution Repair
# ============================================================================

# Common OCR character confusions
# These are applied more broadly but still with some context checking
CHARACTER_SUBSTITUTIONS = {
    # rn often misread as m (or vice versa)
    # We can't blindly replace these - need dictionary validation

    # Common specific word fixes - h misread as li
    "tlie": "the",
    "liave": "have",
    "liis": "his",
    "lier": "her",
    "liim": "him",
    "liow": "how",
    "wlio": "who",
    "wlien": "when",
    "wliere": "where",
    "wliich": "which",
    "wliat": "what",
    "wliy": "why",
    "wliile": "while",
    "wliole": "whole",
    "tliis": "this",
    "tliat": "that",
    "tlien": "then",
    "tliere": "there",
    "tliey": "they",
    "tlieir": "their",
    "tliese": "these",
    "tliose": "those",
    "tliougli": "though",
    "tlirougli": "through",
    "tliouglit": "thought",
    "witli": "with",
    "witliout": "without",
    "witliin": "within",
    "otlier": "other",
    "altliougli": "although",
    "notliing": "nothing",
    "sometliing": "something",
    "everytliing": "everything",
    "anytliing": "anything",
    # h misread as b
    "fatber": "father",
    "motber": "mother",
    "brotber": "brother",
    "togetber": "together",
    "whetber": "whether",
    "anotber": "another",
    "ratber": "rather",
    "eitber": "either",
    "neitber": "neither",
    "gatber": "gather",
    "weatlier": "weather",
    "featber": "feather",
    "leatber": "leather",
    # cl misread as d
    "indude": "include",
    "exdude": "exclude",
    "condude": "conclude",
    # d misread as cl
    "woulcl": "would",
    "coulcl": "could",
    "shoulcl": "should",
    # Note: ligature issues (fi, fl, ff) are handled separately in
    # repair_broken_ligatures() with context-aware patterns that
    # require word characters on both sides to avoid false positives
    # like "of imaginary" -> "ofimaginary"
}


def repair_character_substitutions(text: str) -> tuple[str, int]:
    """
    Repair common OCR character substitution errors.

    This handles specific known word corruptions that are unambiguous.

    Args:
        text: The text to repair

    Returns:
        Tuple of (repaired text, count of repairs made)
    """
    repairs = 0

    for corrupted, correct in CHARACTER_SUBSTITUTIONS.items():
        # Case-insensitive matching with case preservation
        pattern = re.compile(re.escape(corrupted), re.IGNORECASE)

        def replace_preserving_case(match):
            nonlocal repairs
            original = match.group(0)
            repairs += 1

            # Preserve the case pattern of the original
            if original.isupper():
                return correct.upper()
            elif original[0].isupper():
                return correct.capitalize()
            else:
                return correct

        text = pattern.sub(replace_preserving_case, text)

    return text, repairs


# ============================================================================
# Ligature Repair
# ============================================================================

def repair_broken_ligatures(text: str) -> tuple[str, int]:
    """
    Repair broken ligatures where spaces were incorrectly inserted.

    Common ligatures that break: fi, fl, ff, ffi, ffl

    Args:
        text: The text to repair

    Returns:
        Tuple of (repaired text, count of repairs made)
    """
    repairs = 0

    # Patterns for broken ligatures
    # Require 2+ chars before the 'f' to avoid matching word boundaries like "of imaginary"
    # Single-char words like "of" followed by space + "i" are almost always word boundaries
    ligature_patterns = [
        (r'\bf\s+f\s+i', 'ffi'),   # f f i → ffi (word start)
        (r'\bf\s+f\s+l', 'ffl'),   # f f l → ffl (word start)
        (r'([a-z]{2,})f\s+i([a-z])', r'\1fi\2'),  # ...f i... → ...fi... (2+ chars before f)
        (r'([a-z]{2,})f\s+l([a-z])', r'\1fl\2'),  # ...f l... → ...fl... (2+ chars before f)
        (r'([a-z]{2,})f\s+f([a-z])', r'\1ff\2'),  # ...f f... → ...ff... (2+ chars before f)
    ]

    for pattern, replacement in ligature_patterns:
        new_text, count = re.subn(pattern, replacement, text)
        if count > 0:
            text = new_text
            repairs += count
            logger.debug(f"Repaired {count} broken ligatures matching '{pattern}'")

    return text, repairs


# ============================================================================
# Main Entry Point
# ============================================================================

def repair_ocr_errors(
    text: str,
    repair_roman_numerals: bool = True,
    repair_substitutions: bool = True,
    repair_ligatures: bool = True,
) -> tuple[str, dict]:
    """
    Main entry point for OCR error repair.

    Applies multiple repair strategies to fix common OCR errors.

    Args:
        text: The text to repair
        repair_roman_numerals: Whether to repair Roman numeral corruptions
        repair_substitutions: Whether to repair character substitutions
        repair_ligatures: Whether to repair broken ligatures

    Returns:
        Tuple of (repaired text, metadata dict with repair stats)
    """
    metadata = {
        "roman_numeral_repairs": 0,
        "substitution_repairs": 0,
        "ligature_repairs": 0,
        "total_repairs": 0,
    }

    # Apply repairs in order
    if repair_roman_numerals:
        text, count = globals()['repair_roman_numerals'](text)
        metadata["roman_numeral_repairs"] = count

    if repair_substitutions:
        text, count = repair_character_substitutions(text)
        metadata["substitution_repairs"] = count

    if repair_ligatures:
        text, count = repair_broken_ligatures(text)
        metadata["ligature_repairs"] = count

    metadata["total_repairs"] = (
        metadata["roman_numeral_repairs"] +
        metadata["substitution_repairs"] +
        metadata["ligature_repairs"]
    )

    if metadata["total_repairs"] > 0:
        logger.info(
            f"OCR repair: {metadata['total_repairs']} total repairs "
            f"(Roman numerals: {metadata['roman_numeral_repairs']}, "
            f"substitutions: {metadata['substitution_repairs']}, "
            f"ligatures: {metadata['ligature_repairs']})"
        )

    return text, metadata
