"""
Regex-based chapter proposer.

This is the deterministic baseline - fast, reproducible, no LLM dependency.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from ..models import ChapterProposal, DocumentProfile
from ....utils.debug_log import append_debug_event
from .base import BaseProposer

logger = logging.getLogger(__name__)


@dataclass
class ChapterPattern:
    """A pattern for detecting chapter markers."""

    pattern: re.Pattern
    confidence: float
    description: str
    # F10: Explicit hard boundaries dominate over soft signals
    is_hard_boundary: bool = False  # True for explicit markers


# Patterns ordered from most to least specific
# F10: Explicit markers (is_hard_boundary=True) dominate over soft signals
CHAPTER_PATTERNS = [
    # Explicit "Chapter" markers - HARD BOUNDARIES
    ChapterPattern(
        re.compile(
            r"^\s*(Chapter|CHAPTER)\s+(\d+|[IVXLC]+)(?:\s*[:\.\-—–]\s*(.+?))?$", re.MULTILINE
        ),
        confidence=0.95,
        description="explicit_chapter_numbered",
        is_hard_boundary=True,
    ),
    ChapterPattern(
        re.compile(r"^\s*(CHAPTER|Chapter)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$", re.MULTILINE),
        confidence=0.90,
        description="explicit_chapter_word_number",
        is_hard_boundary=True,
    ),
    # Part markers - HARD BOUNDARIES
    ChapterPattern(
        re.compile(
            r"^\s*(Part|PART)\s+(\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:\s*[:\.\-—–]\s*(.+?))?$",
            re.MULTILINE | re.IGNORECASE,
        ),
        confidence=0.95,
        description="part_marker",
        is_hard_boundary=True,
    ),
    # Roman numeral only (common in classic literature)
    # STRICT: Must be centered (10+ spaces) - works for all Roman numerals including "I"
    # HARD BOUNDARY
    ChapterPattern(
        re.compile(r"^\s{10,}([IVXLC]+)\s*$", re.MULTILINE),
        confidence=0.85,
        description="roman_numeral_centered",
        is_hard_boundary=True,
    ),
    # RELAXED but safer: Requires 2+ characters to avoid matching "I" pronoun in dialogue
    # This is a softer signal, not a hard boundary
    ChapterPattern(
        re.compile(r"^\s*([IVXLC]{2,7})\s*$", re.MULTILINE),
        confidence=0.70,
        description="roman_numeral_line",
        is_hard_boundary=False,
    ),
    # Roman numeral with trailing period (e.g., "I.", "II.", "III.")
    # Common in classic literature - HARD BOUNDARY since the period is explicit
    ChapterPattern(
        re.compile(r"^\s*([IVXLC]+)\.\s*$", re.MULTILINE),
        confidence=0.90,
        description="roman_numeral_with_period",
        is_hard_boundary=True,
    ),
    # Arabic numeral only (centered) - HARD BOUNDARY when centered
    ChapterPattern(
        re.compile(r"^\s{10,}(\d{1,3})\s*$", re.MULTILINE),
        confidence=0.75,
        description="arabic_numeral_centered",
        is_hard_boundary=True,
    ),
    # Named chapters (all caps on own line) - softer signal
    ChapterPattern(
        re.compile(r"^\s*([A-Z][A-Z\s]{5,40})\s*$", re.MULTILINE),
        confidence=0.60,
        description="all_caps_title",
        is_hard_boundary=False,
    ),
    # Prologue/Epilogue and other special sections - HARD BOUNDARIES
    ChapterPattern(
        re.compile(
            r"^\s*(Prologue|PROLOGUE|Epilogue|EPILOGUE|Introduction|INTRODUCTION|Preface|PREFACE|"
            r"Foreword|FOREWORD|Afterword|AFTERWORD|Appendix|APPENDIX|Acknowledgments|ACKNOWLEDGMENTS|"
            r"Dedication|DEDICATION|Notes|NOTES|Glossary|GLOSSARY|Interlude|INTERLUDE|Intermezzo|INTERMEZZO)\s*$",
            re.MULTILINE,
        ),
        confidence=0.95,
        description="special_section",
        is_hard_boundary=True,
    ),
    # Letters in epistolary novels (Letter 1, Letter I, etc.) - HARD BOUNDARIES
    ChapterPattern(
        re.compile(
            r"^\s*(Letter|LETTER)\s+(\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:\s*[:\.\-—–]\s*(.+?))?$",
            re.MULTILINE | re.IGNORECASE,
        ),
        confidence=0.95,
        description="letter_section",
        is_hard_boundary=True,
    ),
    # "Book One", "Book Two" etc. - HARD BOUNDARIES
    ChapterPattern(
        re.compile(
            r"^\s*(Book|BOOK)\s+(\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|[IVXLC]+)(?:\s*[:\.\-—–]\s*(.+?))?$",
            re.MULTILINE | re.IGNORECASE,
        ),
        confidence=0.95,
        description="book_division",
        is_hard_boundary=True,
    ),
]


class RegexProposer(BaseProposer):
    """
    Proposes chapter boundaries using regex patterns.

    This is the baseline proposer - deterministic and fast.
    """

    name = "regex"

    def __init__(self, min_chapter_words: int = 100):
        """
        Args:
            min_chapter_words: Minimum words between chapter markers to be considered valid
        """
        self.min_chapter_words = min_chapter_words

    def propose(
        self,
        text: str,
        profile: Optional[DocumentProfile] = None,
    ) -> list[ChapterProposal]:
        """Find chapter boundaries using regex patterns."""
        proposals = []
        seen_positions = set()  # Avoid duplicates

        # If we have a profile with front matter info, start after it
        start_position = profile.front_matter_end if profile else 0
        logger.info(
            f"[DEBUG] RegexProposer: start_position={start_position} (front_matter_end) "
            f"at line {text[:start_position].count(chr(10))+1 if start_position < len(text) else 'EOF'}"
        )

        # Track matches per pattern for debugging
        pattern_match_counts = {}
        skipped_front_matter = 0
        skipped_duplicate = 0

        for pattern_def in CHAPTER_PATTERNS:
            pattern_matches = 0
            for match in pattern_def.pattern.finditer(text):
                position = match.start()

                # Skip if in front matter
                if position < start_position:
                    skipped_front_matter += 1
                    logger.debug(
                        f"  Skipped (front matter): '{match.group(0).strip()[:40]}' "
                        f"at pos {position}"
                    )
                    continue

                # Skip if we already have a proposal very close to this position
                if any(abs(position - p) < 50 for p in seen_positions):
                    skipped_duplicate += 1
                    logger.debug(
                        f"  Skipped (duplicate): '{match.group(0).strip()[:40]}' "
                        f"at pos {position}"
                    )
                    continue

                # Extract title from match groups
                title = self._extract_title(match, pattern_def.description)

                # Get the matched text as evidence
                evidence = match.group(0).strip()

                # Adjust confidence based on context
                confidence = self._adjust_confidence(
                    text, position, pattern_def.confidence, pattern_def.description
                )

                proposals.append(
                    ChapterProposal(
                        strategy=self.name,
                        position=position,
                        title=title,
                        evidence=evidence,
                        confidence=confidence,
                        reasoning=f"Matched pattern: {pattern_def.description}",
                        is_hard_boundary=pattern_def.is_hard_boundary,
                    )
                )
                seen_positions.add(position)
                pattern_matches += 1

            if pattern_matches > 0:
                pattern_match_counts[pattern_def.description] = pattern_matches

        # Log summary of matches found
        if pattern_match_counts:
            logger.info(f"RegexProposer matches by pattern: {pattern_match_counts}")
        logger.debug(
            f"RegexProposer: skipped {skipped_front_matter} (front matter), "
            f"{skipped_duplicate} (duplicate)"
        )

        # Log all proposals before filtering
        logger.info(f"RegexProposer: {len(proposals)} proposals before size filtering:")
        for p in sorted(proposals, key=lambda x: x.position):
            logger.debug(f"  pos={p.position}: '{p.title}' (conf={p.confidence:.2f})")

        # Filter proposals that are too close together (likely false positives)
        pre_filter_count = len(proposals)
        proposals = self._filter_too_close(text, proposals)

        if len(proposals) != pre_filter_count:
            logger.info(
                f"RegexProposer: filtered {pre_filter_count - len(proposals)} "
                f"proposals (too close), {len(proposals)} remaining"
            )

        # Sort by position
        proposals.sort(key=lambda p: p.position)

        # Final summary
        logger.info(f"RegexProposer: returning {len(proposals)} proposals")
        for p in proposals:
            logger.info(f"  [{p.position}] {p.title} (conf={p.confidence:.2f})")

        # region agent log (chapter-v-bug) - hypothesis A/D
        try:
            _titles_u = [(p.title or "").strip().upper() for p in proposals]
            _has_v = any(t in ("V", "CHAPTER V") or t.endswith(" V") for t in _titles_u)
            _has_i = any(t in ("I", "CHAPTER I") or t.endswith(" I") for t in _titles_u)
            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "chapter-v-bug-pre",
                    "hypothesisId": "D",
                    "location": "src/pipeline/chapter_detection/proposers/regex.py:RegexProposer.propose:summary",
                    "message": "Regex proposer summary (pattern counts + I/V presence)",
                    "data": {
                        "front_matter_end": (getattr(profile, "front_matter_end", None) if profile else None),
                        "pattern_match_counts": pattern_match_counts,
                        "skipped_front_matter": skipped_front_matter,
                        "skipped_duplicate": skipped_duplicate,
                        "proposal_count_returned": len(proposals),
                        "has_I": _has_i,
                        "has_V": _has_v,
                        "first_20_titles": [p.title for p in proposals[:20]],
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        return proposals

    def _extract_title(self, match: re.Match, pattern_type: str) -> Optional[str]:
        """Extract chapter title from regex match."""
        groups = match.groups()

        if pattern_type in ["explicit_chapter_numbered", "explicit_chapter_word_number"]:
            # Groups: (Chapter/CHAPTER, number, optional title)
            base = f"Chapter {groups[1]}"
            if len(groups) > 2 and groups[2]:
                return f"{base}: {groups[2].strip()}"
            return base

        elif pattern_type == "part_marker":
            base = f"Part {groups[1]}"
            if len(groups) > 2 and groups[2]:
                return f"{base}: {groups[2].strip()}"
            return base

        elif pattern_type in ["roman_numeral_centered", "roman_numeral_line"]:
            return f"Chapter {groups[0]}"

        elif pattern_type == "arabic_numeral_centered":
            return f"Chapter {groups[0]}"

        elif pattern_type == "all_caps_title":
            return groups[0].strip().title()

        elif pattern_type == "special_section":
            return groups[0].strip().title()

        elif pattern_type == "book_division":
            base = f"Book {groups[1]}"
            if len(groups) > 2 and groups[2]:
                return f"{base}: {groups[2].strip()}"
            return base

        return match.group(0).strip()

    def _adjust_confidence(
        self,
        text: str,
        position: int,
        base_confidence: float,
        pattern_type: str,
    ) -> float:
        """Adjust confidence based on context around the match."""
        confidence = base_confidence

        # Check if there's significant whitespace before (chapter markers often follow blank lines)
        before = text[max(0, position - 50) : position]
        blank_lines_before = before.count("\n\n") + before.count("\n \n")
        if blank_lines_before >= 1:
            confidence = min(1.0, confidence + 0.05)

        # Check if there's text after (not just end of document)
        after = text[position : min(len(text), position + 500)]
        if len(after.strip()) < 100:
            confidence -= 0.1  # Might be end matter, not a real chapter

        # All caps titles need more validation - check they're not just headers in text
        if pattern_type == "all_caps_title":
            # Lower confidence if surrounded by regular text (not preceded by blank lines)
            if blank_lines_before < 1:
                confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _filter_too_close(
        self,
        text: str,
        proposals: list[ChapterProposal],
    ) -> list[ChapterProposal]:
        """Filter out proposals that would create chapters smaller than min_chapter_words."""
        if len(proposals) < 2:
            return proposals

        # Sort by position
        sorted_proposals = sorted(proposals, key=lambda p: p.position)

        filtered = [sorted_proposals[0]]
        for proposal in sorted_proposals[1:]:
            last_pos = filtered[-1].position
            text_between = text[last_pos : proposal.position]
            word_count = len(text_between.split())

            if word_count >= self.min_chapter_words:
                filtered.append(proposal)
            else:
                # Keep the one with higher confidence
                if proposal.confidence > filtered[-1].confidence:
                    logger.debug(
                        f"  Replaced '{filtered[-1].title}' (conf={filtered[-1].confidence:.2f}) "
                        f"with '{proposal.title}' (conf={proposal.confidence:.2f}) "
                        f"- only {word_count} words between"
                    )
                    filtered[-1] = proposal
                else:
                    logger.debug(
                        f"  Discarded '{proposal.title}' (conf={proposal.confidence:.2f}) "
                        f"- only {word_count} words from '{filtered[-1].title}'"
                    )

        return filtered
