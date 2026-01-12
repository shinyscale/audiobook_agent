"""
Character reconciliation.

Final safety check for duplicate characters after profile generation.
Uses LLM to identify and merge any remaining duplicates.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .models import CharacterProfile, AppearanceProfile, PersonalityProfile, VoiceGuidance, CharacterRelationship
from ..llm import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class DuplicatePair:
    """A pair of characters identified as duplicates."""
    name1: str
    name2: str
    reason: str
    confidence: float


RECONCILIATION_SYSTEM = """You are a literary analyst checking for duplicate character entries.

CRITICAL RULES:
1. Family members with same last name are DIFFERENT people (keep separate)
   - Example: "Mr. Wilson" and "Mrs. Wilson" are husband and wife - DIFFERENT
   - Example: "Tom Buchanan" and "Daisy Buchanan" are married - DIFFERENT

2. Birth name and assumed name are the SAME person (merge)
   - Example: "James Gatz" and "Jay Gatsby" - SAME person
   - Example: "Saul" and "Paul" (biblical) - SAME person

3. Different first names are DIFFERENT people (keep separate)
   - Example: "George Wilson" and "Myrtle Wilson" - DIFFERENT
   - Example: "Nick" and "Tom" - DIFFERENT

4. First name and formal name may be SAME person (check context)
   - Example: "Myrtle" and "Mrs. Wilson" - could be SAME (need context)
   - Example: "Jay" and "Mr. Gatsby" - SAME person

Only flag duplicates when you are CONFIDENT. When in doubt, keep separate.

Always respond with valid JSON. No other text."""


RECONCILIATION_PROMPT = """Review this character list for any duplicate entries (same person listed twice).

CHARACTER LIST:
{character_summary}

For each character, consider:
- Could this be the same person as another character under a different name?
- Are there any birth name / assumed name pairs?
- Are there any first-name / formal-name pairs for the same person?

IMPORTANT:
- Only flag CLEAR duplicates where you are confident
- Family members with same last name are DIFFERENT people (do not merge)
- Different first names usually means different people (keep separate)
- When in doubt, keep characters separate

Return JSON:
```json
{{
  "duplicates": [
    {{
      "name1": "Character A name",
      "name2": "Character B name",
      "reason": "Why you believe these are the same person",
      "confidence": 0.0-1.0
    }}
  ],
  "analysis": "Brief summary of your review"
}}
```

If no duplicates found, return empty duplicates array.

Return ONLY valid JSON. No other text."""


class CharacterReconciler:
    """Final safety check for duplicate characters."""

    def __init__(self, llm_client: LLMClient, confidence_threshold: float = 0.85):
        """
        Args:
            llm_client: LLM client for reconciliation
            confidence_threshold: Minimum confidence to merge duplicates
        """
        self.llm = llm_client
        self.confidence_threshold = confidence_threshold

    def reconcile(
        self,
        profiles: list[CharacterProfile],
    ) -> list[CharacterProfile]:
        """
        Check for and merge any duplicate characters.

        This is a SAFETY NET, not the primary mechanism.
        Most duplicates should already be handled by
        summary-driven identification.

        Args:
            profiles: List of character profiles

        Returns:
            Reconciled list of profiles (duplicates merged)
        """
        if len(profiles) <= 1:
            return profiles

        # Build summary for LLM review
        char_summary = self._build_character_summary(profiles)

        prompt = RECONCILIATION_PROMPT.format(character_summary=char_summary)

        result, response = self.llm.query_json(prompt, system=RECONCILIATION_SYSTEM)

        if not response.success or result is None:
            logger.warning(f"Reconciliation LLM call failed: {response.error}")
            return profiles

        # Parse duplicates
        duplicates = self._parse_duplicates(result)

        if not duplicates:
            logger.info("No duplicates found during reconciliation")
            return profiles

        # Merge high-confidence duplicates
        merged_profiles = profiles.copy()
        for dup in duplicates:
            if dup.confidence >= self.confidence_threshold:
                logger.info(
                    f"Merging duplicate characters: {dup.name1} + {dup.name2} "
                    f"(confidence={dup.confidence:.2f}, reason={dup.reason})"
                )
                merged_profiles = self._merge_profiles(merged_profiles, dup.name1, dup.name2)
            else:
                logger.info(
                    f"Skipping low-confidence duplicate: {dup.name1} + {dup.name2} "
                    f"(confidence={dup.confidence:.2f})"
                )

        return merged_profiles

    def _build_character_summary(self, profiles: list[CharacterProfile]) -> str:
        """Build a summary of characters for LLM review."""
        lines = []
        for i, profile in enumerate(profiles, 1):
            aliases_str = ", ".join(profile.aliases) if profile.aliases else "None"
            lines.append(f"{i}. {profile.canonical_name}")
            lines.append(f"   Aliases: {aliases_str}")
            lines.append(f"   Role: {profile.role}")
            if profile.appearance.summary:
                lines.append(f"   Appearance: {profile.appearance.summary[:100]}")
            if profile.relationships:
                rels = ", ".join([f"{r.character} ({r.relationship_type})" for r in profile.relationships[:3]])
                lines.append(f"   Relationships: {rels}")
            lines.append("")
        return "\n".join(lines)

    def _parse_duplicates(self, result: dict) -> list[DuplicatePair]:
        """Parse LLM response for duplicate pairs."""
        duplicates = []
        for dup in result.get("duplicates", []):
            name1 = dup.get("name1", "")
            name2 = dup.get("name2", "")
            if name1 and name2:
                duplicates.append(DuplicatePair(
                    name1=name1,
                    name2=name2,
                    reason=dup.get("reason", ""),
                    confidence=dup.get("confidence", 0.5),
                ))
        return duplicates

    def _merge_profiles(
        self,
        profiles: list[CharacterProfile],
        name1: str,
        name2: str,
    ) -> list[CharacterProfile]:
        """
        Merge two character profiles into one.

        The character with more complete information is kept as primary.
        """
        profile1 = self._find_profile(profiles, name1)
        profile2 = self._find_profile(profiles, name2)

        if not profile1 or not profile2:
            logger.warning(f"Could not find profiles to merge: {name1}, {name2}")
            return profiles

        if profile1 == profile2:
            logger.warning(f"Same profile matched for both names: {name1}, {name2}")
            return profiles

        # Determine which profile has more information (keep as primary)
        score1 = self._profile_completeness_score(profile1)
        score2 = self._profile_completeness_score(profile2)

        if score1 >= score2:
            primary, secondary = profile1, profile2
        else:
            primary, secondary = profile2, profile1

        # Merge aliases
        merged_aliases = list(set(primary.aliases + secondary.aliases + [secondary.canonical_name]))
        # Remove primary name if it ended up in aliases
        merged_aliases = [a for a in merged_aliases if a != primary.canonical_name]

        # Merge relationships (avoid duplicates)
        existing_rel_chars = {r.character.lower() for r in primary.relationships}
        for rel in secondary.relationships:
            if rel.character.lower() not in existing_rel_chars:
                primary.relationships.append(rel)

        # Use more complete sub-profiles
        if not primary.appearance.summary and secondary.appearance.summary:
            primary.appearance = secondary.appearance
        if not primary.personality.summary and secondary.personality.summary:
            primary.personality = secondary.personality
        if not primary.voice_guidance.suggested_tone and secondary.voice_guidance.suggested_tone:
            primary.voice_guidance = secondary.voice_guidance

        # Merge chapters present
        merged_chapters = sorted(set(primary.chapters_present + secondary.chapters_present))

        # Update primary profile
        primary.aliases = merged_aliases
        primary.chapters_present = merged_chapters

        # Update confidence (lower due to merge)
        primary.confidence = min(primary.confidence, secondary.confidence) * 0.95

        # Remove secondary from list
        return [p for p in profiles if p != secondary]

    def _find_profile(self, profiles: list[CharacterProfile], name: str) -> Optional[CharacterProfile]:
        """Find profile by canonical name or alias."""
        name_lower = name.lower()
        for profile in profiles:
            if profile.canonical_name.lower() == name_lower:
                return profile
            if any(alias.lower() == name_lower for alias in profile.aliases):
                return profile
        return None

    def _profile_completeness_score(self, profile: CharacterProfile) -> float:
        """Score how complete a profile is (for merge priority)."""
        score = 0.0

        if profile.appearance.summary:
            score += 1.0
        if profile.personality.summary:
            score += 1.0
        if profile.voice_guidance.suggested_tone:
            score += 1.0
        if profile.relationships:
            score += 0.5
        if profile.aliases:
            score += 0.2 * len(profile.aliases)
        if profile.chapters_present:
            score += 0.1 * len(profile.chapters_present)

        return score


def reconcile_characters(
    profiles: list[CharacterProfile],
    llm_client: LLMClient,
    confidence_threshold: float = 0.85,
) -> list[CharacterProfile]:
    """
    Convenience function for character reconciliation.

    Args:
        profiles: List of character profiles
        llm_client: LLM client
        confidence_threshold: Minimum confidence to merge duplicates

    Returns:
        Reconciled list of profiles
    """
    reconciler = CharacterReconciler(llm_client, confidence_threshold)
    return reconciler.reconcile(profiles)
