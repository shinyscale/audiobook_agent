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
from ..llm import LLMClient

logger = logging.getLogger(__name__)

# Common titles that should be ignored when comparing character names
# These are not part of the actual name but indicate social status or role
TITLES = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord', 'professor', 'captain', 'major'}

PAIRWISE_ALIAS_SYSTEM = """You are a literary analyst identifying whether two character names refer to the SAME PERSON.

CRITICAL:
- Use ONLY the evidence provided below (chapter appearances and context snippets).
- Be conservative: false negatives (missing an alias) are better than false positives (merging different people).
- Titles (Mr/Mrs/Miss/Dr/etc.) are not part of the name; treat them as address forms.

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

        # Resolve aliases
        if self.use_llm_alias_resolution and len(name_groups) > 1:
            logger.info("CharacterConsensusBuilder: using LLM alias resolution")
            alias_groups = self._llm_alias_resolution(name_groups)
        else:
            logger.info("CharacterConsensusBuilder: using heuristic alias resolution")
            alias_groups = self._heuristic_alias_resolution(name_groups, valid_results)

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

        Priority:
        1. Longer names (more complete)
        2. Untitled over titled
        3. Higher mention count (NEW!)
        4. Alphabetically first
        """
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

        # Prefer higher mention count (most frequently used name)
        if count1 != count2:
            return (name1, name2) if count1 > count2 else (name2, name1)

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
        ctx_a = self._format_contexts(results_a, max_contexts=6 if amb else 4, max_chars=200 if amb else 160)
        ctx_b = self._format_contexts(results_b, max_contexts=6 if amb else 4, max_chars=200 if amb else 160)

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

        # Evaluate candidates
        accepted = 0
        for a, b in candidates:
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
        alias_map: dict[str, list[str]] = {}
        for _root, members in components.items():
            if len(members) == 1:
                alias_map[members[0]] = []
                continue

            def score(name: str) -> tuple[int, int, int, str]:
                parts = name.split()
                has_title = 1 if parts and parts[0].rstrip('.').lower() in TITLES else 0
                mention_count = self._total_mentions_for_name(name, name_groups)
                # higher is better for first/third; lower is better for has_title
                return (len(parts), -has_title, mention_count, name)

            canonical = max(members, key=score)
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

    def _validate_merge(
        self,
        canonical: str,
        alias: str,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> tuple[bool, float]:
        """
        Validate LLM merge decision with sanity checks.

        Key checks:
        1. Reject merges that only share a last name when multiple people have that last name
        2. Reject merges with no shared words and no chapter overlap

        Returns:
            (is_valid, confidence) tuple
        """
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
        # If both are single-word names with NO shared words, reject immediately
        # NOTE: This is intentionally strict. Legitimate nicknames (Tom/Thomas) should be
        # caught by LLM alias resolution earlier in the pipeline. This prevents the
        # worst over-merges (Alice + Robert) during validation.
        if len(significant1) == 1 and len(significant2) == 1:
            if not shared_words:  # Different single-word names
                logger.debug(
                    f"Merge rejected: {canonical} <-> {alias} "
                    f"(both single-word names with no similarity - likely different characters)"
                )
                return False, 0.05

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
                    if len(words1) == 1 or len(words2) == 1:
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

                        # Get contexts for both names to check for alias indicators
                        canonical_contexts = []
                        alias_contexts = []
                        for result in canonical_results[:5]:  # Check first 5 contexts
                            if hasattr(result.proposal, 'context') and result.proposal.context:
                                canonical_contexts.append(result.proposal.context.lower())
                        for result in alias_results[:5]:
                            if hasattr(result.proposal, 'context') and result.proposal.context:
                                alias_contexts.append(result.proposal.context.lower())

                        # Check if any context mentions alias relationship
                        all_contexts = canonical_contexts + alias_contexts
                        for context in all_contexts:
                            # Check for birth name indicators
                            for indicator in birth_name_indicators:
                                if indicator in context:
                                    # Additional validation: both names should appear or be referenced in context
                                    # This prevents false positives from generic "birth name" mentions
                                    canonical_lower = canonical.lower()
                                    alias_lower = alias.lower()

                                    # Check if either name appears in the context
                                    if canonical_lower in context or alias_lower in context:
                                        logger.info(
                                            f"Merge ALLOWED: {canonical} <- {alias} "
                                            f"(birth name/alias indicator found: '{indicator}')"
                                        )
                                        return True, 0.85  # High confidence for explicit alias mentions

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

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID for a character."""
        # Use hash of lowercase name for consistency
        name_hash = hashlib.md5(name.lower().encode()).hexdigest()[:8]
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:20]
        return f"char_{safe_name}_{name_hash}"
