"""
Name normalization for character extraction.

Feature F13: Normalize character names to prevent duplicate entries caused by:
- Trailing punctuation ('Daisy!', 'Daisy?')
- Possessive forms ("Daisy's", "Tom's")
- Unicode apostrophe variants (', ʼ, ʻ, ΄)
- Quoted names ("Tom", 'Nick')
- Leading/trailing whitespace
"""

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)


# Unicode apostrophe variants that should be normalized to ASCII apostrophe
APOSTROPHE_VARIANTS = [
    "\u2019",  # RIGHT SINGLE QUOTATION MARK (')
    "\u2018",  # LEFT SINGLE QUOTATION MARK (')
    "\u02bc",  # MODIFIER LETTER APOSTROPHE (ʼ)
    "\u02bb",  # MODIFIER LETTER TURNED COMMA (ʻ)
    "\u0384",  # GREEK TONOS (΄)
    "\u0027",  # ASCII APOSTROPHE (')
    "\u0060",  # GRAVE ACCENT (`)
    "\u00b4",  # ACUTE ACCENT (´)
]

# Compile apostrophe pattern for efficiency
APOSTROPHE_PATTERN = re.compile(f"[{''.join(APOSTROPHE_VARIANTS)}]")

# Pattern for possessive suffixes (handles both ASCII and Unicode apostrophes)
POSSESSIVE_PATTERN = re.compile(f"[{''.join(APOSTROPHE_VARIANTS)}]s$", re.IGNORECASE)

# Pattern for trailing punctuation
TRAILING_PUNCT_PATTERN = re.compile(r"[.!?,;:]+$")

# Pattern for leading/trailing quotes
QUOTE_PATTERN = re.compile(r'^["\'""' ']+|["\'""' "]+$")

# Pattern for parenthetical suffixes like "(deceased)" or "[sic]"
PARENTHETICAL_PATTERN = re.compile(r"\s*[\(\[][^)\]]*[\)\]]\s*$")


def normalize_name(name: str) -> str:
    """
    Normalize a character name for consistent matching.

    Args:
        name: Raw character name

    Returns:
        Normalized name string

    Examples:
        >>> normalize_name("Daisy!")
        'Daisy'
        >>> normalize_name("Tom's")
        'Tom'
        >>> normalize_name('"Nick"')
        'Nick'
        >>> normalize_name("Gatsby's")
        'Gatsby'
    """
    if not name:
        return name

    original = name
    normalized = name.strip()

    # Remove leading/trailing quotes
    normalized = QUOTE_PATTERN.sub("", normalized)

    # Normalize unicode apostrophes to ASCII
    normalized = APOSTROPHE_PATTERN.sub("'", normalized)

    # Remove possessive suffix
    normalized = POSSESSIVE_PATTERN.sub("", normalized)

    # Remove trailing punctuation
    normalized = TRAILING_PUNCT_PATTERN.sub("", normalized)

    # Remove parenthetical suffixes
    normalized = PARENTHETICAL_PATTERN.sub("", normalized)

    # Final strip
    normalized = normalized.strip()

    # Normalize unicode characters (e.g., accented characters)
    normalized = unicodedata.normalize("NFC", normalized)

    if normalized != original:
        logger.debug(f"Normalized name: '{original}' -> '{normalized}'")

    return normalized


def normalize_names_list(names: list[str]) -> list[str]:
    """
    Normalize a list of names and remove duplicates that result.

    Args:
        names: List of raw character names

    Returns:
        List of unique normalized names
    """
    seen = set()
    result = []

    for name in names:
        normalized = normalize_name(name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def names_match(name1: str, name2: str) -> bool:
    """
    Check if two names match after normalization.

    Args:
        name1: First name
        name2: Second name

    Returns:
        True if names match after normalization
    """
    return normalize_name(name1) == normalize_name(name2)


def is_possessive(name: str) -> bool:
    """
    Check if a name is in possessive form.

    Args:
        name: Name to check

    Returns:
        True if name ends with possessive suffix
    """
    # Normalize apostrophes first
    normalized = APOSTROPHE_PATTERN.sub("'", name)
    return bool(POSSESSIVE_PATTERN.search(normalized))


def extract_base_name(name: str) -> tuple[str, Optional[str]]:
    """
    Extract the base name and any suffix from a name.

    Args:
        name: Full name with possible suffixes

    Returns:
        Tuple of (base_name, suffix) where suffix may be None

    Examples:
        >>> extract_base_name("Tom's")
        ('Tom', "'s")
        >>> extract_base_name("Daisy!")
        ('Daisy', '!')
        >>> extract_base_name("Nick")
        ('Nick', None)
    """
    if not name:
        return (name, None)

    original = name.strip()
    base = normalize_name(original)

    if base == original:
        return (base, None)

    # Find what was removed
    suffix = original[len(base) :] if original.startswith(base) else None
    if not suffix:
        # The removal was at the start (quotes)
        suffix = original[: len(original) - len(base)]

    return (base, suffix if suffix else None)
