"""
Cross-chapter character consensus builder.

Merges character proposals across chapters, resolves aliases,
and produces the final CharacterMap.
"""

import re
import hashlib
import time
from typing import Optional, Iterable
from collections import defaultdict
from difflib import SequenceMatcher
import logging

from .models import (
    CharacterProposal,
    CharacterValidationResult,
    Character,
    CharacterMap,
    CharacterMention,
    CharacterType,
)
from .constants import are_potential_nicknames, get_nickname_variants
from ..llm import LLMClient

logger = logging.getLogger(__name__)

# Character classification prompts
CHARACTER_TYPE_SYSTEM = """You are a literary analyst classifying character types.

Classify each character as one of:
- STORY: An active participant in the narrative who appears in scenes, speaks dialogue, or takes actions
- HISTORICAL: A real historical figure mentioned in passing (e.g., Napoleon, Einstein)
- REFERENCED: A fictional character from other works mentioned in passing (e.g., Hamlet, Sherlock Holmes)

Return ONLY valid JSON. No other text."""

CHARACTER_TYPE_PROMPT = """Classify this character's role in the narrative.

CHARACTER: {name}
MENTION COUNT: {mention_count}
CHAPTERS PRESENT: {chapters}
SAMPLE CONTEXTS:
{contexts}

Based on the contexts, determine if this character:
1. Actively participates (speaks, acts, appears in scenes) → STORY
2. Is a real historical figure mentioned in passing → HISTORICAL
3. Is a fictional character from other works → REFERENCED

Return JSON:
{{
  "character_type": "story" | "historical" | "referenced",
  "confidence": 0.0-1.0,
  "reason": "brief justification"
}}"""

# Common titles that should be ignored when comparing character names
# These are not part of the actual name but indicate social status or role
TITLES = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord', 'professor', 'captain', 'major'}

# Epithet alias resolution prompt
EPITHET_ALIAS_SYSTEM = """You are a literary analyst identifying whether different descriptive handles (epithets) refer to the SAME unnamed character.

Descriptive handles are phrases like "the creature", "the monster", "the old man", "the detective".

CRITICAL RULES:
1. Only merge epithets that CLEARLY refer to the same entity with HIGH CONFIDENCE
2. Use chapter appearances and context clues to verify they're the same character
3. Different descriptive characters (e.g., "the old man" in cottage vs "the old man" at inn) should NOT be merged
4. Generic phrases that could refer to anyone should NOT be merged together

Return ONLY valid JSON. No other text."""

EPITHET_ALIAS_PROMPT = """Identify which descriptive handles refer to the SAME unnamed character.

DESCRIPTIVE HANDLES (with chapter info and sample contexts):
{epithets}

For each group of handles that refer to the SAME entity:
1. Pick the most specific/unique handle as canonical (e.g., "the creature" over "the monster")
2. List all other handles as aliases

Return JSON array:
```json
[
  {{"canonical": "the creature", "aliases": ["the monster", "the wretch", "the fiend"]}},
  {{"canonical": "the old man", "aliases": []}}
]
```

Return ONLY the JSON array. Include only handles you're confident about - omit uncertain ones."""

# Cross-group (epithet-to-proper-name) resolution prompt
CROSS_GROUP_SYSTEM = """You are a literary analyst identifying whether descriptive handles (epithets) refer to named characters.

Examples:
- "the prince" might refer to "Prince Prospero"
- "the duke" might refer to "Prince Prospero" (if the story mentions he's also a duke)
- "the creature" might refer to "Adam" (if named)
- "my father" might refer to "Alphonse Frankenstein"

CRITICAL RULES:
1. Only link when context CLEARLY indicates they're the same person
2. Use chapter co-appearances and context clues
3. Titles/roles (the king, the general, my father) can refer to properly-named characters
4. Generic epithets that could be anyone should NOT be linked
5. DO NOT link if the epithet and proper name are in CONFLICT, OPPOSITION, or CONFRONTATION
   - If context shows them interacting as separate entities, they are different people
   - Examples: "the intruder" confronting "Prince Prospero", "the stranger" fighting "the hero"
6. DO NOT link if one entity DIES in interaction with the other entity
   - If context shows one character dying near/after encountering the other, they are DIFFERENT people
   - Examples: "fell prostrate in death" near another entity, "killed by" another entity
   - Death in proximity to another character means they cannot be the same person

Return ONLY valid JSON. No other text."""

CROSS_GROUP_PROMPT = """Identify which descriptive handles refer to properly-named characters.

DESCRIPTIVE HANDLES:
{epithets}

NAMED CHARACTERS:
{proper_names}

IMPORTANT: Read the context snippets carefully. If an epithet and proper name appear in contexts showing them as SEPARATE ENTITIES (confronting, fighting, observing each other), DO NOT link them.

For each epithet that CLEARLY refers to a named character, return a match.

Return JSON array:
```json
[
  {{"epithet": "the prince", "proper_name": "Prince Prospero"}},
  {{"epithet": "my father", "proper_name": "Alphonse Frankenstein"}}
]
```

Return ONLY the JSON array. Include only matches you're confident about - omit uncertain ones."""

PAIRWISE_ALIAS_SYSTEM = """You are a literary analyst identifying whether two character names refer to the SAME PERSON.

CRITICAL:
- Use ONLY the evidence provided below (chapter appearances and context snippets).
- Be conservative: false negatives (missing an alias) are better than false positives (merging different people).
- Titles (Mr/Mrs/Miss/Dr/etc.) are not part of the name; treat them as address forms.
- DEATH RULE: If one name KILLS or CAUSES THE DEATH of the other name in the context, they are DIFFERENT people.
- CONFRONTATION RULE: If the contexts show one name physically attacking, confronting with a weapon, or fighting against the other name, they are likely DIFFERENT people.

Return ONLY valid JSON. No other text."""

PAIRWISE_ALIAS_PROMPT = """Decide whether these two names refer to the SAME PERSON in this novel.

NAME A: {name_a}
MENTIONS A: {mentions_a}
CHAPTERS A: {chapters_a}
CONTEXT A:
{contexts_a}

NAME B: {name_b}
MENTIONS B: {mentions_b}
CHAPTERS B: {chapters_b}
CONTEXT B:
{contexts_b}

Rules:
- Only say same_person=true if there is strong evidence they are the same character (name overlap, title variants, obvious nickname/full-name relationship, or clear contextual cues).
- If the only overlap is a last name, be VERY cautious (family members/spouses share last names).
- If they never appear in overlapping chapters, be cautious unless it's clearly a full-name/short-name relationship.
- DEATH/VIOLENCE: If the context shows one name killing, causing the death of, or physically attacking the other with a weapon, they are DIFFERENT people. Example: if the context says "X stabbed Y and Y died" then X and Y are separate characters.
- ANTAGONISTIC RELATIONSHIP: If the contexts show one name as an antagonist, enemy, or threat to the other, they are likely DIFFERENT people.

Return JSON:
{{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "canonical": "Which of the two names should be canonical if same_person=true (must be exactly one of the provided names)",
  "alias": "The other name if same_person=true (must be exactly one of the provided names)",
  "reason": "brief justification"
}}"""


ALIAS_RESOLUTION_SYSTEM = """You are a literary analyst identifying character aliases.

Your task is to determine which character names refer to the SAME PERSON.

IMPORTANT: Titles, ranks, and honorifics should be IGNORED when matching names.
The underlying PERSON is what matters, not how they're addressed. Examples:
- Military: "SSgt Otto" = "Staff Sergeant Mark Otto" = "Mark Otto" (but NOT just "Otto" alone)
- Civilian: "Mr. Smith" = "John Smith" (but NOT just "Smith" alone - could be family member)
- Religious: "Father O'Brien" = "Patrick O'Brien" (but NOT just "O'Brien" alone)
- Academic: "Professor Williams" = "Dr. Williams" = "Jane Williams"

CRITICAL RULES - BE CONSERVATIVE:
1. Only merge names if they CLEARLY refer to the same individual with HIGH CONFIDENCE
2. Different people with similar names should NEVER be merged
3. Pay close attention to chapter appearances and context clues
4. When in doubt, keep names SEPARATE - false negatives are better than false positives
5. A bare FIRST name can merge with a full name (e.g., "Mike" → "Michael Anderson")
6. A bare LAST name is RISKY - only merge if you're absolutely certain (could be family member)

For the canonical name, prefer the FULL CIVILIAN NAME (first + last) over titled versions.

NEVER merge:
- Different characters who happen to share only a first name (e.g., two characters named Michael)
- Different characters who share ONLY a last name (family members, spouses, siblings)
  - "Mr. Anderson" (father) ≠ "Michael" (son) even if both are Andersons
  - "Robert Wilson" ≠ "Mrs. Wilson" (his wife Emma)
- Characters who appear in completely different parts of the book with no overlap
- Names that are clearly different major characters (check mention counts - if both have 50+ mentions, they're probably separate people!)

BE EXTREMELY CAUTIOUS WITH:
- Bare last names (could be family members)
- Gendered titles (Mr. vs Mrs. vs Miss suggests different people)
- Characters with similar but different names (e.g., "Michael" vs "Michelle")

SPECIFIC ANTI-PATTERNS (DO NOT MERGE):
- Different first names + same last name (likely family members): spouses, siblings, parents/children
- Single-word names with no overlap: completely different characters with unrelated names
- Characters who co-occur but have different identities: appearing together ≠ being the same person

ONLY merge when confident:
1. Full name + partial name: full name contains the partial name as a component
2. Title variations: titled form and untitled form of the same name
3. Obvious nickname patterns: common nickname/full name pairs

CRITICAL MERGE PATTERNS:

MERGE these patterns (HIGH CONFIDENCE):
- Full name variations: "FirstName LastName" = "LastName" = "Title LastName"
- Nickname patterns: Shortened forms or diminutives of the same character
- Birth/married names: Known alternate names for the same person (when contextually clear)

DO NOT MERGE these patterns:
- Title-only matches: Characters sharing only a title but different last names are DIFFERENT people
- Family members: Different first names + same last name typically indicates spouses, siblings, or family (separate characters)
- Similar titles: Same professional title (Professor, Doctor, Captain) doesn't indicate same person

CONTEXTUAL CLUES to consider:
- Relationship descriptors: "his/her spouse", "his/her parent", "his/her sibling" indicate SEPARATE characters
- Gendered pronouns: Consistent he/she usage helps distinguish characters with ambiguous names
- First-person narrative: First-person "I" may indicate narrator (check for self-references)

MENTION COUNT HEURISTIC:
- Large disparity (e.g., 200+ vs <10 mentions) often indicates full name vs shortened form
- Similar counts (both >20 mentions) often indicates distinct characters of comparable importance

When in doubt, keep SEPARATE. False negatives (missing an alias) are better than false positives (merging different characters)."""


ALIAS_RESOLUTION_PROMPT = """Identify which character names refer to the SAME PERSON in this novel.

CHARACTER NAMES (with chapter info and sample contexts):
{characters}

ANALYZE CAREFULLY:
1. Check if names appear in similar chapters (overlapping chapters = might be same person)
2. Check if contexts suggest the same person
3. Look at mention counts - if both names have many mentions (50+), they're likely different major characters
4. Check for gendered title conflicts (Mr. vs Mrs. suggests different people)
5. When uncertain, keep names SEPARATE - it's better to have duplicates than to merge different people

EXAMPLES OF CORRECT MERGES:
- "Sarah Miller" + "Sarah" → SAME (first name matches full name)
- "Robert Chen" + "Chen" + "Mr. Chen" → SAME (last name and titled version)
- "Michael Anderson" + "Mike" → SAME (nickname matches full name)
- "Emma Wilson" + "Wilson" + "Miss Wilson" → SAME (last name and titled version)
- "Dr. Williams" + "James Williams" → SAME (titled version of full name)
- "Elizabeth Harper" + "Liz" → SAME (nickname matches full name)

EXAMPLES OF INCORRECT MERGES (DO NOT DO THIS!):
- "Mr. Anderson" + "Chen" → WRONG! (completely different people, no name overlap)
- "Mr. Anderson" + "Emma" → WRONG! (completely different people)
- "Mr. Roberts" + "Mrs. Roberts" → WRONG! (likely spouses, different people)
- "Michael Brown" + "Sarah Brown" → WRONG! (different people with same last name)
- "Sarah" + "Emma" → WRONG! (different first names = different people)

Return JSON array:
```json
[
  {{"canonical": "Full Name", "aliases": ["Nickname", "Title LastName"]}},
  {{"canonical": "Another Character", "aliases": []}}
]
```

Return ONLY the JSON array. Include only names you're confident about - omit uncertain names entirely rather than making bad merges."""


class CharacterConsensusBuilder:
    """
    Builds consensus across chapters and resolves aliases.

    Takes validated proposals from all chapters and produces
    the final character map with merged mentions and aliases.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        confidence_threshold: float = 0.6,
        use_llm_alias_resolution: bool = True,
    ):
        """
        Args:
            llm_client: LLM for alias resolution
            confidence_threshold: Threshold for high-confidence characters
            use_llm_alias_resolution: Whether to use LLM for alias resolution
        """
        self.llm = llm_client
        self.confidence_threshold = confidence_threshold
        self.use_llm_alias_resolution = use_llm_alias_resolution and llm_client is not None

    def build_consensus(
        self,
        validations: list[CharacterValidationResult],
        total_chapters: int,
    ) -> CharacterMap:
        """
        Build the final character map from validated proposals.

        Args:
            validations: All validation results from all chapters
            total_chapters: Total number of chapters in document

        Returns:
            Final CharacterMap with merged characters
        """
        logger.info(f"CharacterConsensusBuilder: received {len(validations)} validations")

        # Filter to valid proposals
        valid_results = [v for v in validations if v.is_valid]
        invalid_count = len(validations) - len(valid_results)
        if invalid_count > 0:
            logger.info(f"CharacterConsensusBuilder: filtered {invalid_count} invalid proposals")

        if not valid_results:
            return CharacterMap(
                characters=[],
                low_confidence_characters=[],
                total_mentions=0,
                total_chapters=total_chapters,
                pipeline_metadata={"warning": "No valid character proposals found"},
            )

        # Group by name (exact match first)
        name_groups = self._group_by_name(valid_results)
        logger.info(f"CharacterConsensusBuilder: grouped into {len(name_groups)} unique names")

        # Log the top names by mention count
        sorted_names = sorted(
            name_groups.items(),
            key=lambda x: sum(r.proposal.mention_count for r in x[1]),
            reverse=True
        )
        for name, results in sorted_names[:20]:
            mentions = sum(r.proposal.mention_count for r in results)
            chapters = sorted(set(r.proposal.chapter_index for r in results))
            logger.debug(f"  '{name}': {mentions} mentions, chapters {chapters}")
        if len(sorted_names) > 20:
            logger.debug(f"  ... and {len(sorted_names) - 20} more names")

        # Separate proper names from descriptive handles
        proper_name_groups = {}
        epithet_groups = {}
        for name, results in name_groups.items():
            if self._is_descriptive_handle(name):
                epithet_groups[name] = results
                logger.debug(f"Classified as epithet: '{name}'")
            else:
                proper_name_groups[name] = results
                logger.debug(f"Classified as proper name: '{name}'")

        if epithet_groups:
            logger.info(f"CharacterConsensusBuilder: found {len(epithet_groups)} descriptive handles")
            logger.info(f"Epithets: {list(epithet_groups.keys())}")
        if proper_name_groups:
            logger.info(f"Proper names: {list(proper_name_groups.keys())}")

        # Resolve aliases for proper names
        if self.use_llm_alias_resolution and len(proper_name_groups) > 1:
            logger.info("CharacterConsensusBuilder: using LLM alias resolution")
            alias_groups = self._llm_alias_resolution(proper_name_groups)
        else:
            logger.info("CharacterConsensusBuilder: using heuristic alias resolution")
            alias_groups = self._heuristic_alias_resolution(proper_name_groups, valid_results)

        # Resolve aliases for epithets separately
        if epithet_groups and self.use_llm_alias_resolution:
            logger.info("CharacterConsensusBuilder: running epithet alias resolution")
            epithet_alias_groups = self._llm_epithet_resolution(epithet_groups)
            # Merge epithet alias groups into main alias groups
            for canonical, aliases in epithet_alias_groups.items():
                alias_groups[canonical] = aliases
        elif epithet_groups:
            # No LLM - just add epithets as separate characters
            for name in epithet_groups:
                alias_groups[name] = []

        # Cross-group resolution: link epithets to proper names (e.g., "the prince" -> "Prince Prospero")
        if epithet_groups and proper_name_groups and self.use_llm_alias_resolution:
            logger.info("CharacterConsensusBuilder: running cross-group (epithet-to-proper) resolution")
            cross_merges = self._llm_cross_group_resolution(epithet_groups, proper_name_groups)
            # Apply cross-group merges
            for epithet_name, proper_name in cross_merges.items():
                if proper_name in alias_groups and epithet_name in alias_groups:
                    # Add epithet as alias to proper name
                    alias_groups[proper_name].append(epithet_name)
                    # Also add any aliases the epithet had
                    alias_groups[proper_name].extend(alias_groups[epithet_name])
                    # Remove epithet as standalone character
                    del alias_groups[epithet_name]
                    logger.info(f"Cross-group merge: '{proper_name}' <- epithet '{epithet_name}'")

        # Merge name_groups to include epithets for downstream processing
        name_groups.update(epithet_groups)

        # Log alias groups
        logger.info(f"CharacterConsensusBuilder: resolved to {len(alias_groups)} characters")
        for canonical, aliases in sorted(alias_groups.items(), key=lambda x: -len(x[1])):
            if aliases:
                logger.info(f"  '{canonical}' <- aliases: {aliases}")
            else:
                logger.debug(f"  '{canonical}' (no aliases)")

        # Build final characters
        characters = []
        low_confidence = []

        for canonical_name, aliases in alias_groups.items():
            # Collect all mentions for this character
            all_mentions = []
            all_strategies = set()
            all_confidences = []
            chapters_present = set()
            all_types = []  # Track character types from all proposals

            # Get mentions from canonical name
            if canonical_name in name_groups:
                for result in name_groups[canonical_name]:
                    all_mentions.extend(result.proposal.mentions)
                    all_strategies.add(result.proposal.strategy)
                    all_confidences.append(result.overall_score)
                    chapters_present.add(result.proposal.chapter_index)
                    # Collect character type if available
                    if hasattr(result.proposal, 'character_type'):
                        all_types.append(result.proposal.character_type)

            # Get mentions from aliases
            for alias in aliases:
                if alias in name_groups:
                    for result in name_groups[alias]:
                        all_mentions.extend(result.proposal.mentions)
                        all_strategies.add(result.proposal.strategy)
                        all_confidences.append(result.overall_score)
                        chapters_present.add(result.proposal.chapter_index)
                        # Collect character type if available
                        if hasattr(result.proposal, 'character_type'):
                            all_types.append(result.proposal.character_type)

            if not all_mentions:
                continue

            # Deduplicate mentions by position (same position = same mention)
            # This handles cases where NER and LLM both find the same mention
            seen_positions = set()
            unique_mentions = []
            for mention in all_mentions:
                if mention.position not in seen_positions:
                    seen_positions.add(mention.position)
                    unique_mentions.append(mention)
            all_mentions = unique_mentions

            # Sort mentions by position
            all_mentions.sort(key=lambda m: m.position)

            # Calculate final confidence
            if not all_confidences:
                error_msg = f"No confidences available for character '{canonical_name}' - cannot continue"
                logger.error(error_msg)
                raise ValueError(error_msg)
            avg_confidence = sum(all_confidences) / len(all_confidences)

            # Boost confidence for multiple strategies or many chapters
            if len(all_strategies) > 1:
                avg_confidence = min(1.0, avg_confidence + 0.1)
            if len(chapters_present) > 3:
                avg_confidence = min(1.0, avg_confidence + 0.05)

            # Boost confidence based on mention count
            # High-mention characters should have high confidence (major characters)
            mention_count = len(all_mentions)
            if mention_count >= 100:
                avg_confidence = min(1.0, avg_confidence + 0.15)
            elif mention_count >= 50:
                avg_confidence = min(1.0, avg_confidence + 0.10)
            elif mention_count >= 20:
                avg_confidence = min(1.0, avg_confidence + 0.05)

            # Determine final character type by majority vote (prefer non-UNCERTAIN)
            final_type = CharacterType.UNCERTAIN
            if all_types:
                type_counts = {}
                for t in all_types:
                    if t != CharacterType.UNCERTAIN:
                        type_counts[t] = type_counts.get(t, 0) + 1
                if type_counts:
                    final_type = max(type_counts.keys(), key=lambda t: type_counts[t])

            # LLM fallback for uncertain character types
            if final_type == CharacterType.UNCERTAIN and self.llm:
                final_type = self._llm_classify_character_type(
                    canonical_name, all_mentions, chapters_present
                )

            # Create character
            char_id = self._generate_id(canonical_name)
            first_chapter = min(chapters_present) if chapters_present else 1

            character = Character(
                id=char_id,
                canonical_name=canonical_name,
                aliases=list(aliases),
                mentions=all_mentions,
                first_appearance_chapter=first_chapter,
                mention_count=len(all_mentions),
                chapters_present=sorted(chapters_present),
                confidence=avg_confidence,
                supporting_strategies=list(all_strategies),
                character_type=final_type,
            )

            if avg_confidence >= self.confidence_threshold:
                characters.append(character)
            else:
                low_confidence.append(character)

        # Sort by mention count
        characters.sort(key=lambda c: c.mention_count, reverse=True)
        low_confidence.sort(key=lambda c: c.mention_count, reverse=True)

        total_mentions = sum(c.mention_count for c in characters)
        total_mentions += sum(c.mention_count for c in low_confidence)

        return CharacterMap(
            characters=characters,
            low_confidence_characters=low_confidence,
            total_mentions=total_mentions,
            total_chapters=total_chapters,
            pipeline_metadata={
                "high_confidence_count": len(characters),
                "low_confidence_count": len(low_confidence),
                "confidence_threshold": self.confidence_threshold,
                "used_llm_aliases": self.use_llm_alias_resolution,
            },
        )

    def _group_by_name(
        self,
        results: list[CharacterValidationResult],
    ) -> dict[str, list[CharacterValidationResult]]:
        """Group validation results by character name."""
        groups = defaultdict(list)
        for result in results:
            groups[result.proposal.name].append(result)
        return dict(groups)

    def _heuristic_alias_resolution(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
        all_results: list[CharacterValidationResult],
    ) -> dict[str, list[str]]:
        """
        Resolve aliases using heuristics.

        Returns dict mapping canonical name to list of aliases.
        """
        # Start with each name as its own group
        alias_map = {name: set() for name in name_groups.keys()}

        # Collect alias candidates from validation
        alias_candidates = defaultdict(set)
        for result in all_results:
            name = result.proposal.name
            for candidate in result.alias_candidates:
                alias_candidates[name].add(candidate)

        names = list(name_groups.keys())

        # Find matches based on name components
        for i, name1 in enumerate(names):
            for name2 in names[i + 1:]:
                if self._names_match(name1, name2):
                    # Merge: keep longer/more complete name as canonical
                    # Calculate mention counts for both names
                    count1 = sum(r.proposal.mention_count for r in name_groups[name1])
                    count2 = sum(r.proposal.mention_count for r in name_groups[name2])
                    canonical, alias = self._pick_canonical(name1, name2, count1, count2)
                    if canonical in alias_map:
                        alias_map[canonical].add(alias)
                        # Merge alias's aliases
                        if alias in alias_map:
                            alias_map[canonical].update(alias_map[alias])
                            del alias_map[alias]

        # Add validator's alias candidates if they match actual names
        for name, candidates in alias_candidates.items():
            if name in alias_map:
                for candidate in candidates:
                    # Check if candidate matches any actual name
                    for actual_name in name_groups.keys():
                        if actual_name != name and self._names_match(candidate, actual_name):
                            # Calculate mention counts for both names
                            count_name = sum(r.proposal.mention_count for r in name_groups[name])
                            count_actual = sum(r.proposal.mention_count for r in name_groups[actual_name])
                            canonical, alias = self._pick_canonical(name, actual_name, count_name, count_actual)
                            if canonical in alias_map and alias in alias_map:
                                alias_map[canonical].add(alias)
                                alias_map[canonical].update(alias_map[alias])
                                del alias_map[alias]

        return {k: list(v) for k, v in alias_map.items()}

    def _names_match(self, name1: str, name2: str) -> bool:
        """
        Check if two names likely refer to the same person.

        Note: This is a simple heuristic check. For last-name-only matches,
        the caller should verify there aren't multiple people with that last name.
        """
        # Exact match (case insensitive)
        if name1.lower() == name2.lower():
            return True

        # Normalize: remove titles, lowercase
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        if norm1 == norm2:
            return True

        parts1 = norm1.split()
        parts2 = norm2.split()

        # Check if one is FIRST name of the other (safe to match)
        if len(parts1) == 1 and len(parts2) > 1:
            # name1 might be first name of name2
            if parts1[0] == parts2[0]:
                return True
            # Note: We NO LONGER match last names here - too risky for family members
            # The LLM alias resolution with _validate_merge handles this case

        if len(parts2) == 1 and len(parts1) > 1:
            # name2 might be first name of name1
            if parts2[0] == parts1[0]:
                return True

        # Check for titled version (Mr. Smith == Smith) - but be careful
        # Only match if the title suggests same gender/role
        if len(parts1) == 1 and len(parts2) == 2:
            title = parts2[0].rstrip('.').lower()
            if title in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}:
                if parts1[0] == parts2[1]:
                    # This is a last-name match - risky, don't auto-merge
                    # Let LLM handle it with proper validation
                    return False

        if len(parts2) == 1 and len(parts1) == 2:
            title = parts1[0].rstrip('.').lower()
            if title in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}:
                if parts2[0] == parts1[1]:
                    # This is a last-name match - risky, don't auto-merge
                    return False

        return False

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove common titles
        name = re.sub(
            r'^(mr|mrs|ms|miss|dr|sir|lady|lord)\.?\s+',
            '',
            name,
            flags=re.IGNORECASE
        )
        return ' '.join(name.lower().split())

    def _pick_canonical(self, name1: str, name2: str, count1: int = 0, count2: int = 0) -> tuple[str, str]:
        """
        Pick which name should be canonical vs alias.

        F15: Priority order (mention count is PRIMARY):
        1. Higher mention count (most frequently used form is canonical)
        2. Longer names (more complete)
        3. Untitled over titled
        4. Alphabetically first (tiebreaker only)
        """
        # F15: Prefer higher mention count FIRST (most used form is canonical)
        if count1 != count2:
            return (name1, name2) if count1 > count2 else (name2, name1)

        # Prefer full names over first names
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) > len(parts2):
            return name1, name2
        elif len(parts2) > len(parts1):
            return name2, name1

        # Prefer untitled over titled (Jay Gatsby over Mr. Gatsby)
        has_title1 = parts1[0].rstrip('.').lower() in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}
        has_title2 = parts2[0].rstrip('.').lower() in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}

        if has_title1 and not has_title2:
            return name2, name1
        elif has_title2 and not has_title1:
            return name1, name2

        # Default: alphabetically first is canonical
        return (name1, name2) if name1 < name2 else (name2, name1)

    def _is_ambiguous_name(self, name: str) -> bool:
        """
        Heuristic for names that require more evidence during alias resolution.

        Ambiguous examples:
        - Single-word names (often last-name-only)
        - Titled names (Mr./Mrs./Dr. X)
        """
        words = re.sub(r"[^\w\s]", "", name.lower()).split()
        if not words:
            return True
        if words[0] in TITLES:
            return True
        significant = self._filter_title_words(words)
        return len(significant) <= 1

    def _iter_all_mentions(self, results: list[CharacterValidationResult]) -> list[CharacterMention]:
        """Collect all mentions from a list of validation results (can be many)."""
        mentions: list[CharacterMention] = []
        for r in results:
            if r.proposal and r.proposal.mentions:
                mentions.extend(r.proposal.mentions)
        return mentions

    def _format_contexts(
        self,
        results: list[CharacterValidationResult],
        *,
        max_contexts: int,
        max_chars: int,
    ) -> str:
        """
        Format diverse context snippets sampled across early/mid/late mentions.

        Notes:
        - Mention contexts are already short (~100 chars) upstream; we avoid over-truncating further.
        - We prefer chapter diversity and narrative spread over "first 2 mentions".
        """
        mentions = self._iter_all_mentions(results)
        if not mentions:
            return "(no context)"

        # Sort for deterministic sampling across the narrative
        mentions_sorted = sorted(mentions, key=lambda m: (m.chapter_index, m.position))

        # Seed picks: early / middle / late
        picks: list[CharacterMention] = []
        for idx in {0, len(mentions_sorted) // 2, len(mentions_sorted) - 1}:
            if 0 <= idx < len(mentions_sorted):
                picks.append(mentions_sorted[idx])

        # Fill with additional mentions from new chapters if needed
        seen_chapters = {m.chapter_index for m in picks}
        seen_contexts = {m.context for m in picks if m.context}

        for m in mentions_sorted:
            if len(picks) >= max_contexts:
                break
            if not m.context:
                continue
            if m.chapter_index in seen_chapters and m.context in seen_contexts:
                continue
            # Prefer new chapters
            if m.chapter_index not in seen_chapters:
                picks.append(m)
                seen_chapters.add(m.chapter_index)
                seen_contexts.add(m.context)

        # Still short? Add any remaining distinct contexts (even same chapter)
        if len(picks) < max_contexts:
            for m in mentions_sorted:
                if len(picks) >= max_contexts:
                    break
                if not m.context or m.context in seen_contexts:
                    continue
                picks.append(m)
                seen_contexts.add(m.context)

        # Render
        lines = []
        for i, m in enumerate(picks[:max_contexts], 1):
            ctx = (m.context or "").replace("\n", " ").strip()
            if max_chars > 0 and len(ctx) > max_chars:
                ctx = ctx[:max_chars].rstrip() + "..."
            dlg = "dialogue" if getattr(m, "in_dialogue", False) else "narrative"
            lines.append(f"{i}. [ch {m.chapter_index}, {dlg}] \"{ctx}\"")
        return "\n".join(lines) if lines else "(no context)"

    def _total_mentions_for_name(
        self,
        name: str,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> int:
        results = name_groups.get(name, [])
        return sum(r.proposal.mention_count for r in results)

    def _chapters_for_name(
        self,
        name: str,
        name_groups: dict[str, list[CharacterValidationResult]],
        *,
        max_chapters: int = 12,
    ) -> str:
        results = name_groups.get(name, [])
        chapters = sorted(set(r.proposal.chapter_index for r in results))
        if not chapters:
            return "(none)"
        if len(chapters) <= max_chapters:
            return ", ".join(str(c) for c in chapters)
        return ", ".join(str(c) for c in chapters[:max_chapters]) + f"... ({len(chapters)} total)"

    def _build_alias_prompt_global(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> str:
        """Build the global alias-resolution prompt with richer contexts."""
        char_lines: list[str] = []

        # Sort by total mention count (desc) for more salient characters first.
        sorted_items = sorted(
            name_groups.items(),
            key=lambda x: -sum(r.proposal.mention_count for r in x[1]),
        )

        for name, results in sorted_items:
            total_mentions = sum(r.proposal.mention_count for r in results)
            chapters_str = self._chapters_for_name(name, name_groups, max_chapters=12)

            # More evidence for ambiguous names (last-name-only, titled forms)
            ambiguous = self._is_ambiguous_name(name)
            max_ctx = 6 if ambiguous else 4
            max_chars = 180 if ambiguous else 140
            context_str = self._format_contexts(results, max_contexts=max_ctx, max_chars=max_chars)

            char_lines.append(f"- {name} ({total_mentions} mentions, chapters: {chapters_str})")
            char_lines.append(f"  Context:\n{context_str}")

        characters_str = "\n".join(char_lines)
        return ALIAS_RESOLUTION_PROMPT.format(characters=characters_str)

    def _candidate_pairs_for_merge(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
        *,
        max_pairs: int = 250,
    ) -> list[tuple[str, str]]:
        """
        Generate plausible alias candidate pairs using cheap heuristics.

        Goal: avoid O(n^2) on large casts while still capturing obvious merges.
        """
        names = list(name_groups.keys())
        if len(names) < 2:
            return []

        # Token index for significant words (excluding titles)
        token_to_names: dict[str, list[str]] = defaultdict(list)
        for name in names:
            words = re.sub(r"[^\w\s]", "", name.lower()).split()
            sig = self._filter_title_words(words)
            for w in sig:
                token_to_names[w].append(name)

        # Rank names by mention count for throttling big token buckets
        mention_rank = {n: self._total_mentions_for_name(n, name_groups) for n in names}

        pairs_set: set[tuple[str, str]] = set()

        def add_pair(a: str, b: str):
            if a == b:
                return
            x, y = (a, b) if a < b else (b, a)
            pairs_set.add((x, y))

        # Generate within token buckets
        for token, bucket in token_to_names.items():
            if len(bucket) < 2:
                continue
            # For very common tokens, only consider the top-N by mentions to avoid blowup
            bucket_sorted = sorted(bucket, key=lambda n: -mention_rank.get(n, 0))
            cap = 20 if len(bucket_sorted) > 20 else len(bucket_sorted)
            bucket_sorted = bucket_sorted[:cap]

            for i in range(len(bucket_sorted)):
                for j in range(i + 1, len(bucket_sorted)):
                    add_pair(bucket_sorted[i], bucket_sorted[j])
                    if len(pairs_set) >= max_pairs:
                        break
                if len(pairs_set) >= max_pairs:
                    break
            if len(pairs_set) >= max_pairs:
                break

        # Add substring-based candidates (e.g., "Gatsby" in "Jay Gatsby")
        if len(pairs_set) < max_pairs:
            # Only compare top-N by mentions to keep it bounded
            top = sorted(names, key=lambda n: -mention_rank.get(n, 0))[:80]
            norm = {n: self._normalize_name(n) for n in top}
            for i in range(len(top)):
                for j in range(i + 1, len(top)):
                    n1, n2 = top[i], top[j]
                    a, b = norm[n1], norm[n2]
                    if a and b and (a in b or b in a):
                        add_pair(n1, n2)
                        if len(pairs_set) >= max_pairs:
                            break
                if len(pairs_set) >= max_pairs:
                    break

        # Add nickname-based candidates (e.g., "Kate" and "Cathy", "Elizabeth" and "Lizzy")
        # This catches aliases that share no words but are known nickname variants
        if len(pairs_set) < max_pairs:
            # Build index of names by their first significant word (likely the first name)
            # Only consider top characters by mention count to avoid explosion
            top = sorted(names, key=lambda n: -mention_rank.get(n, 0))[:100]

            # Extract the likely "first name" from each name for nickname matching
            def extract_first_name(name: str) -> str:
                """Extract the first name (excluding titles) for nickname matching."""
                words = re.sub(r"[^\w\s]", "", name.lower()).split()
                significant = self._filter_title_words(words)
                return list(significant)[0] if significant else ""

            first_names = {n: extract_first_name(n) for n in top}

            # Group names by their nickname variant sets
            # Names with overlapping variant sets should be paired
            for i in range(len(top)):
                if len(pairs_set) >= max_pairs:
                    break
                n1 = top[i]
                fn1 = first_names[n1]
                if not fn1:
                    continue

                for j in range(i + 1, len(top)):
                    if len(pairs_set) >= max_pairs:
                        break
                    n2 = top[j]
                    fn2 = first_names[n2]
                    if not fn2:
                        continue

                    # Check if the first names are potential nickname variants
                    if are_potential_nicknames(fn1, fn2):
                        add_pair(n1, n2)
                        logger.debug(
                            f"Nickname match: '{n1}' ({fn1}) <-> '{n2}' ({fn2})"
                        )

        return list(pairs_set)

    def _llm_pairwise_merge_decision(
        self,
        name_a: str,
        name_b: str,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> tuple[bool, float, Optional[str], Optional[str]]:
        """
        Ask the LLM whether two names should be merged.

        Returns:
          (same_person, confidence, canonical, alias)
        """
        results_a = name_groups.get(name_a, [])
        results_b = name_groups.get(name_b, [])

        # More evidence when ambiguous
        amb = self._is_ambiguous_name(name_a) or self._is_ambiguous_name(name_b)
        # Increased context size to 300/250 chars to capture death/confrontation scenes where both entities appear
        # (e.g., "fell prostrate in death the Prince Prospero... seizing the mummer" = 221 chars)
        ctx_a = self._format_contexts(results_a, max_contexts=6 if amb else 4, max_chars=300 if amb else 250)
        ctx_b = self._format_contexts(results_b, max_contexts=6 if amb else 4, max_chars=300 if amb else 250)

        prompt = PAIRWISE_ALIAS_PROMPT.format(
            name_a=name_a,
            mentions_a=self._total_mentions_for_name(name_a, name_groups),
            chapters_a=self._chapters_for_name(name_a, name_groups, max_chapters=16),
            contexts_a=ctx_a,
            name_b=name_b,
            mentions_b=self._total_mentions_for_name(name_b, name_groups),
            chapters_b=self._chapters_for_name(name_b, name_groups, max_chapters=16),
            contexts_b=ctx_b,
        )

        result, response = self.llm.query_json(prompt, system=PAIRWISE_ALIAS_SYSTEM)
        if not response.success or result is None or not isinstance(result, dict):
            raise ValueError(f"Pairwise alias LLM failed for '{name_a}' vs '{name_b}'")

        same = bool(result.get("same_person", False))
        conf = float(result.get("confidence", 0.0) or 0.0)
        canonical = result.get("canonical")
        alias = result.get("alias")

        # Enforce canonical/alias must be exactly one of the provided names
        if same:
            if canonical not in (name_a, name_b) or alias not in (name_a, name_b) or canonical == alias:
                # Fall back to deterministic canonical choice
                count_a = self._total_mentions_for_name(name_a, name_groups)
                count_b = self._total_mentions_for_name(name_b, name_groups)
                canonical, alias = self._pick_canonical(name_a, name_b, count_a, count_b)
        return same, conf, canonical, alias

    def _llm_alias_resolution_pairwise(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, list[str]]:
        """
        Two-stage alias resolution:
        1) Cheap heuristics propose candidate merges
        2) LLM evaluates candidates pairwise with richer evidence
        """
        names = list(name_groups.keys())
        if len(names) < 2:
            return {n: [] for n in names}

        candidates = self._candidate_pairs_for_merge(name_groups, max_pairs=250)
        logger.info(f"Pairwise alias resolution: evaluating {len(candidates)} candidate pairs")

        # Union-Find to build clusters
        parent: dict[str, str] = {n: n for n in names}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        # PRE-MERGE: Handle obvious substring matches BEFORE LLM evaluation
        # This ensures "Prospero" merges with "Prince Prospero" instead of "the mummer"
        # when both pairs are in candidates
        mention_rank = {n: self._total_mentions_for_name(n, name_groups) for n in names}
        norm_names = {n: self._normalize_name(n) for n in names}
        substring_merges = 0

        for i, name1 in enumerate(names):
            if find(name1) != name1:  # Already merged
                continue
            norm1 = norm_names[name1]
            if not norm1:
                continue

            for j in range(i + 1, len(names)):
                name2 = names[j]
                if find(name2) != name2:  # Already merged
                    continue
                norm2 = norm_names[name2]
                if not norm2:
                    continue

                # Check if one name is a substring of the other
                if norm1 in norm2 or norm2 in norm1:
                    logger.debug(f"Pre-merge substring check: '{name1}' ('{norm1}') vs '{name2}' ('{norm2}')")
                    # Validate the merge is sensible (chapter overlap, not death-related)
                    is_valid, _vconf = self._validate_merge(name1, name2, name_groups)
                    if is_valid:
                        union(name1, name2)
                        substring_merges += 1
                        logger.debug(f"Pre-merge substring match ACCEPTED: '{name1}' <-> '{name2}'")
                    else:
                        logger.warning(f"Pre-merge substring match REJECTED by validation: '{name1}' <-> '{name2}' (conf={_vconf:.2f})")

        if substring_merges > 0:
            logger.info(f"Pre-merged {substring_merges} substring matches before LLM evaluation")

        # Evaluate candidates
        accepted = 0
        for a, b in candidates:
            # Skip if already merged by pre-merge phase
            if find(a) == find(b):
                continue

            same, conf, canonical, alias = self._llm_pairwise_merge_decision(a, b, name_groups)
            if not same or conf < 0.7:
                continue

            # Validate with our strict sanity checks before merging
            is_valid, _vconf = self._validate_merge(canonical or a, alias or b, name_groups)
            if not is_valid:
                continue

            union(a, b)
            accepted += 1

        logger.info(f"Pairwise alias resolution: accepted {accepted}/{len(candidates)} merges")

        # Build components
        components: dict[str, list[str]] = defaultdict(list)
        for n in names:
            components[find(n)].append(n)

        # Choose canonical for each component deterministically using mention counts + name completeness
        # F15: Mention count is PRIMARY factor, then name quality indicators
        alias_map: dict[str, list[str]] = {}
        for _root, members in components.items():
            if len(members) == 1:
                alias_map[members[0]] = []
                continue

            def score(name: str) -> tuple[int, int, int, int, str]:
                parts = name.split()
                has_title = 1 if parts and parts[0].rstrip('.').lower() in TITLES else 0
                mention_count = self._total_mentions_for_name(name, name_groups)
                # F15: Priority order:
                # 1. Higher mention count (PRIMARY - most used form is canonical)
                # 2. More name parts (more complete names)
                # 3. No title preferred (-has_title: untitled=0 > titled=-1)
                # 4. Alphabetically first (tiebreaker only)
                # Note: we negate name for alphabetically-first tiebreaker with max()
                return (mention_count, len(parts), -has_title, 0, name)

            # Use min on inverted tuple for alphabetical tiebreaker (first alphabetically wins)
            def score_with_alpha_first(name: str) -> tuple:
                parts = name.split()
                has_title = 1 if parts and parts[0].rstrip('.').lower() in TITLES else 0
                mention_count = self._total_mentions_for_name(name, name_groups)
                # Negate values we want to maximize, so min() picks the best
                return (-mention_count, -len(parts), has_title, name.lower())

            canonical = min(members, key=score_with_alpha_first)
            aliases = [m for m in members if m != canonical]
            alias_map[canonical] = aliases

        # Post-check obvious merges the LLM missed (still useful)
        alias_map = self._post_llm_merge_check(alias_map, name_groups)
        return alias_map

    def _llm_alias_resolution(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, list[str]]:
        """Use LLM to resolve aliases with rich context."""
        # If there are many unique names, a single giant "merge everyone" prompt becomes
        # both expensive and error-prone. Switch to pairwise mode automatically.
        if len(name_groups) > 60:
            logger.info(f"CharacterConsensusBuilder: large cast ({len(name_groups)} names) - using pairwise LLM alias resolution")
            return self._llm_alias_resolution_pairwise(name_groups)

        prompt = self._build_alias_prompt_global(name_groups)

        # Retry logic: LLM is essential for character merging
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result, response = self.llm.query_json(prompt, system=ALIAS_RESOLUTION_SYSTEM)

                if result is None:
                    raise ValueError("LLM returned None - possibly parsing failure")

                if not isinstance(result, list):
                    raise ValueError(f"LLM returned non-list: {type(result)}")

                # Success - break out of retry loop
                break

            except Exception as e:
                last_error = e
                logger.warning(f"LLM alias resolution attempt {attempt + 1} failed: {e}")

                if attempt == max_retries:
                    # All retries exhausted - fail loudly
                    logger.error("All LLM attempts failed - character alias resolution cannot proceed")
                    raise RuntimeError(
                        "LLM alias resolution failed after all retries. "
                        "LLM is required for accurate character merging. "
                        f"Last error: {last_error}"
                    ) from last_error

                # Record retry in metrics if available
                if self.llm.metrics and self.llm.metrics.current_stage:
                    self.llm.metrics.current_stage.record_retry()

                # Wait before retry
                time.sleep(1)

        # Parse LLM response WITH VALIDATION
        alias_map = {}
        seen_names = set()

        for group in result:
            if not isinstance(group, dict):
                continue

            canonical = group.get("canonical", "")
            aliases = group.get("aliases", [])

            if not canonical:
                continue

            # Verify canonical exists in our names (strict matching)
            matched_canonical = self._find_closest_name(canonical, name_groups.keys())
            if not matched_canonical:
                continue

            if matched_canonical in seen_names:
                continue

            seen_names.add(matched_canonical)
            alias_map[matched_canonical] = []

            for alias in aliases:
                matched_alias = self._find_closest_name(alias, name_groups.keys())
                if not matched_alias or matched_alias in seen_names:
                    continue

                # VALIDATE the merge before accepting it
                is_valid, confidence = self._validate_merge(
                    matched_canonical, matched_alias, name_groups
                )

                if is_valid:
                    alias_map[matched_canonical].append(matched_alias)
                    seen_names.add(matched_alias)
                    logger.debug(f"Accepted merge: {matched_canonical} <- {matched_alias} (conf={confidence:.2f})")
                else:
                    logger.debug(f"Rejected merge: {matched_canonical} <- {matched_alias} (conf={confidence:.2f})")

        # Add any names not covered by LLM
        for name in name_groups.keys():
            if name not in seen_names:
                alias_map[name] = []

        # Post-LLM validation: Check for obvious merges the LLM missed
        # e.g., "Nick" should merge with "Nick Carraway" even if LLM didn't suggest it
        alias_map = self._post_llm_merge_check(alias_map, name_groups)

        return alias_map

    def _post_llm_merge_check(
        self,
        alias_map: dict[str, list[str]],
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, list[str]]:
        """
        Check for obvious merges the LLM missed.

        Handles cases like "Nick" + "Nick Carraway" where the first name
        clearly matches the full name.
        """
        canonicals = list(alias_map.keys())
        merged = set()  # Track names that get merged

        for i, name1 in enumerate(canonicals):
            if name1 in merged:
                continue

            for name2 in canonicals[i + 1:]:
                if name2 in merged:
                    continue

                # Check if these should be merged
                is_valid, confidence = self._validate_merge(name1, name2, name_groups)

                # Higher threshold for post-LLM merges to avoid introducing false merges
                if is_valid and confidence >= 0.85:
                    # Merge: pick the more complete name as canonical
                    # Calculate mention counts for both names
                    count1 = sum(r.proposal.mention_count for r in name_groups[name1])
                    count2 = sum(r.proposal.mention_count for r in name_groups[name2])
                    canonical, alias = self._pick_canonical(name1, name2, count1, count2)

                    # If canonical was name2, we need to swap in alias_map
                    if canonical == name2:
                        canonical, alias = name2, name1

                    if canonical in alias_map and alias in alias_map:
                        logger.info(
                            f"Post-LLM merge: '{canonical}' <- '{alias}' "
                            f"(LLM missed this merge)"
                        )
                        alias_map[canonical].append(alias)
                        alias_map[canonical].extend(alias_map.get(alias, []))
                        del alias_map[alias]
                        merged.add(alias)

        return alias_map

    def _find_closest_name(
        self,
        target: str,
        candidates: list[str],
    ) -> Optional[str]:
        """Find the closest matching name from candidates (strict matching)."""
        target_lower = target.lower()
        target_norm = self._normalize_name(target)

        # Priority 1: Exact match (case insensitive)
        for candidate in candidates:
            if candidate.lower() == target_lower:
                return candidate

        # Priority 2: Normalized match (after removing titles)
        for candidate in candidates:
            if self._normalize_name(candidate) == target_norm:
                return candidate

        # Priority 3: High similarity match (>0.85)
        # This catches minor typos but not completely different names
        best_match = None
        best_score = 0.0
        for candidate in candidates:
            score = self._name_similarity(target, candidate)
            if score > best_score and score > 0.85:
                best_score = score
                best_match = candidate

        if best_match:
            return best_match

        # NO partial/component matching - too error-prone
        # If we can't find a clear match, return None
        return None

    def _filter_title_words(self, words: list[str]) -> set[str]:
        """
        Extract significant words from a name, excluding titles.

        Titles like "Mr.", "Miss", "Dr." are social indicators, not part of the actual name.
        Filtering them prevents spurious merges like "Miss X" with "Miss Y" based solely
        on the shared title word.

        Args:
            words: List of words from a character name

        Returns:
            Set of significant words (length >= 3, not titles)
        """
        return {w for w in words if len(w) >= 3 and w.lower() not in TITLES}

    def _check_aggressive_alias_patterns(self, name1: str, name2: str) -> tuple[bool, float]:
        """
        Check for common alias patterns that should be merged aggressively.

        Handles hyphenation and spacing variants like:
        - "Owl Eyes" vs "Owl-eyes"
        - "Mc Donald" vs "McDonald"

        Returns:
            (should_merge, confidence) tuple
        """
        # Normalize: lowercase, remove hyphens/dots, collapse spaces
        n1_lower = name1.lower().replace('-', ' ').replace('.', '')
        n2_lower = name2.lower().replace('-', ' ').replace('.', '')

        n1_normalized = ' '.join(n1_lower.split())
        n2_normalized = ' '.join(n2_lower.split())

        # Exact match after normalization (handles "Owl-Eyes" vs "Owl Eyes")
        if n1_normalized == n2_normalized:
            return True, 0.95

        # Match after removing all spaces (handles "Owl Eyes" vs "Owleyes")
        if n1_normalized.replace(' ', '') == n2_normalized.replace(' ', ''):
            return True, 0.90

        return False, 0.0

    def _check_birth_name_pattern(
        self,
        canonical: str,
        alias: str,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> tuple[bool, float]:
        """
        Check if two names represent a birth name / assumed name pattern.

        Looks for context clues like "born as", "real name", "changed his name"
        in the mentions for either name.

        IMPORTANT: We iterate through each name's contexts separately and check
        if they mention the OTHER name with an indicator. This catches patterns
        like "He was born as James Gatz" in Jay Gatsby's context.

        Returns:
            (should_merge, confidence) tuple
        """
        birth_name_indicators = [
            "born as", "real name", "birth name", "whose real name",
            "formerly known as", "changed his name", "changed her name",
            "once called", "used to be called", "originally named",
            "actually named", "true name", "given name",
        ]

        # Normalize names for matching
        canonical_lower = canonical.lower()
        alias_lower = alias.lower()

        # Also check individual name components (first/last names, excluding short words)
        canonical_parts = {p for p in canonical_lower.split() if len(p) > 2}
        alias_parts = {p for p in alias_lower.split() if len(p) > 2}

        def name_in_context(name_lower: str, parts: set, context: str) -> bool:
            """Check if a name (or its significant parts) appears in context."""
            if name_lower in context:
                return True
            return any(part in context for part in parts)

        # Check canonical's contexts for mentions of alias (the OTHER name)
        for result in name_groups.get(canonical, [])[:10]:
            for mention in result.proposal.mentions[:5]:
                if not mention.context:
                    continue
                context = mention.context.lower()
                for indicator in birth_name_indicators:
                    if indicator in context:
                        # Check if the OTHER name (alias) appears in canonical's context
                        if name_in_context(alias_lower, alias_parts, context):
                            logger.info(
                                f"Birth name pattern detected: {canonical} <-> {alias} "
                                f"(indicator: '{indicator}' in {canonical}'s context mentions {alias})"
                            )
                            return True, 0.85

        # Check alias's contexts for mentions of canonical (the OTHER name)
        for result in name_groups.get(alias, [])[:10]:
            for mention in result.proposal.mentions[:5]:
                if not mention.context:
                    continue
                context = mention.context.lower()
                for indicator in birth_name_indicators:
                    if indicator in context:
                        # Check if the OTHER name (canonical) appears in alias's context
                        if name_in_context(canonical_lower, canonical_parts, context):
                            logger.info(
                                f"Birth name pattern detected: {canonical} <-> {alias} "
                                f"(indicator: '{indicator}' in {alias}'s context mentions {canonical})"
                            )
                            return True, 0.85

        return False, 0.0

    def _llm_classify_character_type(
        self,
        name: str,
        mentions: list[CharacterMention],
        chapters_present: set[int],
    ) -> CharacterType:
        """
        Use LLM to classify uncertain character types.

        Called when majority voting fails to determine character type.
        Returns CharacterType based on LLM analysis of contexts.
        """
        if not self.llm:
            return CharacterType.UNCERTAIN

        # Format contexts for prompt
        context_lines = []
        for i, mention in enumerate(mentions[:6]):  # Sample up to 6 contexts
            if mention.context:
                dlg = "dialogue" if mention.in_dialogue else "narrative"
                context_lines.append(
                    f"{i+1}. [ch {mention.chapter_index}, {dlg}] \"{mention.context[:150]}\""
                )

        if not context_lines:
            return CharacterType.UNCERTAIN

        prompt = CHARACTER_TYPE_PROMPT.format(
            name=name,
            mention_count=len(mentions),
            chapters=", ".join(str(c) for c in sorted(chapters_present)),
            contexts="\n".join(context_lines),
        )

        try:
            result, response = self.llm.query_json(prompt, system=CHARACTER_TYPE_SYSTEM)

            if result and isinstance(result, dict):
                char_type_str = result.get("character_type", "").lower()
                confidence = float(result.get("confidence", 0.0) or 0.0)

                # Only accept high-confidence classifications
                if confidence >= 0.7:
                    if char_type_str == "story":
                        logger.debug(f"LLM classified '{name}' as STORY (conf={confidence:.2f})")
                        return CharacterType.STORY
                    elif char_type_str == "historical":
                        logger.debug(f"LLM classified '{name}' as HISTORICAL (conf={confidence:.2f})")
                        return CharacterType.HISTORICAL
                    elif char_type_str == "referenced":
                        logger.debug(f"LLM classified '{name}' as REFERENCED (conf={confidence:.2f})")
                        return CharacterType.REFERENCED

        except Exception as e:
            logger.warning(f"LLM character type classification failed for '{name}': {e}")

        return CharacterType.UNCERTAIN

    def _validate_merge(
        self,
        canonical: str,
        alias: str,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> tuple[bool, float]:
        """
        Validate LLM merge decision with sanity checks.

        Key checks:
        1. Check aggressive alias patterns (hyphenation/spacing variants) first
        2. Check birth name patterns (context clues like "real name", "born as")
        3. Reject merges that only share a last name when multiple people have that last name
        4. Reject merges with no shared words and no chapter overlap

        Returns:
            (is_valid, confidence) tuple
        """
        # CHECK 1: Aggressive alias patterns (hyphenation/spacing variants)
        # These should always merge regardless of other checks
        is_alias_pattern, alias_conf = self._check_aggressive_alias_patterns(canonical, alias)
        if is_alias_pattern:
            logger.debug(
                f"Merge accepted: {canonical} <- {alias} "
                f"(aggressive alias pattern, conf={alias_conf:.2f})"
            )
            return True, alias_conf

        # CHECK 2: Birth name patterns (context clues)
        # These can merge names with no shared words if context supports it
        is_birth_name, birth_conf = self._check_birth_name_pattern(canonical, alias, name_groups)
        if is_birth_name:
            logger.debug(
                f"Merge accepted: {canonical} <- {alias} "
                f"(birth name pattern, conf={birth_conf:.2f})"
            )
            return True, birth_conf

        # Extract words from names, filtering out titles
        words1 = re.sub(r'[^\w\s]', '', canonical.lower()).split()
        words2 = re.sub(r'[^\w\s]', '', alias.lower()).split()
        # Use helper to filter title words - prevents spurious merges on title alone
        significant1 = self._filter_title_words(words1)
        significant2 = self._filter_title_words(words2)
        shared_words = significant1 & significant2

        # SINGLE-WORD NAME HANDLING
        # When comparing single-word vs multi-word names, assume the single word is the LAST NAME
        # (most common pattern in literature: "Smith" is the last name in "John Smith")
        is_single_word1 = len(significant1) == 1
        is_single_word2 = len(significant2) == 1

        if is_single_word1 and not is_single_word2:
            # Comparing single-word (e.g., "Smith") vs multi-word (e.g., "John Smith")
            # Assume single word is the LAST NAME
            single_word = list(significant1)[0]
            multi_words = significant2

            # Check if single word appears in multi-word name
            if single_word in multi_words:
                # This is likely the same person (full name variant)
                logger.debug(
                    f"Merge accepted: {canonical} <- {alias} "
                    f"(single-word '{single_word}' appears in multi-word name)"
                )
                return True, 0.90  # High confidence

        elif is_single_word2 and not is_single_word1:
            # Reverse case: multi-word vs single-word
            single_word = list(significant2)[0]
            multi_words = significant1

            if single_word in multi_words:
                logger.debug(
                    f"Merge accepted: {canonical} <- {alias} "
                    f"(single-word '{single_word}' appears in multi-word name)"
                )
                return True, 0.90  # High confidence

        # NEW CHECK: Reject completely different single-word names
        # If both are single-word names with NO shared words, reject UNLESS they are
        # known nickname variants (e.g., Kate/Cathy, Elizabeth/Lizzy)
        # NOTE: This prevents the worst over-merges (Alice + Robert) during validation
        # while allowing legitimate nickname pairs to be merged.
        if len(significant1) == 1 and len(significant2) == 1:
            if not shared_words:  # Different single-word names
                # Check if they're known nickname variants before rejecting
                word1 = list(significant1)[0].lower()
                word2 = list(significant2)[0].lower()
                if not are_potential_nicknames(word1, word2):
                    logger.debug(
                        f"Merge rejected: {canonical} <-> {alias} "
                        f"(both single-word names with no similarity - likely different characters)"
                    )
                    return False, 0.05
                else:
                    logger.debug(
                        f"Allowing potential nickname merge: {canonical} <-> {alias} "
                        f"({word1} and {word2} are known nickname variants)"
                    )

        # Check for gendered title conflicts
        # Mr. vs Mrs./Miss suggests different people (likely spouses/family)
        male_titles = {'mr', 'sir', 'lord'}
        female_titles = {'mrs', 'ms', 'miss', 'lady'}
        title1 = words1[0] if words1 and words1[0] in (male_titles | female_titles) else None
        title2 = words2[0] if words2 and words2[0] in (male_titles | female_titles) else None

        if title1 and title2:
            if (title1 in male_titles and title2 in female_titles) or \
               (title1 in female_titles and title2 in male_titles):
                logger.debug(
                    f"Merge rejected: {canonical} <-> {alias} "
                    f"(gendered title conflict: {title1} vs {title2})"
                )
                return False, 0.05

        # Get chapter info
        canonical_results = name_groups.get(canonical, [])
        alias_results = name_groups.get(alias, [])
        canonical_chapters = set(r.proposal.chapter_index for r in canonical_results)
        alias_chapters = set(r.proposal.chapter_index for r in alias_results)
        has_chapter_overlap = bool(canonical_chapters & alias_chapters)

        # Calculate overlap ratio for weighted chapter overlap checks
        if len(canonical_chapters) > 0 and len(alias_chapters) > 0:
            overlap_count = len(canonical_chapters & alias_chapters)
            total_chapters = len(canonical_chapters | alias_chapters)
            overlap_ratio = overlap_count / total_chapters if total_chapters > 0 else 0
        else:
            overlap_ratio = 0

        # Check for family member conflict:
        # If names share ONLY a last name, check if multiple people have that last name
        if shared_words:
            # Check if shared word is likely a last name (appears at end of full names)
            shared_might_be_lastname = False
            for shared in shared_words:
                # Is this word at the end of either multi-word name?
                if len(words1) > 1 and words1[-1] == shared:
                    shared_might_be_lastname = True
                if len(words2) > 1 and words2[-1] == shared:
                    shared_might_be_lastname = True

            if shared_might_be_lastname:
                # Count how many distinct full names share this last name
                names_with_lastname = []
                for shared in shared_words:
                    for name in name_groups.keys():
                        name_words = re.sub(r'[^\w\s]', '', name.lower()).split()
                        if len(name_words) > 1 and name_words[-1] == shared:
                            # This is a full name with this last name
                            first_name = name_words[0]
                            if first_name not in ['mr', 'mrs', 'ms', 'miss', 'dr']:
                                names_with_lastname.append(name)

                # If multiple DIFFERENT full names share this last name, reject merge
                if len(names_with_lastname) > 1:
                    # Check if canonical and alias have DIFFERENT first names
                    first1 = words1[0] if words1 else ""
                    first2 = words2[0] if words2 else ""

                    # Skip titles when comparing first names
                    titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}
                    if first1 in titles and len(words1) > 1:
                        first1 = words1[1]
                    if first2 in titles and len(words2) > 1:
                        first2 = words2[1]

                    # If one is just a last name, it's ambiguous - reject
                    # EXCEPT: Allow if one name is a substring of the other (high-confidence match)
                    if len(words1) == 1 or len(words2) == 1:
                        # Check for substring relationship - these are almost always valid
                        norm1 = self._normalize_name(canonical)
                        norm2 = self._normalize_name(alias)
                        if norm1 in norm2 or norm2 in norm1:
                            logger.debug(
                                f"Merge accepted: {canonical} <- {alias} "
                                f"(substring match overrides ambiguous last name check)"
                            )
                            return True, 0.95  # High confidence for substring matches

                        logger.debug(
                            f"Merge rejected: {canonical} <-> {alias} "
                            f"(ambiguous last name with multiple family members: {names_with_lastname})"
                        )
                        return False, 0.2

                    # BEFORE rejecting different first names, check for birth name / assumed name patterns
                    # Look for phrases like "born as", "real name", "formerly known as", etc.
                    if first1 != first2 and first1 and first2:
                        birth_name_indicators = [
                            "born as",
                            "real name",
                            "formerly known as",
                            "changed his name",
                            "changed her name",
                            "once called",
                            "used to be called",
                            "whose real name",
                            "originally named",
                            "birth name",
                        ]

                        canonical_lower = canonical.lower()
                        alias_lower = alias.lower()
                        canonical_parts = {p for p in canonical_lower.split() if len(p) > 2}
                        alias_parts = {p for p in alias_lower.split() if len(p) > 2}

                        def name_in_ctx(name_lower: str, parts: set, ctx: str) -> bool:
                            return name_lower in ctx or any(p in ctx for p in parts)

                        # Check canonical's contexts for mentions of alias (OTHER name)
                        for result in canonical_results[:5]:
                            for mention in result.proposal.mentions[:3]:
                                if not mention.context:
                                    continue
                                context = mention.context.lower()
                                for indicator in birth_name_indicators:
                                    if indicator in context:
                                        # Check if the OTHER name (alias) appears
                                        if name_in_ctx(alias_lower, alias_parts, context):
                                            logger.info(
                                                f"Merge ALLOWED: {canonical} <- {alias} "
                                                f"(birth name indicator '{indicator}' in {canonical}'s context)"
                                            )
                                            return True, 0.85

                        # Check alias's contexts for mentions of canonical (OTHER name)
                        for result in alias_results[:5]:
                            for mention in result.proposal.mentions[:3]:
                                if not mention.context:
                                    continue
                                context = mention.context.lower()
                                for indicator in birth_name_indicators:
                                    if indicator in context:
                                        # Check if the OTHER name (canonical) appears
                                        if name_in_ctx(canonical_lower, canonical_parts, context):
                                            logger.info(
                                                f"Merge ALLOWED: {canonical} <- {alias} "
                                                f"(birth name indicator '{indicator}' in {alias}'s context)"
                                            )
                                            return True, 0.85

                    # If they have different first names and no birth name evidence, reject
                    if first1 != first2 and first1 and first2:
                        logger.debug(
                            f"Merge rejected: {canonical} <-> {alias} "
                            f"(different first names, same last name - likely family members)"
                        )
                        return False, 0.1

            # Check for first-name-only conflict when BOTH names are multi-word:
            # "Martin Sharpe" and "Martin Luther King" share first name but different last names
            if len(words1) > 1 and len(words2) > 1:
                titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}

                # Get first name (skip title if present)
                first1 = words1[0]
                if first1 in titles and len(words1) > 1:
                    first1 = words1[1]

                first2 = words2[0]
                if first2 in titles and len(words2) > 1:
                    first2 = words2[1]

                last1 = words1[-1]
                last2 = words2[-1]

                # Same first name but different last names = different people
                if first1 == first2 and last1 != last2:
                    logger.debug(
                        f"Merge rejected: {canonical} <-> {alias} "
                        f"(same first name '{first1}', different last names '{last1}' vs '{last2}')"
                    )
                    return False, 0.1

            # Shared words and passed family check - accept
            # But require higher confidence for single-word merges
            confidence = 0.85
            if len(words1) == 1 or len(words2) == 1:
                if confidence < 0.85:
                    logger.debug(
                        f"Merge rejected: {canonical} <-> {alias} "
                        f"(single-word name, confidence {confidence:.2f} < 0.85 threshold)"
                    )
                    return False, confidence * 0.5
            logger.debug(f"Merge accepted: {canonical} <- {alias} (shared words: {shared_words})")
            return True, confidence

        # No shared words - be much more cautious
        # First, reject if BOTH have 3+ chapters AND zero chapter overlap
        if len(canonical_chapters) >= 3 and len(alias_chapters) >= 3:
            if not has_chapter_overlap:
                logger.debug(f"Merge rejected: {canonical} <-> {alias} (no shared words, no chapter overlap, both multi-chapter)")
                return False, 0.1

        # Additional safety: if one is single-word and other is multi-word,
        # single word must match first or last name of multi-word
        if len(words1) == 1 or len(words2) == 1:
            if len(words1) == 1:
                single_word = words1[0]
                multi_words = words2
            else:
                single_word = words2[0]
                multi_words = words1

            if len(multi_words) > 1:
                # Skip titles in multi-word name
                titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}

                # Check if multi-word is just "Title LastName" (e.g., "Mr. Carraway")
                # In this case, single word could be first name (e.g., "Nick")
                is_title_lastname = (
                    len(multi_words) == 2 and
                    multi_words[0].rstrip('.').lower() in titles
                )

                # If multi-word is title+lastname, only accept with strong evidence
                # Chapter overlap alone is not enough (co-occurring characters can be different people)
                # Require EITHER shared words OR strong chapter overlap (>60%)
                # Lowered from 0.8 to 0.6 to allow legitimate title variations
                # (e.g., "Nick" + "Mr. Carraway" where title form appears in subset of chapters)
                if is_title_lastname:
                    if shared_words or (has_chapter_overlap and overlap_ratio > 0.6):
                        # Single-word names need higher confidence to merge
                        confidence = 0.75
                        if len(words1) == 1 or len(words2) == 1:
                            if confidence < 0.85:
                                logger.debug(
                                    f"Merge rejected: {canonical} <-> {alias} "
                                    f"(single-word name, confidence {confidence:.2f} < 0.85 threshold)"
                                )
                                return False, confidence * 0.5
                        logger.debug(
                            f"Merge accepted: {canonical} <- {alias} "
                            f"(title+lastname pattern with strong evidence: shared_words={bool(shared_words)}, "
                            f"overlap_ratio={overlap_ratio:.2f})"
                        )
                        return True, confidence
                    else:
                        logger.debug(
                            f"Merge rejected: {canonical} <-> {alias} "
                            f"(title pattern but insufficient overlap or similarity: "
                            f"shared_words={bool(shared_words)}, overlap_ratio={overlap_ratio:.2f})"
                        )
                        return False, 0.3

                first_word = multi_words[0]
                if first_word in titles and len(multi_words) > 1:
                    first_word = multi_words[1]

                last_word = multi_words[-1]

                # Single word must match first name or last name
                if single_word != first_word and single_word != last_word:
                    logger.debug(
                        f"Merge rejected: {canonical} <-> {alias} "
                        f"(no shared words, '{single_word}' doesn't match first '{first_word}' or last '{last_word}')"
                    )
                    return False, 0.1

        # CRITICAL: We should NEVER merge names with zero shared words
        # The only exceptions are specific patterns we've already handled above:
        # - title+lastname pattern (already returned True if applicable)
        # - single-word matching first/last (already returned False if not matched)
        #
        # If we reach here with no shared words, something is wrong - likely LLM hallucination
        logger.debug(
            f"Merge rejected: {canonical} <-> {alias} "
            f"(no shared words - LLM likely hallucinating or confused)"
        )
        return False, 0.2

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names (0.0 to 1.0)."""
        # Normalize both names
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        # Exact match after normalization
        if n1 == n2:
            return 1.0

        # Check if one is a substring of the other
        # e.g., "Nick" in "Nick Carraway" or "Gatsby" in "Jay Gatsby"
        if n1 in n2 or n2 in n1:
            # Longer containment = higher confidence
            shorter = min(len(n1), len(n2))
            longer = max(len(n1), len(n2))
            return 0.7 + (0.3 * shorter / longer)

        # Use SequenceMatcher for general similarity
        return SequenceMatcher(None, n1, n2).ratio()

    def _is_descriptive_handle(self, name: str) -> bool:
        """
        Detect if a name is a descriptive handle (epithet) like "the creature".

        Descriptive handles start with "the" followed by a noun/adjective phrase.
        Proper names with articles like "the Prince Prospero" are NOT epithets.
        """
        name_lower = name.lower().strip()
        # Must start with "the "
        if not name_lower.startswith("the "):
            return False
        # Should not be a title pattern like "the Mr. Smith"
        rest = name_lower[4:]
        if rest.split()[0].rstrip('.') in TITLES:
            return False

        # Check if this is a proper name with article (e.g., "the Prince Prospero")
        # vs a generic epithet (e.g., "the prince")
        # Proper names typically have multiple capitalized words after "the"
        original_rest = name.strip()[4:]  # Get the part after "the " without lowercasing
        words = original_rest.split()

        if len(words) >= 2:
            # If we have 2+ words and they're capitalized, it's likely a proper name
            # e.g., "the Prince Prospero" → proper name
            # e.g., "the blind priest" → epithet
            capitalized_count = sum(1 for w in words if w and w[0].isupper())
            if capitalized_count >= 2:
                return False  # This is a proper name with article, not an epithet

        return True

    def _llm_epithet_resolution(
        self,
        epithet_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, list[str]]:
        """
        Use LLM to resolve aliases among descriptive handles (epithets).

        This handles cases like "the creature" = "the monster" = "the wretch"
        that share no name components but refer to the same unnamed character.
        """
        if not self.llm or len(epithet_groups) < 2:
            return {name: [] for name in epithet_groups}

        # Build prompt with epithet info
        epithet_lines = []
        sorted_epithets = sorted(
            epithet_groups.items(),
            key=lambda x: -sum(r.proposal.mention_count for r in x[1]),
        )

        for name, results in sorted_epithets:
            total_mentions = sum(r.proposal.mention_count for r in results)
            chapters_str = self._chapters_for_name(name, epithet_groups, max_chapters=12)
            context_str = self._format_contexts(results, max_contexts=4, max_chars=140)

            epithet_lines.append(f"- {name} ({total_mentions} mentions, chapters: {chapters_str})")
            epithet_lines.append(f"  Context:\n{context_str}")

        epithets_str = "\n".join(epithet_lines)
        prompt = EPITHET_ALIAS_PROMPT.format(epithets=epithets_str)

        try:
            result, response = self.llm.query_json(prompt, system=EPITHET_ALIAS_SYSTEM)

            if result is None or not isinstance(result, list):
                logger.warning("LLM epithet resolution returned invalid response")
                return {name: [] for name in epithet_groups}

            # Parse response
            alias_map = {}
            seen_names = set()

            for group in result:
                if not isinstance(group, dict):
                    continue

                canonical = group.get("canonical", "")
                aliases = group.get("aliases", [])

                if not canonical:
                    continue

                # Match to actual epithet names
                matched_canonical = self._find_closest_name(canonical, epithet_groups.keys())
                if not matched_canonical or matched_canonical in seen_names:
                    continue

                seen_names.add(matched_canonical)
                alias_map[matched_canonical] = []

                for alias in aliases:
                    matched_alias = self._find_closest_name(alias, epithet_groups.keys())
                    if not matched_alias or matched_alias in seen_names:
                        continue

                    alias_map[matched_canonical].append(matched_alias)
                    seen_names.add(matched_alias)
                    logger.info(f"Epithet merge: '{matched_canonical}' <- '{matched_alias}'")

            # Add unmatched epithets
            for name in epithet_groups:
                if name not in seen_names:
                    alias_map[name] = []

            return alias_map

        except Exception as e:
            logger.error(f"LLM epithet resolution failed: {e}")
            return {name: [] for name in epithet_groups}

    def _entities_in_death_relationship(
        self,
        epithet_name: str,
        proper_name: str,
        epithet_results: list[CharacterValidationResult],
        proper_name_results: list[CharacterValidationResult],
    ) -> bool:
        """
        Check if one entity dies in context with another entity.

        This is an ABSOLUTE merge blocker: if entity A dies in proximity to entity B,
        they cannot be the same person. This handles cases like:
        - "fell prostrate in death the Prince Prospero" near "the mummer"
        - "killed by X" near "Y"

        Returns True if a death relationship is detected, blocking the merge.
        """
        # Death indicators - patterns showing someone dying
        death_patterns = [
            r'\bfell prostrate in death\b',
            r'\b(died|death|dead|dying|killed|slain|slew|murdered)\b',
            r'\b(corpse|body|remains) of\b',
            r'\bbreathed (his|her|their) last\b',
            r'\bexpired\b',
            r'\bperished\b',
        ]

        # Collect all context snippets for both entities
        epithet_contexts = []
        for result in epithet_results:
            for mention in result.proposal.mentions:
                if mention.context:
                    epithet_contexts.append(mention.context.lower())

        proper_contexts = []
        for result in proper_name_results:
            for mention in result.proposal.mentions:
                if mention.context:
                    proper_contexts.append(mention.context.lower())

        # Normalize names for matching - try multiple variants
        epithet_normalized = epithet_name.lower().replace("the ", "").strip()
        epithet_variants = [
            epithet_normalized,
            epithet_name.lower().strip(),  # With "the" if present
        ]

        proper_normalized = proper_name.lower().replace("the ", "").strip()
        proper_parts = proper_normalized.split()
        proper_variants = [
            proper_normalized,
            proper_name.lower().strip(),  # With "the" if present
        ]
        # Add individual parts (last name, first name) for matching
        for part in proper_parts:
            if len(part) > 2:  # Skip very short words
                proper_variants.append(part)

        # Check ALL contexts from BOTH entities
        # If we find a death pattern + BOTH names in the same context, block the merge
        all_contexts = epithet_contexts + proper_contexts

        logger.info(f"Death check: epithet '{epithet_name}' vs proper '{proper_name}'")
        logger.info(f"  Epithet variants: {epithet_variants}")
        logger.info(f"  Proper variants: {proper_variants}")
        logger.info(f"  Total contexts to check: {len(all_contexts)}")

        for i, ctx in enumerate(all_contexts):
            # Check if this context contains a death pattern
            has_death = False
            for pattern in death_patterns:
                if re.search(pattern, ctx, re.IGNORECASE):
                    has_death = True
                    break

            if not has_death:
                continue

            logger.info(f"  Context {i} has death pattern")

            # Check if epithet is mentioned in this context (any variant)
            has_epithet = any(variant in ctx for variant in epithet_variants)

            # Check if proper name is mentioned in this context (any variant)
            has_proper = any(variant in ctx for variant in proper_variants)

            logger.info(f"  Context {i}: has_epithet={has_epithet}, has_proper={has_proper}")
            if has_epithet or has_proper:
                logger.info(f"  Context {i} content: {ctx[:500]}")

            # If we have death + both entities in same context, they're separate people
            if has_death and has_epithet and has_proper:
                logger.warning(
                    f"DEATH RELATIONSHIP DETECTED: Blocking merge of '{epithet_name}' "
                    f"and '{proper_name}' - both appear together in death context: "
                    f"{ctx[:300]}"
                )
                return True

        logger.info(f"Death check complete: NO death relationship found")
        return False

    def _entities_in_confrontation(
        self,
        epithet_name: str,
        proper_name: str,
        epithet_results: list[CharacterValidationResult],
        proper_name_results: list[CharacterValidationResult],
    ) -> bool:
        """
        Check if an epithet and proper name appear in confrontational relationship.

        Returns True if they appear to be separate entities interacting (pursuing,
        confronting, seizing, etc.), which indicates they should NOT be merged.

        Enhanced to detect confrontation even when the other entity is referred to
        indirectly (e.g., "his pursuer", "the retreating figure").
        """
        # Confrontation indicators - verbs and patterns showing separate entities interacting
        confrontation_patterns = [
            # Physical confrontation
            r'\b(pursued|pursuing|chase|chased|chasing|fled|fleeing|escape|escaped|escaping)\b',
            r'\b(seized|seizing|seize|grabbed|grabbing|grab|caught|catching|catch)\b',
            r'\b(confronted|confronting|confront|faced|facing|face)\b',
            r'\b(attacked|attacking|attack|struck|striking|strike|fought|fighting|fight)\b',
            r'\b(approached|approaching|approach|advanced|advancing|advance)\b',
            # Opposition/conflict
            r'\b(opposed|opposing|oppose|resisted|resisting|resist)\b',
            r'\b(retreating|retreat|retreated|backing away|backed away)\b',
            # Observation as separate entities
            r'\b(watched|watching|watch|observed|observing|observe|saw|see|seeing)\b',
            # Interaction verbs showing separate agents
            r'\b(addressed|addressing|address|spoke to|speaking to|speak to)\b',
            # Indirect references suggesting another entity
            r'\b(his|her|their) (pursuer|opponent|attacker|assailant)\b',
            r'\bthe (retreating|advancing|approaching) (figure|form|person|intruder|stranger)\b',
        ]

        # Collect all context snippets for both entities
        epithet_contexts = []
        for result in epithet_results:
            for mention in result.proposal.mentions:
                if mention.context:
                    epithet_contexts.append(mention.context.lower())

        proper_contexts = []
        for result in proper_name_results:
            for mention in result.proposal.mentions:
                if mention.context:
                    proper_contexts.append(mention.context.lower())

        # Normalize names for matching (remove "the ", lowercase, handle variations)
        epithet_normalized = epithet_name.lower().replace("the ", "").strip()
        proper_normalized = proper_name.lower().replace("the ", "").strip()

        # Also check for partial matches (e.g., "Prince" from "Prince Prospero")
        proper_parts = proper_normalized.split()

        # Look for contexts where both names appear together
        confrontation_count = 0
        total_cooccurrence = 0

        # Check epithet contexts for mentions of the proper name
        for ctx in epithet_contexts:
            # Check if proper name or its parts appear in this epithet context
            has_proper_name = False
            if proper_normalized in ctx:
                has_proper_name = True
            else:
                # Check for partial matches (any part of the proper name)
                for part in proper_parts:
                    if len(part) > 2 and part in ctx:  # Avoid matching very short words
                        has_proper_name = True
                        break

            if has_proper_name:
                total_cooccurrence += 1
                # Check for confrontation patterns
                for pattern in confrontation_patterns:
                    if re.search(pattern, ctx, re.IGNORECASE):
                        confrontation_count += 1
                        logger.info(f"Confrontation detected between '{epithet_name}' and '{proper_name}': {ctx[:100]}")
                        break  # Count each context only once

        # Check proper name contexts for mentions of the epithet
        for ctx in proper_contexts:
            if epithet_normalized in ctx:
                total_cooccurrence += 1
                # Check for confrontation patterns
                for pattern in confrontation_patterns:
                    if re.search(pattern, ctx, re.IGNORECASE):
                        confrontation_count += 1
                        logger.info(f"Confrontation detected between '{epithet_name}' and '{proper_name}': {ctx[:100]}")
                        break

        # ENHANCED: Also check for confrontation patterns in ANY context, even without direct co-occurrence
        # This handles cases where long sentences prevent both names from appearing in the same context window
        epithet_confrontation_solo = 0
        for ctx in epithet_contexts:
            for pattern in confrontation_patterns:
                if re.search(pattern, ctx, re.IGNORECASE):
                    epithet_confrontation_solo += 1
                    logger.debug(f"Confrontation pattern in epithet context: {ctx[:80]}")
                    break

        proper_confrontation_solo = 0
        for ctx in proper_contexts:
            for pattern in confrontation_patterns:
                if re.search(pattern, ctx, re.IGNORECASE):
                    proper_confrontation_solo += 1
                    logger.debug(f"Confrontation pattern in proper name context: {ctx[:80]}")
                    break

        # DEBUG: Log detection results
        logger.info(f"Confrontation check: '{epithet_name}' vs '{proper_name}' - "
                   f"co-occur: {total_cooccurrence}, confrontation: {confrontation_count}, "
                   f"epithet_solo: {epithet_confrontation_solo}, proper_solo: {proper_confrontation_solo}")

        # Original logic: If they co-occur and majority show confrontation, block
        if total_cooccurrence >= 2 and confrontation_count >= total_cooccurrence * 0.5:
            logger.info(f"Blocking merge: '{epithet_name}' and '{proper_name}' show confrontation "
                       f"({confrontation_count}/{total_cooccurrence} co-occurrences)")
            return True

        # NEW LOGIC: If BOTH entities have confrontation patterns in their own contexts,
        # they're likely separate entities interacting (even if not in the same snippet)
        if epithet_confrontation_solo >= 2 and proper_confrontation_solo >= 2:
            logger.info(f"Blocking merge: Both entities show confrontation patterns in their contexts "
                       f"(epithet: {epithet_confrontation_solo}, proper: {proper_confrontation_solo})")
            return True

        logger.info(f"No confrontation detected (threshold not met): '{epithet_name}' vs '{proper_name}'")
        return False

    def _llm_cross_group_resolution(
        self,
        epithet_groups: dict[str, list[CharacterValidationResult]],
        proper_name_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, str]:
        """
        Use LLM to link epithets to proper names (e.g., "the prince" -> "Prince Prospero").

        Returns:
            dict mapping epithet_name -> proper_name for confirmed matches
        """
        if not self.llm or len(epithet_groups) == 0 or len(proper_name_groups) == 0:
            return {}

        # Build prompt with epithet info
        epithet_lines = []
        sorted_epithets = sorted(
            epithet_groups.items(),
            key=lambda x: -sum(r.proposal.mention_count for r in x[1]),
        )[:15]  # Limit to top 15 epithets to keep prompt manageable

        for name, results in sorted_epithets:
            total_mentions = sum(r.proposal.mention_count for r in results)
            chapters_str = self._chapters_for_name(name, epithet_groups, max_chapters=8)
            # Increased context size to 800 chars to capture death/confrontation scenes that may span 150+ chars
            # (e.g., Poe's death scene: "fell prostrate in death" to "seizing the mummer" is ~150 chars)
            context_str = self._format_contexts(results, max_contexts=4, max_chars=800)
            epithet_lines.append(f"- {name} ({total_mentions} mentions, chapters: {chapters_str})")
            epithet_lines.append(f"  Context: {context_str}")

        # Build prompt with proper name info
        proper_name_lines = []
        sorted_proper = sorted(
            proper_name_groups.items(),
            key=lambda x: -sum(r.proposal.mention_count for r in x[1]),
        )[:15]  # Limit to top 15 proper names

        for name, results in sorted_proper:
            total_mentions = sum(r.proposal.mention_count for r in results)
            chapters_str = self._chapters_for_name(name, proper_name_groups, max_chapters=8)
            # Increased context size to 600 chars to capture death/confrontation scenes
            context_str = self._format_contexts(results, max_contexts=3, max_chars=600)
            proper_name_lines.append(f"- {name} ({total_mentions} mentions, chapters: {chapters_str})")
            proper_name_lines.append(f"  Context: {context_str}")

        epithets_str = "\n".join(epithet_lines)
        proper_names_str = "\n".join(proper_name_lines)
        prompt = CROSS_GROUP_PROMPT.format(epithets=epithets_str, proper_names=proper_names_str)

        try:
            result, response = self.llm.query_json(prompt, system=CROSS_GROUP_SYSTEM)

            if result is None or not isinstance(result, list):
                logger.warning("LLM cross-group resolution returned invalid response")
                return {}

            # DEBUG: Log LLM recommendations
            logger.info(f"LLM cross-group recommendations: {result}")

            # Parse response into epithet -> proper_name mapping
            cross_map = {}
            for match in result:
                if not isinstance(match, dict):
                    continue

                epithet = match.get("epithet", "")
                proper_name = match.get("proper_name", "")

                if not epithet or not proper_name:
                    continue

                # Match to actual names (fuzzy matching to handle LLM variations)
                matched_epithet = self._find_closest_name(epithet, epithet_groups.keys())
                matched_proper = self._find_closest_name(proper_name, proper_name_groups.keys())

                if matched_epithet and matched_proper:
                    # Pre-filter: Check for absolute merge blockers
                    epithet_results = epithet_groups.get(matched_epithet, [])
                    proper_results = proper_name_groups.get(matched_proper, [])

                    # FIRST: Check for death relationship (absolute blocker)
                    if self._entities_in_death_relationship(matched_epithet, matched_proper, epithet_results, proper_results):
                        logger.info(f"Skipping cross-group match due to death relationship: '{matched_epithet}' vs '{matched_proper}'")
                        continue

                    # SECOND: Check for confrontation (strong indicator they're separate)
                    if self._entities_in_confrontation(matched_epithet, matched_proper, epithet_results, proper_results):
                        logger.info(f"Skipping cross-group match due to confrontation: '{matched_epithet}' vs '{matched_proper}'")
                        continue

                    cross_map[matched_epithet] = matched_proper
                    logger.info(f"Cross-group match: epithet '{matched_epithet}' -> proper name '{matched_proper}'")

            return cross_map

        except Exception as e:
            logger.error(f"LLM cross-group resolution failed: {e}")
            return {}

    def _pick_canonical_epithet(
        self,
        epithets: list[str],
        epithet_groups: dict[str, list[CharacterValidationResult]],
    ) -> str:
        """
        Pick the best canonical name from a group of epithet aliases.

        Priority:
        1. Specificity: more words = more specific (e.g., "the blind old man" > "the old man")
        2. Uniqueness: less common phrases are more unique
        3. Frequency: higher mention count indicates more established usage
        """
        if len(epithets) == 1:
            return epithets[0]

        def score(epithet: str) -> tuple[int, int, int]:
            # Word count (more = more specific)
            words = epithet.lower().split()
            word_count = len(words)

            # Uniqueness: inverse of how common each word is
            # More unique words = better canonical
            common_words = {'the', 'a', 'an', 'old', 'young', 'man', 'woman', 'person'}
            unique_words = sum(1 for w in words if w not in common_words)

            # Mention count
            results = epithet_groups.get(epithet, [])
            mention_count = sum(r.proposal.mention_count for r in results)

            return (word_count, unique_words, mention_count)

        return max(epithets, key=score)

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID for a character."""
        # Use hash of lowercase name for consistency
        name_hash = hashlib.md5(name.lower().encode()).hexdigest()[:8]
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:20]
        return f"char_{safe_name}_{name_hash}"
