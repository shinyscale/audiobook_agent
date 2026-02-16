"""
Character profile generator.

Generates rich character profiles from gathered passages using LLM.

Feature F2: Summary-Derived Profile Evidence
Summary evidence is included as PRIMARY evidence, ranked above raw text mentions.

Feature F3: Moral Valence Propagation to Profiles
Moral valence classification is passed to profile generator as HARD CONSTRAINT.
ANTAGONIST classification prevents positive descriptors in generated profiles.
"""

import logging
from typing import Optional

from ..chapter_detection.models import ChapterMap
from ..chapter_summary.models import ChapterSummaryMap
from ..llm import LLMClient
from .models import (
    ActionAnalysis,
    AppearanceProfile,
    CharacterProfile,
    CharacterRelationship,
    IdentifiedCharacter,
    PersonalityProfile,
    VoiceGuidance,
)
from .moral_valence import MoralValence, MoralValenceResult
from .passage_gatherer import CharacterPassage, CharacterPassageGatherer
from .summary_evidence import CharacterSummaryEvidence, SummaryEvidenceExtractor

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

ANTI-HALLUCINATION (Feature F19):
- NEVER invent backstory, relationships, or traits not in the provided text
- NEVER conflate character names with places, organizations, or other entities
- If the passages don't support a claim, don't make it - use "unknown" instead
- Every evidence quote must be traceable to the provided passages

Always respond with valid JSON. No other text."""


PROFILE_GENERATION_PROMPT = """Create a comprehensive character profile for audiobook narration.

CHARACTER: {name}
ALIASES: {aliases}
ROLE: {role}
{moral_valence_constraint}
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

ANTI-HALLUCINATION RULES (Feature F19):
- NEVER invent information not explicitly stated in the provided passages
- NEVER conflate character names with location names (e.g., "Mrs. Roosevelt" is not about the White House)
- Every claim in the profile MUST be traceable to a specific passage
- If you're uncertain about something, leave it as "unknown" rather than guessing
- Do NOT assume background or history not explicitly mentioned
- The "evidence" arrays MUST contain actual quotes from the provided passages

Return ONLY valid JSON. No other text."""


# Moral valence constraint templates (Feature F3)
MORAL_VALENCE_CONSTRAINTS = {
    MoralValence.ANTAGONIST: """
=== HARD CONSTRAINT: ANTAGONIST ===
This character has been classified as an ANTAGONIST based on their actions.
DO NOT USE positive descriptors like: effective, composed, capable, charming, attractive, pleasant
DO USE negative/neutral descriptors that reflect harmful behavior: manipulative, dangerous, cruel, calculating, cold
The profile MUST reflect their harmful nature. Any positive traits should be secondary to their villainous actions.
""",
    MoralValence.PROTAGONIST: """
=== MORAL CLASSIFICATION: PROTAGONIST ===
This character has been classified as a PROTAGONIST based on their actions.
The profile should emphasize their positive qualities and heroic actions.
""",
    MoralValence.MORALLY_AMBIGUOUS: """
=== MORAL CLASSIFICATION: MORALLY AMBIGUOUS ===
This character has been classified as MORALLY AMBIGUOUS - they perform both harmful and beneficial actions.
The profile should reflect this complexity without favoring either aspect.
""",
    MoralValence.VICTIM: """
=== MORAL CLASSIFICATION: VICTIM ===
This character has been classified primarily as a VICTIM of others' actions.
The profile should acknowledge their suffering and any agency they maintain.
""",
}


def _format_moral_valence_constraint(moral_valence: Optional[MoralValenceResult]) -> str:
    """Format moral valence as a hard constraint for profile generation (Feature F3)."""
    if moral_valence is None:
        return ""

    constraint = MORAL_VALENCE_CONSTRAINTS.get(moral_valence.valence, "")

    if constraint and moral_valence.key_actions:
        actions_text = "\n".join(f"  - {a.get('action', a)}" for a in moral_valence.key_actions[:5])
        constraint += f"\nKEY ACTIONS supporting this classification:\n{actions_text}\n"

    return constraint


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
        moral_valence: Optional[MoralValenceResult] = None,
        narrative_style: str = "unknown",
    ) -> CharacterProfile:
        """
        Generate comprehensive profile for a character.

        Args:
            character: The identified character
            full_text: Complete document text
            chapter_map: Chapter boundaries
            passages: Optional pre-gathered passages
            summary_evidence: Optional pre-extracted summary evidence (Feature F2)
            moral_valence: Optional moral valence classification (Feature F3)
                          When provided, acts as HARD CONSTRAINT on profile generation
            narrative_style: Narrative style for first-person evidence extraction

        Returns:
            Rich CharacterProfile
        """
        # Gather passages if not provided
        if passages is None:
            passages = self.passage_gatherer.gather_passages(
                character,
                full_text,
                chapter_map,
                narrative_style=narrative_style,
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
                is_narrator=character.is_narrator,
                narrative_style=narrative_style,
            )

        # Format evidence for prompt
        summary_evidence_text = ""
        if summary_evidence and summary_evidence.evidence:
            summary_evidence_text = summary_evidence.format_for_prompt()
            logger.info(
                f"Including {len(summary_evidence.evidence)} summary evidence items "
                f"for {character.canonical_name}"
            )

        # Format moral valence constraint (Feature F3)
        moral_valence_text = _format_moral_valence_constraint(moral_valence)
        if moral_valence and moral_valence.valence != MoralValence.UNCERTAIN:
            logger.info(
                f"Applying moral valence constraint {moral_valence.valence.value} "
                f"for {character.canonical_name}"
            )

        # Format passages for prompt
        passages_text = self._format_passages(passages)

        # Generate profile via LLM
        prompt = PROFILE_GENERATION_PROMPT.format(
            name=character.canonical_name,
            aliases=", ".join(character.aliases) if character.aliases else "None",
            role=character.role,
            moral_valence_constraint=moral_valence_text,
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
        profile = self._parse_profile_response(profile, result, passages, character.canonical_name)

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
        character_name: str = "Unknown",
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
                    profile.relationships.append(
                        CharacterRelationship(
                            character=rel["character"],
                            relationship_type=rel.get("type", ""),
                            description=rel.get("description", ""),
                        )
                    )

        # Set confidence (F14: warn when missing)
        confidence_raw = result.get("confidence")
        if confidence_raw is None:
            logger.warning(
                f"Profile generation for '{character_name}' did not return confidence - "
                "using conservative default 0.6"
            )
            profile.confidence = 0.6
        else:
            profile.confidence = float(confidence_raw)

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

        # F19: Validate evidence grounding - warn about potential hallucinations
        self._validate_evidence_grounding(profile, passages, character_name)

        return profile

    def _validate_evidence_grounding(
        self,
        profile: CharacterProfile,
        passages: list[CharacterPassage],
        character_name: str,
    ) -> None:
        """
        F19: Validate that evidence claims are grounded in the source text.

        Logs warnings for potential hallucinations where evidence quotes
        don't appear in the provided passages.
        """
        # Combine all passage text for validation
        all_passage_text = " ".join(p.text.lower() for p in passages)

        def check_evidence(section_name: str, evidence: list[str]) -> int:
            """Check evidence quotes against passage text, return ungrounded count."""
            ungrounded = 0
            for quote in evidence:
                # Normalize quote for matching
                quote_lower = quote.lower().strip().strip("\"'")
                if len(quote_lower) < 10:
                    continue  # Skip very short quotes

                # Check if quote appears in passages (allow some flexibility)
                if quote_lower not in all_passage_text:
                    # Try partial match (first 30 chars)
                    partial = quote_lower[:30]
                    if partial not in all_passage_text:
                        ungrounded += 1
                        logger.debug(
                            f"F19: Potentially ungrounded evidence for {character_name} "
                            f"in {section_name}: '{quote[:50]}...'"
                        )
            return ungrounded

        total_ungrounded = 0

        # Check each profile section's evidence
        if profile.action_analysis and profile.action_analysis.evidence:
            total_ungrounded += check_evidence("action_analysis", profile.action_analysis.evidence)

        if profile.appearance and profile.appearance.evidence:
            total_ungrounded += check_evidence("appearance", profile.appearance.evidence)

        if profile.personality and profile.personality.evidence:
            total_ungrounded += check_evidence("personality", profile.personality.evidence)

        if total_ungrounded > 0:
            logger.warning(
                f"F19: Profile for '{character_name}' has {total_ungrounded} potentially "
                f"ungrounded evidence quotes - may indicate hallucination"
            )


def generate_character_profile(
    character: IdentifiedCharacter,
    full_text: str,
    chapter_map: ChapterMap,
    llm_client: LLMClient,
    summary_map: Optional[ChapterSummaryMap] = None,
    moral_valence: Optional[MoralValenceResult] = None,
    narrative_style: str = "unknown",
) -> CharacterProfile:
    """
    Convenience function to generate a character profile.

    Args:
        character: The identified character
        full_text: Complete document text
        chapter_map: Chapter boundaries
        llm_client: LLM client
        summary_map: Optional chapter summaries for summary evidence (Feature F2)
        moral_valence: Optional moral valence constraint (Feature F3)
        narrative_style: Narrative style for first-person evidence extraction

    Returns:
        Rich CharacterProfile
    """
    generator = CharacterProfileGenerator(llm_client, summary_map=summary_map)
    return generator.generate_profile(
        character,
        full_text,
        chapter_map,
        moral_valence=moral_valence,
        narrative_style=narrative_style,
    )
