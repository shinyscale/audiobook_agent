"""
Perspective-based filtering helpers.

These utilities reduce "narrator contamination" when extracting evidence/passages
for a character in first-person narratives.

Core idea:
- In first-person texts, many sentences look like "I did X to John" or
  "I thought John was Y". These sentences primarily describe the narrator's
  actions/thoughts, not John's actions/traits.
- For NON-narrator characters, we conservatively filter such sentences unless
  the character is clearly the grammatical subject/co-subject or is introduced
  appositively ("my nephew John", "John, my nephew, ...").
"""

from __future__ import annotations

import re


_FIRST_PERSON_ANY_RE = re.compile(
    r"\b(I|me|my|mine|myself|we|us|our|ours|ourselves)\b", re.IGNORECASE
)

# Starts with narrator as subject, allowing leading ellipsis/quotes.
_FIRST_PERSON_SUBJECT_START_RE = re.compile(
    r'^\s*(\.\.\.)?\s*["\'“”‘’]?\s*(I|We)\b', re.IGNORECASE
)


def is_first_person_text(text: str) -> bool:
    return bool(_FIRST_PERSON_ANY_RE.search(text or ""))


def _is_character_subject_or_co_subject(text: str, matched_name: str) -> bool:
    """
    Heuristic: treat name as subject if it appears near sentence start or
    appears in a co-subject construction with I/we ("John and I ...", "I and John ...").
    """
    if not text or not matched_name:
        return False

    name = re.escape(matched_name)

    # Co-subject patterns
    if re.search(rf"\b{name}\b\s+and\s+\b(I|we)\b", text, re.IGNORECASE):
        return True
    if re.search(rf"\b(I|we)\b\s+and\s+\b{name}\b", text, re.IGNORECASE):
        return True

    # Subject-ish: name begins the sentence (allow leading ellipsis/quotes)
    if re.search(rf'^\s*(\.\.\.)?\s*["\'“”‘’]?\s*\b{name}\b', text, re.IGNORECASE):
        return True

    return False


def _is_appositive_my_relation(text: str, matched_name: str) -> bool:
    """
    Keep sentences where first-person narrator is introducing/labeling the character,
    e.g. "my nephew John", "John, my nephew, ..."
    """
    if not text or not matched_name:
        return False

    name = re.escape(matched_name)
    relations = (
        "father|mother|dad|mom|son|daughter|child|brother|sister|uncle|aunt|"
        "nephew|niece|cousin|husband|wife|friend|companion"
    )

    if re.search(rf"\bmy\b\s+({relations})\s+\b{name}\b", text, re.IGNORECASE):
        return True
    if re.search(rf"\b{name}\b\s*,\s*my\b\s+({relations})\b", text, re.IGNORECASE):
        return True

    return False


def should_exclude_narrator_perspective_for_non_narrator(
    text: str,
    matched_name: str,
) -> bool:
    """
    Return True if this text is likely narrator-centric (narrator as subject) and
    should be excluded when extracting evidence for a NON-narrator character.
    """
    if not text or not matched_name:
        return False

    if not is_first_person_text(text):
        return False

    # If narrator is not clearly the subject, don't exclude.
    if not _FIRST_PERSON_SUBJECT_START_RE.search(text):
        return False

    # Keep if character is subject/co-subject or appositively described.
    if _is_character_subject_or_co_subject(text, matched_name):
        return False
    if _is_appositive_my_relation(text, matched_name):
        return False

    return True

