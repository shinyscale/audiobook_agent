"""
Chapter Detection Pipeline Orchestrator.

Coordinates the multi-stage pipeline:
1. Document Profiling (+ TOC extraction)
2. Proposal Generation (multiple strategies)
3. Proposal Validation
4. Consensus Building

Supports checkpointing for save/resume functionality.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import logging

from .models import (
    Chapter,
    ChapterMap,
    PipelineCheckpoint,
    ChapterProposal,
    ValidationResult,
    DocumentProfile,
)
from .profiler import DocumentProfiler
from .proposers import RegexProposer, LLMMarkerProposer, LLMNarrativeProposer
from .validator import ProposalValidator
from .consensus import ConsensusBuilder
from ..llm import LLMClient, LLMConfig, create_client

logger = logging.getLogger(__name__)


class ChapterDetectionPipeline:
    """
    Orchestrates the multi-agent chapter detection pipeline.

    Usage:
        # Basic usage
        pipeline = ChapterDetectionPipeline()
        result = pipeline.run(text, source_file="book.txt")

        # With LLM enhancement
        pipeline = ChapterDetectionPipeline.with_ollama("llama3.2")
        result = pipeline.run(text, source_file="book.txt")

        # Resume from checkpoint
        result = pipeline.run(text, source_file="book.txt", checkpoint_path="checkpoint.json")
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        llm_marker_chunk_size: int = 15000,
        llm_marker_chunk_overlap: int = 1000,
        llm_narrative_chunk_size: int = 20000,
        llm_narrative_chunk_overlap: int = 2000,
    ):
        """
        Args:
            llm_client: Optional LLM client for enhanced detection
            checkpoint_dir: Directory to save checkpoints
            progress_callback: Optional callback(stage_name, progress_percent)
        """
        self.llm = llm_client
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback

        # Initialize components
        self.profiler = DocumentProfiler(llm_client=llm_client)
        self.regex_proposer = RegexProposer()
        self.validator = ProposalValidator(llm_client=llm_client)
        self.consensus_builder = ConsensusBuilder(llm_client=llm_client)

        # LLM proposers (only if LLM available)
        if llm_client:
            self.llm_marker_proposer = LLMMarkerProposer(
                llm_client,
                chunk_size=llm_marker_chunk_size,
                chunk_overlap=llm_marker_chunk_overlap,
            )
            self.llm_narrative_proposer = LLMNarrativeProposer(
                llm_client,
                chunk_size=llm_narrative_chunk_size,
                chunk_overlap=llm_narrative_chunk_overlap,
            )
        else:
            self.llm_marker_proposer = None
            self.llm_narrative_proposer = None

    @classmethod
    def with_ollama(
        cls,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        **kwargs,
    ) -> "ChapterDetectionPipeline":
        """Create pipeline with Ollama LLM."""
        client = create_client("ollama", model=model, base_url=base_url)
        return cls(llm_client=client, **kwargs)

    @classmethod
    def with_openai(
        cls,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        **kwargs,
    ) -> "ChapterDetectionPipeline":
        """Create pipeline with OpenAI LLM."""
        client = create_client("openai", model=model, api_key=api_key)
        return cls(llm_client=client, **kwargs)

    @classmethod
    def with_anthropic(
        cls,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        **kwargs,
    ) -> "ChapterDetectionPipeline":
        """Create pipeline with Anthropic LLM."""
        client = create_client("anthropic", model=model, api_key=api_key)
        return cls(llm_client=client, **kwargs)

    @classmethod
    def deterministic_only(cls, **kwargs) -> "ChapterDetectionPipeline":
        """Create pipeline without LLM (regex-only, fast)."""
        return cls(llm_client=None, **kwargs)

    def run(
        self,
        text: str,
        source_file: str = "document",
        checkpoint_path: Optional[Path] = None,
        save_checkpoint: bool = True,
    ) -> ChapterMap:
        """
        Run the chapter detection pipeline.

        Args:
            text: Full document text
            source_file: Source file path (for checkpoint identification)
            checkpoint_path: Path to existing checkpoint to resume from
            save_checkpoint: Whether to save checkpoints after each stage

        Returns:
            ChapterMap with detected chapters
        """
        # Create or load checkpoint
        text_hash = self._hash_text(text)

        if checkpoint_path and checkpoint_path.exists():
            checkpoint = PipelineCheckpoint.load(checkpoint_path)

            # Verify same document
            if checkpoint.text_hash != text_hash:
                logger.warning("Checkpoint text hash mismatch - starting fresh")
                checkpoint = PipelineCheckpoint.create_new(source_file, text_hash)
        else:
            checkpoint = PipelineCheckpoint.create_new(source_file, text_hash)

        # Determine checkpoint save path
        if save_checkpoint and self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            save_path = self.checkpoint_dir / f"checkpoint_{Path(source_file).stem}.json"
        else:
            save_path = None

        # Run pipeline stages
        try:
            # Stage 1: Profiling
            if checkpoint.stage == "profiling" or checkpoint.document_profile is None:
                self._report_progress("Profiling document", 0.1)
                checkpoint.document_profile = self.profiler.profile(text)
                checkpoint.stage = "proposals"
                self._save_checkpoint(checkpoint, save_path)

            # Stage 2: Proposals
            if checkpoint.stage == "proposals" or checkpoint.proposals is None:
                self._report_progress("Generating proposals", 0.3)
                checkpoint.proposals = self._generate_proposals(text, checkpoint.document_profile)
                checkpoint.stage = "validation"
                self._save_checkpoint(checkpoint, save_path)

            # Stage 2.5: TOC-guided bypass
            # If all proposals are from TOC-guided and we found the expected count,
            # bypass validation/consensus for reliability
            if (
                checkpoint.proposals
                and all(p.strategy == "toc_guided" for p in checkpoint.proposals)
                and checkpoint.document_profile.table_of_contents
                and len(checkpoint.proposals) == len(checkpoint.document_profile.table_of_contents.entries)
            ):
                logger.info(
                    f"TOC-guided complete: {len(checkpoint.proposals)} chapters found - "
                    f"bypassing validation/consensus for reliability"
                )
                self._report_progress("Building chapter map from TOC", 0.9)
                checkpoint.chapter_map = self._build_chapter_map_from_toc(
                    checkpoint.proposals, text, checkpoint.document_profile
                )
                checkpoint.stage = "complete"
                self._save_checkpoint(checkpoint, save_path)

                self._report_progress("Complete", 1.0)

                checkpoint.chapter_map.pipeline_metadata.update({
                    "completed_at": datetime.now().isoformat(),
                    "llm_enabled": self.llm is not None,
                    "proposal_count": len(checkpoint.proposals),
                    "validation_count": 0,
                    "toc_guided_bypass": True,
                })

                return checkpoint.chapter_map

            # Stage 3: Validation
            if checkpoint.stage == "validation" or checkpoint.validations is None:
                self._report_progress("Validating proposals", 0.6)
                checkpoint.validations = self.validator.validate(
                    checkpoint.proposals, text, checkpoint.document_profile
                )
                checkpoint.stage = "consensus"
                self._save_checkpoint(checkpoint, save_path)

            # Stage 4: Consensus
            if checkpoint.stage == "consensus" or checkpoint.chapter_map is None:
                self._report_progress("Building consensus", 0.9)
                checkpoint.chapter_map = self.consensus_builder.build_consensus(
                    checkpoint.validations, text, checkpoint.document_profile
                )
                checkpoint.stage = "complete"
                self._save_checkpoint(checkpoint, save_path)

            self._report_progress("Complete", 1.0)

            # Add pipeline metadata
            checkpoint.chapter_map.pipeline_metadata.update({
                "completed_at": datetime.now().isoformat(),
                "llm_enabled": self.llm is not None,
                "proposal_count": len(checkpoint.proposals) if checkpoint.proposals else 0,
                "validation_count": len(checkpoint.validations) if checkpoint.validations else 0,
            })

            return checkpoint.chapter_map

        except Exception as e:
            checkpoint.errors.append(f"{checkpoint.stage}: {str(e)}")
            self._save_checkpoint(checkpoint, save_path)
            raise

    def _generate_proposals(
        self,
        text: str,
        profile: DocumentProfile,
    ) -> list[ChapterProposal]:
        """Generate proposals from all available strategies."""
        proposals = []

        # Try TOC-guided detection first (most reliable when TOC exists)
        if profile.table_of_contents and profile.table_of_contents.entries:
            logger.info("Running TOC-guided detection...")
            toc_proposals = self.regex_proposer.propose_from_toc(text, profile)
            expected_count = len(profile.table_of_contents.entries)

            if len(toc_proposals) == expected_count:
                # Found all expected chapters - use these exclusively
                logger.info(
                    f"TOC-guided: found all {expected_count} expected chapters, "
                    f"using TOC-guided proposals exclusively"
                )
                # Log proposal details for debugging
                for p in sorted(toc_proposals, key=lambda x: x.position):
                    logger.info(
                        f"  TOC-guided proposal: '{p.title}' at position {p.position} "
                        f"(hard_boundary={p.is_hard_boundary})"
                    )
                return toc_proposals
            elif len(toc_proposals) >= expected_count * 0.8:
                # Found most chapters (80%+) - use TOC-guided but fall through for extras
                logger.info(
                    f"TOC-guided: found {len(toc_proposals)}/{expected_count} chapters, "
                    f"using as primary proposals"
                )
                proposals.extend(toc_proposals)
            else:
                # TOC-guided didn't find enough - fall back to standard detection
                logger.info(
                    f"TOC-guided: found only {len(toc_proposals)}/{expected_count} chapters, "
                    f"falling back to standard detection"
                )

        # Always run regex proposer (unless we already have all TOC-guided proposals)
        if not proposals or len(proposals) < len(profile.table_of_contents.entries if profile.table_of_contents else []):
            logger.info("Running regex proposer...")
            regex_proposals = self.regex_proposer.propose(text, profile)
            proposals.extend(regex_proposals)
            logger.info(f"Regex proposer found {len(regex_proposals)} proposals")

        # Run LLM proposers if available
        if self.llm_marker_proposer:
            logger.info("Running LLM marker proposer...")
            try:
                marker_proposals = self.llm_marker_proposer.propose(text, profile)
                proposals.extend(marker_proposals)
                logger.info(f"LLM marker proposer found {len(marker_proposals)} proposals")
            except Exception as e:
                logger.warning(f"LLM marker proposer failed: {e}")

        if self.llm_narrative_proposer and not profile.has_explicit_markers:
            logger.info("Running LLM narrative proposer...")
            try:
                narrative_proposals = self.llm_narrative_proposer.propose(text, profile)
                proposals.extend(narrative_proposals)
                logger.info(f"LLM narrative proposer found {len(narrative_proposals)} proposals")
            except Exception as e:
                logger.warning(f"LLM narrative proposer failed: {e}")

        logger.info(f"Total proposals: {len(proposals)}")
        return proposals

    def _build_chapter_map_from_toc(
        self,
        proposals: list[ChapterProposal],
        text: str,
        profile: DocumentProfile,
    ) -> ChapterMap:
        """
        Build ChapterMap directly from TOC-guided proposals.

        This bypasses validation and consensus when TOC-guided detection
        found all expected chapters - providing maximum reliability.
        """
        # Sort proposals by position
        sorted_proposals = sorted(proposals, key=lambda p: p.position)

        chapters = []
        total_words = 0

        for i, proposal in enumerate(sorted_proposals):
            start = proposal.position

            # End is start of next chapter or end of text
            if i + 1 < len(sorted_proposals):
                end = sorted_proposals[i + 1].position
            else:
                end = len(text)

            # Count words
            chapter_text = text[start:end]
            word_count = len(chapter_text.split())
            total_words += word_count

            # Clean the title (remove redundant "Chapter X:" prefixes)
            cleaned_title = self._clean_chapter_title(proposal.title)

            chapters.append(Chapter(
                index=i + 1,
                title=cleaned_title,
                start_position=start,
                end_position=end,
                word_count=word_count,
                confidence=1.0,  # Maximum confidence for TOC-guided
                toc_validated=True,
            ))

        logger.info(f"Built ChapterMap from TOC: {len(chapters)} chapters, {total_words:,} words")

        return ChapterMap(
            chapters=chapters,
            low_confidence_boundaries=[],  # No low-confidence when TOC-guided
            document_profile=profile,
            total_word_count=total_words,
            toc_agreement_score=1.0,  # Perfect agreement - we used TOC
            pipeline_metadata={
                "toc_guided_bypass": True,
                "chapter_count": len(chapters),
            },
        )

    def _clean_chapter_title(self, title: Optional[str]) -> Optional[str]:
        """Clean chapter title by removing redundant 'Chapter X:' prefixes."""
        if not title:
            return None

        # Check if title is "Chapter" followed by standalone Roman numeral
        match = re.match(
            r'^(?:Chapter|CHAPTER)\s+([IVXLC]+)\s*$',
            title,
            re.IGNORECASE
        )
        if match:
            return match.group(1)

        # If title starts with "Chapter N:" extract just the subtitle
        match = re.match(
            r'^(?:Chapter|CHAPTER)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*[:\-—–]\s*(.+)$',
            title,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()

        # If title is JUST "Chapter N" with no subtitle, return None
        if re.match(r'^(?:Chapter|CHAPTER)\s+(?:\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*$', title, re.IGNORECASE):
            return None

        # Preserve standalone Roman numerals
        if re.match(r'^[IVXLC]+$', title.strip()):
            return title.strip()

        return title

    def _hash_text(self, text: str) -> str:
        """Create a hash of the text for checkpoint verification."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _save_checkpoint(self, checkpoint: PipelineCheckpoint, path: Optional[Path]) -> None:
        """Save checkpoint if path is provided."""
        if path:
            checkpoint.timestamp = datetime.now().isoformat()
            checkpoint.save(path)
            logger.debug(f"Checkpoint saved to {path}")

    def _report_progress(self, stage: str, progress: float) -> None:
        """Report progress via callback if available."""
        logger.info(f"Pipeline stage: {stage} ({progress:.0%})")
        if self.progress_callback:
            self.progress_callback(stage, progress)


def detect_chapters(
    text: str,
    source_file: str = "document",
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    checkpoint_dir: Optional[Path] = None,
) -> ChapterMap:
    """
    Convenience function to detect chapters in a document.

    Args:
        text: Full document text
        source_file: Source file path
        llm_provider: Optional LLM provider ("ollama", "openai", "anthropic")
        llm_model: Optional LLM model name
        checkpoint_dir: Optional directory for checkpoints

    Returns:
        ChapterMap with detected chapters
    """
    if llm_provider:
        llm_client = create_client(llm_provider, model=llm_model)
    else:
        llm_client = None

    pipeline = ChapterDetectionPipeline(
        llm_client=llm_client,
        checkpoint_dir=checkpoint_dir,
    )

    return pipeline.run(text, source_file=source_file)
