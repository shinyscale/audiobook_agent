"""
Character profile generator.

Generates rich character profiles from gathered passages using LLM.

Feature F2: Summary-Derived Profile Evidence
Summary evidence is included as PRIMARY evidence, ranked above raw text mentions.
"""

import json
import logging
from typing import Optional

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    ActionAnalysis,
    AppearanceProfile,
    PersonalityProfile,
    VoiceGuidance,
    CharacterRelationship,
    ProfileEvidence,
)
from .passage_gatherer import CharacterPassage, CharacterPassageGatherer
from .summary_evidence import CharacterSummaryEvidence, SummaryEvidenceExtractor
from ..chapter_detection.models import ChapterMap
from ..chapter_summary.models import ChapterSummaryMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


PROFILE_GENERATION_SYSTEM = """You are a literary analyst creating character profiles for audiobook narration.

CRITICAL PRINCIPLE: CHARACTER = ACTIONS
A character is defined by what they DO, not how they are DESCRIBED.
A beautiful character can be a monster. A physically ugly character can be heroic.

EVIDENCE PRIORITY ORDER (highest to lowest):
1. SUMMARY EVIDENCE (highest weight) - Facts from chapter summaries are CONFIRMED plot events
2. ACTIONS (very high weight) - What the character DOES (murders, helps, betrays, protects)
3. SPEECH (high weight) - What the character SAYS and how they say it
4. RELATIONSHIPS (medium weight) - How they treat and interact with others
5. DESCRIPTIONS (lowest weight) - How they LOOK or are described physically

IMPORTANT: Summary evidence represents CONFIRMED facts about what happens in the story.
If a chapter summary says a character "poisons" or "murders" someone, this is a FACT
that MUST be reflected prominently in the profile.

IMPORTANT RULES:
- Summary evidence ALWAYS takes priority over raw text interpretations
- If actions contradict descriptions, ACTIONS WIN
- "Beautiful" or "charming" descriptions do NOT indicate moral goodness
- Harmful actions (murder, manipulation, cruelty, abuse) MUST dominate the profile
- Backstory explains but does NOT excuse harmful actions

Your goal is to help narrators understand each character for voice work.

CRITICAL: Prioritize SUMMARY EVIDENCE when available. Include specific quotes as evidence.

Always respond with valid JSON. No other text."""


PROFILE_GENERATION_PROMPT = """Create a comprehensive character profile for audiobook narration.

CHARACTER: {name}
ALIASES: {aliases}
ROLE: {role}

{summary_evidence}
RELEVANT TEXT PASSAGES:
{passages}

=== THREE-PHASE ANALYSIS ===

PHASE 1: ACTION ANALYSIS (Most Important)
First, identify and categorize ALL significant actions this character takes:
- HARMFUL: murder, assault, manipulation, deception, cruelty, abuse, betrayal, theft
- BENEFICIAL: helping others, sacrifice, protection, honesty, kindness, healing
- NEUTRAL: daily activities, travel, work, observation

PHASE 2: PERSONALITY FROM ACTIONS
Derive personality traits from the action analysis:
- If primarily HARMFUL actions → describe the character as villainous/antagonistic
- If primarily BENEFICIAL actions → describe the character as heroic/protagonistic
- If mixed significant HARMFUL and BENEFICIAL → describe as morally ambiguous

PHASE 3: SURFACE DETAILS (Lowest Priority)
Only after analyzing actions, note physical appearance and other surface details.
These should NEVER override the action-based assessment.

=== OUTPUT FORMAT ===

Return JSON in this exact format:
```json
{{
  "action_analysis": {{
    "harmful_actions": ["specific harmful action 1", "specific harmful action 2"],
    "beneficial_actions": ["specific beneficial action 1"],
    "neutral_actions": ["neutral action"],
    "dominant_pattern": "harmful/beneficial/mixed/neutral",
    "evidence": ["quote showing action"]
  }},
  "personality": {{
    "summary": "1-2 sentence overview - LEAD with action-based assessment",
    "traits": ["trait derived from actions", "another trait from actions"],
    "temperament": "calm/volatile/nervous/steady/etc",
    "moral_alignment": "heroic/villainous/morally ambiguous/neutral",
    "key_behaviors": "Description focusing on WHAT THEY DO and how they treat others",
    "speech_patterns": ["formal", "uses slang", "interrupts"],
    "evidence": ["quote supporting personality claim"]
  }},
  "appearance": {{
    "summary": "1-2 sentence physical description (LOW PRIORITY)",
    "details": {{
      "age": "age indication",
      "build": "physical build",
      "distinguishing": "notable features"
    }},
    "age_indication": "young adult/middle-aged/elderly/unknown",
    "distinguishing_features": ["feature1", "feature2"],
    "evidence": ["quote supporting appearance claim"]
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

CRITICAL RULES:
- The personality summary MUST lead with action-based traits, not physical descriptions
- If a character murders, manipulates, or harms others, this MUST be prominent
- "Beautiful" or "charming" descriptions do NOT make someone good
- Appearance evidence is LOW PRIORITY - actions and behavior are HIGH PRIORITY
- Only include information from the provided passages
- Use "unknown" or empty values if information isn't available

Return ONLY valid JSON. No other text."""


class CharacterProfileGenerator:
    """Generate rich character profiles from full text."""

    def __init__(
        self,
        llm_client: LLMClient,
        passage_gatherer: Optional[CharacterPassageGatherer] = None,
        summary_map: Optional[ChapterSummaryMap] = None,
    ):
        """
        Args:
            llm_client: LLM client for profile generation
            passage_gatherer: Optional custom passage gatherer
            summary_map: Optional chapter summary map for summary evidence (Feature F2)
        """
        self.llm = llm_client
        self.passage_gatherer = passage_gatherer or CharacterPassageGatherer()
        self.summary_map = summary_map
        self.summary_extractor = SummaryEvidenceExtractor(llm_client) if summary_map else None

    def generate_profile(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
        passages: Optional[list[CharacterPassage]] = None,
        summary_evidence: Optional[CharacterSummaryEvidence] = None,
    ) -> CharacterProfile:
        """
        Generate comprehensive profile for a character.

        Args:
            character: The identified character
            full_text: Complete document text
            chapter_map: Chapter boundaries
            passages: Optional pre-gathered passages
            summary_evidence: Optional pre-extracted summary evidence (Feature F2)

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

        # Extract summary evidence if available (Feature F2)
        if summary_evidence is None and self.summary_map is not None:
            summary_evidence = self.summary_extractor.extract_evidence(
                character.canonical_name,
                character.aliases,
                self.summary_map,
            )

        # Format evidence for prompt
        summary_evidence_text = ""
        if summary_evidence and summary_evidence.evidence:
            summary_evidence_text = summary_evidence.format_for_prompt()
            logger.info(
                f"Including {len(summary_evidence.evidence)} summary evidence items "
                f"for {character.canonical_name}"
            )

        # Format passages for prompt
        passages_text = self._format_passages(passages)

        # Generate profile via LLM
        prompt = PROFILE_GENERATION_PROMPT.format(
            name=character.canonical_name,
            aliases=", ".join(character.aliases) if character.aliases else "None",
            role=character.role,
            summary_evidence=summary_evidence_text,
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

        # Parse action analysis (Feature F3 - primary for moral assessment)
        if "action_analysis" in result:
            aa = result["action_analysis"]
            profile.action_analysis = ActionAnalysis(
                harmful_actions=aa.get("harmful_actions", []),
                beneficial_actions=aa.get("beneficial_actions", []),
                neutral_actions=aa.get("neutral_actions", []),
                dominant_pattern=aa.get("dominant_pattern", "unknown"),
                evidence=aa.get("evidence", []),
            )

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
                moral_alignment=pers.get("moral_alignment", "unknown"),
                key_behaviors=pers.get("key_behaviors", ""),
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
    summary_map: Optional[ChapterSummaryMap] = None,
) -> CharacterProfile:
    """
    Convenience function to generate a character profile.

    Args:
        character: The identified character
        full_text: Complete document text
        chapter_map: Chapter boundaries
        llm_client: LLM client
        summary_map: Optional chapter summaries for summary evidence (Feature F2)

    Returns:
        Rich CharacterProfile
    """
    generator = CharacterProfileGenerator(llm_client, summary_map=summary_map)
    return generator.generate_profile(character, full_text, chapter_map)
