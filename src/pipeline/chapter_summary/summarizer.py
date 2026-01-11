"""
Chapter summarizer with chunking support for long chapters.

Handles breaking long chapters into manageable chunks for LLM processing,
then consolidating chunk summaries into cohesive chapter summaries.
"""

import re
from typing import Optional
import logging

from .models import ChapterSummary, ChunkSummary, ToneType, DialogueDensity
from ..llm import LLMClient

logger = logging.getLogger(__name__)

# Target chunk size in words (most LLMs handle ~4000 tokens well)
DEFAULT_CHUNK_SIZE = 2500
CHUNK_OVERLAP = 200  # Words of overlap between chunks for context continuity


CHUNK_SUMMARY_SYSTEM = """You are a literary analyst creating summaries for audiobook narration preparation.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or characters.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

Your summaries should help a narrator understand:
- What happens in this section
- The emotional tone and pacing
- Which characters appear and speak
- Key moments that require vocal emphasis or character voices

Always respond with valid JSON. No other text."""


CHUNK_SUMMARY_PROMPT = """Summarize this section of a chapter for audiobook narration preparation.

CHAPTER: {chapter_title}
SECTION: {chunk_num} of {total_chunks}

TEXT:
{text}

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The protagonist arrives at an unfamiliar location and encounters a mysterious stranger. They engage in tense conversation that reveals hidden motivations. The section ends with an unexpected revelation.",
  "key_events": [
    "Protagonist enters the building",
    "Confrontation with the stranger",
    "Discovery of a hidden letter",
    "Decision to investigate further"
  ],
  "characters_mentioned": ["Michael", "Sarah", "Dr. Patterson"],
  "tone": "suspenseful"
}}
```

Valid tone values: tense, suspenseful, action, romantic, comedic, somber, reflective, dramatic, peaceful, mysterious, hopeful, dark

Return ONLY valid JSON matching the above structure. No other text."""


CONSOLIDATE_SYSTEM = """You are a literary analyst creating chapter summaries for audiobook narration.

CRITICAL: Base your analysis ONLY on the section summaries provided below.
Do NOT use any prior knowledge about this book, author, or characters.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided summaries.

Combine section summaries into a cohesive chapter summary that captures the full arc.

Always respond with valid JSON. No other text."""


CONSOLIDATE_PROMPT = """Combine these section summaries into a single chapter summary.

CHAPTER: {chapter_title}
WORD COUNT: {word_count}

SECTION SUMMARIES:
{chunk_summaries}

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The chapter begins with a quiet morning that quickly escalates into conflict. Characters confront long-buried tensions as past events resurface. A series of revelations shifts relationships and alliances. The chapter concludes with an uncertain truce that sets up future complications.",
  "key_events": [
    "Morning conversation reveals underlying tension",
    "Discovery of the missing item",
    "Heated argument between main characters",
    "Unexpected ally provides crucial information",
    "Temporary resolution with conditions",
    "Hint at future complications"
  ],
  "characters_present": ["Michael", "Sarah", "Dr. Patterson", "James", "Elizabeth"],
  "primary_tone": "tense",
  "secondary_tones": ["hopeful", "mysterious"],
  "dialogue_density": "high",
  "pov_character": "Michael"
}}
```

Valid tone values: tense, suspenseful, action, romantic, comedic, somber, reflective, dramatic, peaceful, mysterious, hopeful, dark
Valid dialogue_density values: "high", "medium", "low"
Set pov_character to null if not identifiable from the summaries

Return ONLY valid JSON matching the above structure. No other text."""


SINGLE_CHAPTER_SYSTEM = """You are a literary analyst creating chapter summaries for audiobook narration.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or characters.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

Your summaries help narrators understand plot, tone, and character presence before recording.

Always respond with valid JSON. No other text."""


SINGLE_CHAPTER_PROMPT = """Summarize this chapter for audiobook narration preparation.

CHAPTER: {chapter_title}
WORD COUNT: {word_count}

TEXT:
{text}

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The chapter begins with a quiet morning that quickly escalates into conflict. Characters confront long-buried tensions as past events resurface. A series of revelations shifts relationships and alliances. The chapter concludes with an uncertain truce that sets up future complications.",
  "key_events": [
    "Morning conversation reveals underlying tension",
    "Discovery of the missing item",
    "Heated argument between main characters",
    "Unexpected ally provides crucial information",
    "Temporary resolution with conditions",
    "Hint at future complications"
  ],
  "characters_present": ["Michael", "Sarah", "Dr. Patterson", "James", "Elizabeth"],
  "primary_tone": "tense",
  "secondary_tones": ["hopeful", "mysterious"],
  "dialogue_density": "high",
  "pov_character": "Michael"
}}
```

Valid tone values: tense, suspenseful, action, romantic, comedic, somber, reflective, dramatic, peaceful, mysterious, hopeful, dark
Valid dialogue_density values: "high", "medium", "low"
Set pov_character to null if not identifiable from the text

Return ONLY valid JSON matching the above structure. No other text."""


class ChapterSummarizer:
    """
    Summarizes chapters using LLM with chunking for long chapters.

    For chapters under the chunk threshold, generates summary directly.
    For longer chapters, breaks into chunks, summarizes each, then consolidates.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        known_characters: Optional[list[str]] = None,
    ):
        """
        Args:
            llm_client: LLM client for summarization
            chunk_size: Target words per chunk
            chunk_overlap: Words of overlap between chunks
            known_characters: List of known character names for reference
        """
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.known_characters = known_characters or []

    def summarize_chapter(
        self,
        chapter_text: str,
        chapter_index: int,
        chapter_title: Optional[str] = None,
    ) -> ChapterSummary:
        """
        Summarize a single chapter.

        Args:
            chapter_text: Full text of the chapter
            chapter_index: Chapter number
            chapter_title: Optional chapter title

        Returns:
            ChapterSummary with summary and metadata
        """
        word_count = len(chapter_text.split())
        title = chapter_title or f"Chapter {chapter_index}"

        logger.info(f"Summarizing chapter {chapter_index}: {word_count} words")

        # Short chapter: summarize directly
        if word_count <= self.chunk_size * 1.2:  # Allow 20% buffer before chunking
            return self._summarize_short_chapter(
                chapter_text, chapter_index, title, word_count
            )

        # Long chapter: chunk and consolidate
        return self._summarize_long_chapter(
            chapter_text, chapter_index, title, word_count
        )

    def _summarize_short_chapter(
        self,
        text: str,
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Summarize a chapter that fits in one LLM call."""
        prompt = SINGLE_CHAPTER_PROMPT.format(
            chapter_title=title,
            word_count=word_count,
            text=text,
        )

        result, _ = self.llm.query_json(prompt, system=SINGLE_CHAPTER_SYSTEM)

        if result is None:
            logger.warning(f"LLM summarization failed for chapter {chapter_index}")
            return self._create_fallback_summary(chapter_index, title, word_count)

        return self._parse_chapter_result(result, chapter_index, title, word_count)

    def _summarize_long_chapter(
        self,
        text: str,
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Summarize a long chapter using chunking."""
        # Split into chunks
        chunks = self._split_into_chunks(text)
        logger.info(f"Chapter {chapter_index} split into {len(chunks)} chunks")

        # Summarize each chunk
        chunk_summaries = []
        for i, chunk_text in enumerate(chunks):
            chunk_summary = self._summarize_chunk(
                chunk_text, i, len(chunks), title
            )
            chunk_summaries.append(chunk_summary)

        # Consolidate chunk summaries
        return self._consolidate_chunks(
            chunk_summaries, chapter_index, title, word_count
        )

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split text into overlapping chunks at sentence boundaries."""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))

                # Start new chunk with overlap
                overlap_words = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    overlap_words += len(s.split())
                    overlap_sentences.insert(0, s)
                    if overlap_words >= self.chunk_overlap:
                        break

                current_chunk = overlap_sentences
                current_word_count = overlap_words

            current_chunk.append(sentence)
            current_word_count += sentence_words

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _summarize_chunk(
        self,
        text: str,
        chunk_index: int,
        total_chunks: int,
        chapter_title: str,
    ) -> ChunkSummary:
        """Summarize a single chunk."""
        prompt = CHUNK_SUMMARY_PROMPT.format(
            chapter_title=chapter_title,
            chunk_num=chunk_index + 1,
            total_chunks=total_chunks,
            text=text,
        )

        result, _ = self.llm.query_json(prompt, system=CHUNK_SUMMARY_SYSTEM)

        word_count = len(text.split())

        if result is None:
            logger.warning(f"LLM failed for chunk {chunk_index}")
            return ChunkSummary(
                chunk_index=chunk_index,
                summary="[Summary generation failed]",
                key_events=[],
                characters_mentioned=[],
                tone="reflective",
                word_count=word_count,
            )

        tone = result.get("tone", "reflective")
        if tone not in self._valid_tones():
            tone = "reflective"

        return ChunkSummary(
            chunk_index=chunk_index,
            summary=result.get("summary", ""),
            key_events=result.get("key_events", []),
            characters_mentioned=result.get("characters_mentioned", []),
            tone=tone,
            word_count=word_count,
        )

    def _consolidate_chunks(
        self,
        chunk_summaries: list[ChunkSummary],
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Consolidate chunk summaries into a chapter summary."""
        # Format chunk summaries for prompt
        chunks_text = []
        for cs in chunk_summaries:
            events_str = "; ".join(cs.key_events) if cs.key_events else "N/A"
            chunks_text.append(
                f"Section {cs.chunk_index + 1}: {cs.summary}\n"
                f"  Events: {events_str}\n"
                f"  Characters: {', '.join(cs.characters_mentioned)}\n"
                f"  Tone: {cs.tone}"
            )

        prompt = CONSOLIDATE_PROMPT.format(
            chapter_title=title,
            word_count=word_count,
            chunk_summaries="\n\n".join(chunks_text),
        )

        result, response = self.llm.query_json(prompt, system=CONSOLIDATE_SYSTEM)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"Consolidation failed for chapter {chapter_index}: {response.error}")
            return self._merge_chunk_summaries(chunk_summaries, chapter_index, title, word_count)

        if result is None or not isinstance(result, dict):
            # JSON parsing failure or wrong type
            error_detail = f"got {type(result).__name__}" if result is not None else "failed to parse JSON"
            logger.warning(f"Consolidation failed for chapter {chapter_index} ({error_detail})")
            # Fallback: merge chunk summaries manually
            return self._merge_chunk_summaries(chunk_summaries, chapter_index, title, word_count)

        return self._parse_chapter_result(result, chapter_index, title, word_count)

    def _merge_chunk_summaries(
        self,
        chunks: list[ChunkSummary],
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Fallback: manually merge chunk summaries."""
        # Combine summaries
        summaries = [c.summary for c in chunks if c.summary]
        combined_summary = " ".join(summaries)

        # Collect all events
        all_events = []
        for c in chunks:
            all_events.extend(c.key_events)

        # Deduplicate characters
        all_chars = set()
        for c in chunks:
            all_chars.update(c.characters_mentioned)

        # Count tones
        tone_counts: dict[str, int] = {}
        for c in chunks:
            tone_counts[c.tone] = tone_counts.get(c.tone, 0) + 1
        primary_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "reflective"

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=combined_summary[:500],  # Truncate if too long
            key_events=all_events[:6],
            primary_tone=primary_tone,
            secondary_tones=[],
            dialogue_density="medium",
            characters_present=list(all_chars),
            pov_character=None,
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,
            confidence=0.5,
        )

    def _parse_chapter_result(
        self,
        result: dict,
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Parse LLM result into ChapterSummary."""
        primary_tone = result.get("primary_tone", "reflective")
        if primary_tone not in self._valid_tones():
            primary_tone = "reflective"

        secondary_tones = []
        for t in result.get("secondary_tones", []):
            if t in self._valid_tones() and t != primary_tone:
                secondary_tones.append(t)

        dialogue = result.get("dialogue_density", "medium")
        if dialogue not in ["high", "medium", "low"]:
            dialogue = "medium"

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=result.get("summary", ""),
            key_events=result.get("key_events", []),
            primary_tone=primary_tone,
            secondary_tones=secondary_tones,
            dialogue_density=dialogue,
            characters_present=result.get("characters_present", []),
            pov_character=result.get("pov_character"),
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,  # ~150 wpm narration
            confidence=0.85,
        )

    def _create_fallback_summary(
        self,
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Create a fallback summary when LLM fails."""
        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary="[Summary generation failed - manual review needed]",
            key_events=[],
            primary_tone="reflective",
            secondary_tones=[],
            dialogue_density="medium",
            characters_present=[],
            pov_character=None,
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,
            confidence=0.0,
        )

    @staticmethod
    def _valid_tones() -> set[str]:
        """Return set of valid tone values."""
        return {
            "tense", "suspenseful", "action", "romantic", "comedic", "somber",
            "reflective", "dramatic", "peaceful", "mysterious", "hopeful", "dark"
        }
