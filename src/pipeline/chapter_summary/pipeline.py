"""
Chapter summary pipeline orchestrator.

Coordinates the full chapter summarization workflow with checkpointing.
Supports parallel chapter summarization for faster processing.
Supports competitive multi-model consensus for summary generation when enabled.
"""

import hashlib
import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from ..chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..character_extraction.models import CharacterMap as CharacterExtractionMap
from ..llm import LLMClient
from .models import (
    ChapterSummary,
    ChapterSummaryMap,
    SummaryPipelineCheckpoint,
)
from .summarizer import ChapterSummarizer

if TYPE_CHECKING:
    from ...agents.config import CompetitiveConfig

logger = logging.getLogger(__name__)


class ChapterSummaryPipeline:
    """
    Orchestrates the chapter summarization workflow.

    Stages:
    1. Summarization: Generate summaries for each chapter
    2. Consolidation: Build document-level analysis

    Supports checkpointing to save/resume progress.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        parallel_chapters: bool = False,
        max_workers: int = 4,
        llm_client_factory: Optional[Callable[[], LLMClient]] = None,
        summarizer_chunk_size_words: int = 2500,
        summarizer_chunk_overlap_words: int = 200,
        competitive_config: Optional["CompetitiveConfig"] = None,
        json_llm: Optional[LLMClient] = None,
    ):
        """
        Args:
            llm_client: LLM client for summarization
            checkpoint_dir: Directory for saving checkpoints
            progress_callback: Callback(stage, current, total) for progress updates
            parallel_chapters: Whether to summarize chapters in parallel
            max_workers: Max threads for parallel summarization
            llm_client_factory: Factory function to create new LLM clients for parallel execution
            competitive_config: Optional config for multi-model consensus
            json_llm: Optional JSON-capable LLM client for fallback when primary fails JSON parsing
        """
        self.llm = llm_client
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback
        self.parallel_chapters = parallel_chapters
        self.max_workers = max_workers
        self.llm_client_factory = llm_client_factory
        self._progress_lock = threading.Lock()  # Thread-safe progress reporting
        self.summarizer_chunk_size_words = summarizer_chunk_size_words
        self.summarizer_chunk_overlap_words = summarizer_chunk_overlap_words
        self.competitive_config = competitive_config
        self.json_llm = json_llm

    def run(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        character_map: Optional[CharacterExtractionMap] = None,
        source_file: str = "unknown",
        resume_from: Optional[SummaryPipelineCheckpoint] = None,
    ) -> tuple[ChapterSummaryMap, SummaryPipelineCheckpoint]:
        """
        Run the full chapter summary pipeline.

        Args:
            full_text: The complete document text
            chapter_map: Chapter boundaries from chapter detection
            character_map: Optional character data for reference
            source_file: Source file name for checkpointing
            resume_from: Optional checkpoint to resume from

        Returns:
            Tuple of (ChapterSummaryMap, final checkpoint)
        """
        # Calculate text hash for checkpoint validation
        text_hash = hashlib.md5(full_text.encode()).hexdigest()

        # Extract known character names if available
        known_characters = []
        if character_map:
            known_characters = [c.canonical_name for c in character_map.characters]

        # Create summarizer with character context
        summarizer = ChapterSummarizer(
            llm_client=self.llm,
            known_characters=known_characters,
            chunk_size=self.summarizer_chunk_size_words,
            chunk_overlap=self.summarizer_chunk_overlap_words,
            competitive_config=self.competitive_config,
            json_llm=self.json_llm,
        )

        # Initialize or validate checkpoint
        if resume_from:
            if resume_from.text_hash != text_hash:
                logger.warning("Text hash mismatch - starting fresh")
                checkpoint = SummaryPipelineCheckpoint.create_new(source_file, text_hash)
            else:
                checkpoint = resume_from
                logger.info(f"Resuming from stage: {checkpoint.stage}")
        else:
            checkpoint = SummaryPipelineCheckpoint.create_new(source_file, text_hash)

        # Stage 1: Summarization
        if checkpoint.stage == "summarization":
            if self.parallel_chapters and len(chapter_map.chapters) > 1:
                logger.info(
                    f"Stage 1: Generating chapter summaries in parallel ({self.max_workers} workers)"
                )
                checkpoint = self._run_summarization_parallel(
                    full_text, chapter_map, summarizer, checkpoint, known_characters
                )
            else:
                logger.info("Stage 1: Generating chapter summaries")
                checkpoint = self._run_summarization(full_text, chapter_map, summarizer, checkpoint)
            self._save_checkpoint(checkpoint)

        # Stage 2: Consolidation
        if checkpoint.stage == "consolidation":
            logger.info("Stage 2: Building document-level analysis")
            checkpoint = self._run_consolidation(checkpoint)
            self._save_checkpoint(checkpoint)

        return checkpoint.summary_map, checkpoint

    def _run_summarization(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        summarizer: ChapterSummarizer,
        checkpoint: SummaryPipelineCheckpoint,
    ) -> SummaryPipelineCheckpoint:
        """Generate summaries for all chapters."""
        summaries = checkpoint.chapter_summaries or []
        completed = set(checkpoint.completed_chapters)
        total_chapters = len(chapter_map.chapters)

        for i, chapter in enumerate(chapter_map.chapters):
            chapter_idx = chapter.index

            # Skip already completed chapters (for resume)
            if chapter_idx in completed:
                continue

            self._report_progress("summarization", i + 1, total_chapters)

            # Extract chapter text
            start = chapter.start_position
            end = chapter.end_position
            chapter_text = full_text[start:end]

            try:
                summary = summarizer.summarize_chapter(
                    chapter_text=chapter_text,
                    chapter_index=chapter_idx,
                    chapter_title=chapter.title,
                )
                summaries.append(summary)
                completed.add(chapter_idx)

                logger.info(
                    f"Chapter {chapter_idx}: {summary.word_count} words, "
                    f"tone={summary.primary_tone}, "
                    f"{len(summary.characters_present)} characters"
                )

            except Exception as e:
                logger.error(f"Summarization failed for chapter {chapter_idx}: {e}")
                checkpoint.errors.append(
                    f"Summarization failed for chapter {chapter_idx}: {str(e)}"
                )

            # Save progress periodically
            if len(completed) % 5 == 0:
                checkpoint.chapter_summaries = summaries
                checkpoint.completed_chapters = list(completed)
                self._save_checkpoint(checkpoint)

        checkpoint.chapter_summaries = summaries
        checkpoint.completed_chapters = list(completed)
        checkpoint.stage = "consolidation"
        checkpoint.timestamp = datetime.now().isoformat()

        return checkpoint

    def _run_summarization_parallel(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        summarizer: ChapterSummarizer,
        checkpoint: SummaryPipelineCheckpoint,
        known_characters: list[str],
    ) -> SummaryPipelineCheckpoint:
        """Generate summaries for all chapters in parallel using ThreadPoolExecutor."""
        completed = set(checkpoint.completed_chapters)
        total_chapters = len(chapter_map.chapters)

        # Prepare chapters that need processing
        chapters_to_process = [ch for ch in chapter_map.chapters if ch.index not in completed]

        if not chapters_to_process:
            logger.info("All chapters already completed, skipping summarization")
            checkpoint.stage = "consolidation"
            return checkpoint

        logger.info(
            f"Processing {len(chapters_to_process)} chapters with {self.max_workers} workers"
        )

        # Thread-safe collections for results
        summaries: list[ChapterSummary] = list(checkpoint.chapter_summaries or [])
        summaries_lock = threading.Lock()
        errors: list[str] = []
        errors_lock = threading.Lock()
        progress_counter = [len(completed)]  # Mutable for closure

        def summarize_chapter(chapter) -> Optional[ChapterSummary]:
            """Worker function to summarize a single chapter."""
            chapter_idx = chapter.index

            # Extract chapter text
            start = chapter.start_position
            end = chapter.end_position
            chapter_text = full_text[start:end]

            try:
                # Create a fresh LLM client for this thread if factory provided
                if self.llm_client_factory:
                    thread_llm = self.llm_client_factory()
                    thread_summarizer = ChapterSummarizer(
                        llm_client=thread_llm,
                        known_characters=known_characters,
                        chunk_size=self.summarizer_chunk_size_words,
                        chunk_overlap=self.summarizer_chunk_overlap_words,
                        competitive_config=self.competitive_config,
                        json_llm=self.json_llm,  # Shared JSON fallback client
                    )
                else:
                    thread_summarizer = summarizer

                summary = thread_summarizer.summarize_chapter(
                    chapter_text=chapter_text,
                    chapter_index=chapter_idx,
                    chapter_title=chapter.title,
                )

                logger.info(
                    f"Chapter {chapter_idx}: {summary.word_count} words, "
                    f"tone={summary.primary_tone}, "
                    f"{len(summary.characters_present)} characters"
                )

                return summary

            except Exception as e:
                error_msg = f"Summarization failed for chapter {chapter_idx}: {str(e)}"
                logger.error(error_msg)
                with errors_lock:
                    errors.append(error_msg)
                return None

        # Execute summarization in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_chapter = {
                executor.submit(summarize_chapter, ch): ch for ch in chapters_to_process
            }

            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    summary = future.result()
                    if summary:
                        with summaries_lock:
                            summaries.append(summary)
                            completed.add(chapter.index)

                        # Thread-safe progress update
                        with self._progress_lock:
                            progress_counter[0] += 1
                            self._report_progress(
                                "summarization", progress_counter[0], total_chapters
                            )

                except Exception as e:
                    error_msg = f"Unexpected error for chapter {chapter.index}: {str(e)}"
                    logger.error(error_msg)
                    with errors_lock:
                        errors.append(error_msg)

        # Update checkpoint
        checkpoint.chapter_summaries = summaries
        checkpoint.completed_chapters = list(completed)
        checkpoint.errors.extend(errors)
        checkpoint.stage = "consolidation"
        checkpoint.timestamp = datetime.now().isoformat()

        logger.info(
            f"Parallel summarization complete: {len(summaries)} chapters, {len(errors)} errors"
        )

        return checkpoint

    def _run_consolidation(
        self,
        checkpoint: SummaryPipelineCheckpoint,
    ) -> SummaryPipelineCheckpoint:
        """Build document-level analysis from chapter summaries."""
        summaries = checkpoint.chapter_summaries or []

        if not summaries:
            checkpoint.warnings.append("No chapter summaries to consolidate")
            checkpoint.summary_map = ChapterSummaryMap(
                summaries=[],
                total_chapters=0,
                total_word_count=0,
                total_duration_minutes=0,
                overall_tones={},
                character_appearances={},
                pipeline_metadata={"warning": "No summaries generated"},
            )
            checkpoint.stage = "complete"
            return checkpoint

        self._report_progress("consolidation", 1, 1)

        # Calculate totals
        total_words = sum(s.word_count for s in summaries)
        total_duration = sum(s.estimated_duration_minutes for s in summaries)

        # Count tone distribution
        tone_counts: dict[str, int] = defaultdict(int)
        for s in summaries:
            tone_counts[s.primary_tone] += 1

        # Track character appearances by chapter
        character_appearances: dict[str, list[int]] = defaultdict(list)
        for s in summaries:
            for char in s.characters_present:
                character_appearances[char].append(s.chapter_index)

        summary_map = ChapterSummaryMap(
            summaries=sorted(summaries, key=lambda s: s.chapter_index),
            total_chapters=len(summaries),
            total_word_count=total_words,
            total_duration_minutes=total_duration,
            overall_tones=dict(tone_counts),
            character_appearances=dict(character_appearances),
            pipeline_metadata={
                "source_file": checkpoint.source_file,
                "generated_at": datetime.now().isoformat(),
            },
        )

        checkpoint.summary_map = summary_map
        checkpoint.stage = "complete"
        checkpoint.timestamp = datetime.now().isoformat()

        logger.info(
            f"Consolidation complete: {len(summaries)} chapters, "
            f"{total_words:,} words, {total_duration:.0f} minutes"
        )

        return checkpoint

    def _save_checkpoint(self, checkpoint: SummaryPipelineCheckpoint) -> None:
        """Save checkpoint to disk if checkpoint_dir is configured."""
        if not self.checkpoint_dir:
            return

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(checkpoint.source_file).stem
        checkpoint_file = self.checkpoint_dir / f"summaries_{safe_name}.json"

        try:
            checkpoint.save(checkpoint_file)
            logger.debug(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is configured."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)


def summarize_chapters(
    full_text: str,
    chapter_map: ChapterDetectionMap,
    llm_client: LLMClient,
    character_map: Optional[CharacterExtractionMap] = None,
    checkpoint_dir: Optional[Path] = None,
    source_file: str = "unknown",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> ChapterSummaryMap:
    """
    Convenience function for chapter summarization.

    Args:
        full_text: Complete document text
        chapter_map: Chapter boundaries from chapter detection
        llm_client: LLM client for summarization
        character_map: Optional character data for reference
        checkpoint_dir: Optional directory for checkpoints
        source_file: Source file name
        progress_callback: Optional progress callback

    Returns:
        ChapterSummaryMap with all chapter summaries
    """
    pipeline = ChapterSummaryPipeline(
        llm_client=llm_client,
        checkpoint_dir=checkpoint_dir,
        progress_callback=progress_callback,
    )

    summary_map, _ = pipeline.run(
        full_text=full_text,
        chapter_map=chapter_map,
        character_map=character_map,
        source_file=source_file,
    )

    return summary_map
