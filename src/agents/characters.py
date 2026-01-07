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

from .base import Agent, AgentContext, AgentResult, VerificationResult, VerificationIssue
from .config import AgentConfig
from ..pipeline.character_extraction.pipeline import CharacterExtractionPipeline
from ..pipeline.character_extraction.models import CharacterMap, Character
from ..pipeline.chapter_detection.models import ChapterMap as ChapterDetectionMap
from ..pipeline.llm import LLMClient

logger = logging.getLogger(__name__)


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
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()

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

    def verify(self, result: AgentResult[CharacterMap]) -> VerificationResult:
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

        # Check 2: Look for potential duplicates using heuristics
        duplicate_issues = self._check_duplicates_heuristic(character_map.characters)
        issues.extend(duplicate_issues)

        # Check 3: Verify mention distribution
        distribution_issues = self._check_mention_distribution(character_map)
        issues.extend(distribution_issues)

        # Check 4: Verify alias consistency
        alias_issues = self._check_alias_consistency(character_map.characters)
        issues.extend(alias_issues)

        # Check 5: LLM duplicate check for high-value verification
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

        For now, we flag issues but don't automatically fix them.
        Future: implement automatic duplicate merging.
        """
        character_map = result.data

        # Add issues to pipeline metadata for review
        issue_descriptions = [i.description for i in issues]
        if issue_descriptions:
            character_map.pipeline_metadata["verification_issues"] = issue_descriptions
            character_map.pipeline_metadata["needs_review"] = True

        # Log errors
        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            logger.warning(
                f"CharacterAgent: {len(error_issues)} errors found but refinement not yet implemented"
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
        return CharacterExtractionPipeline(llm_client=self.llm)

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
            logger.warning(f"LLM duplicate check failed: {e}")

        return issues
