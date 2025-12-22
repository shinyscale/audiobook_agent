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
)
from ..llm import LLMClient

logger = logging.getLogger(__name__)


ALIAS_RESOLUTION_SYSTEM = """You are a literary analyst identifying character aliases.

Your task is to determine which character names refer to the SAME PERSON.

CRITICAL RULES:
1. Only merge names if they CLEARLY refer to the same individual
2. Different people with similar names should NEVER be merged
3. Pay attention to chapter appearances and context clues
4. When in doubt, keep names SEPARATE

Valid alias patterns:
- Full name ↔ First name only: "Nick Carraway" = "Nick"
- Full name ↔ Titled name: "Elizabeth Bennet" = "Miss Bennet"
- Full name ↔ Nickname: "Elizabeth" = "Lizzy"

NEVER merge:
- Different characters who happen to share a first name
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
        # Filter to valid proposals
        valid_results = [v for v in validations if v.is_valid]

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

        # Resolve aliases
        if self.use_llm_alias_resolution and len(name_groups) > 1:
            alias_groups = self._llm_alias_resolution(name_groups)
        else:
            alias_groups = self._heuristic_alias_resolution(name_groups, valid_results)

        # Build final characters
        characters = []
        low_confidence = []

        for canonical_name, aliases in alias_groups.items():
            # Collect all mentions for this character
            all_mentions = []
            all_strategies = set()
            all_confidences = []
            chapters_present = set()

            # Get mentions from canonical name
            if canonical_name in name_groups:
                for result in name_groups[canonical_name]:
                    all_mentions.extend(result.proposal.mentions)
                    all_strategies.add(result.proposal.strategy)
                    all_confidences.append(result.overall_score)
                    chapters_present.add(result.proposal.chapter_index)

            # Get mentions from aliases
            for alias in aliases:
                if alias in name_groups:
                    for result in name_groups[alias]:
                        all_mentions.extend(result.proposal.mentions)
                        all_strategies.add(result.proposal.strategy)
                        all_confidences.append(result.overall_score)
                        chapters_present.add(result.proposal.chapter_index)

            if not all_mentions:
                continue

            # Sort mentions by position
            all_mentions.sort(key=lambda m: m.position)

            # Calculate final confidence
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.5

            # Boost confidence for multiple strategies or many chapters
            if len(all_strategies) > 1:
                avg_confidence = min(1.0, avg_confidence + 0.1)
            if len(chapters_present) > 3:
                avg_confidence = min(1.0, avg_confidence + 0.05)

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
        """Check if two names likely refer to the same person."""
        # Exact match (case insensitive)
        if name1.lower() == name2.lower():
            return True

        # Normalize: remove titles, lowercase
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        if norm1 == norm2:
            return True

        # Check if one is first name of the other
        parts1 = norm1.split()
        parts2 = norm2.split()

        if len(parts1) == 1 and len(parts2) > 1:
            # name1 might be first name of name2
            if parts1[0] == parts2[0] or parts1[0] == parts2[-1]:
                return True

        if len(parts2) == 1 and len(parts1) > 1:
            # name2 might be first name of name1
            if parts2[0] == parts1[0] or parts2[0] == parts1[-1]:
                return True

        # Check for titled version (Mr. Smith == Smith)
        if len(parts1) == 1 and len(parts2) == 2:
            if parts2[0].rstrip('.').lower() in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}:
                if parts1[0] == parts2[1]:
                    return True

        if len(parts2) == 1 and len(parts1) == 2:
            if parts1[0].rstrip('.').lower() in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}:
                if parts2[0] == parts1[1]:
                    return True

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
            logger.warning("LLM alias resolution failed, falling back to heuristics")
            return self._heuristic_alias_resolution(name_groups, [r for results in name_groups.values() for r in results])

        if not isinstance(result, list):
            logger.warning("LLM alias resolution returned non-list")
            return self._heuristic_alias_resolution(name_groups, [r for results in name_groups.values() for r in results])

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
        Validate if two names should be merged.

        Returns:
            (is_valid, confidence) tuple
        """
        # Check 1: Name similarity
        similarity = self._name_similarity(canonical, alias)
        if similarity < 0.3:
            # Very different names - definitely not aliases
            logger.debug(f"Merge rejected: {canonical} <-> {alias} (similarity={similarity:.2f} < 0.3)")
            return False, 0.0

        # Check 2: Chapter overlap
        canonical_results = name_groups.get(canonical, [])
        alias_results = name_groups.get(alias, [])

        canonical_chapters = set(r.proposal.chapter_index for r in canonical_results)
        alias_chapters = set(r.proposal.chapter_index for r in alias_results)

        # If both appear in 3+ chapters with zero overlap, they're probably different people
        if len(canonical_chapters) >= 3 and len(alias_chapters) >= 3:
            overlap = canonical_chapters & alias_chapters
            if not overlap:
                logger.debug(f"Merge rejected: {canonical} <-> {alias} (no chapter overlap)")
                return False, 0.1

        # Check 3: Name structure compatibility
        # Names like "Daisy" and "Catherine" have no structural relationship
        if not self._names_structurally_compatible(canonical, alias):
            logger.debug(f"Merge rejected: {canonical} <-> {alias} (structurally incompatible)")
            return False, 0.2

        # Calculate final confidence based on similarity and patterns
        confidence = similarity

        # Boost for known patterns
        if self._is_known_alias_pattern(canonical, alias):
            confidence = min(1.0, confidence + 0.2)

        # Require minimum confidence
        return confidence >= 0.5, confidence

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

    def _names_structurally_compatible(self, name1: str, name2: str) -> bool:
        """
        Check if two names have a structural relationship that suggests they could be aliases.

        Returns True if:
        - One is a first name of the other
        - One is a titled version of the other (Mr. Smith vs Smith)
        - They share significant components
        """
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        parts1 = norm1.split()
        parts2 = norm2.split()

        # Single name matching part of multi-name
        if len(parts1) == 1 and len(parts2) > 1:
            if parts1[0] in parts2:
                return True

        if len(parts2) == 1 and len(parts1) > 1:
            if parts2[0] in parts1:
                return True

        # Multi-name sharing components
        if len(parts1) > 1 and len(parts2) > 1:
            # Must share at least one full name component
            if set(parts1) & set(parts2):
                return True

        # Single names must have high similarity to be compatible
        if len(parts1) == 1 and len(parts2) == 1:
            # "Daisy" and "Catherine" are NOT compatible (different base names)
            # "Lizzy" and "Elizabeth" might be (similarity-based)
            return SequenceMatcher(None, parts1[0], parts2[0]).ratio() > 0.6

        return False

    def _is_known_alias_pattern(self, name1: str, name2: str) -> bool:
        """Check if names follow a known alias pattern."""
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        # Title + Name vs Name (Mr. Gatsby vs Gatsby)
        parts1 = name1.lower().split()
        parts2 = name2.lower().split()

        titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}

        if len(parts1) == 2 and parts1[0].rstrip('.') in titles:
            if len(parts2) == 1 and parts2[0] == parts1[1]:
                return True

        if len(parts2) == 2 and parts2[0].rstrip('.') in titles:
            if len(parts1) == 1 and parts1[0] == parts2[1]:
                return True

        # First name vs Full name (Nick vs Nick Carraway)
        if len(parts1) == 1 and len(parts2) > 1:
            if parts1[0] == parts2[0]:  # First name match
                return True

        if len(parts2) == 1 and len(parts1) > 1:
            if parts2[0] == parts1[0]:  # First name match
                return True

        return False

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID for a character."""
        # Use hash of lowercase name for consistency
        name_hash = hashlib.md5(name.lower().encode()).hexdigest()[:8]
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:20]
        return f"char_{safe_name}_{name_hash}"
