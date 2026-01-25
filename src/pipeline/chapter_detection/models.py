"""
Data models for chapter detection pipeline.

These models represent the flow of data through the propose -> validate -> reconcile pipeline.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional


@dataclass
class TOCEntry:
    """An entry from the Table of Contents."""

    title: str  # Chapter title as it appears in TOC
    position_in_toc: int  # Character position of this entry in TOC
    page_number: Optional[int] = None  # If present in TOC
    level: int = 1  # Nesting level (1=chapter, 2=section, etc.)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "position_in_toc": self.position_in_toc,
            "page_number": self.page_number,
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TOCEntry":
        return cls(**data)


@dataclass
class TableOfContents:
    """Extracted Table of Contents - serves as ground truth when present."""

    entries: list[TOCEntry]
    toc_start_position: int
    toc_end_position: int
    confidence: float  # How confident we are this is actually a TOC

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "toc_start_position": self.toc_start_position,
            "toc_end_position": self.toc_end_position,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TableOfContents":
        return cls(
            entries=[TOCEntry.from_dict(e) for e in data["entries"]],
            toc_start_position=data["toc_start_position"],
            toc_end_position=data["toc_end_position"],
            confidence=data["confidence"],
        )


@dataclass
class DocumentProfile:
    """Understanding of document structure before chapter detection."""

    document_type: Literal["novel", "anthology", "memoir", "epistolary", "technical", "unknown"]
    has_explicit_markers: bool  # "Chapter 1", "Part Two", etc.
    table_of_contents: Optional[TableOfContents]  # Extracted TOC if present
    estimated_chapter_count: Optional[int]
    structural_conventions: list[
        str
    ]  # e.g., ["roman_numerals", "part_divisions", "named_chapters"]
    front_matter_end: int  # Position where actual content begins (after title page, TOC, etc.)
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Why we classified it this way

    @property
    def has_table_of_contents(self) -> bool:
        return self.table_of_contents is not None and len(self.table_of_contents.entries) > 0

    def to_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "has_explicit_markers": self.has_explicit_markers,
            "table_of_contents": (
                self.table_of_contents.to_dict() if self.table_of_contents else None
            ),
            "estimated_chapter_count": self.estimated_chapter_count,
            "structural_conventions": self.structural_conventions,
            "front_matter_end": self.front_matter_end,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentProfile":
        toc_data = data.get("table_of_contents")
        return cls(
            document_type=data["document_type"],
            has_explicit_markers=data["has_explicit_markers"],
            table_of_contents=TableOfContents.from_dict(toc_data) if toc_data else None,
            estimated_chapter_count=data["estimated_chapter_count"],
            structural_conventions=data["structural_conventions"],
            front_matter_end=data["front_matter_end"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
        )


@dataclass
class ChapterProposal:
    """A proposed chapter boundary from one strategy."""

    strategy: str  # "regex", "llm_marker", "llm_narrative", "toc_match"
    position: int  # Character offset in document
    title: Optional[str]  # "Chapter 1", "The Beginning", etc.
    evidence: str  # The actual text that triggered this proposal
    confidence: float  # Strategy's self-assessed confidence (0.0 - 1.0)
    reasoning: Optional[str] = None  # Why this was proposed
    toc_match: Optional[str] = None  # If this matches a TOC entry, which one
    # F10: Explicit hard boundaries dominate over soft signals
    is_hard_boundary: bool = False  # True for explicit markers (Chapter N, centered Roman numerals)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "position": self.position,
            "title": self.title,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "toc_match": self.toc_match,
            "is_hard_boundary": self.is_hard_boundary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterProposal":
        return cls(**data)


@dataclass
class ValidationResult:
    """Result of validating a proposal."""

    proposal: ChapterProposal
    ending_score: float  # How much does preceding text feel like an ending? (0-1)
    beginning_score: float  # How much does following text feel like a beginning? (0-1)
    title_validity: float  # Is this actually a chapter title? (0-1)
    toc_match_score: float  # Does this match a TOC entry? (0-1, 0 if no TOC)
    overall_score: float  # Combined validation score
    is_valid: bool  # Above threshold?
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "proposal": self.proposal.to_dict(),
            "ending_score": self.ending_score,
            "beginning_score": self.beginning_score,
            "title_validity": self.title_validity,
            "toc_match_score": self.toc_match_score,
            "overall_score": self.overall_score,
            "is_valid": self.is_valid,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        return cls(
            proposal=ChapterProposal.from_dict(data["proposal"]),
            ending_score=data["ending_score"],
            beginning_score=data["beginning_score"],
            title_validity=data["title_validity"],
            toc_match_score=data.get("toc_match_score", 0.0),
            overall_score=data["overall_score"],
            is_valid=data["is_valid"],
            reasoning=data["reasoning"],
        )


@dataclass
class ChapterBoundary:
    """A validated chapter boundary with consensus information."""

    position: int
    title: Optional[str]
    confidence: float
    supporting_strategies: list[str]  # Which proposers agreed
    validation_score: float
    evidence: str  # The text at this boundary
    toc_validated: bool  # Was this validated against TOC?

    def to_dict(self) -> dict:
        return {
            "position": self.position,
            "title": self.title,
            "confidence": self.confidence,
            "supporting_strategies": self.supporting_strategies,
            "validation_score": self.validation_score,
            "evidence": self.evidence,
            "toc_validated": self.toc_validated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterBoundary":
        return cls(**data)


@dataclass
class Chapter:
    """A single chapter with boundaries and metadata."""

    index: int
    title: Optional[str]
    start_position: int
    end_position: int
    word_count: int
    confidence: float
    toc_validated: bool = False  # Was this chapter validated against TOC?

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "word_count": self.word_count,
            "confidence": self.confidence,
            "toc_validated": self.toc_validated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        return cls(**data)


@dataclass
class ChapterMap:
    """Final output: validated chapter structure."""

    chapters: list[Chapter]
    low_confidence_boundaries: list[ChapterBoundary]  # Flagged for review
    document_profile: DocumentProfile
    total_word_count: int
    toc_agreement_score: float  # How well do our chapters match TOC? (0-1, or -1 if no TOC)
    pipeline_metadata: dict = field(default_factory=dict)  # Timing, proposal counts, etc.

    def to_dict(self) -> dict:
        return {
            "chapters": [ch.to_dict() for ch in self.chapters],
            "low_confidence_boundaries": [b.to_dict() for b in self.low_confidence_boundaries],
            "document_profile": self.document_profile.to_dict(),
            "total_word_count": self.total_word_count,
            "toc_agreement_score": self.toc_agreement_score,
            "pipeline_metadata": self.pipeline_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterMap":
        return cls(
            chapters=[Chapter.from_dict(ch) for ch in data["chapters"]],
            low_confidence_boundaries=[
                ChapterBoundary.from_dict(b) for b in data["low_confidence_boundaries"]
            ],
            document_profile=DocumentProfile.from_dict(data["document_profile"]),
            total_word_count=data["total_word_count"],
            toc_agreement_score=data.get("toc_agreement_score", -1.0),
            pipeline_metadata=data.get("pipeline_metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save chapter map to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ChapterMap":
        """Load chapter map from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    def summary(self) -> str:
        """Human-readable summary of the chapter map."""
        lines = [
            f"Document Type: {self.document_profile.document_type}",
            f"Total Chapters: {len(self.chapters)}",
            f"Total Words: {self.total_word_count:,}",
        ]
        if self.toc_agreement_score >= 0:
            lines.append(f"TOC Agreement: {self.toc_agreement_score:.1%}")
        if self.low_confidence_boundaries:
            lines.append(
                f"Low Confidence Boundaries: {len(self.low_confidence_boundaries)} (need review)"
            )
        lines.append("")
        lines.append("Chapters:")
        for ch in self.chapters:
            conf = "TOC" if ch.toc_validated else f"{ch.confidence:.0%}"
            title = ch.title or "(untitled)"
            lines.append(f"  {ch.index}. {title} - {ch.word_count:,} words [{conf}]")
        return "\n".join(lines)


@dataclass
class PipelineCheckpoint:
    """Checkpoint for saving/resuming pipeline state."""

    stage: Literal["profiling", "proposals", "validation", "consensus", "complete"]
    timestamp: str
    source_file: str
    text_hash: str  # To verify we're resuming with same document

    # Stage outputs (populated as pipeline progresses)
    document_profile: Optional[DocumentProfile] = None
    proposals: Optional[list[ChapterProposal]] = None
    validations: Optional[list[ValidationResult]] = None
    chapter_map: Optional[ChapterMap] = None

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "text_hash": self.text_hash,
            "document_profile": self.document_profile.to_dict() if self.document_profile else None,
            "proposals": [p.to_dict() for p in self.proposals] if self.proposals else None,
            "validations": [v.to_dict() for v in self.validations] if self.validations else None,
            "chapter_map": self.chapter_map.to_dict() if self.chapter_map else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineCheckpoint":
        return cls(
            stage=data["stage"],
            timestamp=data["timestamp"],
            source_file=data["source_file"],
            text_hash=data["text_hash"],
            document_profile=(
                DocumentProfile.from_dict(data["document_profile"])
                if data.get("document_profile")
                else None
            ),
            proposals=(
                [ChapterProposal.from_dict(p) for p in data["proposals"]]
                if data.get("proposals")
                else None
            ),
            validations=(
                [ValidationResult.from_dict(v) for v in data["validations"]]
                if data.get("validations")
                else None
            ),
            chapter_map=(
                ChapterMap.from_dict(data["chapter_map"]) if data.get("chapter_map") else None
            ),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

    def save(self, path: Path) -> None:
        """Save checkpoint to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "PipelineCheckpoint":
        """Load checkpoint from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    @staticmethod
    def create_new(source_file: str, text_hash: str) -> "PipelineCheckpoint":
        """Create a new checkpoint for starting a pipeline run."""
        return PipelineCheckpoint(
            stage="profiling",
            timestamp=datetime.now().isoformat(),
            source_file=source_file,
            text_hash=text_hash,
        )
