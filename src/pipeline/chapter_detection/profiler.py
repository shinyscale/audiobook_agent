"""
Document profiler for chapter detection.

Stage 1: Understand the document structure before detecting chapters.
This includes TOC extraction when present.
"""

import re
from typing import Optional
import logging

from .models import DocumentProfile, TableOfContents, TOCEntry
from ..llm import LLMClient

logger = logging.getLogger(__name__)


# Patterns for detecting TOC
TOC_HEADER_PATTERNS = [
    re.compile(r"^\s*(Table\s+of\s+Contents|Contents|CONTENTS|TABLE OF CONTENTS)\s*$", re.MULTILINE | re.IGNORECASE),
]

# Pattern for TOC entries (title followed by optional page number)
TOC_ENTRY_PATTERN = re.compile(
    r"^\s*(.+?)\s*(?:\.{2,}|…+|\s{3,})?\s*(\d+)?\s*$",
    re.MULTILINE,
)

# Patterns indicating end of front matter
CONTENT_START_PATTERNS = [
    re.compile(r"^\s*(Chapter|CHAPTER)\s+", re.MULTILINE),
    re.compile(r"^\s{10,}(I|1)\s*$", re.MULTILINE),  # Centered numeral
    re.compile(r"^\s*(Prologue|PROLOGUE)\s*$", re.MULTILINE),
]


PROFILER_SYSTEM_PROMPT = """You are a document structure analyst. Analyze the opening of a book to understand its structure.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or its structure.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

Consider:
1. Document type: novel (single narrative), anthology (short stories), memoir, epistolary (letters/diary), technical
2. Whether it has explicit chapter markers or uses more subtle divisions
3. Any table of contents present
4. Structural conventions used (numbered chapters, named chapters, parts, etc.)"""

PROFILER_PROMPT_TEMPLATE = """Analyze this document opening to understand its structure.

DOCUMENT OPENING (first ~5000 characters):
{text}

Determine:
1. document_type: "novel", "anthology", "memoir", "epistolary", or "technical"
2. has_explicit_markers: true if it uses "Chapter 1", "Part One", roman numerals, etc.
3. structural_conventions: list of patterns like "numbered_chapters", "named_chapters", "roman_numerals", "part_divisions"
4. estimated_chapter_count: rough estimate if you can tell from TOC or pattern
5. reasoning: brief explanation of your analysis

Return JSON:
```json
{{
  "document_type": "novel",
  "has_explicit_markers": true,
  "structural_conventions": ["roman_numerals", "numbered_chapters"],
  "estimated_chapter_count": 9,
  "reasoning": "Book has Table of Contents showing 9 Roman numeral chapters (I-IX)"
}}
```"""


class DocumentProfiler:
    """
    Profiles a document to understand its structure before chapter detection.

    This includes:
    - Detecting document type
    - Extracting Table of Contents if present
    - Identifying structural conventions
    - Finding where front matter ends
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client

    def profile(self, text: str) -> DocumentProfile:
        """
        Profile a document to understand its structure.

        Args:
            text: Full document text

        Returns:
            DocumentProfile with structural information
        """
        logger.info(f"DocumentProfiler: profiling document ({len(text):,} chars)")

        # 1. Try to extract TOC (deterministic)
        toc = self._extract_toc(text)
        if toc:
            logger.info(
                f"DocumentProfiler: found TOC with {len(toc.entries)} entries "
                f"(pos {toc.toc_start_position}-{toc.toc_end_position})"
            )
            for entry in toc.entries[:10]:
                logger.debug(f"  TOC entry: '{entry.title}' (page {entry.page_number})")
            if len(toc.entries) > 10:
                logger.debug(f"  ... and {len(toc.entries) - 10} more entries")
        else:
            logger.info("DocumentProfiler: no TOC detected")

        # 2. Find where front matter ends
        front_matter_end = self._find_front_matter_end(text, toc)
        logger.info(f"DocumentProfiler: front_matter_end={front_matter_end}")

        # Log what's at that position
        context_start = max(0, front_matter_end - 50)
        context_end = min(len(text), front_matter_end + 100)
        logger.debug(
            f"DocumentProfiler: text at front_matter_end: "
            f"...{repr(text[context_start:front_matter_end])} | "
            f"{repr(text[front_matter_end:context_end])}..."
        )

        # 3. Detect structural conventions (deterministic first)
        conventions = self._detect_conventions(text, front_matter_end)
        logger.info(f"DocumentProfiler: detected conventions: {conventions}")

        # 4. Use LLM to enhance understanding if available
        if self.llm:
            llm_profile = self._llm_profile(text[:8000])
            if llm_profile:
                logger.info(f"DocumentProfiler: LLM profile: {llm_profile}")
        else:
            llm_profile = None

        # 5. Combine deterministic and LLM analysis
        profile = self._build_profile(text, toc, front_matter_end, conventions, llm_profile)

        logger.info(
            f"DocumentProfiler: final profile - type={profile.document_type}, "
            f"explicit_markers={profile.has_explicit_markers}, "
            f"estimated_chapters={profile.estimated_chapter_count}"
        )

        return profile

    def _extract_toc(self, text: str) -> Optional[TableOfContents]:
        """Extract Table of Contents if present."""
        # Find TOC header
        toc_start = None
        for pattern in TOC_HEADER_PATTERNS:
            match = pattern.search(text[:10000])  # TOC usually in first 10k chars
            if match:
                toc_start = match.start()
                break

        if toc_start is None:
            return None

        # Find TOC end (next major section or blank line run)
        toc_region = text[toc_start:toc_start + 5000]

        # TOC typically ends with multiple blank lines or content start
        toc_end_match = re.search(r"\n\s*\n\s*\n", toc_region)
        if toc_end_match:
            toc_end = toc_start + toc_end_match.end()
        else:
            toc_end = toc_start + len(toc_region)

        toc_text = text[toc_start:toc_end]

        # Parse TOC entries
        entries = self._parse_toc_entries(toc_text, toc_start)

        if not entries:
            return None

        return TableOfContents(
            entries=entries,
            toc_start_position=toc_start,
            toc_end_position=toc_end,
            confidence=0.9 if len(entries) >= 3 else 0.6,
        )

    def _is_metadata_line(self, line: str) -> bool:
        """Check if a line is metadata rather than a TOC entry."""
        line_lower = line.lower()
        metadata_indicators = [
            'copyright', 'published', 'edition', 'isbn',
            'all rights', 'reserved', 'author', 'introduction',
            'foreword', 'preface', 'acknowledgments', 'dedication',
            'translator', 'editor', 'illustrated', 'written by',
        ]
        for indicator in metadata_indicators:
            if indicator in line_lower:
                return True
        # Check for "by Author" pattern at start
        if line_lower.startswith('by ') and len(line) > 5:
            return True
        # Also reject very long lines (likely prose, not TOC)
        if len(line) > 80:
            return True
        return False

    def _validate_toc_entries(self, entries: list[TOCEntry]) -> list[TOCEntry]:
        """Validate and filter TOC entries for consistency."""
        if not entries:
            return entries

        # Check for Roman numeral sequence
        roman_pattern = re.compile(r'^[IVXLC]+$')
        roman_entries = [e for e in entries if roman_pattern.match(e.title.strip())]

        if len(roman_entries) >= 3 and len(roman_entries) / len(entries) > 0.3:
            logger.info(f"TOC validation: detected Roman numeral pattern, "
                        f"keeping {len(roman_entries)} of {len(entries)} entries")
            return roman_entries

        # Check for "Chapter N" pattern
        chapter_pattern = re.compile(r'^chapter\s+\d+', re.IGNORECASE)
        chapter_entries = [e for e in entries if chapter_pattern.match(e.title.strip())]

        if len(chapter_entries) >= 3 and len(chapter_entries) / len(entries) > 0.3:
            logger.info(f"TOC validation: detected Chapter N pattern, "
                        f"keeping {len(chapter_entries)} of {len(entries)} entries")
            return chapter_entries

        # Warn on unreasonable counts
        if len(entries) > 30:
            logger.warning(f"TOC validation: {len(entries)} entries seems too many")
            level1_entries = [e for e in entries if e.level == 1]
            if len(level1_entries) >= 3:
                logger.info(f"TOC validation: filtering to {len(level1_entries)} level-1 entries")
                return level1_entries

        return entries

    def _parse_toc_entries(self, toc_text: str, toc_start: int) -> list[TOCEntry]:
        """Parse individual TOC entries."""
        entries = []

        # Skip the header line
        lines = toc_text.split("\n")[1:]

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Skip non-entry lines
            if line_stripped.lower() in ["table of contents", "contents"]:
                continue

            # Skip metadata lines
            if self._is_metadata_line(line_stripped):
                logger.debug(f"TOC: skipping metadata line: {line_stripped[:50]}")
                continue

            # Try to parse as TOC entry
            entry = self._parse_toc_line(line, toc_start)
            if entry:
                entries.append(entry)

        # Validate and filter entries
        return self._validate_toc_entries(entries)

    def _parse_toc_line(self, line: str, base_position: int) -> Optional[TOCEntry]:
        """Parse a single TOC line."""
        # Common TOC formats:
        # "Chapter 1..........15"
        # "I. The Beginning   1"
        # "Part One"

        # Strip leader dots and extra spaces
        cleaned = re.sub(r"\.{2,}|…+", "  ", line)
        parts = cleaned.split()

        if not parts:
            return None

        # Check for page number at end
        page_num = None
        if parts[-1].isdigit():
            page_num = int(parts[-1])
            parts = parts[:-1]

        if not parts:
            return None

        title = " ".join(parts)

        # Filter out lines that don't look like chapter entries
        # Allow single-character Roman numerals (I, V, X, L, C, D, M)
        is_roman_numeral = bool(re.match(r"^[IVXLCDM]+$", title))
        if len(title) > 100:
            return None
        if len(title) < 2 and not is_roman_numeral:
            return None

        # Determine nesting level
        level = 1
        if re.match(r"^\s{4,}", line):  # Indented = nested
            level = 2

        return TOCEntry(
            title=title,
            position_in_toc=base_position,
            page_number=page_num,
            level=level,
        )

    def _find_front_matter_end(self, text: str, toc: Optional[TableOfContents]) -> int:
        """Find where front matter ends and main content begins."""
        # If we have a TOC, front matter ends after it
        if toc:
            start_search = toc.toc_end_position
        else:
            start_search = 0

        # Look for first chapter marker after TOC
        for pattern in CONTENT_START_PATTERNS:
            match = pattern.search(text[start_search:start_search + 20000])
            if match:
                return start_search + match.start()

        # Fallback: look for significant prose (paragraph of 100+ words)
        para_pattern = re.compile(r"\n\s*\n(.{500,}?)\n\s*\n", re.DOTALL)
        match = para_pattern.search(text[start_search:start_search + 30000])
        if match:
            return start_search + match.start()

        # Default: assume front matter is first 1000 chars or start of text
        return min(1000, len(text) // 10)

    def _detect_conventions(self, text: str, front_matter_end: int) -> list[str]:
        """Detect structural conventions used in the document."""
        conventions = []
        sample = text[front_matter_end:front_matter_end + 50000]

        # Check for various patterns
        if re.search(r"Chapter\s+\d+", sample, re.IGNORECASE):
            conventions.append("numbered_chapters")

        if re.search(r"Chapter\s+[IVXLC]+", sample, re.IGNORECASE):
            conventions.append("roman_numeral_chapters")

        if re.search(r"^\s{5,}[IVXLC]+\s*$", sample, re.MULTILINE):
            conventions.append("roman_numerals_standalone")

        if re.search(r"Part\s+(One|Two|Three|\d+|[IVXLC]+)", sample, re.IGNORECASE):
            conventions.append("part_divisions")

        if re.search(r"^Chapter\s+\d+\s*[:\-—]\s*.+$", sample, re.MULTILINE | re.IGNORECASE):
            conventions.append("named_chapters")

        # REMOVED: Scene breaks should NOT be treated as structural chapter markers
        # They are scene transitions WITHIN chapters
        # if re.search(r"\*\s*\*\s*\*|\-\s*\-\s*\-|~\s*~\s*~", sample):
        #     conventions.append("scene_breaks")

        return conventions

    def _llm_profile(self, text_sample: str) -> Optional[dict]:
        """Use LLM to profile the document."""
        prompt = PROFILER_PROMPT_TEMPLATE.format(text=text_sample)

        result, response = self.llm.query_json(prompt, system=PROFILER_SYSTEM_PROMPT)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM profiler failed: {response.error}")
            return None

        if result is None or not isinstance(result, dict):
            # JSON parsing failure or wrong type
            error_detail = f"got {type(result).__name__}" if result is not None else "failed to parse JSON"
            logger.warning(f"LLM profiler failed ({error_detail}): {response.content[:200] if response.content else 'empty response'}")
            return None

        return result

    def _build_profile(
        self,
        text: str,
        toc: Optional[TableOfContents],
        front_matter_end: int,
        conventions: list[str],
        llm_profile: Optional[dict],
    ) -> DocumentProfile:
        """Combine all information into a DocumentProfile."""
        # Start with deterministic analysis
        has_explicit = bool(conventions)

        # Estimate chapter count from TOC if available
        estimated_count = len(toc.entries) if toc else None

        # Document type - default to novel
        doc_type = "novel"

        # Merge LLM insights if available
        if llm_profile:
            if llm_profile.get("document_type"):
                doc_type = llm_profile["document_type"]

            if llm_profile.get("structural_conventions"):
                # Merge conventions, preferring our deterministic ones
                llm_conventions = llm_profile["structural_conventions"]
                for conv in llm_conventions:
                    if conv not in conventions:
                        conventions.append(conv)

            if not estimated_count and llm_profile.get("estimated_chapter_count"):
                estimated_count = llm_profile["estimated_chapter_count"]

            has_explicit = has_explicit or llm_profile.get("has_explicit_markers", False)

            reasoning = llm_profile.get("reasoning", "")
        else:
            reasoning = f"Detected conventions: {conventions}"

        # Calculate confidence based on how much information we have
        confidence = 0.5
        if toc:
            confidence += 0.3
        if conventions:
            confidence += 0.1
        if llm_profile:
            confidence += 0.1
        confidence = min(1.0, confidence)

        return DocumentProfile(
            document_type=doc_type,
            has_explicit_markers=has_explicit,
            table_of_contents=toc,
            estimated_chapter_count=estimated_count,
            structural_conventions=conventions,
            front_matter_end=front_matter_end,
            confidence=confidence,
            reasoning=reasoning,
        )
