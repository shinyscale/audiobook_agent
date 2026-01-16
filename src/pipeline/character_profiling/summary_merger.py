"""
Summary-driven character merge detection.

Parses book summary for explicit identity statements like:
- "A is later known as B"
- "A, later revealed to be B"
- "A—later revealed to be the cruel brothel madam Kate"

These explicit statements force-merge characters regardless of
distribution patterns (which may be misleading when a character's
old name is occasionally referenced in later chapters).

Feature F1 from character-profiling-enhancements-v2.prd.json
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..llm import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class IdentityStatement:
    """An explicit identity statement from the summary."""
    name_a: str  # First name mentioned
    name_b: str  # Second name (the "also known as")
    pattern_matched: str  # Which pattern matched
    quote: str  # The text that matched
    confidence: float = 0.9  # High confidence for explicit statements


@dataclass
class SummaryMergeResult:
    """Result of summary-based merge detection."""
    merge_pairs: list[tuple[str, str]]  # List of (name_a, name_b) pairs to merge
    statements: list[IdentityStatement]  # The statements that triggered merges
    raw_summary: str = ""  # The summary that was parsed


# Regex patterns for detecting explicit identity statements
# These patterns look for constructs like:
# - "A is later known as B"
# - "A, later revealed to be B"
# - "A—later revealed to be the cruel brothel madam Kate"
# - "A (also known as B)"
# - "A, also called B"
IDENTITY_PATTERNS = [
    # "A is later known as B" / "A is also known as B"
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r"(?:\s+is|\s+was)\s+"
        r"(?:later|also|now)\s+"
        r"(?:known|called|referred to)\s+as\s+"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        "is_known_as"
    ),
    # "A, later revealed to be B" / "A—later revealed to be B"
    # Match: "Cathy Ames—later revealed to be the cruel brothel madam Kate—"
    # The name B is typically at the end, often followed by punctuation or em-dash
    # We need to find the LAST capitalized word before the delimiter
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r"[,—–-]\s*"
        r"(?:later|eventually|ultimately)\s+"
        r"(?:revealed|discovered|shown|known)\s+"
        r"(?:to be|as)\s+"
        r"(?:(?:the|a|an)\s+)?(?:[\w]+\s+)*?"  # Optional descriptive words
        r"([A-Z][a-zA-Z]+)"  # Name B (must start with capital)
        r"(?=[—–\-,.\s]|$)",  # Followed by delimiter, punctuation, or end
        "revealed_to_be"
    ),
    # "A (also known as B)" / "A (aka B)"
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r"\s*\(\s*"
        r"(?:also\s+known\s+as|a\.?k\.?a\.?|formerly|née)\s+"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"
        r"\s*\)",
        "parenthetical_aka"
    ),
    # "A, also called/named B" - name only, not followed by prepositions
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r",\s+"
        r"(?:also\s+)?(?:called|named|known as)\s+"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name B
        r"(?=\s*[,.]|\s+(?:by|in|at|is|was|to|and|or|who|which|that|\Z))",  # Followed by punctuation or prepositions
        "also_called"
    ),
    # "A becomes/became B" (name change)
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r"\s+(?:becomes|became|transforms into|reinvents\s+(?:him|her)self\s+as)\s+"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        "becomes"
    ),
    # "born A" ... "known as B" (birth name pattern)
    (
        r"born\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Birth name
        r"[^.]*?"
        r"(?:known|called|went by|adopted the name)\s+"
        r"(?:as\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        "birth_name"
    ),
    # "A, whose real name is B"
    (
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"  # Name A
        r",?\s+whose\s+(?:real|true|birth|given)\s+name\s+(?:is|was)\s+"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        "real_name"
    ),
]

# Patterns that require case sensitivity to detect proper names
CASE_SENSITIVE_PATTERNS = {"revealed_to_be"}

# Compile patterns - some need case sensitivity, others don't
COMPILED_PATTERNS = []
for pattern, name in IDENTITY_PATTERNS:
    if name in CASE_SENSITIVE_PATTERNS:
        COMPILED_PATTERNS.append((re.compile(pattern), name))  # Case sensitive
    else:
        COMPILED_PATTERNS.append((re.compile(pattern, re.IGNORECASE), name))


LLM_IDENTITY_SYSTEM = """You are analyzing a book summary to identify when two character names refer to the same person.

Your job is to find EXPLICIT statements where the text says two names are the same person, such as:
- "Cathy Ames is later known as Kate"
- "Born James Gatz, he reinvented himself as Jay Gatsby"
- "The creature (also called Frankenstein's monster)"

IMPORTANT: Only report name pairs where the text EXPLICITLY states they are the same person.
Do NOT infer based on context alone.

Respond with valid JSON only."""


LLM_IDENTITY_PROMPT = """Analyze this summary and find any EXPLICIT statements that two names refer to the same person.

SUMMARY:
{summary}

Return a JSON array of identity pairs found:
```json
{{
  "identity_pairs": [
    {{
      "name_a": "First name mentioned",
      "name_b": "Second name (the alias)",
      "quote": "The exact text that states they are the same person",
      "confidence": 0.9
    }}
  ]
}}
```

If no explicit identity statements are found, return:
```json
{{
  "identity_pairs": []
}}
```

Return ONLY valid JSON."""


class SummaryMerger:
    """
    Detects character identity statements in book summaries.

    Uses regex patterns first for common constructs, then optionally
    uses LLM for more complex or ambiguous cases.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: Optional LLM client for enhanced detection.
                        If not provided, only regex patterns are used.
        """
        self.llm = llm_client

    def find_identity_statements(
        self,
        summary: str,
        use_llm: bool = True,
    ) -> SummaryMergeResult:
        """
        Find explicit identity statements in a summary.

        Args:
            summary: The book/plot summary text
            use_llm: Whether to use LLM for enhanced detection

        Returns:
            SummaryMergeResult with merge pairs and statements
        """
        statements: list[IdentityStatement] = []

        # First pass: regex patterns
        for pattern, pattern_name in COMPILED_PATTERNS:
            for match in pattern.finditer(summary):
                name_a = match.group(1).strip()
                name_b = match.group(2).strip()
                quote = match.group(0).strip()

                # Skip if names are identical (case-insensitive)
                if name_a.lower() == name_b.lower():
                    continue

                statements.append(IdentityStatement(
                    name_a=name_a,
                    name_b=name_b,
                    pattern_matched=pattern_name,
                    quote=quote,
                    confidence=0.9,
                ))
                logger.info(f"Found identity statement via regex: {name_a} = {name_b} (pattern: {pattern_name})")

        # Second pass: LLM (if available and enabled)
        if use_llm and self.llm:
            llm_statements = self._llm_detection(summary)

            # Merge LLM results, avoiding duplicates
            existing_pairs = {(s.name_a.lower(), s.name_b.lower()) for s in statements}
            existing_pairs.update({(s.name_b.lower(), s.name_a.lower()) for s in statements})

            for stmt in llm_statements:
                pair = (stmt.name_a.lower(), stmt.name_b.lower())
                reverse = (stmt.name_b.lower(), stmt.name_a.lower())
                if pair not in existing_pairs and reverse not in existing_pairs:
                    statements.append(stmt)
                    existing_pairs.add(pair)
                    logger.info(f"Found identity statement via LLM: {stmt.name_a} = {stmt.name_b}")

        # Build merge pairs
        merge_pairs = [(s.name_a, s.name_b) for s in statements]

        return SummaryMergeResult(
            merge_pairs=merge_pairs,
            statements=statements,
            raw_summary=summary,
        )

    def _llm_detection(self, summary: str) -> list[IdentityStatement]:
        """Use LLM to find identity statements."""
        if not self.llm:
            return []

        prompt = LLM_IDENTITY_PROMPT.format(summary=summary)
        result, response = self.llm.query_json(prompt, system=LLM_IDENTITY_SYSTEM)

        if not response.success or result is None:
            logger.warning(f"LLM identity detection failed: {response.error}")
            return []

        statements = []
        for pair in result.get("identity_pairs", []):
            name_a = pair.get("name_a", "").strip()
            name_b = pair.get("name_b", "").strip()

            if not name_a or not name_b:
                continue

            if name_a.lower() == name_b.lower():
                continue

            statements.append(IdentityStatement(
                name_a=name_a,
                name_b=name_b,
                pattern_matched="llm_detection",
                quote=pair.get("quote", ""),
                confidence=pair.get("confidence", 0.85),
            ))

        return statements


def find_summary_merges(
    summary: str,
    llm_client: Optional[LLMClient] = None,
) -> SummaryMergeResult:
    """
    Convenience function to find character merges from a summary.

    Args:
        summary: The book/plot summary text
        llm_client: Optional LLM client for enhanced detection

    Returns:
        SummaryMergeResult with merge pairs
    """
    merger = SummaryMerger(llm_client)
    return merger.find_identity_statements(summary)


def apply_summary_merges(
    characters: list,
    merge_result: SummaryMergeResult,
) -> list:
    """
    Apply merge pairs to a list of characters.

    For each merge pair (name_a, name_b), finds the characters with
    those names and merges them into a single character entry.

    Args:
        characters: List of character objects with canonical_name and aliases
        merge_result: Result from find_summary_merges

    Returns:
        Updated character list with merges applied
    """
    if not merge_result.merge_pairs:
        return characters

    # Build a lookup for characters by name (including aliases)
    name_to_char: dict[str, Any] = {}
    for char in characters:
        name_to_char[char.canonical_name.lower()] = char
        for alias in getattr(char, 'aliases', []):
            name_to_char[alias.lower()] = char

    # Track which characters to remove (merged into others)
    to_remove: set = set()

    for name_a, name_b in merge_result.merge_pairs:
        char_a = name_to_char.get(name_a.lower())
        char_b = name_to_char.get(name_b.lower())

        if char_a is None or char_b is None:
            logger.debug(f"Could not find both characters for merge: {name_a}, {name_b}")
            continue

        if char_a is char_b:
            logger.debug(f"Characters already merged: {name_a}, {name_b}")
            continue

        # Merge char_b into char_a
        logger.info(f"Merging character '{char_b.canonical_name}' into '{char_a.canonical_name}'")

        # Add char_b's canonical name and aliases to char_a
        if char_b.canonical_name not in char_a.aliases:
            char_a.aliases.append(char_b.canonical_name)
        for alias in getattr(char_b, 'aliases', []):
            if alias not in char_a.aliases and alias.lower() != char_a.canonical_name.lower():
                char_a.aliases.append(alias)

        # Merge chapters present if available
        if hasattr(char_a, 'chapters_present') and hasattr(char_b, 'chapters_present'):
            combined = sorted(set(char_a.chapters_present + char_b.chapters_present))
            char_a.chapters_present = combined

        # Merge mention data if available
        if hasattr(char_a, 'mention_count') and hasattr(char_b, 'mention_count'):
            char_a.mention_count = char_a.mention_count + char_b.mention_count

        if hasattr(char_a, 'mentions') and hasattr(char_b, 'mentions'):
            char_a.mentions = char_a.mentions + char_b.mentions

        # Mark char_b for removal
        to_remove.add(id(char_b))

        # Update lookup to point char_b names to char_a
        name_to_char[char_b.canonical_name.lower()] = char_a
        for alias in getattr(char_b, 'aliases', []):
            name_to_char[alias.lower()] = char_a

    # Remove merged characters
    return [char for char in characters if id(char) not in to_remove]
