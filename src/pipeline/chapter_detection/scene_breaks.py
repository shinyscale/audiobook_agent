"""Scene break detection utility.

This module provides functions to detect scene break markers in text,
which are typically lines of repeated punctuation (dashes, asterisks, equals)
used to indicate transitions within chapters.

Scene breaks should NOT be treated as chapter boundaries.
"""

import re
from typing import List, Tuple

# Pattern matches lines of repeated punctuation used as scene breaks
# Matches:
#   - Lines of dashes: ---- or --------
#   - Lines of asterisks: **** or ********
#   - Lines of equals: ==== or ========
#   - Lines of tildes: ~~~~ or ~~~~~~~~
#   - Lines of dots: .... or ........
#   - Spaced asterisks: * * * or *  *  *
#   - Centered scene break markers with whitespace padding
SCENE_BREAK_PATTERN = re.compile(
    r"^[\s]*[-=*~.]{3,}[\s]*$|"  # ----, ***, ===, ~~~, ....
    r"^\s*[*]\s+[*]\s+[*]\s*$|"  # * * * (spaced asterisks)
    r"^\s*[*]\s*[*]\s*[*]\s*$",  # *** with optional spacing
    re.MULTILINE,
)


def find_scene_breaks(text: str) -> List[Tuple[int, int]]:
    """Find positions of scene break markers in text.

    Args:
        text: The full text to search for scene breaks.

    Returns:
        List of (start, end) tuples indicating the character positions
        of each scene break marker.
    """
    return [(m.start(), m.end()) for m in SCENE_BREAK_PATTERN.finditer(text)]


def is_near_scene_break(
    position: int,
    scene_breaks: List[Tuple[int, int]],
    threshold: int = 100,
) -> bool:
    """Check if a position is near a scene break.

    This is used to filter out chapter proposals that are near scene breaks,
    since these are likely false positives from the LLM detecting the scene
    break line itself as a chapter marker.

    Args:
        position: The character position to check.
        scene_breaks: List of (start, end) tuples from find_scene_breaks().
        threshold: Maximum distance in characters to consider "near".
            Default is 100 characters.

    Returns:
        True if the position is within threshold characters of any scene break.
    """
    for start, end in scene_breaks:
        if abs(position - start) < threshold or abs(position - end) < threshold:
            return True
    return False


def get_scene_break_positions(text: str) -> List[int]:
    """Get start positions of all scene breaks.

    Convenience function that returns just the start positions,
    useful for simple position checks.

    Args:
        text: The full text to search for scene breaks.

    Returns:
        List of start character positions for each scene break.
    """
    return [start for start, _ in find_scene_breaks(text)]


def get_scene_break_line_numbers(text: str) -> List[int]:
    """Get line numbers where scene breaks occur.

    This is useful for debugging and logging purposes.

    Args:
        text: The full text to search for scene breaks.

    Returns:
        List of 1-indexed line numbers containing scene breaks.
    """
    breaks = find_scene_breaks(text)
    line_numbers = []

    for start, _ in breaks:
        # Count newlines before this position to get line number
        line_num = text[:start].count("\n") + 1
        line_numbers.append(line_num)

    return line_numbers
