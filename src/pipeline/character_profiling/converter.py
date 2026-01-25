"""
Character profile converter.

Converts CharacterProfile to the existing Character model for backward compatibility,
while preserving rich profile data (appearance, personality, voice guidance).
"""

from typing import Optional

from ...models import Character, CharacterDescription, ConfidenceLevel
from .models import CharacterProfile, CharacterProfileMap


def profile_to_character(profile: CharacterProfile) -> Character:
    """
    Convert a CharacterProfile to a Character model.

    This preserves all rich profile data by:
    1. Storing appearance/personality/voice summaries in descriptions
    2. Converting relationships to dict format
    3. Preserving evidence

    Args:
        profile: CharacterProfile to convert

    Returns:
        Character model with rich data
    """
    # Build descriptions list with all profile sections
    descriptions = []

    # Main profile description (combined summary)
    main_description = _build_main_description(profile)
    if main_description:
        descriptions.append(
            CharacterDescription(
                text=main_description,
                source_position=0,
                confidence=ConfidenceLevel.LLM_REFINED,
            )
        )

    # Convert confidence from float to enum
    if profile.confidence >= 0.7:
        confidence = ConfidenceLevel.HIGH
    elif profile.confidence >= 0.4:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    # Convert relationships to dict format
    relationships = {}
    for rel in profile.relationships:
        relationships[rel.character] = rel.relationship_type

    # Convert evidence to list of dicts
    evidence = []
    for ev in profile.evidence:
        evidence.append(
            {
                "type": "profile_evidence",
                "statement": ev.statement,
                "quote": ev.quote,
                "chapter": ev.chapter,
                "position": ev.position,
            }
        )

    # Build voice notes from voice guidance
    voice_notes = _build_voice_notes(profile)

    # Build structured data for F8: Simplified Character Output
    appearance_dict = None
    if profile.appearance and profile.appearance.summary:
        appearance_dict = {
            "summary": profile.appearance.summary,
            "age_indication": profile.appearance.age_indication,
            "distinguishing_features": profile.appearance.distinguishing_features or [],
        }

    personality_dict = None
    if profile.personality and profile.personality.summary:
        personality_dict = {
            "summary": profile.personality.summary,
            "traits": profile.personality.traits or [],
            "temperament": profile.personality.temperament,
            "moral_alignment": profile.personality.moral_alignment,
        }

    voice_guidance_dict = None
    vg = profile.voice_guidance
    if vg and (vg.suggested_tone or vg.dialect_notes or vg.verbal_tics):
        voice_guidance_dict = {
            "suggested_tone": vg.suggested_tone,
            "dialect_notes": vg.dialect_notes,
            "verbal_tics": vg.verbal_tics or [],
            "formality_level": vg.formality_level,
            "emotional_range": vg.emotional_range,
            "example_quotes": vg.example_quotes or [],
        }

    return Character(
        id=profile.id,
        canonical_name=profile.canonical_name,
        aliases=profile.aliases,
        role=profile.role,
        appearance=appearance_dict,
        personality=personality_dict,
        voice_guidance=voice_guidance_dict,
        descriptions=descriptions,
        first_appearance_chapter=profile.first_appearance_chapter,
        mention_count=_estimate_mention_count(profile),
        relationships=relationships,
        voice_notes=voice_notes,
        evidence=evidence,
        confidence=confidence,
        is_narrator=profile.is_narrator,
        narrative_role=profile.narrative_role,
    )


def _build_main_description(profile: CharacterProfile) -> str:
    """
    Build a comprehensive description from profile sections.

    Combines appearance, personality summaries into readable prose.
    """
    sections = []

    # Appearance
    if (
        profile.appearance.summary
        and profile.appearance.summary != "No physical description available in text."
    ):
        sections.append(f"**Appearance:** {profile.appearance.summary}")
        if profile.appearance.age_indication and profile.appearance.age_indication != "unknown":
            sections.append(f"Age: {profile.appearance.age_indication}")
        if profile.appearance.distinguishing_features:
            features = ", ".join(profile.appearance.distinguishing_features)
            sections.append(f"Distinguishing features: {features}")

    # Personality
    if (
        profile.personality.summary
        and profile.personality.summary != "Insufficient information for personality analysis."
    ):
        sections.append(f"**Personality:** {profile.personality.summary}")
        if profile.personality.traits:
            traits = ", ".join(profile.personality.traits)
            sections.append(f"Traits: {traits}")
        if profile.personality.temperament and profile.personality.temperament != "unknown":
            sections.append(f"Temperament: {profile.personality.temperament}")

    # Role
    if profile.role:
        sections.append(f"**Role:** {profile.role}")

    if not sections:
        return ""

    return "\n".join(sections)


def _build_voice_notes(profile: CharacterProfile) -> Optional[str]:
    """
    Build voice notes from voice guidance.

    Formats voice guidance into actionable narrator notes.
    """
    vg = profile.voice_guidance
    if not vg.suggested_tone and not vg.dialect_notes and not vg.verbal_tics:
        return None

    notes = []

    if vg.suggested_tone and vg.suggested_tone != "No specific voice guidance available.":
        notes.append(f"Tone: {vg.suggested_tone}")

    if vg.dialect_notes:
        notes.append(f"Dialect: {vg.dialect_notes}")

    if vg.verbal_tics:
        tics = ", ".join(f'"{t}"' for t in vg.verbal_tics)
        notes.append(f"Verbal tics: {tics}")

    if vg.formality_level and vg.formality_level != "moderate":
        notes.append(f"Formality: {vg.formality_level}")

    if vg.emotional_range:
        notes.append(f"Emotional range: {vg.emotional_range}")

    if vg.example_quotes:
        notes.append("Example quotes:")
        for quote in vg.example_quotes[:3]:
            notes.append(f"  - {quote}")

    return "\n".join(notes) if notes else None


def _estimate_mention_count(profile: CharacterProfile) -> int:
    """
    Estimate mention count from profile data.

    Uses mention_frequency and chapters_present to estimate.
    For first-person narrators, boosts the count significantly as they
    are present throughout but not explicitly named.
    """
    frequency_map = {
        "frequent": 50,
        "moderate": 25,
        "occasional": 10,
        "rare": 3,
    }

    base = frequency_map.get(profile.mention_frequency, 10)
    # Adjust based on chapters present
    chapter_factor = max(1, len(profile.chapters_present))

    estimated = base * chapter_factor

    # Boost for first-person narrators who speak as "I" throughout
    if (
        profile.is_narrator
        and profile.narrative_role
        and "first-person" in profile.narrative_role.lower()
    ):
        # First-person narrators are effectively present in every sentence they narrate
        # Boost their count to reflect narrative presence
        estimated = max(estimated, 100)  # Minimum 100 for first-person narrators

    return estimated


def profile_map_to_characters(profile_map: CharacterProfileMap) -> list[Character]:
    """
    Convert a CharacterProfileMap to list of Character models.

    Args:
        profile_map: CharacterProfileMap to convert

    Returns:
        List of Character models with rich profile data
    """
    return [profile_to_character(p) for p in profile_map.profiles]


def character_to_rich_dict(char: Character) -> dict:
    """
    Convert Character to a rich dictionary format for JSON output.

    This structures the output to prioritize narrator-useful information
    (appearance, personality, voice guidance) over metrics (mention counts).

    Args:
        char: Character model to convert

    Returns:
        Dictionary with structured rich profile data
    """
    # Parse structured data from descriptions if available
    appearance = _extract_section(char.descriptions, "Appearance")
    personality = _extract_section(char.descriptions, "Personality")
    role = _extract_section(char.descriptions, "Role")

    result = {
        "id": char.id,
        "canonical_name": char.canonical_name,
        "aliases": char.aliases,
        "role": role or "unknown",
        "is_narrator": char.is_narrator,
        "narrative_role": char.narrative_role,
        # Primary profile data for narration
        "appearance": {
            "summary": appearance or "No physical description available.",
        },
        "personality": {
            "summary": personality or "No personality analysis available.",
        },
        "voice_guidance": _parse_voice_notes(char.voice_notes),
        # Relationships
        "relationships": (
            [
                {"character": name, "type": rel_type, "description": ""}
                for name, rel_type in char.relationships.items()
            ]
            if char.relationships
            else []
        ),
        # Evidence
        "evidence": char.evidence,
        # Metadata (secondary)
        "metadata": {
            "first_appearance_chapter": char.first_appearance_chapter,
            "mention_count": char.mention_count,
            "confidence": char.confidence.value,
        },
    }

    return result


def _extract_section(descriptions: list[CharacterDescription], section_name: str) -> Optional[str]:
    """Extract a section from descriptions by marker."""
    if not descriptions:
        return None

    for desc in descriptions:
        if f"**{section_name}:**" in desc.text:
            # Extract the content after the marker
            parts = desc.text.split(f"**{section_name}:**")
            if len(parts) > 1:
                # Get content until next section or end
                content = parts[1].split("**")[0].strip()
                return content

    return None


def _parse_voice_notes(voice_notes: Optional[str]) -> dict:
    """Parse voice notes string back into structured dict."""
    if not voice_notes:
        return {
            "suggested_tone": "",
            "dialect_notes": "",
            "verbal_tics": [],
            "formality_level": "moderate",
            "emotional_range": "",
            "example_quotes": [],
        }

    result = {
        "suggested_tone": "",
        "dialect_notes": "",
        "verbal_tics": [],
        "formality_level": "moderate",
        "emotional_range": "",
        "example_quotes": [],
    }

    lines = voice_notes.split("\n")
    in_quotes = False
    quotes = []

    for line in lines:
        line = line.strip()
        if line.startswith("Tone:"):
            result["suggested_tone"] = line[5:].strip()
        elif line.startswith("Dialect:"):
            result["dialect_notes"] = line[8:].strip()
        elif line.startswith("Verbal tics:"):
            # Parse quoted strings
            import re

            tics = re.findall(r'"([^"]+)"', line)
            result["verbal_tics"] = tics
        elif line.startswith("Formality:"):
            result["formality_level"] = line[10:].strip()
        elif line.startswith("Emotional range:"):
            result["emotional_range"] = line[16:].strip()
        elif line == "Example quotes:":
            in_quotes = True
        elif in_quotes and line.startswith("- "):
            quotes.append(line[2:])

    if quotes:
        result["example_quotes"] = quotes

    return result
