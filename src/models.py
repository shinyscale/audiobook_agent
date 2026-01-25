"""
Data models for audiobook prep analysis.
These define the structure of extracted information.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """How confident we are in a detection."""

    HIGH = "high"  # Clear regex match, explicit markup
    MEDIUM = "medium"  # Heuristic match, likely correct
    LOW = "low"  # Inference, needs review
    LLM_REFINED = "llm_refined"  # Confirmed/corrected by LLM


class StructureType(str, Enum):
    """Types of structural elements we detect."""

    BOOK_TITLE = "book_title"
    PART = "part"
    CHAPTER = "chapter"
    SCENE_BREAK = "scene_break"
    SECTION = "section"
    JOURNAL_ENTRY = "journal_entry"
    LETTER = "letter"
    EPIGRAPH = "epigraph"
    PROLOGUE = "prologue"
    EPILOGUE = "epilogue"
    APPENDIX = "appendix"
    PARAGRAPH = "paragraph"


class PronunciationFlag(str, Enum):
    """Why a word was flagged for pronunciation review."""

    PROPER_NOUN = "proper_noun"
    FOREIGN = "foreign"
    ARCHAIC = "archaic"
    TECHNICAL = "technical"
    FICTIONAL = "fictional"
    HOMOGRAPH = "homograph"  # read/read, lead/lead
    UNUSUAL = "unusual"
    UNKNOWN = "unknown"


class CharacterMention(BaseModel):
    """A single mention of a character in the text."""

    name_form: str  # The exact form used ("Lizzy", "Elizabeth", etc.)
    position: int  # Character offset in source text
    context: str  # Surrounding sentence/paragraph
    chapter_index: Optional[int] = None


class CharacterDescription(BaseModel):
    """A description or trait associated with a character."""

    text: str
    source_position: int
    chapter_index: Optional[int] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class Character(BaseModel):
    """A character extracted from the book.

    Fields are organized to prioritize narrator-useful information:
    1. Identity: canonical_name, aliases, role
    2. Narration guidance: appearance, personality, voice_guidance
    3. Relationships: relationships dict
    4. Metadata: mention_count, first_appearance_chapter, confidence
    """

    id: str  # Unique identifier
    canonical_name: str  # Primary name to use
    aliases: list[str] = Field(default_factory=list)

    # Narrator-useful structured profile data (F8: Simplified Character Output)
    role: Optional[str] = None  # protagonist, antagonist, supporting, minor
    appearance: Optional[dict] = None  # {summary, age_indication, distinguishing_features}
    personality: Optional[dict] = None  # {summary, traits, temperament, emotional_range}
    voice_guidance: Optional[dict] = (
        None  # {suggested_tone, dialect_notes, verbal_tics, formality_level}
    )

    # Legacy description field (still used for backward compatibility)
    descriptions: list[CharacterDescription] = Field(default_factory=list)

    # Relationships (narrator-useful for understanding dynamics)
    relationships: dict[str, str] = Field(default_factory=dict)  # char_id -> relationship

    # Evidence for profile claims
    evidence: list[dict] = Field(default_factory=list)

    # User notes (editable by narrator)
    voice_notes: Optional[str] = None  # User notes for performance

    # Metadata (secondary info - less prominent in output)
    first_appearance_chapter: Optional[int] = None
    mention_count: int = 0
    mentions: list["CharacterMention"] = Field(
        default_factory=list
    )  # Actual mention objects for profile generation
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Narrator role detection
    is_narrator: bool = False
    narrative_role: Optional[str] = None  # e.g., "First-person narrator", "POV character"


class PronunciationEntry(BaseModel):
    """A word flagged for pronunciation attention."""

    word: str
    flag_reason: PronunciationFlag
    occurrences: int = 1
    first_position: int
    chapter_indices: list[int] = Field(default_factory=list)
    context_examples: list[str] = Field(default_factory=list, max_length=3)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Pronunciation info (populated by Phase 2)
    ipa: Optional[str] = None
    phonetic_spelling: Optional[str] = None
    audio_url: Optional[str] = None
    user_pronunciation: Optional[str] = None  # User's custom pronunciation
    notes: Optional[str] = None


class GlossaryEntry(BaseModel):
    """A single glossary entry (term + definition)."""

    term: str
    definition: str
    position: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class GlossaryMap(BaseModel):
    """Extracted glossary from the document."""

    entries: list[GlossaryEntry] = Field(default_factory=list)
    source_region_start: int = 0
    source_region_end: int = 0

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def entries_by_letter(self) -> dict[str, list["GlossaryEntry"]]:
        """Group entries by first letter for alphabet navigation."""
        grouped: dict[str, list[GlossaryEntry]] = {}
        for entry in sorted(self.entries, key=lambda e: e.term.lower()):
            letter = entry.term[0].upper() if entry.term else "#"
            if not letter.isalpha():
                letter = "#"
            grouped.setdefault(letter, []).append(entry)
        return grouped


class StructuralElement(BaseModel):
    """A structural element in the book (chapter, scene, etc.)."""

    type: StructureType
    title: Optional[str] = None
    index: int  # Sequential index within its type
    start_position: int
    end_position: int
    word_count: int = 0
    estimated_duration_minutes: float = 0.0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Nested content
    children: list["StructuralElement"] = Field(default_factory=list)

    # Characters appearing in this section
    characters_present: list[str] = Field(default_factory=list)  # Character IDs

    # LLM-generated chapter summary for narrator prep
    summary: Optional[str] = None


class BookMetadata(BaseModel):
    """Metadata about the source book."""

    title: Optional[str] = None
    author: Optional[str] = None
    source_file: str
    source_format: str  # pdf, docx, epub, txt
    total_word_count: int = 0
    total_character_count: int = 0
    estimated_total_duration_minutes: float = 0.0

    # Analysis settings used
    words_per_minute: int = 150  # Default narration pace


class ConsensusVoteRecord(BaseModel):
    """Record of a single consensus voting decision."""

    vote_type: str  # "alias", "boundary", "summary_event", "summary_character"
    subject: str  # What was being voted on (e.g., alias name, boundary position)
    context: Optional[str] = None  # Additional context (e.g., canonical name for alias)
    votes: list[bool] = Field(default_factory=list)  # Individual model votes
    vote_count: int = 0  # Total votes cast
    yes_count: int = 0  # Votes in favor
    threshold: float = 0.67  # Required threshold for acceptance
    outcome: str = "unknown"  # "accepted", "rejected", "skipped"
    reason: Optional[str] = None  # Explanation of outcome


class ConsensusLog(BaseModel):
    """Log of all consensus voting decisions during analysis."""

    # Competitive consensus configuration
    enabled: bool = False
    mode: str = "none"  # "none", "single", "multi"
    models: list[str] = Field(default_factory=list)  # Model names used
    stages: list[str] = Field(default_factory=list)  # Stages with consensus enabled

    # Voting records by category
    alias_votes: list[ConsensusVoteRecord] = Field(default_factory=list)
    boundary_votes: list[ConsensusVoteRecord] = Field(default_factory=list)
    summary_votes: list[ConsensusVoteRecord] = Field(default_factory=list)

    # Summary statistics
    total_votes: int = 0
    accepted_count: int = 0
    rejected_count: int = 0


class AnalysisResult(BaseModel):
    """Complete analysis result for a book."""

    metadata: BookMetadata
    structure: list[StructuralElement] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    pronunciations: list[PronunciationEntry] = Field(default_factory=list)
    glossary: Optional[GlossaryMap] = None

    # Overview summary (book structure, plot, models, timing)
    overview: Optional[dict] = None

    # Raw text preserved for reference
    raw_text: Optional[str] = None

    # Consensus voting log (multi-model competitive consensus)
    consensus_log: Optional[ConsensusLog] = None

    # Analysis notes and warnings
    warnings: list[str] = Field(default_factory=list)
    low_confidence_items: list[str] = Field(default_factory=list)

    def get_chapter_summary(self) -> list[dict]:
        """Generate a chapter-by-chapter summary."""
        chapters = [s for s in self.structure if s.type == StructureType.CHAPTER]
        return [
            {
                "index": ch.index,
                "title": ch.title,
                "word_count": ch.word_count,
                "duration_minutes": ch.estimated_duration_minutes,
                "characters": ch.characters_present,
            }
            for ch in chapters
        ]


# Enable forward references for nested models
StructuralElement.model_rebuild()
