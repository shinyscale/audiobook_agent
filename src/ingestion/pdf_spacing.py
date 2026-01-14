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
    _HAS_WORDSEGMENT = True
    _wordsegment_loaded = False
except ImportError:
    _HAS_WORDSEGMENT = False
    _wordsegment_loaded = False
    wordsegment = None  # type: ignore
    logger.warning("wordsegment not installed. PDF spacing correction will be limited.")


def _ensure_wordsegment_loaded() -> None:
    """
    Lazy-load wordsegment data with user feedback.

    This downloads word frequency data (~25MB) on first use,
    which can take 10-30 seconds.
    """
    global _wordsegment_loaded
    if _wordsegment_loaded or not _HAS_WORDSEGMENT:
        return

    logger.info("Loading word segmentation data (first-time only, may take 10-30s)...")
    import sys
    print("🔤 Loading word segmentation data (first run only)...", file=sys.stderr, flush=True)

    wordsegment.load()
    _wordsegment_loaded = True

    logger.info("Word segmentation data loaded.")


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

    # For words 8+ chars, check for very distinctive common words anywhere
    # Use only words that rarely appear in the middle of valid English words
    # This catches patterns like "footofman", "dearsisterofmywelfare"
    if len(word_lower) >= 8:
        # Very distinctive short words that rarely appear mid-word in valid English
        # Avoid: 'in', 'or', 'an', 'as' - these appear in many valid words
        distinctive_common = {'of', 'my'}
        for common in distinctive_common:
            # Look for word boundaries: preceded by lowercase, followed by lowercase
            pattern = rf'[a-z]{common}[a-z]'
            if re.search(pattern, word_lower):
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

    # Lazy-load wordsegment data (may take 10-30s on first use)
    _ensure_wordsegment_loaded()

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
    Also handles punctuation in the middle of tokens (e.g., "nerves,andfillsmewith").
    """
    # First, try to handle tokens with punctuation in the middle
    # Split by common punctuation that might join concatenated words
    if re.search(r'\w[,;:]\w', token):
        # Has punctuation between word characters - split and process each part
        parts = re.split(r'([,;:])', token)
        total_spaces = 0
        result_parts = []
        for part in parts:
            if part in ',;:':
                result_parts.append(part)
            else:
                fixed_part, added = _fix_single_word(part)
                result_parts.append(fixed_part)
                total_spaces += added
        return ''.join(result_parts), total_spaces

    # Simple case: extract leading/trailing punctuation
    return _fix_single_word(token)


# Common short concatenation patterns that are very reliable
# Format: pattern -> replacement (case-sensitive where needed)
_COMMON_SHORT_CONCATENATIONS = {
    # "I" + verb patterns (case sensitive - uppercase I)
    'Iam': 'I am',
    'Iwas': 'I was',
    'Iwill': 'I will',
    'Ishall': 'I shall',
    'Ihave': 'I have',
    'Ihad': 'I had',
    'Ido': 'I do',
    'Idid': 'I did',
    'Ican': 'I can',
    'Icould': 'I could',
    'Imay': 'I may',
    'Imight': 'I might',
    'Imust': 'I must',
    'Iknow': 'I know',
    'Ifelt': 'I felt',
    'Ifeel': 'I feel',
    'Ifound': 'I found',
    'Iwent': 'I went',
    'Icame': 'I came',
    'Isaw': 'I saw',
    'Itook': 'I took',
    'Itried': 'I tried',
    # preposition + article patterns
    'inthe': 'in the',
    'ofthe': 'of the',
    'tothe': 'to the',
    'onthe': 'on the',
    'atthe': 'at the',
    'bythe': 'by the',
    'forthe': 'for the',
    'fromthe': 'from the',
    'withthe': 'with the',
    'ofan': 'of an',
    'ofmy': 'of my',
    'tomy': 'to my',
    'asI': 'as I',
    'ifI': 'if I',
    # Do/Did patterns
    'Doyou': 'Do you',
    'Didyou': 'Did you',
}


def _fix_common_short_concatenation(word: str) -> str | None:
    """
    Fix common short concatenation patterns that are very reliable.

    Returns the fixed string if matched, or None if no match.
    """
    # Check exact matches first (case-sensitive)
    if word in _COMMON_SHORT_CONCATENATIONS:
        return _COMMON_SHORT_CONCATENATIONS[word]

    # Check lowercase version for preposition patterns
    word_lower = word.lower()
    if word_lower in _COMMON_SHORT_CONCATENATIONS:
        replacement = _COMMON_SHORT_CONCATENATIONS[word_lower]
        # Try to preserve original case
        if word[0].isupper():
            replacement = replacement[0].upper() + replacement[1:]
        return replacement

    return None


def _fix_single_word(token: str) -> tuple[str, int]:
    """
    Fix spacing in a single word token.

    Handles leading/trailing punctuation and preserves case.
    """
    # Extract leading/trailing punctuation
    match = re.match(r'^([^\w]*)(\w+)([^\w]*)$', token)
    if not match:
        return token, 0

    prefix, word, suffix = match.groups()

    # Handle common short concatenations first (before length check)
    # These are very reliable patterns that don't need full segmentation
    short_fix = _fix_common_short_concatenation(word)
    if short_fix:
        return prefix + short_fix + suffix, short_fix.count(' ')

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

        # Post-process: check if this segment is a known short concatenation
        # This catches cases where wordsegment produces "asI" instead of "as I"
        short_fix = _fix_common_short_concatenation(original_segment)
        if short_fix:
            result.append(short_fix)
        else:
            result.append(original_segment)
        pos += seg_len

    return ' '.join(result)


def _is_valid_word(word: str) -> bool:
    """Check if a long word is actually valid (not concatenated)."""
    word_lower = word.lower()

    # Check against wordsegment's unigrams (authoritative dictionary)
    if _HAS_WORDSEGMENT:
        # Lazy-load wordsegment data if needed
        _ensure_wordsegment_loaded()
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

    # For very long words (>15 chars), verify with wordsegment if available
    # Don't trust suffix heuristics alone for these
    if len(word_lower) > 15 and _HAS_WORDSEGMENT:
        segments = wordsegment.segment(word_lower)
        # If it segments into 3+ parts, it's likely concatenated
        if len(segments) >= 3:
            return False

    # Check for common suffixes that make long words valid
    # Only trust this for moderately long words (not extremely long ones)
    if len(word_lower) <= 15:
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
