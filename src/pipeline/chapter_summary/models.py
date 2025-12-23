"""
Data models for chapter summary pipeline.

These models represent chapter summaries with tone, characters, and metadata
useful for audiobook narration preparation.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime
import json
from pathlib import Path


ToneType = Literal[
    "tense", "suspenseful", "action", "romantic", "comedic", "somber",
    "reflective", "dramatic", "peaceful", "mysterious", "hopeful", "dark"
]

DialogueDensity = Literal["high", "medium", "low"]


@dataclass
class ChapterSummary:
    """Summary of a single chapter for audiobook narration."""
    chapter_index: int
    chapter_title: Optional[str]

    # Core summary
    summary: str                    # 3-5 sentence summary
    key_events: list[str]           # Bullet points of main events

    # Narration-relevant metadata
    primary_tone: ToneType          # Dominant emotional tone
    secondary_tones: list[ToneType] # Other tones present
    dialogue_density: DialogueDensity  # How much dialogue vs narrative

    # Character information
    characters_present: list[str]   # Character names appearing in chapter
    pov_character: Optional[str]    # Point-of-view character if applicable

    # Technical info
    word_count: int
    estimated_duration_minutes: float  # Based on ~150 wpm narration

    # Generation metadata
    confidence: float

    def to_dict(self) -> dict:
        return {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "summary": self.summary,
            "key_events": self.key_events,
            "primary_tone": self.primary_tone,
            "secondary_tones": self.secondary_tones,
            "dialogue_density": self.dialogue_density,
            "characters_present": self.characters_present,
            "pov_character": self.pov_character,
            "word_count": self.word_count,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterSummary":
        return cls(**data)


@dataclass
class ChapterSummaryMap:
    """Collection of all chapter summaries for a document."""
    summaries: list[ChapterSummary]
    total_chapters: int
    total_word_count: int
    total_duration_minutes: float

    # Document-level analysis
    overall_tones: dict[str, int]   # Tone -> count of chapters with that tone
    character_appearances: dict[str, list[int]]  # Character -> chapters they appear in

    pipeline_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "summaries": [s.to_dict() for s in self.summaries],
            "total_chapters": self.total_chapters,
            "total_word_count": self.total_word_count,
            "total_duration_minutes": self.total_duration_minutes,
            "overall_tones": self.overall_tones,
            "character_appearances": self.character_appearances,
            "pipeline_metadata": self.pipeline_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterSummaryMap":
        return cls(
            summaries=[ChapterSummary.from_dict(s) for s in data["summaries"]],
            total_chapters=data["total_chapters"],
            total_word_count=data["total_word_count"],
            total_duration_minutes=data["total_duration_minutes"],
            overall_tones=data["overall_tones"],
            character_appearances=data["character_appearances"],
            pipeline_metadata=data.get("pipeline_metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save summary map to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ChapterSummaryMap":
        """Load summary map from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    def summary(self) -> str:
        """Human-readable summary of the chapter summaries."""
        lines = [
            f"Total Chapters: {self.total_chapters}",
            f"Total Words: {self.total_word_count:,}",
            f"Estimated Duration: {self.total_duration_minutes:.0f} minutes ({self.total_duration_minutes / 60:.1f} hours)",
            "",
            "Tone Distribution:",
        ]

        # Sort tones by frequency
        sorted_tones = sorted(self.overall_tones.items(), key=lambda x: x[1], reverse=True)
        for tone, count in sorted_tones[:5]:
            lines.append(f"  {tone}: {count} chapters")

        lines.append("")
        lines.append("Chapter Summaries:")

        for s in self.summaries[:10]:  # First 10
            title = s.chapter_title or "(untitled)"
            lines.append(f"  Ch.{s.chapter_index}: {title} [{s.primary_tone}]")
            lines.append(f"    {s.summary[:100]}...")

        if len(self.summaries) > 10:
            lines.append(f"  ... and {len(self.summaries) - 10} more chapters")

        return "\n".join(lines)


@dataclass
class ChunkSummary:
    """Intermediate summary of a text chunk (for long chapters)."""
    chunk_index: int
    summary: str
    key_events: list[str]
    characters_mentioned: list[str]
    tone: ToneType
    word_count: int

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "summary": self.summary,
            "key_events": self.key_events,
            "characters_mentioned": self.characters_mentioned,
            "tone": self.tone,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChunkSummary":
        return cls(**data)


@dataclass
class SummaryPipelineCheckpoint:
    """Checkpoint for saving/resuming summary pipeline state."""
    stage: Literal["summarization", "consolidation", "complete"]
    timestamp: str
    source_file: str
    text_hash: str

    # Stage outputs
    chunk_summaries: Optional[dict[int, list[ChunkSummary]]] = None  # chapter_idx -> chunks
    chapter_summaries: Optional[list[ChapterSummary]] = None
    summary_map: Optional[ChapterSummaryMap] = None

    # Progress tracking
    completed_chapters: list[int] = field(default_factory=list)

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        chunk_dict = None
        if self.chunk_summaries:
            chunk_dict = {
                str(k): [c.to_dict() for c in v]
                for k, v in self.chunk_summaries.items()
            }

        return {
            "stage": self.stage,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "text_hash": self.text_hash,
            "chunk_summaries": chunk_dict,
            "chapter_summaries": [s.to_dict() for s in self.chapter_summaries] if self.chapter_summaries else None,
            "summary_map": self.summary_map.to_dict() if self.summary_map else None,
            "completed_chapters": self.completed_chapters,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryPipelineCheckpoint":
        chunk_summaries = None
        if data.get("chunk_summaries"):
            chunk_summaries = {
                int(k): [ChunkSummary.from_dict(c) for c in v]
                for k, v in data["chunk_summaries"].items()
            }

        return cls(
            stage=data["stage"],
            timestamp=data["timestamp"],
            source_file=data["source_file"],
            text_hash=data["text_hash"],
            chunk_summaries=chunk_summaries,
            chapter_summaries=[ChapterSummary.from_dict(s) for s in data["chapter_summaries"]] if data.get("chapter_summaries") else None,
            summary_map=ChapterSummaryMap.from_dict(data["summary_map"]) if data.get("summary_map") else None,
            completed_chapters=data.get("completed_chapters", []),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

    def save(self, path: Path) -> None:
        """Save checkpoint to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SummaryPipelineCheckpoint":
        """Load checkpoint from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    @staticmethod
    def create_new(source_file: str, text_hash: str) -> "SummaryPipelineCheckpoint":
        """Create a new checkpoint for starting a pipeline run."""
        return SummaryPipelineCheckpoint(
            stage="summarization",
            timestamp=datetime.now().isoformat(),
            source_file=source_file,
            text_hash=text_hash,
        )
