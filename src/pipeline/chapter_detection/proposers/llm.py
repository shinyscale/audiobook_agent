"""
LLM-based chapter proposers.

Two strategies:
1. LLMMarkerProposer: Finds explicit chapter markers in text
2. LLMNarrativeProposer: Finds narrative/structural breaks (for books without explicit markers)
"""

import logging
import re
from typing import Optional

from ...llm import LLMClient
from ..models import ChapterProposal, DocumentProfile
from .base import BaseProposer

logger = logging.getLogger(__name__)


MARKER_SYSTEM_PROMPT = """You are a document structure analyst. Your job is to find EXPLICIT chapter or section markers in text.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or its structure.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

You are looking for STRUCTURAL MARKERS that divide the book:
- "Chapter 1", "Chapter One", "CHAPTER I"
- "Part One", "Part 1", "PART I"
- Roman numerals standing alone as headings (I, II, III, IV, V...)
- Named section headers in all caps or title case on their own line
- "Prologue", "Epilogue", "Introduction"
- Book divisions ("Book One", "Book Two")

You are NOT looking for:
- Scene breaks: *** or --- or -------- or === or ~~~ or ... (any repeated punctuation)
- These are transitions WITHIN chapters, not chapter boundaries
- Paragraph breaks or whitespace
- Minor section divisions within chapters
- Section headers that are part of the narrative flow

IMPORTANT - Do NOT mark these as chapter markers:
- Scene breaks: lines of dashes (--------), asterisks (***), equals (===), tildes (~~~), or dots (...)
- References to chapters in dialogue or narrative (e.g., "In Chapter 1, we saw...")
- Glossary entries or definitions that mention chapter numbers
- Bibliography citations or index references
- Back matter that references chapters (appendix, notes, etc.)
- Text that MENTIONS a chapter number but isn't a STRUCTURAL HEADING

CRITICAL DISTINCTIONS:
- STRUCTURAL MARKER: "Chapter 5" appearing as a HEADING that divides the book into sections
- NOT A MARKER: "...as explained in Chapter 5, the character..." (just a textual reference)
- SCENE BREAK: "--------" or "***" marking a transition WITHIN a chapter (NOT a chapter boundary)

CRITICAL: You must return the EXACT TEXT as it appears. We will search for your text - if you paraphrase, the search will fail."""

MARKER_PROMPT_TEMPLATE = """Find all EXPLICIT chapter/section markers in the following text.

TEXT:
{text}

Return a JSON array of chapter markers found. For each marker:
- "marker_text": The EXACT text of the marker as it appears (copy character-for-character)
- "title": The chapter title/number (e.g., "Chapter 1", "Part Two", "Prologue")
- "confidence": Your confidence this is a real chapter marker (0.0-1.0)
- "reasoning": Brief explanation

Example response:
```json
[
  {{"marker_text": "CHAPTER I", "title": "Chapter 1", "confidence": 0.95, "reasoning": "Explicit chapter marker"}},
  {{"marker_text": "II", "title": "Chapter 2", "confidence": 0.85, "reasoning": "Roman numeral following chapter 1 pattern"}}
]
```

If no chapter markers are found, return an empty array: []

Respond with ONLY the JSON array, no other text."""


NARRATIVE_SYSTEM_PROMPT = """You are a literary analyst identifying major structural breaks in narratives.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or its structure.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

You are looking for MAJOR transitions that would typically separate chapters:
- Significant time jumps (days, weeks, years passing)
- Point-of-view changes (switching narrators)
- Major setting changes (new location, different scene entirely)
- Major plot divisions (end of an act, turning point)

You are NOT looking for:
- Scene breaks within a chapter
- Minor time transitions ("the next morning")
- Brief setting changes that are part of continuous action
- Paragraph transitions

Only identify breaks that would make sense as chapter divisions in a well-structured novel."""

NARRATIVE_PROMPT_TEMPLATE = """Analyze this text for MAJOR narrative breaks that could serve as chapter boundaries.

TEXT:
{text}

For each potential chapter break:
1. Copy the EXACT sentence or phrase where the break occurs
2. Explain why this is a major structural break
3. Rate your confidence (0.0-1.0)

Return a JSON array:
```json
[
  {{
    "break_text": "The exact sentence where the break occurs (copy verbatim)",
    "transition_type": "time_jump|pov_change|setting_change|plot_division",
    "confidence": 0.7,
    "reasoning": "Why this is a major break"
  }}
]
```

If no major breaks are found, return: []

Respond with ONLY the JSON array."""


class LLMMarkerProposer(BaseProposer):
    """
    Proposes chapter boundaries using LLM to find explicit markers.

    This complements the regex proposer by handling:
    - Unusual formatting the regex misses
    - Context-dependent decisions (is "I" a chapter or a pronoun?)
    - Non-English markers
    """

    name = "llm_marker"

    def __init__(
        self,
        llm_client: LLMClient,
        chunk_size: int = 15000,
        chunk_overlap: int = 1000,
    ):
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def propose(
        self,
        text: str,
        profile: Optional[DocumentProfile] = None,
    ) -> list[ChapterProposal]:
        """Find chapter markers using LLM analysis."""
        proposals = []

        # Skip front matter
        start_pos = profile.front_matter_end if profile else 0
        working_text = text[start_pos:]

        # Process in chunks with overlap
        chunks = self._chunk_text(working_text)

        for chunk_start, chunk_text in chunks:
            # Actual position in original text
            actual_start = start_pos + chunk_start

            chunk_proposals = self._analyze_chunk(chunk_text, actual_start, text)
            proposals.extend(chunk_proposals)

        # Deduplicate proposals that might appear in overlapping chunks
        proposals = self._deduplicate(proposals)

        return sorted(proposals, key=lambda p: p.position)

    def _chunk_text(self, text: str) -> list[tuple[int, str]]:
        """Split text into overlapping chunks."""
        chunks = []
        pos = 0

        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))

            # Try to break at a paragraph boundary
            if end < len(text):
                para_break = text.rfind("\n\n", pos + self.chunk_size - 500, end)
                if para_break > pos:
                    end = para_break

            chunks.append((pos, text[pos:end]))
            pos = end - self.chunk_overlap if end < len(text) else end

        return chunks

    def _analyze_chunk(
        self,
        chunk: str,
        chunk_start: int,
        full_text: str,
    ) -> list[ChapterProposal]:
        """Analyze a chunk for chapter markers."""
        prompt = MARKER_PROMPT_TEMPLATE.format(text=chunk)

        result, response = self.llm.query_json(prompt, system=MARKER_SYSTEM_PROMPT)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM marker proposer failed: {response.error}")
            return []

        if result is None:
            # JSON parsing failure
            logger.warning(
                f"LLM marker proposer failed to parse response: {response.content[:200] if response.content else 'empty response'}"
            )
            return []

        # Unwrap dict responses. Different models return different shapes when
        # the prompt asks for a JSON array:
        #   - {"markers": [...]}                wrapper key (most common)
        #   - {"marker_text": ..., "title": ...}   single marker not in a list
        #   - {"error": "..."} / {"message": "..."}   explanation when none found
        #   - {"other_key": [...]}              wrapper with unexpected key name
        if isinstance(result, dict):
            if "markers" in result and isinstance(result["markers"], list):
                result = result["markers"]
            elif "marker_text" in result:
                # Single marker returned as a bare dict — wrap into a one-item list.
                result = [result]
            elif any(isinstance(v, list) for v in result.values()):
                # Wrapper dict with a differently named list field.
                result = next(v for v in result.values() if isinstance(v, list))
            else:
                # No list values anywhere — the model returned an explanation
                # ("error" / "message" / refusal). Treat as empty marker set so
                # the pipeline falls back cleanly to regex proposals.
                logger.debug(
                    f"LLM marker proposer: no markers found "
                    f"(keys={list(result.keys())[:5]})"
                )
                return []

        if not isinstance(result, list):
            logger.warning(f"LLM marker proposer returned non-list: {type(result)}")
            return []

        proposals = []
        for item in result:
            if not isinstance(item, dict):
                continue

            marker_text = item.get("marker_text", "")
            if not marker_text:
                continue

            # Find this marker in the chunk
            position = self._find_text_position(marker_text, chunk, chunk_start, full_text)

            if position is None:
                logger.debug(f"Could not find marker text: {marker_text[:50]}")
                continue

            # F14: Warn when LLM doesn't return confidence
            confidence_raw = item.get("confidence")
            if confidence_raw is None:
                logger.warning(
                    f"LLM chapter detection did not return confidence for marker at {position} - "
                    "using conservative default 0.5"
                )
                confidence = 0.5
            else:
                confidence = float(confidence_raw)

            proposals.append(
                ChapterProposal(
                    strategy=self.name,
                    position=position,
                    title=item.get("title"),
                    evidence=marker_text,
                    confidence=confidence,
                    reasoning=item.get("reasoning"),
                )
            )

        return proposals

    def _find_text_position(
        self,
        marker_text: str,
        chunk: str,
        chunk_start: int,
        full_text: str,
    ) -> Optional[int]:
        """Find the position of marker text, with fallbacks for slight variations.

        IMPORTANT: For short markers (roman numerals like I, V, X), we must ensure
        we match standalone occurrences, not characters embedded in words like "Ventura".
        """
        # For short markers (single roman numerals or "Chapter X" style), require standalone match
        # This prevents matching "V" in "Ventura" when looking for Chapter V
        is_short_marker = len(marker_text.strip()) <= 4 or re.match(
            r"^[IVXLC]+$", marker_text.strip()
        )

        if is_short_marker:
            # Require the marker to be standalone (surrounded by whitespace or line boundaries)
            # Pattern: start of line + optional whitespace + marker + optional whitespace + end of line
            # OR: surrounded by whitespace on both sides
            escaped = re.escape(marker_text.strip())
            # Match centered/standalone markers (common in classic lit)
            pattern = rf"^\s*{escaped}\s*$"
            match = re.search(pattern, chunk, re.MULTILINE)
            if match:
                return chunk_start + match.start()

            # Also try with surrounding whitespace (not at line boundary)
            pattern = rf"(?<=\s){escaped}(?=\s)"
            match = re.search(pattern, chunk)
            if match:
                return chunk_start + match.start()

            # For "Chapter N" format, be more flexible
            if marker_text.strip().lower().startswith("chapter"):
                pattern = re.escape(marker_text.strip())
                match = re.search(pattern, chunk, re.IGNORECASE)
                if match:
                    return chunk_start + match.start()

            # Short marker not found as standalone - don't return false matches
            logger.debug(f"Short marker '{marker_text}' not found as standalone in chunk")
            return None

        # For longer markers, exact match is fine
        pos = chunk.find(marker_text)
        if pos >= 0:
            return chunk_start + pos

        # Try normalized whitespace
        normalized_marker = " ".join(marker_text.split())
        normalized_chunk = " ".join(chunk.split())

        # This is approximate - find in normalized then search original
        if normalized_marker in normalized_chunk:
            # Search for a close match in original
            pattern = re.escape(normalized_marker).replace(r"\ ", r"\s+")
            match = re.search(pattern, chunk)
            if match:
                return chunk_start + match.start()

        # Try case-insensitive
        pos = chunk.lower().find(marker_text.lower())
        if pos >= 0:
            return chunk_start + pos

        return None

    def _deduplicate(self, proposals: list[ChapterProposal]) -> list[ChapterProposal]:
        """Remove duplicate proposals from overlapping chunks."""
        if not proposals:
            return []

        # Sort by position
        sorted_props = sorted(proposals, key=lambda p: p.position)

        deduped = [sorted_props[0]]
        for prop in sorted_props[1:]:
            # If within 100 chars of last proposal, keep higher confidence
            if prop.position - deduped[-1].position < 100:
                if prop.confidence > deduped[-1].confidence:
                    deduped[-1] = prop
            else:
                deduped.append(prop)

        return deduped


class LLMNarrativeProposer(BaseProposer):
    """
    Proposes chapter boundaries based on narrative structure.

    This is for books without explicit markers - finds natural chapter breaks.
    """

    name = "llm_narrative"

    def __init__(
        self,
        llm_client: LLMClient,
        chunk_size: int = 20000,
        chunk_overlap: int = 2000,
    ):
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def propose(
        self,
        text: str,
        profile: Optional[DocumentProfile] = None,
    ) -> list[ChapterProposal]:
        """Find narrative breaks that could serve as chapter boundaries."""
        # Only use this proposer if document lacks explicit markers
        if profile and profile.has_explicit_markers:
            logger.info("Document has explicit markers, skipping narrative proposer")
            return []

        proposals = []

        # Skip front matter
        start_pos = profile.front_matter_end if profile else 0
        working_text = text[start_pos:]

        # Process in chunks
        chunks = self._chunk_text(working_text)

        for chunk_start, chunk_text in chunks:
            actual_start = start_pos + chunk_start
            chunk_proposals = self._analyze_chunk(chunk_text, actual_start, text)
            proposals.extend(chunk_proposals)

        # Deduplicate and filter
        proposals = self._deduplicate(proposals)

        return sorted(proposals, key=lambda p: p.position)

    def _chunk_text(self, text: str) -> list[tuple[int, str]]:
        """Split text into overlapping chunks."""
        chunks = []
        pos = 0

        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))

            if end < len(text):
                para_break = text.rfind("\n\n", pos + self.chunk_size - 1000, end)
                if para_break > pos:
                    end = para_break

            chunks.append((pos, text[pos:end]))
            pos = end - self.chunk_overlap if end < len(text) else end

        return chunks

    def _analyze_chunk(
        self,
        chunk: str,
        chunk_start: int,
        full_text: str,
    ) -> list[ChapterProposal]:
        """Analyze a chunk for narrative breaks."""
        prompt = NARRATIVE_PROMPT_TEMPLATE.format(text=chunk)

        result, response = self.llm.query_json(prompt, system=NARRATIVE_SYSTEM_PROMPT)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM narrative proposer failed: {response.error}")
            return []

        if result is None:
            # JSON parsing failure
            logger.warning(
                f"LLM narrative proposer failed to parse response: {response.content[:200] if response.content else 'empty response'}"
            )
            return []

        # Unwrap dict responses: some models return {"breaks": [...]} instead of bare [...]
        if isinstance(result, dict):
            if "breaks" in result and isinstance(result["breaks"], list):
                result = result["breaks"]
            else:
                # Fall back to first list-valued key
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break

        if not isinstance(result, list):
            return []

        proposals = []
        for item in result:
            if not isinstance(item, dict):
                continue

            break_text = item.get("break_text", "")
            if not break_text:
                continue

            position = self._find_text_position(break_text, chunk, chunk_start)

            if position is None:
                continue

            # Narrative breaks have lower base confidence than explicit markers
            # Reduced from 0.8 to 0.7 to be more conservative and avoid false positives
            # F14: Warn when LLM doesn't return confidence
            confidence_raw = item.get("confidence")
            if confidence_raw is None:
                logger.warning(
                    "LLM narrative break detection did not return confidence - "
                    "using conservative default 0.3"
                )
                base_confidence = 0.3
            else:
                base_confidence = float(confidence_raw) * 0.7
            confidence = base_confidence

            proposals.append(
                ChapterProposal(
                    strategy=self.name,
                    position=position,
                    title=None,  # Narrative breaks don't have titles
                    evidence=break_text,
                    confidence=confidence,
                    reasoning=f"{item.get('transition_type', 'break')}: {item.get('reasoning', '')}",
                )
            )

        return proposals

    def _find_text_position(
        self,
        break_text: str,
        chunk: str,
        chunk_start: int,
    ) -> Optional[int]:
        """Find position of break text in chunk."""
        pos = chunk.find(break_text)
        if pos >= 0:
            return chunk_start + pos

        # Normalized search
        pattern = re.escape(" ".join(break_text.split())).replace(r"\ ", r"\s+")
        match = re.search(pattern, chunk)
        if match:
            return chunk_start + match.start()

        return None

    def _deduplicate(self, proposals: list[ChapterProposal]) -> list[ChapterProposal]:
        """Remove duplicate proposals."""
        if not proposals:
            return []

        sorted_props = sorted(proposals, key=lambda p: p.position)

        deduped = [sorted_props[0]]
        for prop in sorted_props[1:]:
            if prop.position - deduped[-1].position < 500:
                if prop.confidence > deduped[-1].confidence:
                    deduped[-1] = prop
            else:
                deduped.append(prop)

        return deduped
