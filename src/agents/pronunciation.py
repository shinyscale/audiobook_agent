"""
PronunciationAgent - Specialized agent for pronunciation guide generation.

Wraps PronunciationGuidePipeline with self-verification to ensure:
- Homographs have context-specific pronunciations
- Character names have pronunciation entries
- IPA/phonetic spellings are complete for high-priority items
"""

import logging
import time
from typing import Optional

from ..pipeline.llm import LLMClient
from ..pipeline.pronunciation_guide import (
    PronunciationEntry,
    PronunciationFlag,
    PronunciationGuidePipeline,
    PronunciationMap,
)
from .base import (
    Agent,
    AgentContext,
    AgentResult,
    VerificationIssue,
    VerificationLevel,
    VerificationResult,
)
from .config import AgentConfig

logger = logging.getLogger(__name__)


HOMOGRAPH_VERIFICATION_SYSTEM = """You are a pronunciation specialist reviewing homograph entries for audiobook narration.

Your job is to verify that context-dependent words have proper disambiguation for narrators."""


HOMOGRAPH_VERIFICATION_PROMPT = """Review these homograph entries for correct contextualization:

{homograph_entries}

For each homograph, check:
1. Are the different pronunciation options correctly listed?
2. Is there enough context/notes to help a narrator choose the right pronunciation?
3. Are any common homographs missing disambiguation?

Return JSON:
{{
  "issues": [
    {{"word": "...", "description": "...", "severity": "error|warning|info"}}
  ],
  "suggestions": ["..."]
}}

If all homographs are correctly handled, return: {{"issues": [], "suggestions": []}}

Return ONLY valid JSON."""


class PronunciationAgent(Agent):
    """
    Specialized agent for pronunciation guide generation with self-verification.

    Wraps PronunciationGuidePipeline and adds verification:
    - Checks homographs have context-specific pronunciations
    - Validates IPA/phonetic spellings for high-priority items
    - Ensures character names have pronunciation entries
    - Uses LLM to verify homograph disambiguation
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize the PronunciationAgent.

        Args:
            llm_client: LLM client for enrichment and verification
            config: Agent configuration (model, thresholds, etc.)
        """
        self._llm_client = llm_client
        self._config = config or AgentConfig()
        self._pipeline: Optional[PronunciationGuidePipeline] = None

    @property
    def name(self) -> str:
        return "pronunciation"

    @property
    def depends_on(self) -> list[str]:
        # Only needs chapter boundaries; character_map is optional
        return ["structure"]

    @property
    def recommended_models(self) -> list[str]:
        return ["qwen2.5:32b", "qwen2.5:14b", "llama3.2"]

    def _get_pipeline(
        self,
        glossary_entries: Optional[list] = None,
        body_range: Optional[tuple] = None,
    ) -> PronunciationGuidePipeline:
        """Get or create the pronunciation pipeline.

        Rebuilt when glossary/body_range are supplied so the Glossary and Entity
        proposers receive their data (the default proposer list is fixed at
        construction time).
        """
        if self._pipeline is None or glossary_entries is not None or body_range is not None:
            self._pipeline = PronunciationGuidePipeline(
                llm_client=self._llm_client,
                glossary_entries=glossary_entries,
                body_range=body_range,
            )
        return self._pipeline

    def run(self, context: AgentContext) -> AgentResult[PronunciationMap]:
        """
        Run pronunciation guide generation on the document.

        Args:
            context: Input context with document text and chapter map

        Returns:
            AgentResult containing PronunciationMap
        """
        start_time = time.perf_counter()

        # Validate required context
        if not context.chapter_map:
            # Get model info for error case
            model_used = self._config.model if self._config else None
            provider_used = self._config.provider if self._config else None

            return AgentResult(
                data=PronunciationMap(
                    entries=[],
                    low_confidence_entries=[],
                    total_flagged_words=0,
                    total_occurrences=0,
                    by_category={},
                    character_names=[],
                    pipeline_metadata={"error": "No chapter map provided"},
                ),
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                issues=["No chapter map provided - cannot generate pronunciation guide"],
                model_used=model_used,
                provider_used=provider_used,
            )

        glossary_entries = context.metadata.get("glossary_entries")
        body_range = context.metadata.get("body_range")
        pipeline = self._get_pipeline(glossary_entries=glossary_entries, body_range=body_range)
        pronunciation_map, _ = pipeline.run(
            full_text=context.text,
            chapter_map=context.chapter_map,
            character_map=context.character_map,
            source_file=context.source_file,
        )

        # Calculate confidence breakdown
        all_entries = pronunciation_map.entries + pronunciation_map.low_confidence_entries
        high = sum(1 for e in all_entries if e.confidence >= 0.7)
        medium = sum(1 for e in all_entries if 0.4 <= e.confidence < 0.7)
        low = sum(1 for e in all_entries if e.confidence < 0.4)

        # Collect initial issues
        issues = []
        if pronunciation_map.low_confidence_entries:
            issues.append(
                f"{len(pronunciation_map.low_confidence_entries)} entries have low confidence"
            )

        elapsed = time.perf_counter() - start_time

        # Get model info from config or client
        model_used = None
        provider_used = None
        if self._config and self._config.model:
            model_used = self._config.model
            provider_used = self._config.provider
        elif self._llm_client and self._llm_client.config:
            model_used = self._llm_client.config.model
            provider_used = self._llm_client.config.provider

        return AgentResult(
            data=pronunciation_map,
            confidence_scores=[e.confidence for e in all_entries],
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
        result: AgentResult[PronunciationMap],
        level: VerificationLevel = VerificationLevel.SELF_CHECK,
        context: Optional[AgentContext] = None,
    ) -> VerificationResult:
        """
        Verify pronunciation guide for quality issues.

        Checks:
        1. Low-confidence entries
        2. Homograph disambiguation
        3. Missing pronunciation data for high-priority items
        4. Character name coverage
        """
        issues = []
        suggestions = []
        pronunciation_map = result.data

        if not pronunciation_map.entries and not pronunciation_map.low_confidence_entries:
            return VerificationResult(
                passed=True,
                issues=[],
                suggestions=["No pronunciation entries to verify"],
            )

        # Check 1: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(
                VerificationIssue(
                    description=f"{result.low_confidence_count} entries have low confidence",
                    severity="warning",
                )
            )

        # Check 2: Homograph disambiguation
        homograph_issues = self._check_homographs(pronunciation_map.entries)
        issues.extend(homograph_issues)

        # Check 3: Missing pronunciation data for high-priority items
        missing_issues = self._check_missing_pronunciations(pronunciation_map)
        issues.extend(missing_issues)

        # Check 4: Character name coverage
        character_issues = self._check_character_coverage(pronunciation_map)
        issues.extend(character_issues)

        # Check 5: LLM homograph verification (if enabled)
        if self._config.enable_verification and self._llm_client:
            homographs = [
                e for e in pronunciation_map.entries if e.flag_reason == PronunciationFlag.HOMOGRAPH
            ]
            if homographs:
                llm_issues = self._llm_verify_homographs(homographs)
                issues.extend(llm_issues)

        # Determine if passed
        error_count = sum(1 for i in issues if i.severity == "error")
        passed = error_count == 0

        return VerificationResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_homographs(self, entries: list[PronunciationEntry]) -> list[VerificationIssue]:
        """Check that homographs have proper disambiguation."""
        issues = []

        for entry in entries:
            if entry.flag_reason != PronunciationFlag.HOMOGRAPH:
                continue

            # Homographs should have options listed
            if not entry.homograph_options:
                issues.append(
                    VerificationIssue(
                        description=(
                            f"Homograph '{entry.word}' has no pronunciation options listed"
                        ),
                        severity="warning",
                        suggested_fix="Add homograph_options with different pronunciations",
                    )
                )
            elif len(entry.homograph_options) < 2:
                issues.append(
                    VerificationIssue(
                        description=(
                            f"Homograph '{entry.word}' has only one option - "
                            f"should have at least 2"
                        ),
                        severity="info",
                    )
                )

            # Homographs need notes for context
            if not entry.notes:
                issues.append(
                    VerificationIssue(
                        description=(f"Homograph '{entry.word}' has no notes for disambiguation"),
                        severity="warning",
                        suggested_fix="Add notes explaining when to use each pronunciation",
                    )
                )

        return issues

    def _check_missing_pronunciations(
        self, pronunciation_map: PronunciationMap
    ) -> list[VerificationIssue]:
        """Check for missing pronunciation data on high-priority items."""
        issues = []

        # High-priority: character names and high-occurrence words
        high_priority = [
            e for e in pronunciation_map.entries if e.is_character_name or e.occurrence_count > 10
        ]

        for entry in high_priority:
            missing = []
            if not entry.ipa and not entry.phonetic_spelling:
                missing.append("no pronunciation guidance")
            elif not entry.ipa:
                missing.append("no IPA")

            if missing and entry.is_character_name:
                issues.append(
                    VerificationIssue(
                        description=(f"Character name '{entry.word}' has {', '.join(missing)}"),
                        severity="warning",
                        suggested_fix="Add IPA or phonetic spelling",
                    )
                )
            elif missing and entry.occurrence_count > 20:
                issues.append(
                    VerificationIssue(
                        description=(
                            f"Frequent word '{entry.word}' ({entry.occurrence_count} occurrences) "
                            f"has {', '.join(missing)}"
                        ),
                        severity="info",
                    )
                )

        return issues

    def _check_character_coverage(
        self, pronunciation_map: PronunciationMap
    ) -> list[VerificationIssue]:
        """Check that character names from extraction have pronunciation entries."""
        issues = []

        if not pronunciation_map.character_names:
            return issues

        # Get words that are marked as character names
        character_entries = {
            e.word.lower() for e in pronunciation_map.entries if e.is_character_name
        }

        # Check for missing characters
        missing_chars = []
        for char_name in pronunciation_map.character_names:
            # Check if any part of the name is covered
            name_parts = char_name.lower().split()
            if not any(part in character_entries for part in name_parts):
                # Full name not in entries - might be okay if common name
                if len(name_parts) > 1:  # Multi-word name
                    missing_chars.append(char_name)

        if missing_chars and len(missing_chars) <= 5:
            for char in missing_chars:
                issues.append(
                    VerificationIssue(
                        description=f"Character '{char}' has no pronunciation entry",
                        severity="info",
                    )
                )
        elif missing_chars:
            issues.append(
                VerificationIssue(
                    description=f"{len(missing_chars)} characters have no pronunciation entries",
                    severity="info",
                )
            )

        return issues

    def _llm_verify_homographs(
        self, homographs: list[PronunciationEntry]
    ) -> list[VerificationIssue]:
        """Use LLM to verify homograph disambiguation."""
        issues = []

        if not self._llm_client or not homographs:
            return issues

        # Build homograph list for LLM
        homograph_lines = []
        for entry in homographs[:15]:  # Limit for prompt size
            options_str = (
                ", ".join(entry.homograph_options) if entry.homograph_options else "(none)"
            )
            notes_str = entry.notes or "(no notes)"
            homograph_lines.append(f"- {entry.word}: options=[{options_str}], notes={notes_str}")

        homograph_entries = "\n".join(homograph_lines)
        prompt = HOMOGRAPH_VERIFICATION_PROMPT.format(homograph_entries=homograph_entries)

        try:
            result, _ = self._llm_client.query_json(
                prompt,
                system=HOMOGRAPH_VERIFICATION_SYSTEM,
            )

            if result and isinstance(result.get("issues"), list):
                for issue in result["issues"]:
                    if isinstance(issue, dict):
                        issues.append(
                            VerificationIssue(
                                description=(
                                    f"Homograph '{issue.get('word', '?')}': "
                                    f"{issue.get('description', 'Unknown issue')}"
                                ),
                                severity=issue.get("severity", "warning"),
                            )
                        )

        except Exception as e:
            logger.warning(f"LLM homograph verification failed: {e}")

        return issues

    def refine(
        self,
        result: AgentResult[PronunciationMap],
        issues: list[VerificationIssue],
    ) -> AgentResult[PronunciationMap]:
        """
        Attempt to refine pronunciation guide based on verification issues.

        Currently adds issues to metadata for review. Future: re-enrich
        specific entries with issues.
        """
        pronunciation_map = result.data

        # Add issues to pipeline metadata for review
        issue_descriptions = [i.description for i in issues]
        if issue_descriptions:
            pronunciation_map.pipeline_metadata["verification_issues"] = issue_descriptions
            pronunciation_map.pipeline_metadata["needs_review"] = True

        # Log errors
        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            logger.warning(
                f"PronunciationAgent: {len(error_issues)} errors found but "
                f"refinement not yet implemented"
            )

        return AgentResult(
            data=pronunciation_map,
            confidence_scores=result.confidence_scores,
            high_confidence_count=result.high_confidence_count,
            medium_confidence_count=result.medium_confidence_count,
            low_confidence_count=result.low_confidence_count,
            issues=issue_descriptions,
            processing_time_seconds=result.processing_time_seconds,
            model_used=result.model_used,
            provider_used=result.provider_used,
        )


def create_pronunciation_agent(
    llm_client: Optional[LLMClient] = None,
    config: Optional[AgentConfig] = None,
) -> PronunciationAgent:
    """
    Factory function to create a PronunciationAgent.

    Args:
        llm_client: LLM client for enrichment and verification
        config: Agent configuration

    Returns:
        Configured PronunciationAgent
    """
    return PronunciationAgent(llm_client=llm_client, config=config)
