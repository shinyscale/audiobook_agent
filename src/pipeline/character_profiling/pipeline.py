"""
Character profiling pipeline orchestrator.

Coordinates the summary-driven character identification and profiling workflow.
"""

import logging
from typing import Optional, Callable
from datetime import datetime

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    CharacterProfileMap,
)
from .identifier import SummaryDrivenCharacterIdentifier
from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from ..chapter_detection.models import ChapterMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


class CharacterProfilingPipeline:
    """
    Orchestrates the character profiling workflow.

    Stages:
    1. Identification: Extract characters from chapter summaries
    2. Profiling: Generate rich profiles for each character (future)
    3. Reconciliation: Final duplicate check (future)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """
        Args:
            llm_client: LLM client for character identification and profiling
            progress_callback: Callback(stage, current, total) for progress updates
        """
        self.llm = llm_client
        self.progress_callback = progress_callback

    def run(
        self,
        full_text: str,
        chapter_map: ChapterMap,
        summary_map: ChapterSummaryMap,
        plot_summary: Optional[str] = None,
        source_file: str = "unknown",
    ) -> CharacterProfileMap:
        """
        Run the character profiling pipeline.

        Args:
            full_text: Complete document text
            chapter_map: Chapter boundaries from chapter detection
            summary_map: Chapter summaries from summary pipeline
            plot_summary: Optional plot summary for better identification
            source_file: Source file name for metadata

        Returns:
            CharacterProfileMap with all character profiles
        """
        logger.info("Starting character profiling pipeline")
        self._report_progress("identification", 0, 3)

        # Stage 1: Character Identification from Summaries
        logger.info("Stage 1: Identifying characters from summaries")
        identifier = SummaryDrivenCharacterIdentifier(self.llm)

        characters, narrator_name, narrative_style = identifier.identify_characters(
            chapter_summaries=summary_map.summaries,
            plot_summary=plot_summary or "",
        )
        self._report_progress("identification", 1, 3)

        logger.info(f"Identified {len(characters)} characters")
        if narrator_name:
            logger.info(f"Narrator: {narrator_name}")

        # Stage 2: Profile Generation (basic for now, will be enhanced)
        logger.info("Stage 2: Generating character profiles")
        self._report_progress("profiling", 0, len(characters))

        profiles = []
        for i, char in enumerate(characters):
            profile = CharacterProfile.from_identified(char)
            profiles.append(profile)
            self._report_progress("profiling", i + 1, len(characters))

        # Stage 3: Build result
        logger.info("Stage 3: Building profile map")
        self._report_progress("finalization", 1, 1)

        profile_map = CharacterProfileMap(
            profiles=profiles,
            narrator_name=narrator_name,
            narrative_style=narrative_style,
            total_characters=len(profiles),
            pipeline_metadata={
                "source_file": source_file,
                "generated_at": datetime.now().isoformat(),
                "chapter_count": len(summary_map.summaries),
            },
        )

        logger.info(f"Character profiling complete: {len(profiles)} profiles")

        return profile_map

    def identify_only(
        self,
        summary_map: ChapterSummaryMap,
        plot_summary: Optional[str] = None,
    ) -> tuple[list[IdentifiedCharacter], Optional[str], str]:
        """
        Run only the identification stage (for testing or separate workflows).

        Args:
            summary_map: Chapter summaries from summary pipeline
            plot_summary: Optional plot summary for better identification

        Returns:
            Tuple of (characters, narrator_name, narrative_style)
        """
        identifier = SummaryDrivenCharacterIdentifier(self.llm)
        return identifier.identify_characters(
            chapter_summaries=summary_map.summaries,
            plot_summary=plot_summary or "",
        )

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is configured."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)


def profile_characters(
    full_text: str,
    chapter_map: ChapterMap,
    summary_map: ChapterSummaryMap,
    llm_client: LLMClient,
    plot_summary: Optional[str] = None,
    source_file: str = "unknown",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> CharacterProfileMap:
    """
    Convenience function for character profiling.

    Args:
        full_text: Complete document text
        chapter_map: Chapter boundaries from chapter detection
        summary_map: Chapter summaries from summary pipeline
        llm_client: LLM client
        plot_summary: Optional plot summary
        source_file: Source file name
        progress_callback: Optional progress callback

    Returns:
        CharacterProfileMap with all character profiles
    """
    pipeline = CharacterProfilingPipeline(
        llm_client=llm_client,
        progress_callback=progress_callback,
    )

    return pipeline.run(
        full_text=full_text,
        chapter_map=chapter_map,
        summary_map=summary_map,
        plot_summary=plot_summary,
        source_file=source_file,
    )
