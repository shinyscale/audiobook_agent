"""
Chapter summarizer with chunking support for long chapters.

Handles breaking long chapters into manageable chunks for LLM processing,
then consolidating chunk summaries into cohesive chapter summaries.
"""

import logging
import re
from typing import Optional

from ..chapter_detection.scene_breaks import find_scene_breaks
from ..llm import LLMClient
from .models import ChapterSummary, ChunkSummary

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

IMPORTANT GUIDELINES (F12: Prioritize accuracy):
- FACTUAL ACCURACY is more important than brevity - include all significant events
- Include specific setting details (location, transportation method, time of day)
- When referencing events/objects, ALWAYS provide context (e.g., "the inheritance from his uncle" not just "the money")
- Be precise about HOW characters travel (by car, on foot, by train) not just WHERE
- Include character emotions and reactions when they impact the narrative
- If something is vague or unclear in the text, say so rather than guessing
{length_guidance}

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The protagonist arrives by car at an unfamiliar mansion on the outskirts of West Egg and encounters a mysterious stranger smoking on the front steps. They engage in a tense conversation that reveals the stranger knows about the protagonist's past investigation into the Meyer Wolfsheim connection. The stranger mentions a hidden letter from Gatsby but refuses to explain its significance or whereabouts. The section ends with an unexpected revelation: the mansion's previous owner was murdered, not died naturally as claimed.",
  "key_events": [
    "Protagonist drives to the mansion",
    "Meeting with the stranger on the steps",
    "Confrontation about the investigation",
    "Mention of a hidden letter (contents unknown)",
    "Revelation about previous owner"
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

IMPORTANT GUIDELINES (F12: Prioritize accuracy):
- FACTUAL ACCURACY is more important than brevity - preserve ALL significant details from sections
- Include setting details (location, transportation method, time) when mentioned
- When events/objects are referenced, ALWAYS include context from the sections
- Be precise about HOW characters travel and WHERE specific events occur
- If something is vague in the section summaries, preserve that vagueness rather than inventing details
{length_guidance}

CRITICAL CHARACTER DISTINCTION:
- "active_characters": People who APPEAR "on stage" in this chapter - they speak, act, make decisions,
  interact with others, or participate in events. Include the narrator if they participate.
- "mentioned_characters": People who are REFERENCED but don't appear - historical figures, people being
  discussed, names in guest lists, people from the past. These characters are talked ABOUT but not present.

Example: If a chapter has a party where 50 guests are listed by name but only 3 guests actually speak
or do anything significant, those 3 go in active_characters and the other 47 in mentioned_characters.

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The chapter begins with a quiet morning at the West Egg estate that quickly escalates into conflict when Tom's old friend Chester arrives unexpectedly by automobile from Chicago. Characters confront long-buried tensions as past events from their Yale days resurface during a heated conversation in the oak-paneled library. A series of revelations about a hidden letter from Gatsby shifts the relationship between Nick and Daisy. The chapter concludes with an uncertain truce reached in the rose garden as dusk falls, but Tom's final glare at Chester suggests future complications.",
  "key_events": [
    "Morning conversation reveals underlying tension",
    "Unexpected visitor arrives by car",
    "Discovery of the missing letter in the library",
    "Heated argument between main characters",
    "Unexpected ally provides crucial information",
    "Temporary resolution in the garden",
    "Hint at future complications"
  ],
  "active_characters": ["Michael", "Sarah", "Dr. Patterson"],
  "mentioned_characters": ["James", "Elizabeth", "the late Mr. Harrison"],
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

IMPORTANT GUIDELINES (F12: Prioritize accuracy):
- FACTUAL ACCURACY is more important than brevity - include all significant events
- Include specific setting details (location, transportation method, time of day)
- When referencing events/objects, ALWAYS provide context (e.g., "the inheritance from his uncle" not just "the money")
- Be precise about HOW characters travel (by car, on foot, by train) not just WHERE
- Include character emotions and reactions when they impact the narrative
- If something is vague or unclear in the text, say so rather than guessing
{length_guidance}

CRITICAL CHARACTER DISTINCTION:
- "active_characters": People who APPEAR "on stage" in this chapter - they speak, act, make decisions,
  interact with others, or participate in events. Include the narrator if they participate.
- "mentioned_characters": People who are REFERENCED but don't appear - historical figures, people being
  discussed, names in guest lists, people from the past. These characters are talked ABOUT but not present.

Example: If a chapter has a party where 50 guests are listed by name but only 3 guests actually speak
or do anything significant, those 3 go in active_characters and the other 47 in mentioned_characters.

Return a JSON response matching this example format exactly:

```json
{{
  "summary": "The chapter begins with a quiet morning at the West Egg estate that quickly escalates into conflict when Tom's old friend Chester arrives unexpectedly by automobile from Chicago. Characters confront long-buried tensions as past events from their Yale days resurface during a heated conversation in the oak-paneled library. A series of revelations about a hidden letter from Gatsby shifts the relationship between Nick and Daisy. The chapter concludes with an uncertain truce reached in the rose garden as dusk falls, but Tom's final glare at Chester suggests future complications.",
  "key_events": [
    "Morning conversation reveals underlying tension",
    "Unexpected visitor arrives by car",
    "Discovery of the missing letter in the library",
    "Heated argument between main characters",
    "Unexpected ally provides crucial information",
    "Temporary resolution in the garden",
    "Hint at future complications"
  ],
  "active_characters": ["Michael", "Sarah", "Dr. Patterson"],
  "mentioned_characters": ["James", "Elizabeth", "the late Mr. Harrison"],
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
        summary_length: str = "standard",
    ):
        """
        Args:
            llm_client: LLM client for summarization
            chunk_size: Target words per chunk
            chunk_overlap: Words of overlap between chunks
            known_characters: List of known character names for reference
            summary_length: Length preference - "brief" (2-3 sentences), "standard" (4-6 sentences), "detailed" (6-8 sentences)
        """
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.known_characters = known_characters or []
        self.summary_length = summary_length

    def _get_length_guidance(self) -> str:
        """Get length guidance text based on summary_length setting.

        F12: Increased default summary length to 3-5 sentences for better accuracy.
        """
        if self.summary_length == "brief":
            return "- Aim for 2-3 concise sentences in your summary"
        elif self.summary_length == "detailed":
            return "- Aim for 6-8 detailed sentences in your summary, preserving ALL significant events"
        else:  # standard (F12: increased from 4-6 to 3-5 with accuracy emphasis)
            return (
                "- Aim for 3-5 DETAILED sentences in your summary\n"
                "- NEVER sacrifice accuracy for brevity - include all significant events\n"
                "- When referencing events or objects, provide context (e.g., 'the pearl necklace her mother gave her' not just 'pearls')\n"
                "- Include HOW characters travel (by car, on foot, by train) not just WHERE"
            )

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
            return self._summarize_short_chapter(chapter_text, chapter_index, title, word_count)

        # Long chapter: chunk and consolidate
        return self._summarize_long_chapter(chapter_text, chapter_index, title, word_count)

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
            length_guidance=self._get_length_guidance(),
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
            chunk_summary = self._summarize_chunk(chunk_text, i, len(chunks), title)
            chunk_summaries.append(chunk_summary)

        # Consolidate chunk summaries
        return self._consolidate_chunks(chunk_summaries, chapter_index, title, word_count)

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split text into chunks, respecting scene breaks as natural boundaries."""
        scene_breaks = find_scene_breaks(text)

        if scene_breaks:
            return self._split_by_scene_breaks(text, scene_breaks)
        else:
            return self._split_by_word_count(text)

    def _split_by_scene_breaks(self, text: str, scene_breaks: list[tuple[int, int]]) -> list[str]:
        """Split text at scene breaks, then chunk large sections if needed.

        Scene breaks provide natural narrative boundaries that result in
        better-structured summaries with paragraph breaks at scene transitions.
        """
        sections = []
        prev_end = 0

        for start, end in scene_breaks:
            section = text[prev_end:start].strip()
            if section:
                sections.append(section)
            prev_end = end

        # Don't forget the last section
        final = text[prev_end:].strip()
        if final:
            sections.append(final)

        # Chunk any sections that are too long
        chunks = []
        for section in sections:
            word_count = len(section.split())
            if word_count > self.chunk_size * 1.2:  # Allow 20% buffer
                # Large section - further chunk by word count
                chunks.extend(self._split_by_word_count(section))
            else:
                chunks.append(section)

        logger.debug(
            f"Split by scene breaks: {len(scene_breaks)} breaks -> {len(sections)} sections -> {len(chunks)} chunks"
        )
        return chunks

    def _split_by_word_count(self, text: str) -> list[str]:
        """Original chunking logic: split by word count at sentence boundaries."""
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))

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
            chunks.append(" ".join(current_chunk))

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
            length_guidance=self._get_length_guidance(),
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
            length_guidance=self._get_length_guidance(),
        )

        result, response = self.llm.query_json(prompt, system=CONSOLIDATE_SYSTEM)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"Consolidation failed for chapter {chapter_index}: {response.error}")
            return self._merge_chunk_summaries(chunk_summaries, chapter_index, title, word_count)

        if result is None or not isinstance(result, dict):
            # JSON parsing failure or wrong type
            error_detail = (
                f"got {type(result).__name__}" if result is not None else "failed to parse JSON"
            )
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

        # Deduplicate characters (fallback treats all as active since we don't have the distinction)
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
            active_characters=list(all_chars),  # Fallback: treat all as active
            mentioned_characters=[],
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

        # Handle new active/mentioned character format with backward compatibility
        if "active_characters" in result:
            active_characters = result.get("active_characters", [])
            mentioned_characters = result.get("mentioned_characters", [])
        else:
            # Old format: all characters_present treated as active
            active_characters = result.get("characters_present", [])
            mentioned_characters = []

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=result.get("summary", ""),
            key_events=result.get("key_events", []),
            primary_tone=primary_tone,
            secondary_tones=secondary_tones,
            dialogue_density=dialogue,
            active_characters=active_characters,
            mentioned_characters=mentioned_characters,
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
            active_characters=[],
            mentioned_characters=[],
            pov_character=None,
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,
            confidence=0.0,
        )

    @staticmethod
    def _valid_tones() -> set[str]:
        """Return set of valid tone values."""
        return {
            "tense",
            "suspenseful",
            "action",
            "romantic",
            "comedic",
            "somber",
            "reflective",
            "dramatic",
            "peaceful",
            "mysterious",
            "hopeful",
            "dark",
        }
