"""
Data models for pronunciation guide pipeline.

These models track words needing pronunciation attention for audiobook narrators.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal, Optional


class PronunciationFlag(str, Enum):
    """Why a word was flagged for pronunciation review."""

    PROPER_NOUN = "proper_noun"
    FOREIGN = "foreign"
    HOMOGRAPH = "homograph"
    UNKNOWN = "unknown"  # Not in CMU dictionary
    CHARACTER = "character"  # Character name from extraction


@dataclass
class PronunciationMention:
    """A single occurrence of a word in the text."""

    word_form: str  # Exact text found (preserves case)
    position: int  # Character offset in full document
    chapter_index: int  # Which chapter (1-indexed)
    context: str  # Surrounding text (~100 chars)

    def to_dict(self) -> dict:
        return {
            "word_form": self.word_form,
            "position": self.position,
            "chapter_index": self.chapter_index,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationMention":
        return cls(**data)


@dataclass
class PronunciationProposal:
    """A proposed word needing pronunciation attention."""

    strategy: str  # "cmu", "foreign", "homograph", "character"
    word: str  # Canonical form of the word
    flag_reason: PronunciationFlag
    mentions: list[PronunciationMention]
    confidence: float  # 0.0 - 1.0
    language_hint: Optional[str] = None  # e.g., "French", "German"
    homograph_options: Optional[list[str]] = None  # For homographs
    reasoning: Optional[str] = None

    @property
    def occurrence_count(self) -> int:
        return len(self.mentions)

    @property
    def chapters_present(self) -> list[int]:
        return sorted(set(m.chapter_index for m in self.mentions))

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "word": self.word,
            "flag_reason": self.flag_reason.value,
            "mentions": [m.to_dict() for m in self.mentions],
            "confidence": self.confidence,
            "language_hint": self.language_hint,
            "homograph_options": self.homograph_options,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationProposal":
        return cls(
            strategy=data["strategy"],
            word=data["word"],
            flag_reason=PronunciationFlag(data["flag_reason"]),
            mentions=[PronunciationMention.from_dict(m) for m in data["mentions"]],
            confidence=data["confidence"],
            language_hint=data.get("language_hint"),
            homograph_options=data.get("homograph_options"),
            reasoning=data.get("reasoning"),
        )


@dataclass
class PronunciationEnrichment:
    """Enrichment data for a pronunciation entry (from LLM)."""

    word: str
    ipa: Optional[str] = None  # IPA notation
    phonetic_spelling: Optional[str] = None  # Lay-person spelling
    notes: Optional[str] = None  # Context-sensitive notes
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "ipa": self.ipa,
            "phonetic_spelling": self.phonetic_spelling,
            "notes": self.notes,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationEnrichment":
        return cls(**data)


@dataclass
class PronunciationEntry:
    """Final pronunciation entry for narrator reference."""

    id: str
    word: str  # Canonical spelling
    flag_reason: PronunciationFlag
    occurrence_count: int
    first_position: int
    chapters_present: list[int]  # Chapters where word appears
    context_examples: list[str]  # Up to 3 context examples

    # Pronunciation guidance
    ipa: Optional[str] = None
    phonetic_spelling: Optional[str] = None
    notes: Optional[str] = None

    # For homographs
    homograph_options: Optional[list[str]] = None

    # Metadata
    supporting_strategies: list[str] = field(default_factory=list)
    confidence: float = 0.5
    is_character_name: bool = False  # Flagged for priority

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "word": self.word,
            "flag_reason": self.flag_reason.value,
            "occurrence_count": self.occurrence_count,
            "first_position": self.first_position,
            "chapters_present": self.chapters_present,
            "context_examples": self.context_examples,
            "ipa": self.ipa,
            "phonetic_spelling": self.phonetic_spelling,
            "notes": self.notes,
            "homograph_options": self.homograph_options,
            "supporting_strategies": self.supporting_strategies,
            "confidence": self.confidence,
            "is_character_name": self.is_character_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationEntry":
        return cls(
            id=data["id"],
            word=data["word"],
            flag_reason=PronunciationFlag(data["flag_reason"]),
            occurrence_count=data["occurrence_count"],
            first_position=data["first_position"],
            chapters_present=data["chapters_present"],
            context_examples=data["context_examples"],
            ipa=data.get("ipa"),
            phonetic_spelling=data.get("phonetic_spelling"),
            notes=data.get("notes"),
            homograph_options=data.get("homograph_options"),
            supporting_strategies=data.get("supporting_strategies", []),
            confidence=data.get("confidence", 0.5),
            is_character_name=data.get("is_character_name", False),
        )


@dataclass
class PronunciationMap:
    """Final output: complete pronunciation guide for the document."""

    entries: list[PronunciationEntry]
    low_confidence_entries: list[PronunciationEntry]  # Need review

    # Statistics
    total_flagged_words: int
    total_occurrences: int
    by_category: dict[str, int]  # PronunciationFlag -> count

    # Character names (for prioritization)
    character_names: list[str]

    pipeline_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "low_confidence_entries": [e.to_dict() for e in self.low_confidence_entries],
            "total_flagged_words": self.total_flagged_words,
            "total_occurrences": self.total_occurrences,
            "by_category": self.by_category,
            "character_names": self.character_names,
            "pipeline_metadata": self.pipeline_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationMap":
        return cls(
            entries=[PronunciationEntry.from_dict(e) for e in data["entries"]],
            low_confidence_entries=[
                PronunciationEntry.from_dict(e) for e in data["low_confidence_entries"]
            ],
            total_flagged_words=data["total_flagged_words"],
            total_occurrences=data["total_occurrences"],
            by_category=data["by_category"],
            character_names=data["character_names"],
            pipeline_metadata=data.get("pipeline_metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save pronunciation map to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "PronunciationMap":
        """Load pronunciation map from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Total Flagged Words: {self.total_flagged_words}",
            f"Total Occurrences: {self.total_occurrences:,}",
            "",
            "By Category:",
        ]

        for category, count in sorted(self.by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {category}: {count}")

        if self.low_confidence_entries:
            lines.append(f"\nLow Confidence (need review): {len(self.low_confidence_entries)}")

        lines.append("")
        lines.append("Top Entries:")

        # Show character names first
        char_entries = [e for e in self.entries if e.is_character_name][:5]
        if char_entries:
            lines.append("  Character Names:")
            for e in char_entries:
                phonetic = e.phonetic_spelling or "?"
                lines.append(f"    {e.word}: {phonetic} ({e.occurrence_count} occurrences)")

        # Then others
        other_entries = [e for e in self.entries if not e.is_character_name][:10]
        if other_entries:
            lines.append("  Other Words:")
            for e in other_entries:
                phonetic = e.phonetic_spelling or "?"
                lines.append(f"    {e.word}: {phonetic} [{e.flag_reason.value}]")

        return "\n".join(lines)

    def export_for_narrator(self) -> str:
        """Export as markdown for narrator use."""
        lines = ["# Pronunciation Guide", ""]

        # Character Names section
        char_entries = [e for e in self.entries if e.is_character_name]
        if char_entries:
            lines.append("## Character Names")
            lines.append("| Word | IPA | Phonetic | Chapters |")
            lines.append("|------|-----|----------|----------|")
            for e in sorted(char_entries, key=lambda x: x.occurrence_count, reverse=True):
                ipa = e.ipa or "-"
                phonetic = e.phonetic_spelling or "-"
                chapters = ", ".join(str(c) for c in e.chapters_present[:5])
                if len(e.chapters_present) > 5:
                    chapters += "..."
                lines.append(f"| {e.word} | {ipa} | {phonetic} | {chapters} |")
            lines.append("")

        # Homographs section
        homograph_entries = [
            e for e in self.entries if e.flag_reason == PronunciationFlag.HOMOGRAPH
        ]
        if homograph_entries:
            lines.append("## Homographs (Context-Dependent)")
            lines.append("| Word | Pronunciations |")
            lines.append("|------|----------------|")
            for e in homograph_entries:
                options = "; ".join(e.homograph_options) if e.homograph_options else "-"
                lines.append(f"| {e.word} | {options} |")
            lines.append("")

        # Foreign Words section
        foreign_entries = [e for e in self.entries if e.flag_reason == PronunciationFlag.FOREIGN]
        if foreign_entries:
            lines.append("## Foreign Words")
            lines.append("| Word | IPA | Phonetic | Notes |")
            lines.append("|------|-----|----------|-------|")
            for e in foreign_entries:
                ipa = e.ipa or "-"
                phonetic = e.phonetic_spelling or "-"
                notes = e.notes or "-"
                lines.append(f"| {e.word} | {ipa} | {phonetic} | {notes} |")
            lines.append("")

        # Other Unusual Words
        other_entries = [
            e
            for e in self.entries
            if e.flag_reason not in (PronunciationFlag.HOMOGRAPH, PronunciationFlag.FOREIGN)
            and not e.is_character_name
        ]
        if other_entries:
            lines.append("## Other Unusual Words")
            lines.append("| Word | IPA | Phonetic | Category |")
            lines.append("|------|-----|----------|----------|")
            for e in other_entries[:50]:  # Limit
                ipa = e.ipa or "-"
                phonetic = e.phonetic_spelling or "-"
                lines.append(f"| {e.word} | {ipa} | {phonetic} | {e.flag_reason.value} |")
            lines.append("")

        return "\n".join(lines)

    def filter_by_body_region(
        self,
        body_start: int,
        body_end: int,
    ) -> "PronunciationMap":
        """
        Filter entries to only include those within the body region.

        Removes entries from front/back matter based on their first_position.

        Args:
            body_start: Start position of body region
            body_end: End position of body region

        Returns:
            New PronunciationMap with filtered entries
        """
        import logging

        logger = logging.getLogger(__name__)

        def is_in_body(entry: PronunciationEntry) -> bool:
            return body_start <= entry.first_position < body_end

        # Filter entries
        filtered_entries = [e for e in self.entries if is_in_body(e)]
        filtered_low_conf = [e for e in self.low_confidence_entries if is_in_body(e)]

        # Count filtered
        removed_count = (len(self.entries) - len(filtered_entries)) + (
            len(self.low_confidence_entries) - len(filtered_low_conf)
        )

        if removed_count > 0:
            logger.info(f"Filtered {removed_count} pronunciation entries from front/back matter")

        # Rebuild category counts
        by_category = {}
        for entry in filtered_entries:
            cat = entry.flag_reason.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return PronunciationMap(
            entries=filtered_entries,
            low_confidence_entries=filtered_low_conf,
            total_flagged_words=len(filtered_entries),
            total_occurrences=sum(e.occurrence_count for e in filtered_entries),
            by_category=by_category,
            character_names=self.character_names,
            pipeline_metadata={
                **self.pipeline_metadata,
                "filtered_for_body_region": True,
                "entries_removed_from_front_back_matter": removed_count,
            },
        )


@dataclass
class PronunciationPipelineCheckpoint:
    """Checkpoint for save/resume capability."""

    stage: Literal["proposal", "enrichment", "consolidation", "complete"]
    timestamp: str
    source_file: str
    text_hash: str

    # Stage outputs
    proposals: Optional[list[PronunciationProposal]] = None
    enrichments: Optional[dict[str, PronunciationEnrichment]] = None  # word -> enrichment
    pronunciation_map: Optional[PronunciationMap] = None

    # Progress tracking (for resume)
    enriched_words: list[str] = field(default_factory=list)

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        enrichments_dict = None
        if self.enrichments:
            enrichments_dict = {k: v.to_dict() for k, v in self.enrichments.items()}

        return {
            "stage": self.stage,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "text_hash": self.text_hash,
            "proposals": [p.to_dict() for p in self.proposals] if self.proposals else None,
            "enrichments": enrichments_dict,
            "pronunciation_map": (
                self.pronunciation_map.to_dict() if self.pronunciation_map else None
            ),
            "enriched_words": self.enriched_words,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PronunciationPipelineCheckpoint":
        enrichments = None
        if data.get("enrichments"):
            enrichments = {
                k: PronunciationEnrichment.from_dict(v) for k, v in data["enrichments"].items()
            }

        return cls(
            stage=data["stage"],
            timestamp=data["timestamp"],
            source_file=data["source_file"],
            text_hash=data["text_hash"],
            proposals=(
                [PronunciationProposal.from_dict(p) for p in data["proposals"]]
                if data.get("proposals")
                else None
            ),
            enrichments=enrichments,
            pronunciation_map=(
                PronunciationMap.from_dict(data["pronunciation_map"])
                if data.get("pronunciation_map")
                else None
            ),
            enriched_words=data.get("enriched_words", []),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

    def save(self, path: Path) -> None:
        """Save checkpoint to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "PronunciationPipelineCheckpoint":
        """Load checkpoint from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    @staticmethod
    def create_new(source_file: str, text_hash: str) -> "PronunciationPipelineCheckpoint":
        """Create a new checkpoint for starting a pipeline run."""
        return PronunciationPipelineCheckpoint(
            stage="proposal",
            timestamp=datetime.now().isoformat(),
            source_file=source_file,
            text_hash=text_hash,
        )
