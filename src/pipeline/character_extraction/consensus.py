"""
Cross-chapter character consensus builder.

Merges character proposals across chapters, resolves aliases,
and produces the final CharacterMap.
"""

import re
import hashlib
from typing import Optional
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


ALIAS_RESOLUTION_SYSTEM = """You are a literary analyst identifying character aliases.

Your task is to determine which character names refer to the SAME PERSON.

IMPORTANT: Titles, ranks, and honorifics should be IGNORED when matching names.
The underlying PERSON is what matters, not how they're addressed. Examples:
- Military: "SSgt Otto" = "Staff Sergeant Mark Otto" = "Mark Otto" = "Otto"
- Civilian: "Mr. Smith" = "John Smith" = "Smith"
- Religious: "Father O'Brien" = "Patrick O'Brien" = "O'Brien"
- Foreign: "Señor García" = "Miguel García" = "García"
- Academic: "Professor Williams" = "Dr. Williams" = "Jane Williams"
- Nobility: "Lord Pemberton" = "Charles Pemberton" = "Pemberton"

CRITICAL RULES:
1. Only merge names if they CLEARLY refer to the same individual
2. Different people with similar names should NEVER be merged
3. Pay attention to chapter appearances and context clues
4. When in doubt, keep names SEPARATE

For the canonical name, prefer the FULL CIVILIAN NAME (first + last) over titled versions.

NEVER merge:
- Different characters who happen to share a first name (e.g., two Michaels in the same story)
- Different characters who share a LAST name but have different first names (family members, spouses)
  - A married couple sharing a last name are two separate people
  - Siblings sharing a last name are separate people
  - A bare last name should only merge with ONE full-name character
- Characters who appear in completely different parts of the book
- Names that are clearly different people based on context"""


ALIAS_RESOLUTION_PROMPT = """Identify which character names refer to the SAME PERSON in this novel.

CHARACTER NAMES (with chapter info and sample contexts):
{characters}

IMPORTANT: Only merge names if you are CERTAIN they refer to the same person.
- Check if they appear in similar chapters
- Check if the contexts suggest the same person
- When uncertain, keep names SEPARATE

Return JSON array:
```json
[
  {{"canonical": "Full Name", "aliases": ["Nickname"]}},
  {{"canonical": "Another Character", "aliases": []}}
]
```

Return ONLY the JSON array. Every character must appear exactly once (either as canonical or as an alias)."""


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
                    canonical, alias = self._pick_canonical(name1, name2)
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
                            canonical, alias = self._pick_canonical(name, actual_name)
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

    def _pick_canonical(self, name1: str, name2: str) -> tuple[str, str]:
        """Pick which name should be canonical vs alias."""
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

    def _llm_alias_resolution(
        self,
        name_groups: dict[str, list[CharacterValidationResult]],
    ) -> dict[str, list[str]]:
        """Use LLM to resolve aliases with rich context."""
        # Build rich context for each character
        char_lines = []
        for name, results in sorted(name_groups.items(), key=lambda x: -sum(r.proposal.mention_count for r in x[1]), reverse=False):
            total_mentions = sum(r.proposal.mention_count for r in results)
            chapters = sorted(set(r.proposal.chapter_index for r in results))
            chapters_str = ", ".join(str(c) for c in chapters[:5])
            if len(chapters) > 5:
                chapters_str += f"... ({len(chapters)} total)"

            # Get sample contexts (first 2)
            sample_contexts = []
            for r in results[:2]:
                if r.proposal.mentions:
                    ctx = r.proposal.mentions[0].context[:60].replace("\n", " ").strip()
                    if ctx:
                        sample_contexts.append(f'"{ctx}..."')

            context_str = " | ".join(sample_contexts) if sample_contexts else "no context"

            char_lines.append(f"- {name} ({total_mentions} mentions, chapters: {chapters_str})")
            char_lines.append(f"  Context: {context_str}")

        characters_str = "\n".join(char_lines)

        prompt = ALIAS_RESOLUTION_PROMPT.format(characters=characters_str)

        result, response = self.llm.query_json(prompt, system=ALIAS_RESOLUTION_SYSTEM)

        if result is None:
            error_msg = "LLM alias resolution failed - cannot continue with heuristics"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(result, list):
            error_msg = f"LLM alias resolution returned non-list: {type(result)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

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

                if is_valid and confidence >= 0.7:
                    # Merge: pick the more complete name as canonical
                    canonical, alias = self._pick_canonical(name1, name2)

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
        # Extract words from names
        words1 = re.sub(r'[^\w\s]', '', canonical.lower()).split()
        words2 = re.sub(r'[^\w\s]', '', alias.lower()).split()
        significant1 = {w for w in words1 if len(w) >= 3}
        significant2 = {w for w in words2 if len(w) >= 3}
        shared_words = significant1 & significant2

        # Get chapter info
        canonical_results = name_groups.get(canonical, [])
        alias_results = name_groups.get(alias, [])
        canonical_chapters = set(r.proposal.chapter_index for r in canonical_results)
        alias_chapters = set(r.proposal.chapter_index for r in alias_results)
        has_chapter_overlap = bool(canonical_chapters & alias_chapters)

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

                    # If they have different first names, reject
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
            logger.debug(f"Merge accepted: {canonical} <- {alias} (shared words: {shared_words})")
            return True, 0.85

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

        # Only trust LLM if we have chapter overlap
        if has_chapter_overlap:
            logger.debug(f"Merge accepted: {canonical} <- {alias} (trusting LLM, has chapter overlap)")
            return True, 0.6
        else:
            logger.debug(f"Merge rejected: {canonical} <-> {alias} (no shared words, no chapter overlap)")
            return False, 0.3

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
