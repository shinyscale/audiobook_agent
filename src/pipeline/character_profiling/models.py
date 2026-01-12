"""
Data models for character profiling pipeline.

These models represent rich character profiles designed for audiobook narration,
including appearance, personality, and voice guidance.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import json
from pathlib import Path


RoleType = Literal["protagonist", "antagonist", "supporting", "minor"]
MentionFrequency = Literal["frequent", "moderate", "occasional", "rare"]


@dataclass
class ProfileEvidence:
    """Evidence supporting a profile claim."""
    statement: str  # The claim being made
    quote: str  # Supporting quote from text
    chapter: Optional[int] = None  # Chapter where quote appears
    position: Optional[int] = None  # Character position in text


@dataclass
class AppearanceProfile:
    """Physical appearance for narrator visualization."""
    summary: str  # 1-2 sentence overview
    details: dict[str, str] = field(default_factory=dict)  # "hair": "dark, curly"
    age_indication: str = "unknown"  # "young adult", "middle-aged", etc.
    distinguishing_features: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)  # Supporting quotes

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "details": self.details,
            "age_indication": self.age_indication,
            "distinguishing_features": self.distinguishing_features,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppearanceProfile":
        return cls(
            summary=data.get("summary", ""),
            details=data.get("details", {}),
            age_indication=data.get("age_indication", "unknown"),
            distinguishing_features=data.get("distinguishing_features", []),
            evidence=data.get("evidence", []),
        )

    @classmethod
    def empty(cls) -> "AppearanceProfile":
        return cls(summary="No physical description available in text.")


@dataclass
class PersonalityProfile:
    """Personality traits for voice characterization."""
    summary: str  # 1-2 sentence overview
    traits: list[str] = field(default_factory=list)  # "arrogant", "insecure"
    temperament: str = "unknown"  # "volatile", "calm", "anxious"
    speech_patterns: list[str] = field(default_factory=list)  # "formal", "slang"
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "traits": self.traits,
            "temperament": self.temperament,
            "speech_patterns": self.speech_patterns,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersonalityProfile":
        return cls(
            summary=data.get("summary", ""),
            traits=data.get("traits", []),
            temperament=data.get("temperament", "unknown"),
            speech_patterns=data.get("speech_patterns", []),
            evidence=data.get("evidence", []),
        )

    @classmethod
    def empty(cls) -> "PersonalityProfile":
        return cls(summary="Insufficient information for personality analysis.")


@dataclass
class VoiceGuidance:
    """Specific guidance for narrator voice work."""
    suggested_tone: str = ""  # "aristocratic drawl", "nervous energy"
    dialect_notes: str = ""  # "Midwestern", "British upper class"
    verbal_tics: list[str] = field(default_factory=list)  # "old sport", "you know"
    formality_level: str = "moderate"  # "very formal", "casual", etc.
    emotional_range: str = ""  # "repressed", "explosive", "steady"
    example_quotes: list[str] = field(default_factory=list)  # Key dialogue samples

    def to_dict(self) -> dict:
        return {
            "suggested_tone": self.suggested_tone,
            "dialect_notes": self.dialect_notes,
            "verbal_tics": self.verbal_tics,
            "formality_level": self.formality_level,
            "emotional_range": self.emotional_range,
            "example_quotes": self.example_quotes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceGuidance":
        return cls(
            suggested_tone=data.get("suggested_tone", ""),
            dialect_notes=data.get("dialect_notes", ""),
            verbal_tics=data.get("verbal_tics", []),
            formality_level=data.get("formality_level", "moderate"),
            emotional_range=data.get("emotional_range", ""),
            example_quotes=data.get("example_quotes", []),
        )

    @classmethod
    def empty(cls) -> "VoiceGuidance":
        return cls(suggested_tone="No specific voice guidance available.")


@dataclass
class CharacterRelationship:
    """Relationship between characters."""
    character: str  # Name of the other character
    relationship_type: str  # "spouse", "lover", "rival", "friend", etc.
    description: str  # Brief description of the relationship

    def to_dict(self) -> dict:
        return {
            "character": self.character,
            "type": self.relationship_type,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterRelationship":
        return cls(
            character=data["character"],
            relationship_type=data.get("type", ""),
            description=data.get("description", ""),
        )


@dataclass
class IdentifiedCharacter:
    """Character identified from chapter summaries (before full profiling)."""
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    role: RoleType = "supporting"
    is_narrator: bool = False
    narrative_role: Optional[str] = None  # "First-person narrator", etc.
    first_appearance_chapter: int = 1
    chapters_present: list[int] = field(default_factory=list)
    brief_description: str = ""  # From summaries

    def to_dict(self) -> dict:
        return {
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "role": self.role,
            "is_narrator": self.is_narrator,
            "narrative_role": self.narrative_role,
            "first_appearance_chapter": self.first_appearance_chapter,
            "chapters_present": self.chapters_present,
            "brief_description": self.brief_description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IdentifiedCharacter":
        return cls(
            canonical_name=data["canonical_name"],
            aliases=data.get("aliases", []),
            role=data.get("role", "supporting"),
            is_narrator=data.get("is_narrator", False),
            narrative_role=data.get("narrative_role"),
            first_appearance_chapter=data.get("first_appearance_chapter", 1),
            chapters_present=data.get("chapters_present", []),
            brief_description=data.get("brief_description", ""),
        )


@dataclass
class CharacterProfile:
    """Rich character profile for audiobook narration."""
    # Identity
    id: str  # Unique identifier
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    role: RoleType = "supporting"
    is_narrator: bool = False
    narrative_role: Optional[str] = None

    # For Narration (PRIMARY PURPOSE)
    appearance: AppearanceProfile = field(default_factory=AppearanceProfile.empty)
    personality: PersonalityProfile = field(default_factory=PersonalityProfile.empty)
    voice_guidance: VoiceGuidance = field(default_factory=VoiceGuidance.empty)

    # Relationships
    relationships: list[CharacterRelationship] = field(default_factory=list)

    # Evidence
    evidence: list[ProfileEvidence] = field(default_factory=list)
    confidence: float = 0.5

    # Metadata (SECONDARY)
    first_appearance_chapter: int = 1
    chapters_present: list[int] = field(default_factory=list)
    mention_frequency: MentionFrequency = "occasional"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "role": self.role,
            "is_narrator": self.is_narrator,
            "narrative_role": self.narrative_role,
            "appearance": self.appearance.to_dict(),
            "personality": self.personality.to_dict(),
            "voice_guidance": self.voice_guidance.to_dict(),
            "relationships": [r.to_dict() for r in self.relationships],
            "evidence": [{"statement": e.statement, "quote": e.quote, "chapter": e.chapter} for e in self.evidence],
            "confidence": self.confidence,
            "metadata": {
                "first_appearance_chapter": self.first_appearance_chapter,
                "chapters_present": self.chapters_present,
                "mention_frequency": self.mention_frequency,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterProfile":
        metadata = data.get("metadata", {})
        return cls(
            id=data["id"],
            canonical_name=data["canonical_name"],
            aliases=data.get("aliases", []),
            role=data.get("role", "supporting"),
            is_narrator=data.get("is_narrator", False),
            narrative_role=data.get("narrative_role"),
            appearance=AppearanceProfile.from_dict(data.get("appearance", {})),
            personality=PersonalityProfile.from_dict(data.get("personality", {})),
            voice_guidance=VoiceGuidance.from_dict(data.get("voice_guidance", {})),
            relationships=[CharacterRelationship.from_dict(r) for r in data.get("relationships", [])],
            evidence=[ProfileEvidence(e["statement"], e["quote"], e.get("chapter")) for e in data.get("evidence", [])],
            confidence=data.get("confidence", 0.5),
            first_appearance_chapter=metadata.get("first_appearance_chapter", 1),
            chapters_present=metadata.get("chapters_present", []),
            mention_frequency=metadata.get("mention_frequency", "occasional"),
        )

    @classmethod
    def from_identified(cls, char: IdentifiedCharacter, id_suffix: str = "") -> "CharacterProfile":
        """Create a profile from an identified character."""
        import hashlib
        char_id = hashlib.md5(char.canonical_name.encode()).hexdigest()[:8]
        return cls(
            id=f"char_{char.canonical_name.lower().replace(' ', '_')}_{char_id}{id_suffix}",
            canonical_name=char.canonical_name,
            aliases=char.aliases,
            role=char.role,
            is_narrator=char.is_narrator,
            narrative_role=char.narrative_role,
            first_appearance_chapter=char.first_appearance_chapter,
            chapters_present=char.chapters_present,
        )


@dataclass
class CharacterProfileMap:
    """Collection of all character profiles for a document."""
    profiles: list[CharacterProfile]
    narrator_name: Optional[str] = None
    narrative_style: str = "unknown"  # "first-person", "third-person", "mixed"
    total_characters: int = 0
    pipeline_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "narrator_name": self.narrator_name,
            "narrative_style": self.narrative_style,
            "total_characters": self.total_characters,
            "pipeline_metadata": self.pipeline_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterProfileMap":
        return cls(
            profiles=[CharacterProfile.from_dict(p) for p in data.get("profiles", [])],
            narrator_name=data.get("narrator_name"),
            narrative_style=data.get("narrative_style", "unknown"),
            total_characters=data.get("total_characters", 0),
            pipeline_metadata=data.get("pipeline_metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save profile map to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "CharacterProfileMap":
        """Load profile map from JSON file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    def get_profile(self, name: str) -> Optional[CharacterProfile]:
        """Get profile by canonical name or alias."""
        name_lower = name.lower()
        for profile in self.profiles:
            if profile.canonical_name.lower() == name_lower:
                return profile
            if any(alias.lower() == name_lower for alias in profile.aliases):
                return profile
        return None
