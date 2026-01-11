"""
Character extraction pipeline orchestrator.

Coordinates the full character extraction workflow with checkpointing.
"""

import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import logging

from .models import (
    CharacterProposal,
    CharacterValidationResult,
    CharacterMap,
    CharacterPipelineCheckpoint,
)
from .proposers import BaseCharacterProposer, NERProposer, LLMCharacterProposer
from .validator import CharacterValidator
from .consensus import CharacterConsensusBuilder
from ..chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


class CharacterExtractionPipeline:
    """
    Orchestrates the full character extraction workflow.

    Stages:
    1. Extraction: Run proposers on each chapter
    2. Validation: Validate each proposal
    3. Consensus: Merge across chapters, resolve aliases

    Supports checkpointing to save/resume progress.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        proposers: Optional[list[BaseCharacterProposer]] = None,
        validator: Optional[CharacterValidator] = None,
        consensus_builder: Optional[CharacterConsensusBuilder] = None,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """
        Args:
            llm_client: LLM client for LLM-based extraction and validation
            proposers: List of character proposers (default: NER + LLM if client provided)
            validator: Character validator instance
            consensus_builder: Consensus builder instance
            checkpoint_dir: Directory for saving checkpoints
            progress_callback: Callback(stage, current, total) for progress updates
        """
        self.llm = llm_client
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback

        # Set up proposers
        if proposers is not None:
            self.proposers = proposers
        else:
            self.proposers = [NERProposer()]
            if llm_client:
                self.proposers.append(LLMCharacterProposer(llm_client))

        # Set up validator
        self.validator = validator or CharacterValidator(
            llm_client=llm_client,
            use_llm_validation=llm_client is not None,
        )

        # Set up consensus builder
        self.consensus_builder = consensus_builder or CharacterConsensusBuilder(
            llm_client=llm_client,
            use_llm_alias_resolution=llm_client is not None,
        )

    def run(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        source_file: str = "unknown",
        resume_from: Optional[CharacterPipelineCheckpoint] = None,
    ) -> tuple[CharacterMap, CharacterPipelineCheckpoint]:
        """
        Run the full character extraction pipeline.

        Args:
            full_text: The complete document text
            chapter_map: Chapter boundaries from chapter detection
            source_file: Source file name for checkpointing
            resume_from: Optional checkpoint to resume from

        Returns:
            Tuple of (CharacterMap, final checkpoint)
        """
        # Calculate text hash for checkpoint validation
        text_hash = hashlib.md5(full_text.encode()).hexdigest()

        # Initialize or validate checkpoint
        if resume_from:
            if resume_from.text_hash != text_hash:
                logger.warning("Text hash mismatch - starting fresh")
                checkpoint = CharacterPipelineCheckpoint.create_new(source_file, text_hash)
            else:
                checkpoint = resume_from
                logger.info(f"Resuming from stage: {checkpoint.stage}")
        else:
            checkpoint = CharacterPipelineCheckpoint.create_new(source_file, text_hash)

        # Stage 1: Extraction
        if checkpoint.stage == "extraction":
            logger.info("Stage 1: Character extraction from chapters")
            checkpoint = self._run_extraction(full_text, chapter_map, checkpoint)
            self._save_checkpoint(checkpoint)

        # Stage 2: Validation
        if checkpoint.stage == "validation":
            logger.info("Stage 2: Validating character proposals")
            checkpoint = self._run_validation(checkpoint)
            self._save_checkpoint(checkpoint)

        # Stage 3: Consensus
        if checkpoint.stage == "consensus":
            logger.info("Stage 3: Building cross-chapter consensus")
            checkpoint = self._run_consensus(checkpoint, len(chapter_map.chapters))
            self._save_checkpoint(checkpoint)

        return checkpoint.character_map, checkpoint

    def _run_extraction(
        self,
        full_text: str,
        chapter_map: ChapterDetectionMap,
        checkpoint: CharacterPipelineCheckpoint,
    ) -> CharacterPipelineCheckpoint:
        """Run character extraction on all chapters."""
        chapter_proposals = {}
        total_chapters = len(chapter_map.chapters)

        for i, chapter in enumerate(chapter_map.chapters):
            chapter_idx = chapter.index
            self._report_progress("extraction", i + 1, total_chapters)

            # Extract chapter text
            start = chapter.start_position
            end = chapter.end_position
            chapter_text = full_text[start:end]

            # Run all proposers
            proposals = []
            for proposer in self.proposers:
                try:
                    prop_results = proposer.propose(
                        chapter_text=chapter_text,
                        chapter_index=chapter_idx,
                        chapter_start_position=start,
                    )
                    proposals.extend(prop_results)
                    logger.debug(
                        f"  {proposer.name}: found {len(prop_results)} proposals "
                        f"in chapter {chapter_idx}"
                    )
                except Exception as e:
                    logger.error(f"Proposer {proposer.name} failed on chapter {chapter_idx}: {e}")
                    checkpoint.errors.append(
                        f"Proposer {proposer.name} failed on chapter {chapter_idx}: {str(e)}"
                    )
                    # Re-raise to fail fast instead of continuing with errors
                    raise

            chapter_proposals[chapter_idx] = proposals
            logger.info(
                f"Chapter {chapter_idx}: {len(proposals)} total proposals from "
                f"{len(self.proposers)} proposers"
            )

        checkpoint.chapter_proposals = chapter_proposals
        checkpoint.stage = "validation"
        checkpoint.timestamp = datetime.now().isoformat()

        return checkpoint

    def _run_validation(
        self,
        checkpoint: CharacterPipelineCheckpoint,
    ) -> CharacterPipelineCheckpoint:
        """Validate all character proposals."""
        if not checkpoint.chapter_proposals:
            checkpoint.warnings.append("No chapter proposals to validate")
            checkpoint.validations = []
            checkpoint.stage = "consensus"
            return checkpoint

        # Flatten all proposals
        all_proposals = []
        for chapter_idx, proposals in checkpoint.chapter_proposals.items():
            all_proposals.extend(proposals)

        # Deduplicate proposals by normalized name before validation
        # This significantly reduces redundant LLM calls when multiple proposers
        # suggest the same character or when a character appears in multiple chapters
        unique_proposals = {}
        for proposal in all_proposals:
            # Normalize name for deduplication (lowercase, strip whitespace)
            norm_name = proposal.name.lower().strip()
            if norm_name not in unique_proposals:
                unique_proposals[norm_name] = proposal
            # Keep the first occurrence of each unique normalized name

        deduplicated_proposals = list(unique_proposals.values())
        total_proposals = len(deduplicated_proposals)
        original_count = len(all_proposals)
        logger.info(f"Deduplicated {original_count} proposals to {total_proposals} unique names (saved {original_count - total_proposals} validations)")

        # Validate unique proposals with caching
        validation_cache = {}
        validations = []

        for i, proposal in enumerate(deduplicated_proposals):
            self._report_progress("validation", i + 1, total_proposals)

            norm_name = proposal.name.lower().strip()

            # Check cache first
            if norm_name in validation_cache:
                # Reuse cached validation result
                validations.append(validation_cache[norm_name])
                continue

            try:
                result = self.validator.validate(proposal)
                validation_cache[norm_name] = result
                validations.append(result)
            except Exception as e:
                logger.error(f"Validation failed for '{proposal.name}': {e}")
                checkpoint.errors.append(f"Validation failed for '{proposal.name}': {str(e)}")
                # Re-raise to fail fast instead of continuing with errors
                raise

        valid_count = sum(1 for v in validations if v.is_valid)
        logger.info(f"Validation complete: {valid_count}/{total_proposals} valid")

        checkpoint.validations = validations
        checkpoint.stage = "consensus"
        checkpoint.timestamp = datetime.now().isoformat()

        return checkpoint

    def _run_consensus(
        self,
        checkpoint: CharacterPipelineCheckpoint,
        total_chapters: int,
    ) -> CharacterPipelineCheckpoint:
        """Build consensus across all chapters."""
        if not checkpoint.validations:
            checkpoint.character_map = CharacterMap(
                characters=[],
                low_confidence_characters=[],
                total_mentions=0,
                total_chapters=total_chapters,
                pipeline_metadata={"warning": "No validations to build consensus from"},
            )
            checkpoint.stage = "complete"
            return checkpoint

        self._report_progress("consensus", 1, 1)

        try:
            character_map = self.consensus_builder.build_consensus(
                validations=checkpoint.validations,
                total_chapters=total_chapters,
            )
            checkpoint.character_map = character_map
            logger.info(
                f"Consensus complete: {len(character_map.characters)} characters, "
                f"{len(character_map.low_confidence_characters)} low-confidence"
            )
        except Exception as e:
            logger.error(f"Consensus building failed: {e}")
            checkpoint.errors.append(f"Consensus building failed: {str(e)}")
            # Re-raise to fail fast instead of returning empty character map
            raise

        checkpoint.stage = "complete"
        checkpoint.timestamp = datetime.now().isoformat()

        return checkpoint

    def _save_checkpoint(self, checkpoint: CharacterPipelineCheckpoint) -> None:
        """Save checkpoint to disk if checkpoint_dir is configured."""
        if not self.checkpoint_dir:
            return

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Use source file name for checkpoint file
        safe_name = Path(checkpoint.source_file).stem
        checkpoint_file = self.checkpoint_dir / f"characters_{safe_name}.json"

        try:
            checkpoint.save(checkpoint_file)
            logger.debug(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is configured."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)


def extract_characters(
    full_text: str,
    chapter_map: ChapterDetectionMap,
    llm_client: Optional[LLMClient] = None,
    checkpoint_dir: Optional[Path] = None,
    source_file: str = "unknown",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> CharacterMap:
    """
    Convenience function for character extraction.

    Args:
        full_text: Complete document text
        chapter_map: Chapter boundaries from chapter detection
        llm_client: Optional LLM client
        checkpoint_dir: Optional directory for checkpoints
        source_file: Source file name
        progress_callback: Optional progress callback

    Returns:
        CharacterMap with extracted characters
    """
    pipeline = CharacterExtractionPipeline(
        llm_client=llm_client,
        checkpoint_dir=checkpoint_dir,
        progress_callback=progress_callback,
    )

    character_map, _ = pipeline.run(
        full_text=full_text,
        chapter_map=chapter_map,
        source_file=source_file,
    )

    return character_map
