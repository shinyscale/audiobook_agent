"""
CharacterAgent - Specialized agent for character extraction.

Wraps CharacterExtractionPipeline with self-verification to ensure:
- No duplicate characters (same person under different names)
- Consistent alias resolution
- Proper mention distribution
"""

from typing import Optional
import logging
import re
import time

from .base import Agent, AgentContext, AgentResult, VerificationResult, VerificationIssue, VerificationLevel
from .config import AgentConfig, PipelineTuningConfig
from ..pipeline.character_extraction.pipeline import CharacterExtractionPipeline
from ..pipeline.character_extraction.models import CharacterMap, Character
from ..pipeline.chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..pipeline.llm import LLMClient

logger = logging.getLogger(__name__)


# Pronoun/determiner stopwords - characters with these names should be flagged/removed
PRONOUN_STOPWORDS = {
    'he', 'she', 'it', 'they', 'we', 'i', 'you',
    'him', 'her', 'them', 'us', 'me',
    'his', 'hers', 'its', 'their', 'our', 'my', 'your',
    'this', 'that', 'these', 'those', 'the', 'a', 'an',
}

# Agentive verb patterns for detecting unnamed characters
AGENTIVE_VERBS = [
    r'\b(said|asked|replied|whispered|shouted|called|cried|muttered|exclaimed)\b',
    r'\b(walked|ran|stood|turned|looked|smiled|laughed|nodded|frowned)\b',
    r'\b(grabbed|took|held|threw|placed|opened|closed|pushed|pulled)\b',
    r'\b(sat|came|went|entered|left|arrived|departed|approached|retreated)\b',
]


DUPLICATE_CHECK_SYSTEM = """You are a literary analyst checking for duplicate characters.

Your task is to identify characters that may be the SAME PERSON listed separately.

Look for:
1. Names that share components (same first name, same last name)
2. Characters that appear in similar chapters
3. Names that could be nicknames/aliases for each other

Only flag pairs you are CONFIDENT are duplicates."""


DUPLICATE_CHECK_PROMPT = """Review these characters for potential duplicates (same person listed twice):

{character_list}

For each potential duplicate pair, check:
- Do the names share significant components?
- Do they appear in overlapping chapters?
- Could one be a nickname/title for the other?

Return JSON:
{{
  "duplicates": [
    {{"name1": "...", "name2": "...", "reason": "...", "confidence": 0.0-1.0}}
  ],
  "analysis": "Brief summary"
}}

If no duplicates found, return: {{"duplicates": [], "analysis": "No duplicates detected"}}

Return ONLY valid JSON."""


class CharacterAgent(Agent):
    """
    Specialized agent for character extraction with self-verification.

    Wraps the existing CharacterExtractionPipeline and adds verification:
    - Checks for duplicate characters that slipped through alias resolution
    - Validates mention distribution (major characters across chapters)
    - Verifies alias consistency
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        tuning: Optional[PipelineTuningConfig] = None,
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self._tuning = tuning

    @property
    def name(self) -> str:
        return "character_agent"

    @property
    def recommended_models(self) -> list[str]:
        return [
            "gpt-4o",  # Strong narrative understanding
            "claude-3-5-sonnet",  # Good at character relationships
            "llama3.2",  # Local alternative
        ]

    def run(self, context: AgentContext) -> AgentResult[CharacterMap]:
        """Run character extraction pipeline."""
        start_time = time.perf_counter()

        # We need chapter_map from context
        if not context.chapter_map:
            # Get model info for error case
            model_used = self.config.model if self.config else None
            provider_used = self.config.provider if self.config else None

            return AgentResult(
                data=CharacterMap(
                    characters=[],
                    low_confidence_characters=[],
                    total_mentions=0,
                    total_chapters=0,
                    pipeline_metadata={"error": "No chapter map provided"},
                ),
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                issues=["No chapter map provided - cannot extract characters"],
                model_used=model_used,
                provider_used=provider_used,
            )

        pipeline = self._get_pipeline()
        character_map, _ = pipeline.run(
            full_text=context.text,
            chapter_map=context.chapter_map,
            source_file=context.source_file,
        )

        # Calculate confidence breakdown
        high = sum(1 for c in character_map.characters if c.confidence >= 0.7)
        medium = sum(1 for c in character_map.characters if 0.4 <= c.confidence < 0.7)
        low = sum(1 for c in character_map.characters if c.confidence < 0.4)
        low += len(character_map.low_confidence_characters)

        # Collect issues
        issues = []
        if character_map.low_confidence_characters:
            issues.append(
                f"{len(character_map.low_confidence_characters)} low-confidence characters flagged"
            )

        elapsed = time.perf_counter() - start_time

        # Get model info from config or client
        model_used = None
        provider_used = None
        if self.config and self.config.model:
            model_used = self.config.model
            provider_used = self.config.provider
        elif self.llm and self.llm.config:
            model_used = self.llm.config.model
            provider_used = self.llm.config.provider

        return AgentResult(
            data=character_map,
            confidence_scores=[c.confidence for c in character_map.characters],
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
            issues=issues,
            processing_time_seconds=elapsed,
            model_used=model_used,
            provider_used=provider_used,
        )

    def verify(
        self,
        result: AgentResult[CharacterMap],
        level: VerificationLevel = VerificationLevel.SELF_CHECK,
        context: Optional[AgentContext] = None,
    ) -> VerificationResult:
        """
        Verify character extraction quality.

        Checks:
        1. Low-confidence characters
        2. Duplicate detection (same character under different names)
        3. Mention distribution (major characters across chapters)
        4. Alias consistency
        """
        issues = []
        suggestions = []
        character_map = result.data

        if not character_map.characters:
            return VerificationResult(
                passed=True,
                issues=[],
                suggestions=[],
            )

        # Check 1: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(VerificationIssue(
                description=f"{result.low_confidence_count} characters have low confidence",
                severity="warning",
            ))

        # Check 2: Pronoun entries (should be auto-removed)
        pronoun_issues = self._check_pronoun_entries(character_map.characters)
        issues.extend(pronoun_issues)

        # Check 3: Look for potential duplicates using heuristics
        duplicate_issues = self._check_duplicates_heuristic(character_map.characters)
        issues.extend(duplicate_issues)

        # Check 4: Verify mention distribution
        distribution_issues = self._check_mention_distribution(character_map)
        issues.extend(distribution_issues)

        # Check 5: Verify alias consistency
        alias_issues = self._check_alias_consistency(character_map.characters)
        issues.extend(alias_issues)

        # Check 6: Disjoint chapter distributions (potential name changes)
        disjoint_issues = self._check_disjoint_distributions(
            character_map.characters, character_map.total_chapters
        )
        issues.extend(disjoint_issues)

        # Check 7: Missing agentive descriptions (if context available)
        if context and context.text:
            agentive_issues = self._check_missing_agentive_descriptions(
                context.text, character_map.characters
            )
            issues.extend(agentive_issues)

        # Check 8: LLM duplicate check for high-value verification
        if self.config.enable_verification and self.llm and len(character_map.characters) > 1:
            llm_issues = self._llm_duplicate_check(character_map.characters)
            issues.extend(llm_issues)

        # Determine if passed
        error_count = sum(1 for i in issues if i.severity == "error")
        passed = error_count == 0

        return VerificationResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
        )

    def refine(
        self,
        result: AgentResult[CharacterMap],
        issues: list[VerificationIssue],
    ) -> AgentResult[CharacterMap]:
        """
        Refine character map based on verification issues.

        Automatically removes pronoun entries (error severity).
        Other issues are flagged for manual review.
        """
        character_map = result.data

        # Auto-remove pronoun entries (error severity issues)
        pronoun_issues = [i for i in issues if "pronoun/determiner" in i.description.lower()]
        if pronoun_issues:
            # Get the names to remove from issue descriptions
            pronoun_names = set()
            for issue in pronoun_issues:
                # Extract name from description like "Character 'he' is a pronoun/determiner"
                match = re.search(r"Character '([^']+)' is a pronoun/determiner", issue.description)
                if match:
                    pronoun_names.add(match.group(1).lower())

            # Filter out pronoun characters
            original_count = len(character_map.characters)
            character_map.characters = [
                c for c in character_map.characters
                if c.canonical_name.lower() not in pronoun_names
            ]
            character_map.low_confidence_characters = [
                c for c in character_map.low_confidence_characters
                if c.canonical_name.lower() not in pronoun_names
            ]

            removed_count = original_count - len(character_map.characters)
            if removed_count > 0:
                logger.info(f"CharacterAgent: Auto-removed {removed_count} pronoun entries")
                character_map.pipeline_metadata["pronoun_entries_removed"] = removed_count

        # Add issues to pipeline metadata for review
        issue_descriptions = [i.description for i in issues]
        if issue_descriptions:
            character_map.pipeline_metadata["verification_issues"] = issue_descriptions
            character_map.pipeline_metadata["needs_review"] = True

        # Log remaining errors (non-pronoun)
        remaining_errors = [i for i in issues if i.severity == "error" and "pronoun/determiner" not in i.description.lower()]
        if remaining_errors:
            logger.warning(
                f"CharacterAgent: {len(remaining_errors)} errors remain after refinement"
            )

        return AgentResult(
            data=character_map,
            confidence_scores=result.confidence_scores,
            high_confidence_count=result.high_confidence_count,
            medium_confidence_count=result.medium_confidence_count,
            low_confidence_count=result.low_confidence_count,
            issues=issue_descriptions,
            processing_time_seconds=result.processing_time_seconds,
            model_used=result.model_used,
            provider_used=result.provider_used,
        )

    def _get_pipeline(self) -> CharacterExtractionPipeline:
        """Get or create the character extraction pipeline."""
        t = self._tuning or PipelineTuningConfig()
        return CharacterExtractionPipeline(
            llm_client=self.llm,
            llm_chunk_size=t.character_llm_chunk_chars,
            mention_context_window=t.character_mention_context_chars,
        )

    def _check_duplicates_heuristic(self, characters: list[Character]) -> list[VerificationIssue]:
        """Check for potential duplicates using name matching heuristics."""
        issues = []

        for i, char1 in enumerate(characters):
            for char2 in characters[i + 1:]:
                # Skip if already aliases of each other
                if char2.canonical_name in char1.aliases or char1.canonical_name in char2.aliases:
                    continue

                # Check for shared significant name components
                words1 = set(self._extract_name_words(char1.canonical_name))
                words2 = set(self._extract_name_words(char2.canonical_name))

                # Also check aliases
                for alias in char1.aliases:
                    words1.update(self._extract_name_words(alias))
                for alias in char2.aliases:
                    words2.update(self._extract_name_words(alias))

                shared = words1 & words2
                if shared:
                    # Check chapter overlap
                    chapters1 = set(char1.chapters_present)
                    chapters2 = set(char2.chapters_present)
                    overlap = chapters1 & chapters2

                    if overlap:
                        issues.append(VerificationIssue(
                            description=(
                                f"Potential duplicate: '{char1.canonical_name}' and "
                                f"'{char2.canonical_name}' share name component(s) {shared} "
                                f"and appear in same chapters"
                            ),
                            severity="warning",
                            suggested_fix="Consider merging these characters",
                        ))

        return issues

    def _extract_name_words(self, name: str) -> list[str]:
        """Extract significant words from a name (3+ chars, not titles)."""
        # Remove common titles
        name = re.sub(
            r'\b(mr|mrs|ms|miss|dr|sir|lady|lord|captain|colonel|major|general|sergeant|professor)\b\.?',
            '',
            name,
            flags=re.IGNORECASE
        )

        words = re.findall(r'[a-zA-Z]+', name.lower())
        return [w for w in words if len(w) >= 3]

    def _check_mention_distribution(self, character_map: CharacterMap) -> list[VerificationIssue]:
        """Check for unusual mention distributions."""
        issues = []
        total_chapters = character_map.total_chapters

        if total_chapters <= 1:
            return issues

        for char in character_map.characters[:10]:  # Check top 10 characters
            chapters_present = len(char.chapters_present)
            mention_count = char.mention_count

            # High mention count but few chapters = suspicious
            if mention_count > 50 and chapters_present == 1:
                issues.append(VerificationIssue(
                    description=(
                        f"Character '{char.canonical_name}' has {mention_count} mentions "
                        f"but only appears in 1 chapter - may be a non-character entity"
                    ),
                    severity="warning",
                ))

            # Major character (>100 mentions) should appear in multiple chapters
            if mention_count > 100 and chapters_present < total_chapters * 0.3:
                issues.append(VerificationIssue(
                    description=(
                        f"Major character '{char.canonical_name}' ({mention_count} mentions) "
                        f"only appears in {chapters_present}/{total_chapters} chapters"
                    ),
                    severity="info",
                ))

        return issues

    def _check_alias_consistency(self, characters: list[Character]) -> list[VerificationIssue]:
        """Check that aliases are consistent with canonical names."""
        issues = []

        for char in characters:
            if not char.aliases:
                continue

            canonical_words = set(self._extract_name_words(char.canonical_name))

            for alias in char.aliases:
                alias_words = set(self._extract_name_words(alias))

                # Aliases should share at least one word with canonical name
                if not canonical_words & alias_words:
                    # Exception: single word aliases might be nicknames
                    if len(alias_words) > 1:
                        issues.append(VerificationIssue(
                            description=(
                                f"Alias '{alias}' for '{char.canonical_name}' "
                                f"shares no name components - verify correct"
                            ),
                            severity="info",
                        ))

        return issues

    def _llm_duplicate_check(self, characters: list[Character]) -> list[VerificationIssue]:
        """Use LLM to check for duplicates that heuristics might miss."""
        issues = []

        # Build character list for LLM
        char_lines = []
        for char in characters[:30]:  # Limit to top 30 for prompt size
            aliases_str = f" (aliases: {', '.join(char.aliases[:3])})" if char.aliases else ""
            chapters_str = ", ".join(str(c) for c in char.chapters_present[:5])
            if len(char.chapters_present) > 5:
                chapters_str += f"... ({len(char.chapters_present)} total)"

            char_lines.append(
                f"- {char.canonical_name}{aliases_str}: "
                f"{char.mention_count} mentions, chapters {chapters_str}"
            )

        character_list = "\n".join(char_lines)
        prompt = DUPLICATE_CHECK_PROMPT.format(character_list=character_list)

        try:
            result, _ = self.llm.query_json(prompt, system=DUPLICATE_CHECK_SYSTEM)

            if result and isinstance(result.get("duplicates"), list):
                for dup in result["duplicates"]:
                    if dup.get("confidence", 0) >= 0.7:
                        issues.append(VerificationIssue(
                            description=(
                                f"LLM detected potential duplicate: '{dup.get('name1')}' and "
                                f"'{dup.get('name2')}' - {dup.get('reason', 'no reason given')}"
                            ),
                            severity="warning",
                            suggested_fix="Consider merging these characters",
                        ))
        except Exception as e:
            logger.error(f"LLM duplicate check failed: {e}")
            # Re-raise to fail fast instead of silently continuing
            raise

        return issues

    def _check_pronoun_entries(self, characters: list[Character]) -> list[VerificationIssue]:
        """
        Check for pronoun/determiner entries that should not be characters.

        These entries indicate bugs in upstream extraction and should be
        flagged as errors for auto-removal.
        """
        issues = []

        for char in characters:
            name_lower = char.canonical_name.lower()
            if name_lower in PRONOUN_STOPWORDS:
                issues.append(VerificationIssue(
                    description=f"Character '{char.canonical_name}' is a pronoun/determiner and should not be a character",
                    severity="error",
                    suggested_fix="Remove this entry - it is not a character",
                ))

        return issues

    def _check_disjoint_distributions(
        self,
        characters: list[Character],
        total_chapters: int,
    ) -> list[VerificationIssue]:
        """
        Check for character pairs with disjoint but sequential chapter distributions.

        This pattern may indicate a character name change mid-book (e.g., marriage,
        alias adoption, identity reveal).

        Feature F4: Relaxed Disjoint Distribution Heuristic
        Uses 80% dominant chapter ranges instead of strict separation. This catches cases
        where a character is discussed by their old name in later chapters (e.g., flashbacks,
        other characters reminiscing).

        A dominant range is defined as the contiguous span containing 80%+ of the character's
        appearances. If the dominant ranges of two characters are disjoint/sequential,
        they may be the same person.
        """
        issues = []
        MIN_MENTIONS = 10
        DOMINANT_THRESHOLD = 0.80  # 80% of appearances must be in dominant range

        # Only check characters with significant mentions
        significant = [c for c in characters if c.mention_count >= MIN_MENTIONS]

        for i, char1 in enumerate(significant):
            for char2 in significant[i + 1:]:
                # Skip if already aliases of each other
                if char2.canonical_name in char1.aliases or char1.canonical_name in char2.aliases:
                    continue

                set1, set2 = set(char1.chapters_present), set(char2.chapters_present)
                if not set1 or not set2:
                    continue

                # Feature F4: Calculate dominant chapter ranges
                dominant1 = self._get_dominant_range(set1, DOMINANT_THRESHOLD)
                dominant2 = self._get_dominant_range(set2, DOMINANT_THRESHOLD)

                if not dominant1 or not dominant2:
                    continue

                # Check if dominant ranges are disjoint/sequential
                dom_set1 = set(range(dominant1[0], dominant1[1] + 1))
                dom_set2 = set(range(dominant2[0], dominant2[1] + 1))

                overlap = dom_set1 & dom_set2
                if not overlap:  # Dominant ranges are disjoint
                    # Check if sequential
                    is_sequential = dominant1[1] < dominant2[0] or dominant2[1] < dominant1[0]

                    if is_sequential:
                        # Determine which character comes first
                        if dominant1[1] < dominant2[0]:
                            early_char, late_char = char1.canonical_name, char2.canonical_name
                            early_range, late_range = dominant1, dominant2
                        else:
                            early_char, late_char = char2.canonical_name, char1.canonical_name
                            early_range, late_range = dominant2, dominant1

                        issues.append(VerificationIssue(
                            description=(
                                f"Disjoint dominant ranges: '{early_char}' (dominant chapters {early_range[0]}-{early_range[1]}) "
                                f"and '{late_char}' (dominant chapters {late_range[0]}-{late_range[1]}) - "
                                f"could be same character under different name"
                            ),
                            severity="warning",
                            suggested_fix="Review if these are the same character with a name change",
                        ))

        return issues

    def _get_dominant_range(
        self,
        chapters: set[int],
        threshold: float = 0.80,
    ) -> Optional[tuple[int, int]]:
        """
        Find the smallest contiguous range containing at least `threshold` of appearances.

        Feature F4: Relaxed Disjoint Distribution Heuristic
        Uses a sliding window to find the smallest range that contains 80%+ of
        the character's chapter appearances.

        Args:
            chapters: Set of chapter indices where character appears
            threshold: Minimum fraction of appearances required in range (default 0.80)

        Returns:
            Tuple of (start, end) chapter indices, or None if insufficient data
        """
        if not chapters or len(chapters) < 3:
            return None

        sorted_chapters = sorted(chapters)
        n = len(sorted_chapters)
        required = int(n * threshold)

        if required < 1:
            required = 1

        # Find smallest window containing 'required' chapters
        best_range = None
        best_span = float('inf')

        for start_idx in range(n - required + 1):
            end_idx = start_idx + required - 1
            start_ch = sorted_chapters[start_idx]
            end_ch = sorted_chapters[end_idx]
            span = end_ch - start_ch

            if span < best_span:
                best_span = span
                best_range = (start_ch, end_ch)

        return best_range

    def _check_missing_agentive_descriptions(
        self,
        text: str,
        characters: list[Character],
    ) -> list[VerificationIssue]:
        """
        Check for high-frequency agentive descriptions missing from character list.

        Scans for patterns like "the creature said", "the monster walked" that
        appear 10+ times but are not in the character list.
        """
        issues = []

        # Build set of existing character names for quick lookup
        existing_names = set()
        for char in characters:
            existing_names.add(char.canonical_name.lower())
            for alias in char.aliases:
                existing_names.add(alias.lower())

        # Pattern to find "the X <agentive_verb>" constructions
        # We look for "the <noun>" followed by an agentive verb
        descriptive_pattern = r'\bthe\s+([a-z]+(?:\s+[a-z]+)?)\s+'

        # Count occurrences of each descriptive handle followed by agentive verbs
        descriptive_counts = {}

        for verb_pattern in AGENTIVE_VERBS:
            # Build combined pattern: "the X <verb>"
            combined_pattern = descriptive_pattern + verb_pattern[2:]  # Remove leading \b from verb
            for match in re.finditer(combined_pattern, text, re.IGNORECASE):
                handle = "the " + match.group(1).lower()
                # Skip common non-character phrases
                if handle in {'the man', 'the woman', 'the door', 'the room', 'the house',
                              'the time', 'the day', 'the way', 'the end', 'the same',
                              'the first', 'the last', 'the other', 'the next'}:
                    continue
                descriptive_counts[handle] = descriptive_counts.get(handle, 0) + 1

        # Flag handles with 10+ agentive occurrences that aren't in character list
        for handle, count in descriptive_counts.items():
            if count >= 10 and handle.lower() not in existing_names:
                issues.append(VerificationIssue(
                    description=(
                        f"Potential unnamed character: '{handle}' appears {count} times with "
                        f"agentive verbs but is not in the character list"
                    ),
                    severity="warning",
                    suggested_fix=f"Consider adding '{handle}' as a character or alias",
                ))

        return issues
