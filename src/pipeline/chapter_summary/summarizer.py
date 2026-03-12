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
- Use characters' proper names when stated in the text (e.g., if the text names "his father John", write "John" not "his father"). Do not infer relationship types not explicitly stated.
- **FIRST-PERSON NARRATORS**: The narrator is whoever says "I" throughout this section — identified by what "I" DOES and EXPERIENCES, NOT by which characters are mentioned. A character who is MENTIONED by the narrator (e.g., "I saw Victor", "I confronted my creator") is NOT the narrator. In the SUMMARY TEXT, always refer to the narrative voice as "the narrator" — never use any character's proper name as the subject performing actions. The correct name will be substituted during post-processing. However, in the active_characters and characters_mentioned lists, include the narrator's ACTUAL NAME if explicitly stated in the text (e.g., letter signatures like "R. Walton", or explicit self-identification). When a character within the story recounts their own past in first person (an embedded story, flashback, or oral account), attribute those events to THAT character — using their name only if stated in the text.
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
- If something is vague in the section summaries, preserve that vagueness rather than inventing details
- Use characters' proper names when stated in the section summaries (e.g., "his father John" → write "John"). Do not infer relationship types not explicitly stated.
- **FIRST-PERSON NARRATORS**: The narrator is whoever says "I" in these summaries — identified by what "I" DOES and EXPERIENCES, NOT by which characters are mentioned. A character mentioned BY the narrator is NOT the narrator. In the SUMMARY TEXT, always refer to the narrative voice as "the narrator". The correct name will be substituted during post-processing. In the active_characters and characters_mentioned lists, include the narrator's ACTUAL NAME if explicitly stated in these summaries. When a character recounts their own past in first person (embedded story, flashback, oral account), attribute those events to THAT character — using their name only if stated.
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
- Include character emotions and reactions when they impact the narrative
- If something is vague or unclear in the text, say so rather than guessing
- Use characters' proper names when stated in the text (e.g., if the text names "his father John", write "John" not "his father"). Do not infer relationship types not explicitly stated.
- **FIRST-PERSON NARRATORS**: The narrator is whoever says "I" throughout this section — identified by what "I" DOES and EXPERIENCES, NOT by which characters are mentioned. A character who is MENTIONED by the narrator (e.g., "I saw Victor", "I spoke to my creator") is NOT the narrator. In the SUMMARY TEXT, always refer to the narrative voice as "the narrator" — never use any character's proper name as the subject performing actions. In the active_characters list, include the narrator's ACTUAL NAME if explicitly stated in the text. The correct name will be substituted into the summary text during post-processing.
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
    ):
        """
        Args:
            llm_client: LLM client for summarization
            chunk_size: Target words per chunk
            chunk_overlap: Words of overlap between chunks
            known_characters: List of known character names for reference
            summary_length: Length preference - "brief" (2-3 sentences), "standard" (4-6 sentences), "detailed" (6-8 sentences)
            competitive_config: Optional config for multi-model consensus
        """
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.known_characters = known_characters or []
        self.summary_length = summary_length
        self.competitive_config = competitive_config

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
            result = self._competitive_summarize_chapter(
                chapter_text, chapter_index, title, word_count
            )
            self._fix_narrator_attribution(result, chapter_text)
            return result

        # Short chapter: summarize directly
        if word_count <= self.chunk_size * 1.2:  # Allow 20% buffer before chunking
            result = self._summarize_short_chapter(chapter_text, chapter_index, title, word_count)
        else:
            # Long chapter: chunk and consolidate
            result = self._summarize_long_chapter(chapter_text, chapter_index, title, word_count)

        # Post-process: fix narrator misattribution using structural text evidence
        self._fix_narrator_attribution(result, chapter_text)

        return result

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
            events = result.get("key_events", [])
            for event in events:
                # Normalize event for comparison (lowercase, strip)
                normalized = event.lower().strip()
                event_counts[normalized] += 1

        # Keep events with enough votes, preserve original casing from first occurrence
        event_originals: dict[str, str] = {}
        for result in results:
            for event in result.get("key_events", []):
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
            for char in result.get("active_characters", []):
                active_char_counts[char.strip()] += 1
            for char in result.get("mentioned_characters", []):
                mentioned_char_counts[char.strip()] += 1

        consensus_active = [char for char, count in active_char_counts.items() if count >= min_votes]
        consensus_mentioned = [char for char, count in mentioned_char_counts.items() if count >= min_votes]

        # Select best summary based on overlap with consensus events
        best_summary = ""
        best_score = -1
        for result in results:
            summary = result.get("summary", "")
            events = result.get("key_events", [])
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
            for tone in result.get("secondary_tones", []):
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

    @staticmethod
    def _sanitize_llm_text(text: str) -> str:
        """Strip non-Latin script characters (CJK, Cyrillic, Arabic, etc.) from LLM output.

        Preserves Latin, IPA, common punctuation, and standard Unicode.
        Addresses Qwen3 model family occasionally producing Chinese text mid-output.
        """
        import re
        # Remove CJK Unified Ideographs, Hiragana, Katakana, CJK symbols, CJK compatibility
        text = re.sub(r'[　-鿿豈-﫿぀-ゟ゠-ヿ]+', '', text)
        # Remove Arabic script
        text = re.sub(r'[؀-ۿ]+', '', text)
        # Clean up any resulting double-spaces or orphaned punctuation
        text = re.sub(r'  +', ' ', text)
        return text.strip()

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

        # Sanitize LLM text to remove CJK hallucinations from Qwen3
        _summary = self._sanitize_llm_text(result.get("summary", ""))
        _key_events = [self._sanitize_llm_text(e) for e in result.get("key_events", [])]

        return ChapterSummary(
            chapter_index=chapter_index,
            chapter_title=title,
            summary=_summary,
            key_events=_key_events,
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
    def _detect_letter_signatory(chapter_text: str) -> Optional[str]:
        """
        Detect if chapter text is (or follows) an epistolary letter and return
        the letter-writer's name.

        Two detection paths:
        A) The chapter text begins with the closing of a PREVIOUS letter followed
           by the header of the CURRENT letter (e.g., "R. Walton\\nLetter 2\\nTo Mrs. Saville").
           The signatory is the short proper-name line immediately before "Letter N".
        B) Standalone letter: salutation ("To X," or "Dear X,") in the head AND
           a closing signature ("Your... \\nName") in the tail.

        Returns the signatory name, or None if not detected.
        """
        head = chapter_text[:600]

        # Path A: "Letter N" header inside the head (preceded by a signature)
        letter_header_m = re.search(r'\bLetter\s+\w+\s*\n', head)
        if letter_header_m:
            pre_header = head[: letter_header_m.start()]
            # The signatory is the last short proper-name line before the header
            lines = [ln.strip() for ln in pre_header.split("\n") if ln.strip()]
            if lines:
                candidate = lines[-1].strip()
                if re.match(r"^[A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){0,3}\.?$", candidate):
                    # Expand initials (e.g., "R.W." → "Robert Walton") if full name
                    # appears in the chapter text
                    if re.match(r"^[A-Z]\.[A-Za-z.]+$", candidate):
                        initials = [c for c in candidate if c.isupper()]
                        for m in re.finditer(
                            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", chapter_text[:10000]
                        ):
                            name_words = m.group(1).split()
                            if [w[0] for w in name_words] == initials:
                                return m.group(1)
                    return candidate

        # Path B: Standalone letter — salutation in head + closing in tail
        has_salutation = bool(
            re.search(r"^\s*(?:To\s+\w|Dear\s+\w)", head, re.IGNORECASE | re.MULTILINE)
        )
        if has_salutation:
            tail = chapter_text[-600:]
            sig_m = re.search(
                r"(?:Your|Yours|Ever\s+yours|Affectionately|Sincerely|Faithfully)"
                r"[^\n]{0,50}\n\s*([A-Z][A-Za-z\s.]{2,40})",
                tail,
            )
            if sig_m:
                name = sig_m.group(1).strip().rstrip(".")
                name = re.split(r"\n", name)[0].strip()
                return name if len(name.split()) <= 4 else None

        return None

    @staticmethod
    def _apply_letter_narrator(summary: str, signatory: str) -> str:
        """
        Replace an incorrect narrator name in a letter chapter summary.

        Handles:
        - Dual attribution: "Name1, Name2, verb..." → if Name2 matches signatory, strip Name1
          (works mid-sentence, e.g., "In this letter, Name1, Name2, verb...")
        - Single wrong leading name: "Name, verb..." → replace with signatory
        """
        if not summary:
            return summary

        sig_lower = set(signatory.lower().split())

        # Look for dual attribution "[Name1], [Name2], [verb]..." anywhere in first sentence
        first_period = summary.find(".")
        first_sentence_end = first_period if first_period != -1 else len(summary)
        first_sentence = summary[:first_sentence_end]

        # Both name groups must be multi-word (e.g., "Victor Frankenstein, Robert Walton")
        # to avoid matching single-word place/month names (e.g., "March, Victor Frankenstein")
        dual_re = re.compile(
            r"((?:[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)),\s+"
            r"((?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)),\s+"
        )
        for m in dual_re.finditer(first_sentence):
            name1, name2 = m.group(1), m.group(2)
            n1_lower = set(name1.lower().split())
            n2_lower = set(name2.lower().split())
            if sig_lower & n2_lower:
                # Name2 matches signatory — remove "Name1, " from the match
                remove_span = name1 + ", "
                return summary[:m.start()] + summary[m.start() + len(remove_span):]
            elif sig_lower & n1_lower:
                # Name1 matches signatory — remove ", Name2" from the match
                remove_span = ", " + name2
                before = summary[:m.start() + len(name1)]
                after = summary[m.start() + len(name1) + len(remove_span):]
                return before + after
            else:
                # Neither overlaps with signatory — replace both with signatory
                return summary[:m.start()] + signatory + ", " + summary[m.end():]

        # Single leading attribution: "Name, verb..." or "Name verb..."
        single_match = re.match(
            r"^((?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*))(,\s+|\s+)",
            summary,
        )
        if single_match:
            found_name = single_match.group(1)
            found_lower = set(found_name.lower().split())
            if not (sig_lower & found_lower):
                # Name doesn't match signatory — replace it
                return signatory + single_match.group(2) + summary[single_match.end():]

        return summary

    @staticmethod
    def _fix_self_referential_narrator(summary: str) -> str:
        """
        Fix summaries where the same name appears as both the acting subject
        and the target of a "creator/confront" action — indicating the first
        occurrence (as agent) is a narrator misattribution.

        E.g., "Victor Frankenstein, a created being, burns the cottage...
               to confront his creator, Victor Frankenstein"
        → "the narrator, a created being, burns the cottage...
               to confront his creator, Victor Frankenstein"
        """
        # Find all multi-word proper names
        names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', summary)
        if not names:
            return summary

        name_counts = Counter(names)

        for name, count in name_counts.most_common():
            if count < 2:
                break
            # Check: name as agent at start AND as target of creator/confront later
            creator_re = re.compile(
                r'\b' + re.escape(name) + r'\b'
                r'.{10,300}'
                r'(?:creator|created\s+by|confront(?:ed|ing)?)'
                r'.{0,80}\b' + re.escape(name) + r'\b',
                re.IGNORECASE | re.DOTALL,
            )
            if creator_re.search(summary):
                # Replace only the FIRST occurrence (the wrongly-named agent)
                fixed = summary.replace(name, 'the narrator', 1)
                # Lowercase if it now starts "the narrator" after a capital
                return re.sub(r'^The narrator', 'The narrator', fixed)

        return summary

    @staticmethod
    def _fix_created_being_attribution(summary: str) -> str:
        """
        Fix summaries where a human character name is immediately followed by
        an appositive describing a non-human narrator ("a created being",
        "a solitary creature", "earliest conscious experiences", etc.).

        Replaces the wrong name in the first sentence with "the narrator".
        """
        # Pattern: "[Name], a created/conscious/sentient/solitary being/creature"
        # NOTE: do NOT use re.IGNORECASE — [A-Z] must only match uppercase so that
        # common words like "the", "a", "chapter" are not captured as names.
        appositive_re = re.compile(
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*),\s+'
            r'a\s+(?:(?:newly\s+|recently\s+)?(?:created|conscious|sentient)\s+(?:being|creature)'
            r'|solitary\s+(?:creature|being))',
        )
        # Pattern: "[Name]'s earliest conscious/sensory experiences/days of consciousness"
        #          or "awakening". Covers both "earliest conscious experiences" and
        #          "earliest days of consciousness" variants generated by different LLMs.
        # Use [\u2018\u2019'] to match both ASCII apostrophe and Unicode curly quotes.
        awakening_re = re.compile(
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)[' r"'\u2018\u2019]?s?\s+"
            r'(?:earliest\s+(?:conscious|sensory)\s+(?:experiences?|days?)'
            r'|earliest\s+days?\s+of\s+consciousness'
            r'|awakening\s+to\s+(?:consciousness|sensory\s+overload))',
        )

        match = appositive_re.search(summary) or awakening_re.search(summary)
        if not match:
            return summary

        wrong_name = match.group(1)

        # Only replace in the first sentence
        first_dot = summary.find('.')
        end = first_dot + 1 if first_dot != -1 else len(summary)
        first_sentence = summary[:end]
        rest = summary[end:]

        fixed_sentence = first_sentence.replace(wrong_name, 'the narrator', 1)
        return fixed_sentence + rest

    @staticmethod
    def _fix_narrator_attribution(result: "ChapterSummary", chapter_text: str) -> None:
        """
        Post-process a ChapterSummary in-place to fix narrator misattribution.

        Uses structural text evidence (letter signatures, non-human descriptors,
        self-referential contradictions) to override LLM narrator guesses.

        Does NOT use any knowledge of specific novels or characters.

        Static method so it can be called from analyzer.py after the narrator
        substitution pass (which replaces 'the narrator' with the narrator's name,
        undoing any fixes applied during summarization).
        """
        if not result.summary:
            return

        summary = result.summary

        # Fix 1: Letter chapters — extract signatory from text structure
        signatory = ChapterSummarizer._detect_letter_signatory(chapter_text)
        if signatory:
            fixed = ChapterSummarizer._apply_letter_narrator(summary, signatory)
            if fixed != summary:
                logger.info(
                    f"Narrator fix (letter signatory '{signatory}'): "
                    f"{summary[:60]!r} → {fixed[:60]!r}"
                )
                result.summary = fixed
                return

        # Fix 2: Self-referential contradiction — same name as agent and target
        fixed = ChapterSummarizer._fix_self_referential_narrator(summary)
        if fixed != summary:
            logger.info(
                f"Narrator fix (self-referential): {summary[:60]!r} → {fixed[:60]!r}"
            )
            result.summary = fixed
            return

        # Fix 3: Non-human descriptor — "a created being", awakening language
        fixed = ChapterSummarizer._fix_created_being_attribution(summary)
        if fixed != summary:
            logger.info(
                f"Narrator fix (created being): {summary[:60]!r} → {fixed[:60]!r}"
            )
            result.summary = fixed
            return

        # Fix 4: "My creator" in chapter text (outside dialogue) — narrator references
        # their own creator, meaning the narrator is a created being.
        # Universal invariant: if a narrator (not in dialogue) writes "my creator",
        # they are NOT the creator — leading human name is a misattribution.
        # Guard: only fire when "my creator" appears OUTSIDE quotation marks (not in
        # a character's dialogue), to avoid false positives in chapters where another
        # character says "my creator" to the actual (human) narrator.
        if chapter_text:
            creator_phrase_re = re.compile(
                r'\bmy\s+(?:creator|maker)\b', re.IGNORECASE
            )
            # Only match outside dialogue: look for occurrences NOT preceded by a
            # double-quote within the same paragraph (heuristic: nearest " before match
            # is farther away than the nearest newline before match).
            # Support ASCII ("), left-curly (U+201C), and right-curly (U+201D) quotes.
            _scan_text = chapter_text[:3000]
            _found_outside_dialogue = False
            for _m_c in creator_phrase_re.finditer(_scan_text):
                _pos = _m_c.start()
                _before = _scan_text[:_pos]
                _last_quote = max(
                    _before.rfind('"'),       # ASCII double-quote
                    _before.rfind('\u201c'),  # Left curly quote "
                    _before.rfind('\u201d'),  # Right curly quote "
                )
                _last_nl = _before.rfind('\n')
                # If the most recent newline is AFTER the most recent open-quote,
                # this occurrence is in narrative (not inside a quoted speech block).
                if _last_nl >= _last_quote:
                    _found_outside_dialogue = True
                    break
            if _found_outside_dialogue:
                # Replace the leading proper name in the summary with "the narrator"
                leading_name_re = re.compile(
                    r'^((?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*))(,\s+|\s+)'
                )
                m = leading_name_re.match(summary)
                if m:
                    fixed = 'The narrator' + m.group(2) + summary[m.end():]
                    if fixed != summary:
                        logger.info(
                            f"Narrator fix (my creator heuristic): "
                            f"{summary[:60]!r} → {fixed[:60]!r}"
                        )
                        result.summary = fixed
                        return

        # Fix 5: Chapter text opens with quoted first-person prose after a chapter heading.
        # Universal invariant: in nested/frame narratives, inner narrator chapters are
        # formatted as the inner narrator's speech within outer quotation marks.
        # Pattern: after "Chapter N" heading in text, the first prose line begins with "I "
        # (i.e., the inner narrator speaks directly in first person inside a quote block).
        # This catches creature/inner narrator chapters that lack awakening/appositive signals.
        if chapter_text:
            _quoted_fp_re = re.compile(
                r'Chapter\s+\w+\s*\n\s*\u201c?\"?\s*I\s+',  # Chapter N\n"I ...
                re.IGNORECASE,
            )
            if _quoted_fp_re.search(chapter_text[:1000]):
                # Only replace if summary starts with a MULTI-WORD proper name (at least 2 words)
                # to avoid capturing single words like "The", "In", "On" as false names.
                leading_name_re2 = re.compile(
                    r'^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)(,\s+|\s+)'
                )
                m2 = leading_name_re2.match(summary)
                if m2:
                    fixed2 = 'The narrator' + m2.group(2) + summary[m2.end():]
                    if fixed2 != summary:
                        logger.info(
                            f"Narrator fix (quoted first-person inner narrator): "
                            f"{summary[:60]!r} → {fixed2[:60]!r}"
                        )
                        result.summary = fixed2

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
