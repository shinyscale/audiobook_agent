"""
Character profile generator.

Generates rich character profiles from gathered passages using LLM.
"""

import json
import logging
from typing import Optional

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterRelationship,
    ProfileEvidence,
)
from .passage_gatherer import CharacterPassage, CharacterPassageGatherer
from ..chapter_detection.models import ChapterMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


PROFILE_GENERATION_SYSTEM = """You are a literary analyst creating character profiles for audiobook narration.

Your goal is to help narrators understand each character so they can voice them effectively.

Focus on:
1. APPEARANCE - What do they look like? (for narrator visualization)
2. PERSONALITY - What are their core traits? (for voice characterization)
3. VOICE - How do they speak? (for actual narration)
4. RELATIONSHIPS - Who are they connected to? (for understanding dynamics)

CRITICAL: Only include information directly supported by the provided text passages.
Include specific quotes as evidence for each claim.

Always respond with valid JSON. No other text."""


PROFILE_GENERATION_PROMPT = """Create a comprehensive character profile for audiobook narration.

CHARACTER: {name}
ALIASES: {aliases}
ROLE: {role}

RELEVANT TEXT PASSAGES:
{passages}

Generate a profile covering:

1. APPEARANCE: Physical description
   - Age indication (young adult, middle-aged, elderly, etc.)
   - Build/stature (tall, short, thin, heavy, etc.)
   - Distinguishing features (hair, eyes, smile, manner)
   - General presence/how they carry themselves

2. PERSONALITY: Character traits
   - Core personality traits (2-5 key traits)
   - Temperament (calm, volatile, nervous, steady)
   - How they treat others
   - Speech patterns (formal, casual, verbose, terse)

3. VOICE GUIDANCE: For the narrator
   - Suggested tone (aristocratic, working-class, nervous, confident)
   - Dialect or accent clues (if mentioned in text)
   - Verbal tics or catchphrases (specific words they repeat)
   - Formality level (very formal, casual, varies)
   - Emotional range (repressed, explosive, steady)
   - 2-3 example dialogue quotes that capture their voice

4. RELATIONSHIPS: Key connections
   - List important relationships (spouse, rival, friend, lover)
   - Briefly describe the dynamic of each relationship

Return JSON in this exact format:
```json
{{
  "appearance": {{
    "summary": "1-2 sentence physical description",
    "details": {{
      "age": "age indication",
      "build": "physical build",
      "distinguishing": "notable features"
    }},
    "age_indication": "young adult/middle-aged/elderly/unknown",
    "distinguishing_features": ["feature1", "feature2"],
    "evidence": ["quote supporting appearance claim"]
  }},
  "personality": {{
    "summary": "1-2 sentence personality overview",
    "traits": ["trait1", "trait2", "trait3"],
    "temperament": "calm/volatile/nervous/steady/etc",
    "speech_patterns": ["formal", "uses slang", "interrupts"],
    "evidence": ["quote supporting personality claim"]
  }},
  "voice_guidance": {{
    "suggested_tone": "Description of how to voice this character",
    "dialect_notes": "Accent or dialect indicators",
    "verbal_tics": ["catchphrase1", "repeated word"],
    "formality_level": "very formal/formal/casual/varies",
    "emotional_range": "repressed/explosive/steady",
    "example_quotes": ["\"Actual dialogue from text\"", "\"Another example\""]
  }},
  "relationships": [
    {{
      "character": "Other Character Name",
      "type": "spouse/friend/rival/lover/etc",
      "description": "Brief description of the relationship"
    }}
  ],
  "confidence": 0.8
}}
```

IMPORTANT:
- Only include information from the provided passages
- Use "unknown" or empty values if information isn't available
- Include actual quotes from passages as evidence
- Focus on what helps narrators voice the character

Return ONLY valid JSON. No other text."""


class CharacterProfileGenerator:
    """Generate rich character profiles from full text."""

    def __init__(
        self,
        llm_client: LLMClient,
        passage_gatherer: Optional[CharacterPassageGatherer] = None,
    ):
        """
        Args:
            llm_client: LLM client for profile generation
            passage_gatherer: Optional custom passage gatherer
        """
        self.llm = llm_client
        self.passage_gatherer = passage_gatherer or CharacterPassageGatherer()

    def generate_profile(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
        passages: Optional[list[CharacterPassage]] = None,
    ) -> CharacterProfile:
        """
        Generate comprehensive profile for a character.

        Args:
            character: The identified character
            full_text: Complete document text
            chapter_map: Chapter boundaries
            passages: Optional pre-gathered passages

        Returns:
            Rich CharacterProfile
        """
        # Gather passages if not provided
        if passages is None:
            passages = self.passage_gatherer.gather_passages(
                character, full_text, chapter_map
            )

        # Create base profile from identified character
        profile = CharacterProfile.from_identified(character)

        if not passages:
            logger.warning(f"No passages found for {character.canonical_name}")
            return profile

        # Format passages for prompt
        passages_text = self._format_passages(passages)

        # Generate profile via LLM
        prompt = PROFILE_GENERATION_PROMPT.format(
            name=character.canonical_name,
            aliases=", ".join(character.aliases) if character.aliases else "None",
            role=character.role,
            passages=passages_text,
        )

        result, response = self.llm.query_json(prompt, system=PROFILE_GENERATION_SYSTEM)

        if not response.success or result is None:
            logger.warning(
                f"Profile generation failed for {character.canonical_name}: {response.error}"
            )
            return profile

        # Parse and populate profile
        profile = self._parse_profile_response(profile, result, passages)

        logger.info(
            f"Generated profile for {character.canonical_name} "
            f"(confidence={profile.confidence:.2f})"
        )

        return profile

    def _format_passages(self, passages: list[CharacterPassage]) -> str:
        """Format passages for the prompt."""
        lines = []
        for i, passage in enumerate(passages, 1):
            lines.append(f"[Passage {i}, Chapter {passage.chapter_index}]")
            lines.append(passage.text)
            lines.append("")
        return "\n".join(lines)

    def _parse_profile_response(
        self,
        profile: CharacterProfile,
        result: dict,
        passages: list[CharacterPassage],
    ) -> CharacterProfile:
        """Parse LLM response and populate profile."""

        # Parse appearance
        if "appearance" in result:
            app = result["appearance"]
            profile.appearance = AppearanceProfile(
                summary=app.get("summary", ""),
                details=app.get("details", {}),
                age_indication=app.get("age_indication", "unknown"),
                distinguishing_features=app.get("distinguishing_features", []),
                evidence=app.get("evidence", []),
            )

        # Parse personality
        if "personality" in result:
            pers = result["personality"]
            profile.personality = PersonalityProfile(
                summary=pers.get("summary", ""),
                traits=pers.get("traits", []),
                temperament=pers.get("temperament", "unknown"),
                speech_patterns=pers.get("speech_patterns", []),
                evidence=pers.get("evidence", []),
            )

        # Parse voice guidance
        if "voice_guidance" in result:
            voice = result["voice_guidance"]
            profile.voice_guidance = VoiceGuidance(
                suggested_tone=voice.get("suggested_tone", ""),
                dialect_notes=voice.get("dialect_notes", ""),
                verbal_tics=voice.get("verbal_tics", []),
                formality_level=voice.get("formality_level", "moderate"),
                emotional_range=voice.get("emotional_range", ""),
                example_quotes=voice.get("example_quotes", []),
            )

        # Parse relationships
        if "relationships" in result:
            profile.relationships = []
            for rel in result.get("relationships", []):
                if rel.get("character"):
                    profile.relationships.append(CharacterRelationship(
                        character=rel["character"],
                        relationship_type=rel.get("type", ""),
                        description=rel.get("description", ""),
                    ))

        # Set confidence
        profile.confidence = result.get("confidence", 0.7)

        # Determine mention frequency from passages
        num_passages = len(passages)
        if num_passages >= 10:
            profile.mention_frequency = "frequent"
        elif num_passages >= 5:
            profile.mention_frequency = "moderate"
        elif num_passages >= 2:
            profile.mention_frequency = "occasional"
        else:
            profile.mention_frequency = "rare"

        return profile


def generate_character_profile(
    character: IdentifiedCharacter,
    full_text: str,
    chapter_map: ChapterMap,
    llm_client: LLMClient,
) -> CharacterProfile:
    """
    Convenience function to generate a character profile.

    Args:
        character: The identified character
        full_text: Complete document text
        chapter_map: Chapter boundaries
        llm_client: LLM client

    Returns:
        Rich CharacterProfile
    """
    generator = CharacterProfileGenerator(llm_client)
    return generator.generate_profile(character, full_text, chapter_map)
