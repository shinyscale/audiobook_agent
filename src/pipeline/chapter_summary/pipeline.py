"""
Chapter summary pipeline orchestrator.

Coordinates the full chapter summarization workflow with checkpointing.
"""

import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from collections import defaultdict
import logging

from .models import (
    ChapterSummary,
    ChapterSummaryMap,
    SummaryPipelineCheckpoint,
)
from .summarizer import ChapterSummarizer
from ..chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..character_extraction.models import CharacterMap as CharacterExtractionMap
from ..llm import LLMClient

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
    ):
        """
        Args:
            llm_client: LLM client for summarization
            checkpoint_dir: Directory for saving checkpoints
            progress_callback: Callback(stage, current, total) for progress updates
        """
        self.llm = llm_client
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback

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
            logger.info("Stage 1: Generating chapter summaries")
            checkpoint = self._run_summarization(
                full_text, chapter_map, summarizer, checkpoint
            )
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
