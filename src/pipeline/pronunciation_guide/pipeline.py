"""
Pronunciation guide pipeline orchestrator.

Coordinates the full pronunciation guide generation workflow with checkpointing.
"""

import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import logging

from .models import (
    PronunciationMap,
    PronunciationPipelineCheckpoint,
    PronunciationFlag,
)
from .word_index import WordIndex
from .proposers import (
    BasePronunciationProposer,
    CMUProposer,
    ForeignProposer,
    HomographProposer,
    CharacterProposer,
)
from .enricher import PronunciationEnricher
from .consolidator import PronunciationConsolidator
from ..chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..character_extraction.models import CharacterMap as CharacterExtractionMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


class PronunciationGuidePipeline:
    """
    Orchestrates the pronunciation guide generation workflow.

    Stages:
    1. Proposal: Multiple proposers identify words needing attention
    2. Enrichment: LLM generates IPA and phonetic spellings
    3. Consolidation: Merge and prioritize into final guide

    Supports checkpointing to save/resume progress.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        proposers: Optional[list[BasePronunciationProposer]] = None,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        word_index_enabled: bool = True,
        enrichment_batch_size: int = 30,
        enrichment_max_workers: int = 4,
        enrichment_max_retries: int = 3,
        parallel_enrichment: bool = True,
    ):
        """
        Args:
            llm_client: LLM client for enrichment (optional)
            proposers: List of proposers (default: CMU, Foreign, Homograph, Character)
            checkpoint_dir: Directory for saving checkpoints
            progress_callback: Callback(stage, current, total) for progress updates
            word_index_enabled: Enable single-pass word indexing for faster proposals
            enrichment_batch_size: Words per LLM enrichment batch (default 30)
            enrichment_max_workers: Concurrent LLM enrichment workers (default 4)
            enrichment_max_retries: Max retry attempts for failed batches (default 3)
            parallel_enrichment: Enable parallel LLM enrichment (default True)
        """
        self.llm = llm_client
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback
        self.word_index_enabled = word_index_enabled
        self.parallel_enrichment = parallel_enrichment

        # Default proposers
        if proposers is None:
            self.proposers = [
                CMUProposer(),
                ForeignProposer(llm_client=llm_client),  # Pass LLM for validation
                HomographProposer(),
                CharacterProposer(),
            ]
        else:
            self.proposers = proposers

        # Enricher (requires LLM)
        if llm_client:
            self.enricher = PronunciationEnricher(
                llm_client,
                batch_size=enrichment_batch_size,
                max_workers=enrichment_max_workers,
                max_retries=enrichment_max_retries,
            )
        else:
            self.enricher = None

        # Consolidator
        self.consolidator = PronunciationConsolidator()

    def run(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        character_map: Optional[CharacterExtractionMap] = None,
        source_file: str = "unknown",
        resume_from: Optional[PronunciationPipelineCheckpoint] = None,
    ) -> tuple[PronunciationMap, PronunciationPipelineCheckpoint]:
        """
        Run the full pronunciation guide pipeline.

        Args:
            full_text: Complete document text
            chapter_map: Chapter boundaries from chapter detection
            character_map: Character data for prioritization
            source_file: Source file name for checkpointing
            resume_from: Optional checkpoint to resume from

        Returns:
            Tuple of (PronunciationMap, final checkpoint)
        """
        # Extract chapter boundaries
        chapter_boundaries = [
            (ch.index, ch.start_position, ch.end_position)
            for ch in chapter_map.chapters
        ]

        # Extract character names
        character_names = []
        if character_map:
            for char in character_map.characters:
                character_names.append(char.canonical_name)
                character_names.extend(char.aliases)

        # Hash for checkpoint validation
        text_hash = hashlib.md5(full_text.encode()).hexdigest()

        # Initialize or validate checkpoint
        if resume_from:
            if resume_from.text_hash != text_hash:
                logger.warning("Text hash mismatch - starting fresh")
                checkpoint = PronunciationPipelineCheckpoint.create_new(source_file, text_hash)
            else:
                checkpoint = resume_from
                logger.info(f"Resuming from stage: {checkpoint.stage}")
        else:
            checkpoint = PronunciationPipelineCheckpoint.create_new(source_file, text_hash)

        # Stage 1: Proposal
        if checkpoint.stage == "proposal":
            logger.info("Stage 1: Generating pronunciation proposals")
            checkpoint = self._run_proposal(
                full_text, chapter_boundaries, character_names, checkpoint
            )
            self._save_checkpoint(checkpoint)

        # Stage 2: Enrichment
        if checkpoint.stage == "enrichment":
            logger.info("Stage 2: Enriching with LLM pronunciations")
            checkpoint = self._run_enrichment(checkpoint)
            self._save_checkpoint(checkpoint)

        # Stage 3: Consolidation
        if checkpoint.stage == "consolidation":
            logger.info("Stage 3: Consolidating into final map")
            checkpoint = self._run_consolidation(checkpoint, character_names)
            self._save_checkpoint(checkpoint)

        return checkpoint.pronunciation_map, checkpoint

    def _run_proposal(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: list[str],
        checkpoint: PronunciationPipelineCheckpoint,
    ) -> PronunciationPipelineCheckpoint:
        """Run all proposers to identify words needing attention."""
        all_proposals = []
        total_proposers = len(self.proposers)

        # Build word index if enabled (single pass)
        word_index = None
        if self.word_index_enabled:
            logger.info("Building word index (single pass)...")
            word_index = WordIndex(full_text, chapter_boundaries)
            logger.info(
                f"Word index built: {word_index.get_unique_word_count()} unique words, "
                f"{word_index.get_total_word_count()} total occurrences"
            )

        for i, proposer in enumerate(self.proposers):
            self._report_progress("proposal", i + 1, total_proposers)

            try:
                proposals = proposer.propose(
                    full_text, chapter_boundaries, character_names,
                    word_index=word_index
                )
                all_proposals.extend(proposals)
                logger.info(f"{proposer.name} proposer: {len(proposals)} proposals")

            except Exception as e:
                logger.error(f"Proposer {proposer.name} failed: {e}")
                checkpoint.errors.append(f"Proposer {proposer.name}: {str(e)}")

        logger.info(f"Total proposals: {len(all_proposals)}")

        checkpoint.proposals = all_proposals
        checkpoint.stage = "enrichment"
        checkpoint.timestamp = datetime.now().isoformat()

        return checkpoint

    def _run_enrichment(
        self,
        checkpoint: PronunciationPipelineCheckpoint,
    ) -> PronunciationPipelineCheckpoint:
        """Enrich proposals with IPA and phonetic spellings."""
        if not self.enricher:
            logger.info("No LLM client - skipping enrichment")
            checkpoint.enrichments = {}
            checkpoint.stage = "consolidation"
            return checkpoint

        if not checkpoint.proposals:
            checkpoint.enrichments = {}
            checkpoint.stage = "consolidation"
            return checkpoint

        # Get unique words not yet enriched
        unique_proposals = {}
        for proposal in checkpoint.proposals:
            word_lower = proposal.word.lower()
            if word_lower not in unique_proposals and word_lower not in checkpoint.enriched_words:
                # Skip homographs - handle separately
                if proposal.flag_reason == PronunciationFlag.HOMOGRAPH:
                    continue
                unique_proposals[word_lower] = proposal

        # Handle homographs separately
        enrichments = checkpoint.enrichments or {}
        for proposal in checkpoint.proposals:
            if proposal.flag_reason == PronunciationFlag.HOMOGRAPH:
                word_lower = proposal.word.lower()
                if word_lower not in enrichments:
                    enrichments[word_lower] = self.enricher.enrich_homograph(proposal)
                    checkpoint.enriched_words.append(word_lower)

        # Batch enrichment for non-homographs
        proposals_list = list(unique_proposals.values())

        if self.parallel_enrichment:
            # Use parallel enrichment for faster processing
            logger.info(f"Using parallel enrichment for {len(proposals_list)} words")

            def parallel_progress_callback(completed: int, total: int):
                self._report_progress("enrichment", completed, total)

            try:
                batch_enrichments = self.enricher.enrich_parallel(
                    proposals_list,
                    progress_callback=parallel_progress_callback,
                )
                enrichments.update(batch_enrichments)
                checkpoint.enriched_words.extend([p.word.lower() for p in proposals_list])
            except Exception as e:
                logger.error(f"Parallel enrichment failed: {e}")
                checkpoint.warnings.append(f"Parallel enrichment failed: {str(e)}")
        else:
            # Sequential batch enrichment (fallback)
            total_batches = (len(proposals_list) + self.enricher.batch_size - 1) // self.enricher.batch_size

            for i in range(0, len(proposals_list), self.enricher.batch_size):
                batch_num = i // self.enricher.batch_size + 1
                self._report_progress("enrichment", batch_num, total_batches)

                batch = proposals_list[i:i + self.enricher.batch_size]

                try:
                    batch_enrichments = self.enricher.enrich_batch(batch)
                    enrichments.update(batch_enrichments)
                    checkpoint.enriched_words.extend([p.word.lower() for p in batch])

                    # Save progress periodically
                    if batch_num % 5 == 0:
                        checkpoint.enrichments = enrichments
                        self._save_checkpoint(checkpoint)

                except Exception as e:
                    logger.error(f"Enrichment batch {batch_num} failed: {e}")
                    checkpoint.warnings.append(f"Enrichment batch {batch_num}: {str(e)}")

        checkpoint.enrichments = enrichments
        checkpoint.stage = "consolidation"
        checkpoint.timestamp = datetime.now().isoformat()

        logger.info(f"Enriched {len(enrichments)} words")

        return checkpoint

    def _run_consolidation(
        self,
        checkpoint: PronunciationPipelineCheckpoint,
        character_names: list[str],
    ) -> PronunciationPipelineCheckpoint:
        """Consolidate proposals into final pronunciation map."""
        self._report_progress("consolidation", 1, 1)

        pronunciation_map = self.consolidator.consolidate(
            proposals=checkpoint.proposals or [],
            enrichments=checkpoint.enrichments or {},
            character_names=character_names,
        )

        pronunciation_map.pipeline_metadata = {
            "source_file": checkpoint.source_file,
            "generated_at": datetime.now().isoformat(),
            "proposers_used": [p.name for p in self.proposers],
            "llm_enrichment": self.enricher is not None,
        }

        checkpoint.pronunciation_map = pronunciation_map
        checkpoint.stage = "complete"
        checkpoint.timestamp = datetime.now().isoformat()

        logger.info(
            f"Consolidation complete: {len(pronunciation_map.entries)} entries, "
            f"{len(pronunciation_map.low_confidence_entries)} low confidence"
        )

        return checkpoint

    def _save_checkpoint(self, checkpoint: PronunciationPipelineCheckpoint) -> None:
        """Save checkpoint to disk if checkpoint_dir is configured."""
        if not self.checkpoint_dir:
            return

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(checkpoint.source_file).stem
        checkpoint_file = self.checkpoint_dir / f"pronunciation_{safe_name}.json"

        try:
            checkpoint.save(checkpoint_file)
            logger.debug(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is configured."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)


def generate_pronunciation_guide(
    full_text: str,
    chapter_map: ChapterDetectionMap,
    llm_client: Optional[LLMClient] = None,
    character_map: Optional[CharacterExtractionMap] = None,
    checkpoint_dir: Optional[Path] = None,
    source_file: str = "unknown",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> PronunciationMap:
    """
    Convenience function for pronunciation guide generation.

    Args:
        full_text: Complete document text
        chapter_map: Chapter boundaries from chapter detection
        llm_client: Optional LLM client for enrichment
        character_map: Optional character data for prioritization
        checkpoint_dir: Optional directory for checkpoints
        source_file: Source file name
        progress_callback: Optional progress callback

    Returns:
        PronunciationMap with all pronunciation entries
    """
    pipeline = PronunciationGuidePipeline(
        llm_client=llm_client,
        checkpoint_dir=checkpoint_dir,
        progress_callback=progress_callback,
    )

    pronunciation_map, _ = pipeline.run(
        full_text=full_text,
        chapter_map=chapter_map,
        character_map=character_map,
        source_file=source_file,
    )

    return pronunciation_map
