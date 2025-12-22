"""
PDF spacing correction module.

Fixes missing word spaces in PDFs that have tight kerning or
improper text layer encoding (common in old/scanned PDFs).
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import wordsegment for word boundary detection
try:
    import wordsegment
    wordsegment.load()
    _HAS_WORDSEGMENT = True
except ImportError:
    _HAS_WORDSEGMENT = False
    logger.warning("wordsegment not installed. PDF spacing correction will be limited.")


# Common English words for quick checks
COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
    'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
    'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see',
    'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
    'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
    'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
    'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had',
    'were', 'said', 'each', 'very', 'may', 'such', 'much', 'made', 'own',
    'upon', 'shall', 'should', 'must', 'before', 'where', 'while', 'through',
}

# Minimum length for a word to be considered for segmentation
MIN_SUSPICIOUS_LENGTH = 10

# Minimum length for detection sampling
MIN_DETECTION_LENGTH = 8

# Maximum reasonable word length in English
MAX_WORD_LENGTH = 20


def needs_spacing_correction(text: str, sample_size: int = 10000) -> bool:
    """
    Detect if text has missing word spaces.

    Checks for an unusual number of "words" that are likely
    multiple words concatenated together.

    Args:
        text: Text to check
        sample_size: Number of characters to sample

    Returns:
        True if spacing correction is likely needed
    """
    sample = text[:sample_size]
    words = sample.split()

    if not words:
        return False

    # Count suspiciously long words and pattern matches
    suspicious_count = 0
    pattern_matches = 0

    for word in words:
        # Strip punctuation for analysis
        clean = re.sub(r'[^\w]', '', word)

        # Check for clear concatenation patterns (lowercase followed by uppercase)
        if re.search(r'[a-z][A-Z]', word):
            pattern_matches += 1
            continue

        # Check for common word embedded in longer string
        if len(clean) >= MIN_DETECTION_LENGTH:
            if _looks_concatenated(clean):
                suspicious_count += 1

    total_suspicious = suspicious_count + pattern_matches

    # If more than 5% of words are suspicious, we likely need correction
    ratio = total_suspicious / len(words)
    logger.debug(f"Spacing check: {total_suspicious}/{len(words)} suspicious words ({ratio:.1%})")

    # Lower threshold - even 5% suspicious is concerning
    return ratio > 0.05


def _looks_concatenated(word: str) -> bool:
    """Check if a word looks like multiple words concatenated."""
    word_lower = word.lower()

    # Look for patterns like "thecat" -> "the" + "cat"
    # Check if we can find a common word at the start
    for length in range(2, min(8, len(word_lower) - 2)):
        prefix = word_lower[:length]
        if prefix in COMMON_WORDS:
            suffix = word_lower[length:]
            # Check if suffix starts with a lowercase letter (word boundary)
            if suffix and suffix[0].islower():
                return True

    # Check for camelCase-like patterns (uppercase in middle)
    if re.search(r'[a-z][A-Z]', word):
        return True

    return False


def fix_spacing(text: str) -> tuple[str, int]:
    """
    Fix missing word spaces in text.

    Uses word segmentation to identify and fix concatenated words.

    Args:
        text: Text with potential spacing issues

    Returns:
        Tuple of (corrected text, number of spaces added)
    """
    if not _HAS_WORDSEGMENT:
        logger.warning("wordsegment not available, using basic spacing fix")
        return _basic_spacing_fix(text)

    spaces_added = 0
    result_parts = []

    # Process text in chunks to preserve structure
    # Split on whitespace but keep the whitespace
    tokens = re.split(r'(\s+)', text)

    for token in tokens:
        if not token or token.isspace():
            result_parts.append(token)
            continue

        # Check if this token needs segmentation
        fixed_token, added = _fix_token(token)
        result_parts.append(fixed_token)
        spaces_added += added

    return ''.join(result_parts), spaces_added


def _fix_token(token: str) -> tuple[str, int]:
    """
    Fix spacing in a single token.

    Handles punctuation and preserves case.
    """
    # Extract leading/trailing punctuation
    match = re.match(r'^([^\w]*)(\w+)([^\w]*)$', token)
    if not match:
        return token, 0

    prefix, word, suffix = match.groups()

    # Skip very short words (can't be concatenated)
    if len(word) < 6:
        return token, 0

    # For words 6-10 chars, only fix if they clearly look concatenated
    if len(word) < MIN_SUSPICIOUS_LENGTH:
        if not _looks_concatenated(word):
            return token, 0

    # Skip if it's a valid word (in dictionary)
    if _is_valid_word(word):
        return token, 0

    # Try to segment
    segmented = _segment_word(word)

    if segmented == word:
        return token, 0

    # Count spaces added
    spaces_added = segmented.count(' ')

    return prefix + segmented + suffix, spaces_added


def _segment_word(word: str) -> str:
    """
    Segment a concatenated word into component words.

    Preserves original case as much as possible.
    """
    if not _HAS_WORDSEGMENT:
        return word

    # wordsegment works with lowercase
    segments = wordsegment.segment(word.lower())

    if len(segments) <= 1:
        return word

    # Reconstruct with proper case
    result = []
    pos = 0

    for seg in segments:
        # Find this segment in the original word (case-insensitive)
        seg_len = len(seg)
        original_segment = word[pos:pos + seg_len]
        result.append(original_segment)
        pos += seg_len

    return ' '.join(result)


def _is_valid_word(word: str) -> bool:
    """Check if a long word is actually valid (not concatenated)."""
    word_lower = word.lower()

    # Check against wordsegment's unigrams
    if _HAS_WORDSEGMENT:
        # If the word is in the dictionary, it's valid
        if word_lower in wordsegment.UNIGRAMS:
            return True

    # Common long valid words
    valid_long_words = {
        'nevertheless', 'notwithstanding', 'understanding', 'circumstances',
        'extraordinary', 'unfortunately', 'characteristic', 'communication',
        'philosophical', 'consciousness', 'accomplishment', 'demonstration',
        'entertainment', 'disappointment', 'establishment', 'transformation',
        'international', 'representation', 'constantinople', 'mediterranean',
    }

    if word_lower in valid_long_words:
        return True

    # Check for common suffixes that make long words valid
    valid_suffixes = ['tion', 'ness', 'ment', 'able', 'ible', 'ious', 'eous', 'ly', 'ing', 'ed']
    for suffix in valid_suffixes:
        if word_lower.endswith(suffix):
            # Could be a valid word, be conservative
            base = word_lower[:-len(suffix)]
            if len(base) >= 4 and not _looks_concatenated(base):
                return True

    return False


def _basic_spacing_fix(text: str) -> tuple[str, int]:
    """
    Basic spacing fix without wordsegment library.

    Uses simple heuristics to insert spaces at likely word boundaries.
    """
    spaces_added = 0

    def fix_match(match):
        nonlocal spaces_added
        word = match.group(0)

        # Look for common word boundaries
        for i in range(2, len(word) - 2):
            prefix = word[:i].lower()
            if prefix in COMMON_WORDS:
                # Check if what follows looks like a word start
                if word[i].islower():
                    spaces_added += 1
                    return word[:i] + ' ' + word[i:]

        return word

    # Find long words and try to fix them
    result = re.sub(r'\b\w{13,}\b', fix_match, text)

    return result, spaces_added


def correct_pdf_spacing(text: str, force: bool = False) -> tuple[str, dict]:
    """
    Main entry point for PDF spacing correction.

    Args:
        text: Text to correct
        force: If True, apply correction even if not detected as needed

    Returns:
        Tuple of (corrected text, metadata dict with stats)
    """
    metadata = {
        'spacing_correction_applied': False,
        'spaces_added': 0,
        'detection_triggered': False,
    }

    # Check if correction is needed
    if not force and not needs_spacing_correction(text):
        return text, metadata

    metadata['detection_triggered'] = True

    # Apply correction
    corrected, spaces_added = fix_spacing(text)

    if spaces_added > 0:
        metadata['spacing_correction_applied'] = True
        metadata['spaces_added'] = spaces_added
        logger.info(f"PDF spacing correction: added {spaces_added} spaces")

    return corrected, metadata
