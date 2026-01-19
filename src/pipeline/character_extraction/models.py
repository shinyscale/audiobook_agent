"""
Data models for character extraction pipeline.

These models represent the flow of data through the per-chapter extraction,
validation, and cross-chapter consensus stages.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import hashlib


class CharacterType(str, Enum):
    """Classification of character's role in the narrative."""
    STORY = "story"           # Active participant - appears in scenes, speaks, acts
    HISTORICAL = "historical" # Real historical figure mentioned in passing
    REFERENCED = "referenced" # Fictional character from other works mentioned
    DESCRIPTIVE = "descriptive"  # Recurring descriptive handle (e.g., "the creature", "the detective")
    UNCERTAIN = "uncertain"   # Could not determine


@dataclass
class CharacterMention:
    """A single mention of a character in text."""
    text: str               # The exact text found ("Elizabeth", "Lizzy", "Miss Bennet")
    position: int           # Character offset in full document
    chapter_index: int      # Which chapter (1-indexed)
    context: str            # Surrounding text (~100 chars)
    in_dialogue: bool       # Is this within quoted speech?
    is_agentive: bool = False  # Is this mention in an agentive context (speaks/acts)?

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "position": self.position,
            "chapter_index": self.chapter_index,
            "context": self.context,
            "in_dialogue": self.in_dialogue,
            "is_agentive": self.is_agentive,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterMention":
        return cls(
            text=data["text"],
            position=data["position"],
            chapter_index=data["chapter_index"],
            context=data["context"],
            in_dialogue=data["in_dialogue"],
            is_agentive=data.get("is_agentive", False),
        )


@dataclass
class CharacterProposal:
    """A proposed character from one extraction strategy."""
    strategy: str           # "ner", "llm_character", etc.
    name: str               # Proposed canonical name
    mentions: list[CharacterMention]
    confidence: float       # Strategy's confidence (0.0 - 1.0)
    chapter_index: int      # Which chapter this was extracted from
    reasoning: Optional[str] = None
    character_type: CharacterType = CharacterType.UNCERTAIN  # story, historical, or referenced

    @property
    def mention_count(self) -> int:
        return len(self.mentions)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "name": self.name,
            "mentions": [m.to_dict() for m in self.mentions],
            "confidence": self.confidence,
            "chapter_index": self.chapter_index,
            "reasoning": self.reasoning,
            "character_type": self.character_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterProposal":
        char_type = CharacterType.UNCERTAIN
        if "character_type" in data:
            try:
                char_type = CharacterType(data["character_type"])
            except ValueError:
                pass
        return cls(
            strategy=data["strategy"],
            name=data["name"],
            mentions=[CharacterMention.from_dict(m) for m in data["mentions"]],
            confidence=data["confidence"],
            chapter_index=data["chapter_index"],
            reasoning=data.get("reasoning"),
            character_type=char_type,
        )


@dataclass
class CharacterValidationResult:
    """Result of validating a character proposal."""
    proposal: CharacterProposal
    is_person_score: float      # Is this really a person? (0-1)
    context_score: float        # Does context support character interpretation? (0-1)
    alias_candidates: list[str] # Other names that might be same person
    overall_score: float        # Combined validation score
    is_valid: bool              # Above threshold?
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "proposal": self.proposal.to_dict(),
            "is_person_score": self.is_person_score,
            "context_score": self.context_score,
            "alias_candidates": self.alias_candidates,
            "overall_score": self.overall_score,
            "is_valid": self.is_valid,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterValidationResult":
        return cls(
            proposal=CharacterProposal.from_dict(data["proposal"]),
            is_person_score=data["is_person_score"],
            context_score=data["context_score"],
            alias_candidates=data["alias_candidates"],
            overall_score=data["overall_score"],
            is_valid=data["is_valid"],
            reasoning=data["reasoning"],
        )


RoleType = Literal["protagonist", "antagonist", "supporting", "minor"]


@dataclass
class Character:
    """A validated character with all information merged across chapters."""
    id: str                         # Unique identifier
    canonical_name: str             # Primary name to use
    aliases: list[str]              # Other names for this character
    mentions: list[CharacterMention]
    first_appearance_chapter: int   # First chapter where character appears
    mention_count: int              # Total mentions across all chapters
    chapters_present: list[int]     # List of chapter indices where character appears
    confidence: float               # Overall confidence score
    supporting_strategies: list[str]  # Which extraction strategies found this character
    description: str = ""           # LLM-generated prose profile
    character_type: CharacterType = CharacterType.UNCERTAIN  # story, historical, or referenced
    profile_evidence: list[dict] = field(default_factory=list)  # Evidence supporting profile claims
    # Confidence in profile quality (0.0-1.0). None means "no profile was generated/attempted".
    profile_confidence: Optional[float] = None
    # Narrator detection fields
    is_narrator: bool = False       # Is this the narrator of the story?
    narrative_role: Optional[str] = None  # e.g., "First-person narrator"
    role: RoleType = "supporting"   # Character role in the story
    # Effective mention count for narrators (boosted to match main characters)
    effective_mention_count: Optional[int] = None
    # Structured profile fields (F8: Simplified Character Output)
    appearance: Optional[dict] = None  # {summary, age_indication, distinguishing_features}
    personality: Optional[dict] = None  # {summary, traits, temperament, emotional_range}
    voice_guidance: Optional[dict] = None  # {suggested_tone, dialect_notes, verbal_tics, formality_level}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "mentions": [m.to_dict() for m in self.mentions],
            "first_appearance_chapter": self.first_appearance_chapter,
            "mention_count": self.mention_count,
            "chapters_present": self.chapters_present,
            "confidence": self.confidence,
            "supporting_strategies": self.supporting_strategies,
            "description": self.description,
            "character_type": self.character_type.value,
            "profile_evidence": self.profile_evidence,
            "profile_confidence": self.profile_confidence,
            "is_narrator": self.is_narrator,
            "narrative_role": self.narrative_role,
            "role": self.role,
            "effective_mention_count": self.effective_mention_count,
            "appearance": self.appearance,
            "personality": self.personality,
            "voice_guidance": self.voice_guidance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        char_type = CharacterType.UNCERTAIN
        if "character_type" in data:
            try:
                char_type = CharacterType(data["character_type"])
            except ValueError:
                pass
        return cls(
            id=data["id"],
            canonical_name=data["canonical_name"],
            aliases=data["aliases"],
            mentions=[CharacterMention.from_dict(m) for m in data["mentions"]],
            first_appearance_chapter=data["first_appearance_chapter"],
            mention_count=data["mention_count"],
            chapters_present=data["chapters_present"],
            confidence=data["confidence"],
            supporting_strategies=data["supporting_strategies"],
            description=data.get("description", ""),
            character_type=char_type,
            profile_evidence=data.get("profile_evidence", []),
            profile_confidence=data.get("profile_confidence", None),
            is_narrator=data.get("is_narrator", False),
            narrative_role=data.get("narrative_role"),
            role=data.get("role", "supporting"),
            effective_mention_count=data.get("effective_mention_count"),
            appearance=data.get("appearance"),
            personality=data.get("personality"),
            voice_guidance=data.get("voice_guidance"),
        )


@dataclass
class CharacterMap:
    """Final output: all characters extracted from the document."""
    characters: list[Character]
    low_confidence_characters: list[Character]  # Flagged for review
    total_mentions: int
    total_chapters: int
    pipeline_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "characters": [c.to_dict() for c in self.characters],
            "low_confidence_characters": [c.to_dict() for c in self.low_confidence_characters],
            "total_mentions": self.total_mentions,
            "total_chapters": self.total_chapters,
            "pipeline_metadata": self.pipeline_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterMap":
        return cls(
            characters=[Character.from_dict(c) for c in data["characters"]],
            low_confidence_characters=[Character.from_dict(c) for c in data["low_confidence_characters"]],
            total_mentions=data["total_mentions"],
            total_chapters=data["total_chapters"],
            pipeline_metadata=data.get("pipeline_metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save character map to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "CharacterMap":
        """Load character map from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    def summary(self) -> str:
        """Human-readable summary of the character map."""
        lines = [
            f"Total Characters: {len(self.characters)}",
            f"Total Mentions: {self.total_mentions:,}",
            f"Chapters Analyzed: {self.total_chapters}",
        ]

        if self.low_confidence_characters:
            lines.append(f"Low Confidence: {len(self.low_confidence_characters)} (need review)")

        lines.append("")
        lines.append("Characters (by mention count):")

        # Sort by mention count
        sorted_chars = sorted(self.characters, key=lambda c: c.mention_count, reverse=True)

        for char in sorted_chars[:15]:  # Top 15
            aliases_str = f" (aka {', '.join(char.aliases[:3])})" if char.aliases else ""
            lines.append(
                f"  {char.canonical_name}{aliases_str} - "
                f"{char.mention_count} mentions, first in ch.{char.first_appearance_chapter}"
            )

        if len(sorted_chars) > 15:
            lines.append(f"  ... and {len(sorted_chars) - 15} more")

        return "\n".join(lines)


@dataclass
class CharacterPipelineCheckpoint:
    """Checkpoint for saving/resuming character extraction pipeline state."""
    stage: Literal["extraction", "validation", "consensus", "complete"]
    timestamp: str
    source_file: str
    text_hash: str  # To verify we're resuming with same document

    # Stage outputs (populated as pipeline progresses)
    chapter_proposals: Optional[dict[int, list[CharacterProposal]]] = None  # chapter_idx -> proposals
    validations: Optional[list[CharacterValidationResult]] = None
    character_map: Optional[CharacterMap] = None

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        chapter_proposals_dict = None
        if self.chapter_proposals:
            chapter_proposals_dict = {
                str(k): [p.to_dict() for p in v]
                for k, v in self.chapter_proposals.items()
            }

        return {
            "stage": self.stage,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "text_hash": self.text_hash,
            "chapter_proposals": chapter_proposals_dict,
            "validations": [v.to_dict() for v in self.validations] if self.validations else None,
            "character_map": self.character_map.to_dict() if self.character_map else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterPipelineCheckpoint":
        chapter_proposals = None
        if data.get("chapter_proposals"):
            chapter_proposals = {
                int(k): [CharacterProposal.from_dict(p) for p in v]
                for k, v in data["chapter_proposals"].items()
            }

        return cls(
            stage=data["stage"],
            timestamp=data["timestamp"],
            source_file=data["source_file"],
            text_hash=data["text_hash"],
            chapter_proposals=chapter_proposals,
            validations=[CharacterValidationResult.from_dict(v) for v in data["validations"]] if data.get("validations") else None,
            character_map=CharacterMap.from_dict(data["character_map"]) if data.get("character_map") else None,
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

    def save(self, path: Path) -> None:
        """Save checkpoint to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "CharacterPipelineCheckpoint":
        """Load checkpoint from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    @staticmethod
    def create_new(source_file: str, text_hash: str) -> "CharacterPipelineCheckpoint":
        """Create a new checkpoint for starting a pipeline run."""
        return CharacterPipelineCheckpoint(
            stage="extraction",
            timestamp=datetime.now().isoformat(),
            source_file=source_file,
            text_hash=text_hash,
        )
