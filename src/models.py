"""
Data models for audiobook prep analysis.
These define the structure of extracted information.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    """How confident we are in a detection."""
    HIGH = "high"       # Clear regex match, explicit markup
    MEDIUM = "medium"   # Heuristic match, likely correct
    LOW = "low"         # Inference, needs review
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
    position: int   # Character offset in source text
    context: str    # Surrounding sentence/paragraph
    chapter_index: Optional[int] = None


class CharacterDescription(BaseModel):
    """A description or trait associated with a character."""
    text: str
    source_position: int
    chapter_index: Optional[int] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class Character(BaseModel):
    """A character extracted from the book."""
    id: str  # Unique identifier
    canonical_name: str  # Primary name to use
    aliases: list[str] = Field(default_factory=list)
    descriptions: list[CharacterDescription] = Field(default_factory=list)
    first_appearance_chapter: Optional[int] = None
    mention_count: int = 0
    relationships: dict[str, str] = Field(default_factory=dict)  # char_id -> relationship
    voice_notes: Optional[str] = None  # User notes for performance
    # Optional evidence used to build/refine profiles. Each entry is a dict such as:
    # { "type": "...", "statement": "...", "quotes": [{"quote": "...", "position": 12345}], "chunk": "Chapter 3" }
    evidence: list[dict] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


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


class AnalysisResult(BaseModel):
    """Complete analysis result for a book."""
    metadata: BookMetadata
    structure: list[StructuralElement] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    pronunciations: list[PronunciationEntry] = Field(default_factory=list)

    # Overview summary (book structure, plot, models, timing)
    overview: Optional[dict] = None

    # Raw text preserved for reference
    raw_text: Optional[str] = None

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
