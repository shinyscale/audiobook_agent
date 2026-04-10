"""
Chapter summarizer with chunking support for long chapters.

Handles breaking long chapters into manageable chunks for LLM processing,
then consolidating chunk summaries into cohesive chapter summaries.

Supports competitive multi-model consensus for summary generation when enabled.
"""

import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Optional

from ..chapter_detection.scene_breaks import find_scene_breaks
from ..llm import LLMClient, LLMConfig
from ..scalpels import ScalpelLoader, scalpel_available
from ..dialogue_attribution import crf_available, CRFDialogueAttributor
from .models import ChapterSummary, ChunkSummary

if TYPE_CHECKING:
    from ...agents.config import CompetitiveConfig

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
- **FIRST-PERSON NARRATORS**: If the text is told in first person ("I", "we") and the narrator's name is revealed in the text (e.g., another character addresses them by name, or they introduce themselves), USE THAT NAME in your summary instead of "the narrator". Only use "the narrator" if their name is not revealed in this section.
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
- **FIRST-PERSON NARRATORS**: If the section summaries reveal the narrator's name, use that name consistently in the consolidated summary instead of "the narrator". Only use "the narrator" if their name is not revealed in any section.
{length_guidance}

CRITICAL CHARACTER DISTINCTION:
- "active_characters": Entities who APPEAR "on stage" with agency - they speak, act, make decisions,
  interact with others, or participate in events. Include people, AI, monsters, supernatural forces,
  or symbolic objects that drive the plot. Include the narrator if they participate.
- "mentioned_characters": Entities who are REFERENCED but don't appear - historical figures, people being
  discussed, names in guest lists, entities from the past. These are talked ABOUT but not present.

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
  "active_characters": ["Michael", "Sarah", "HAL", "the Monster"],
  "mentioned_characters": ["James", "Elizabeth", "the late Mr. Harrison"],
  "primary_tone": "tense",
  "secondary_tones": ["hopeful", "mysterious"],
  "dialogue_density": "high",
  "pov_character": "Michael"
}}
```

Note: Include non-human entities with names (AI systems, creatures, supernatural beings) in active_characters if they act with agency in the chapter.

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
- "active_characters": Entities who APPEAR "on stage" with agency - they speak, act, make decisions,
  interact with others, or participate in events. Include people, AI, monsters, supernatural forces,
  or symbolic objects that drive the plot. Include the narrator if they participate.
- "mentioned_characters": Entities who are REFERENCED but don't appear - historical figures, people being
  discussed, names in guest lists, entities from the past. These are talked ABOUT but not present.

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
  "active_characters": ["Michael", "Sarah", "HAL", "the Monster"],
  "mentioned_characters": ["James", "Elizabeth", "the late Mr. Harrison"],
  "primary_tone": "tense",
  "secondary_tones": ["hopeful", "mysterious"],
  "dialogue_density": "high",
  "pov_character": "Michael"
}}
```

Note: Include non-human entities with names (AI systems, creatures, supernatural beings) in active_characters if they act with agency in the chapter.

Valid tone values: tense, suspenseful, action, romantic, comedic, somber, reflective, dramatic, peaceful, mysterious, hopeful, dark
Valid dialogue_density values: "high", "medium", "low"
Set pov_character to null if not identifiable from the text

Return ONLY valid JSON matching the above structure. No other text."""


class ChapterSummarizer:
    """
    Summarizes chapters using LLM with chunking for long chapters.

    For chapters under the chunk threshold, generates summary directly.
    For longer chapters, breaks into chunks, summarizes each, then consolidates.

    Supports competitive multi-model consensus for summary generation when enabled.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        known_characters: Optional[list[str]] = None,
        summary_length: str = "standard",
        competitive_config: Optional["CompetitiveConfig"] = None,
        json_llm: Optional[LLMClient] = None,
    ):
        """
        Args:
            llm_client: LLM client for summarization
            chunk_size: Target words per chunk
            chunk_overlap: Words of overlap between chunks
            known_characters: List of known character names for reference
            summary_length: Length preference - "brief" (2-3 sentences), "standard" (4-6 sentences), "detailed" (6-8 sentences)
            competitive_config: Optional config for multi-model consensus
            json_llm: Optional JSON-capable LLM client for fallback when primary fails JSON parsing
        """
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.known_characters = known_characters or []
        self.summary_length = summary_length
        self.competitive_config = competitive_config
        # JSON-capable LLM client for fallback when primary model fails JSON parsing
        self.json_llm = json_llm

        # Collect vote records for consensus logging
        self.vote_records: list[dict] = []

        # Initialize competitor clients if competitive summaries is enabled
        self._competitor_clients: list[LLMClient] = []
        self._models_warmed: bool = False
        if self._use_competitive_summaries():
            self._init_competitor_clients()

    def _use_competitive_summaries(self) -> bool:
        """Check if competitive summary generation should be used."""
        return (
            self.competitive_config is not None
            and self.competitive_config.enabled
            and self.competitive_config.competitive_summaries
            and self.llm is not None
        )

    def _init_competitor_clients(self) -> None:
        """Initialize LLM clients for competitive summary generation."""
        if not self.llm or not self.competitive_config:
            return

        base_config = self.llm.config

        # Get competitor configurations
        competitor_configs = self.competitive_config.get_competitor_configs(
            base_model=base_config.model,
            base_provider=base_config.provider,
            base_url=base_config.base_url,
            base_api_key=base_config.api_key,
        )

        logger.info(
            f"ChapterSummarizer: Initializing competitive summaries with {len(competitor_configs)} competitors"
        )

        for comp_config in competitor_configs:
            logger.info(f"  Competitor: {comp_config.model} @ {comp_config.temperature}")

            new_config = LLMConfig(
                provider=comp_config.provider,
                model=comp_config.model,
                base_url=comp_config.base_url or base_config.base_url,
                api_key=comp_config.get_api_key() or base_config.api_key,
                temperature=comp_config.temperature,
                max_tokens=base_config.max_tokens,
                context_length=base_config.context_length,
            )
            client = LLMClient(new_config)
            self._competitor_clients.append(client)

    def _warm_competitor_models(self) -> None:
        """Pre-load all competitor models into Ollama memory for true parallel execution.

        When running multiple LLM models in parallel, Ollama may need to load/unload
        models between requests if they aren't already in memory. This method sends
        a minimal prompt to each competitor model to force Ollama to load them all
        into memory before the actual analysis begins.

        Configure Ollama with:
        - OLLAMA_MAX_LOADED_MODELS=3 (or higher based on available memory)
        - OLLAMA_KEEP_ALIVE=30m (keep models loaded longer)
        """
        if not self._competitor_clients or self._models_warmed:
            return

        # Check if we have multiple different models (multi-model setup)
        unique_models = {client.config.model for client in self._competitor_clients}

        if len(unique_models) <= 1:
            # Single model with different temperatures - no pre-warming needed
            logger.debug("Single model competitive setup - skipping pre-warm")
            return

        logger.info(
            f"Pre-warming {len(unique_models)} competitor models for parallel execution: "
            f"{sorted(unique_models)}"
        )

        def warm_model(client: LLMClient) -> tuple[str, bool]:
            """Send minimal prompt to force model load."""
            model_name = client.config.model
            try:
                # Minimal prompt to force model load without heavy computation
                client.query("Hello", system="Respond with 'OK'")
                logger.info(f"  Warmed: {model_name}")
                return (model_name, True)
            except Exception as e:
                logger.warning(f"  Failed to warm {model_name}: {e}")
                return (model_name, False)

        # Warm all models in parallel
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            results = list(executor.map(warm_model, self._competitor_clients))

        # Log summary
        successful = sum(1 for _, success in results if success)
        logger.info(f"Model pre-warming complete: {successful}/{len(results)} models loaded")
        self._models_warmed = True

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

        # Use competitive mode if enabled and we have competitor clients
        if self._use_competitive_summaries() and self._competitor_clients:
            return self._competitive_summarize_chapter(
                chapter_text, chapter_index, title, word_count
            )

        # Short chapter: summarize directly
        if word_count <= self.chunk_size * 1.2:  # Allow 20% buffer before chunking
            return self._summarize_short_chapter(chapter_text, chapter_index, title, word_count)

        # Long chapter: chunk and consolidate
        return self._summarize_long_chapter(chapter_text, chapter_index, title, word_count)

    def _competitive_summarize_chapter(
        self,
        chapter_text: str,
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """
        Summarize using multiple models and merge results.

        Strategy:
        - key_events: Union with voting (keep events with 2+ votes)
        - active_characters: Intersection (2/3 must agree)
        - mentioned_characters: Intersection (2/3 must agree)
        - summary: Select best summary based on consensus-event overlap
        """
        # Pre-warm competitor models for true parallel execution (only once)
        self._warm_competitor_models()

        logger.info(f"Running competitive summary for chapter {chapter_index}")

        # Prepare prompt based on chapter length
        if word_count <= self.chunk_size * 1.2:
            prompt = SINGLE_CHAPTER_PROMPT.format(
                chapter_title=title,
                word_count=word_count,
                text=chapter_text,
                length_guidance=self._get_length_guidance(),
            )
            system = SINGLE_CHAPTER_SYSTEM
        else:
            # For long chapters, use chunk-consolidate approach for each model
            # but that's expensive; instead, just use single prompt with truncated text
            # (models can handle longer context now)
            prompt = SINGLE_CHAPTER_PROMPT.format(
                chapter_title=title,
                word_count=word_count,
                text=chapter_text[:50000],  # Truncate for safety
                length_guidance=self._get_length_guidance(),
            )
            system = SINGLE_CHAPTER_SYSTEM

        def query_competitor(client: LLMClient) -> Optional[dict]:
            try:
                result, response = client.query_json(prompt, system=system)
                if response.success and result and isinstance(result, dict):
                    return result
                return None
            except Exception as e:
                logger.warning(f"Competitive summary generation failed: {e}")
                return None

        # Execute all competitors in parallel
        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            futures = [executor.submit(query_competitor, client) for client in self._competitor_clients]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        logger.info(f"Competitive summary: {len(results)}/{len(self._competitor_clients)} models succeeded")

        if not results:
            # All failed - fall back to single model
            logger.warning("All competitive models failed, falling back to single model")
            if word_count <= self.chunk_size * 1.2:
                return self._summarize_short_chapter(chapter_text, chapter_index, title, word_count)
            else:
                return self._summarize_long_chapter(chapter_text, chapter_index, title, word_count)

        # Merge results using consensus
        return self._merge_competitive_summaries(results, chapter_index, title, word_count)

    def _merge_competitive_summaries(
        self,
        results: list[dict],
        chapter_index: int,
        title: str,
        word_count: int,
    ) -> ChapterSummary:
        """Merge summaries from multiple models using voting."""
        num_models = len(results)
        threshold = self.competitive_config.consensus_merge_threshold if self.competitive_config else 0.67
        min_votes = max(1, int(num_models * threshold))

        # Merge key_events with voting
        event_counts: Counter = Counter()
        for result in results:
            events = result.get("key_events") or []
            for event in events:
                # Normalize event for comparison (lowercase, strip)
                normalized = event.lower().strip()
                event_counts[normalized] += 1

        # Keep events with enough votes, preserve original casing from first occurrence
        event_originals: dict[str, str] = {}
        for result in results:
            for event in result.get("key_events") or []:
                normalized = event.lower().strip()
                if normalized not in event_originals:
                    event_originals[normalized] = event

        consensus_events = [
            event_originals[norm]
            for norm, count in event_counts.most_common()
            if count >= min_votes
        ]

        # Merge characters with voting (intersection approach)
        active_char_counts: Counter = Counter()
        mentioned_char_counts: Counter = Counter()
        for result in results:
            for char in result.get("active_characters") or []:
                active_char_counts[char.strip()] += 1
            for char in result.get("mentioned_characters") or []:
                mentioned_char_counts[char.strip()] += 1

        consensus_active = [char for char, count in active_char_counts.items() if count >= min_votes]
        consensus_mentioned = [char for char, count in mentioned_char_counts.items() if count >= min_votes]

        # Select best summary based on overlap with consensus events
        best_summary = ""
        best_score = -1
        for result in results:
            summary = result.get("summary", "")
            events = result.get("key_events") or []
            # Score = number of events that made it to consensus
            score = sum(
                1 for e in events
                if e.lower().strip() in [ce.lower().strip() for ce in consensus_events]
            )
            if score > best_score or (score == best_score and len(summary) > len(best_summary)):
                best_score = score
                best_summary = summary

        # Merge tones (majority vote)
        tone_counts: Counter = Counter()
        for result in results:
            tone = result.get("primary_tone", "reflective")
            if tone in self._valid_tones():
                tone_counts[tone] += 1
        primary_tone = tone_counts.most_common(1)[0][0] if tone_counts else "reflective"

        # Secondary tones - any tone mentioned by 2+ models
        secondary_tone_counts: Counter = Counter()
        for result in results:
            for tone in result.get("secondary_tones") or []:
                if tone in self._valid_tones():
                    secondary_tone_counts[tone] += 1
        secondary_tones = [
            tone for tone, count in secondary_tone_counts.items()
            if count >= min_votes and tone != primary_tone
        ]

        # Dialogue density - majority vote
        dialogue_counts: Counter = Counter()
        for result in results:
            density = result.get("dialogue_density", "medium")
            if density in ["high", "medium", "low"]:
                dialogue_counts[density] += 1
        dialogue_density = dialogue_counts.most_common(1)[0][0] if dialogue_counts else "medium"

        # POV character - majority vote
        pov_counts: Counter = Counter()
        for result in results:
            pov = result.get("pov_character")
            if pov:
                pov_counts[pov] += 1
        pov_character = pov_counts.most_common(1)[0][0] if pov_counts else None

        logger.info(
            f"Competitive summary merged: {len(consensus_events)} events, "
            f"{len(consensus_active)} active chars, {len(consensus_mentioned)} mentioned chars"
        )

        # Record vote statistics for consensus log
        from ..consensus_collector import consensus_collector
        consensus_collector.record_vote(
            vote_type="summary_merge",
            subject=f"Chapter {chapter_index}: {title}",
            context=f"{num_models} models",
            votes=[],  # Summary merges use counts not individual votes
            threshold=threshold,
            outcome="merged",
            reason=f"{len(consensus_events)} events, {len(consensus_active)} active chars agreed on by {min_votes}+ models",
        )

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=best_summary,
            key_events=consensus_events,
            primary_tone=primary_tone,
            secondary_tones=secondary_tones,
            dialogue_density=dialogue_density,
            active_characters=consensus_active,
            mentioned_characters=consensus_mentioned,
            pov_character=pov_character,
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,
            confidence=0.9,  # Higher confidence for consensus
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
            length_guidance=self._get_length_guidance(),
        )

        result, _ = self.llm.query_json(prompt, system=SINGLE_CHAPTER_SYSTEM)

        # Retry with JSON-capable model if primary failed
        if result is None and self.json_llm is not None:
            logger.warning(
                f"Primary model failed JSON for chapter {chapter_index}, "
                f"retrying with JSON-capable model '{self.json_llm.config.model}'"
            )
            result, _ = self.json_llm.query_json(prompt, system=SINGLE_CHAPTER_SYSTEM)

        if result is None:
            logger.warning(f"LLM summarization failed for chapter {chapter_index}")
            return self._create_fallback_summary(chapter_index, title, word_count)

        return self._parse_chapter_result(result, chapter_index, title, word_count, chapter_text=text)

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

        # Retry with JSON-capable model if primary failed
        if result is None and self.json_llm is not None:
            logger.debug(f"Chunk {chunk_index} retry with JSON-capable model")
            result, _ = self.json_llm.query_json(prompt, system=CHUNK_SUMMARY_SYSTEM)

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
            key_events=result.get("key_events") or [],
            characters_mentioned=result.get("characters_mentioned") or [],
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

        # Check if primary model failed and we have a JSON-capable fallback
        primary_failed = not response.success or result is None or not isinstance(result, dict)
        if primary_failed and self.json_llm is not None:
            logger.warning(
                f"Consolidation retry with JSON-capable model for chapter {chapter_index}"
            )
            result, response = self.json_llm.query_json(prompt, system=CONSOLIDATE_SYSTEM)

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
        chapter_text: str = "",
    ) -> ChapterSummary:
        """Parse LLM result into ChapterSummary."""
        primary_tone = result.get("primary_tone", "reflective")
        if primary_tone not in self._valid_tones():
            primary_tone = "reflective"

        secondary_tones = []
        for t in result.get("secondary_tones") or []:
            if t in self._valid_tones() and t != primary_tone:
                secondary_tones.append(t)

        dialogue = result.get("dialogue_density", "medium")
        if dialogue not in ["high", "medium", "low"]:
            dialogue = "medium"

        # Handle new active/mentioned character format with backward compatibility
        if "active_characters" in result:
            active_characters = result.get("active_characters") or []
            mentioned_characters = result.get("mentioned_characters") or []
        else:
            # Old format: all characters_present treated as active
            active_characters = result.get("characters_present") or []
            mentioned_characters = []

        # Override active/mentioned classification with Echo scalpel if available
        all_characters = list(set(active_characters + mentioned_characters))
        if all_characters and scalpel_available("echo"):
            try:
                loader = ScalpelLoader()
                chapter_text = result.get("summary", "")
                texts = [
                    f"{char} [SEP] {chapter_text}" for char in all_characters
                ]
                predictions = loader.predict_batch("echo", texts)

                echo_active = []
                echo_mentioned = []
                for char, (label, conf) in zip(all_characters, predictions):
                    if label == "active":
                        echo_active.append(char)
                    else:
                        echo_mentioned.append(char)

                logger.debug(
                    f"Echo scalpel reclassified chapter {chapter_index}: "
                    f"{len(echo_active)} active, {len(echo_mentioned)} mentioned"
                )
                active_characters = echo_active
                mentioned_characters = echo_mentioned
            except Exception as e:
                logger.warning(f"Echo scalpel failed for chapter {chapter_index}, using LLM result: {e}")

        # CRF dialogue speaker attribution (after echo, uses raw chapter text)
        dialogue_speakers = []
        if chapter_text and active_characters and crf_available():
            try:
                attributor = CRFDialogueAttributor()
                dialogue_speakers = attributor.attribute(
                    chapter_text, active_characters, confidence_threshold=0.6,
                )
                if dialogue_speakers:
                    logger.debug(
                        f"CRF attributed {len(dialogue_speakers)} dialogue lines "
                        f"in chapter {chapter_index}"
                    )
            except Exception as e:
                logger.warning(f"CRF attribution failed for chapter {chapter_index}: {e}")

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=result.get("summary", ""),
            key_events=result.get("key_events") or [],
            primary_tone=primary_tone,
            secondary_tones=secondary_tones,
            dialogue_density=dialogue,
            active_characters=active_characters,
            mentioned_characters=mentioned_characters,
            pov_character=result.get("pov_character"),
            word_count=word_count,
            estimated_duration_minutes=word_count / 150,  # ~150 wpm narration
            confidence=0.85,
            dialogue_speakers=dialogue_speakers,
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
