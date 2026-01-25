"""Utility functions for string similarity comparisons."""

from difflib import SequenceMatcher


def string_similarity(a: str, b: str, case_sensitive: bool = False) -> float:
    """
    Calculate the similarity between two strings using SequenceMatcher.

    Args:
        a: First string to compare
        b: Second string to compare
        case_sensitive: If True, compare strings as-is; if False, normalize to lowercase

    Returns:
        Similarity ratio between 0 and 1
    """
    if not a or not b:
        return 0.0

    # Normalize strings for comparison
    a = a.strip()
    b = b.strip()
    if not case_sensitive:
        a = a.lower()
        b = b.lower()

    return SequenceMatcher(None, a, b).ratio()


def names_similar(name1: str, name2: str, threshold: float = 0.8) -> bool:
    """
    Check if two character names are similar enough to be considered the same.

    This handles cases like:
    - Full name vs first name only ("Jay Gatsby" vs "Jay")
    - Honorifics ("Mr. Wilson" vs "Wilson")
    - Minor spelling variations

    Args:
        name1: First name to compare
        name2: Second name to compare
        threshold: Similarity threshold (default 0.8)

    Returns:
        True if names are similar enough to be the same character
    """
    if not name1 or not name2:
        return False

    # Exact match
    if name1.lower() == name2.lower():
        return True

    # Check if one is a subset of the other (handling first name only cases)
    parts1 = set(name1.lower().split())
    parts2 = set(name2.lower().split())

    if parts1.issubset(parts2) or parts2.issubset(parts1):
        return True

    # Use string similarity for fuzzy matching
    return string_similarity(name1, name2) >= threshold


def fuzzy_lastname_match(name: str, lastname: str, threshold: float = 0.85) -> bool:
    """
    Check if a name matches a lastname with fuzzy matching.

    Args:
        name: Full or partial name to check
        lastname: Lastname to match against
        threshold: Similarity threshold (default 0.85)

    Returns:
        True if the name contains or is similar to the lastname
    """
    if not name or not lastname:
        return False

    # Handle case where name might be a full name
    name_parts = name.split()
    if len(name_parts) > 1:
        # Check the last part as lastname
        return string_similarity(name_parts[-1], lastname) >= threshold
    else:
        # Direct comparison
        return string_similarity(name, lastname) >= threshold


def max_name_similarity(name: str, name_list: list[str]) -> tuple[str, float]:
    """
    Find the name in name_list with maximum similarity to the given name.

    Args:
        name: Name to compare
        name_list: List of names to search

    Returns:
        Tuple of (best_match_name, similarity_score)
    """
    if not name_list:
        return ("", 0.0)

    best_match = ""
    best_score = 0.0

    for candidate in name_list:
        # Full name comparison
        full_sim = string_similarity(name, candidate)

        # First name comparison
        first_name = name.split()[0] if name else ""
        first_candidate = candidate.split()[0] if candidate else ""
        first_sim = (
            string_similarity(first_name, first_candidate)
            if first_name and first_candidate
            else 0.0
        )

        # Take maximum of full and first name similarity
        score = max(full_sim, first_sim)

        if score > best_score:
            best_score = score
            best_match = candidate

    return (best_match, best_score)


def max_similarity_between_names(name1: str, name2: str) -> float:
    """
    Calculate maximum similarity between two names.

    Compares full names and first names separately, returning the maximum.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        Maximum similarity ratio between full comparison and first name comparison
    """
    # Full name comparison
    full_sim = string_similarity(name1, name2)

    # First name comparison
    first1 = name1.split()[0] if name1 else ""
    first2 = name2.split()[0] if name2 else ""

    if first1 and first2:
        first_sim = string_similarity(first1, first2)
        return max(full_sim, first_sim)

    return full_sim
