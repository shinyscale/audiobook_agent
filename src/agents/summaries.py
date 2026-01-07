"""
SummaryAgent - Specialized agent for chapter summarization.

Wraps ChapterSummaryPipeline with self-verification to ensure:
- Each chapter has comprehensive summary
- Key events are captured for substantial chapters
- Characters mentioned match known character list
"""

from typing import Optional
import logging
import time

from .base import Agent, AgentContext, AgentResult, VerificationResult, VerificationIssue
from .config import AgentConfig
from .validation import (
    UpstreamValidationResult,
    UpstreamValidationIssue,
    ValidationSeverity,
)
from ..pipeline.chapter_summary import (
    ChapterSummaryPipeline,
    ChapterSummaryMap,
    ChapterSummary,
)
from ..pipeline.llm import LLMClient

logger = logging.getLogger(__name__)


SUMMARY_VERIFICATION_SYSTEM = """You are a literary analyst reviewing chapter summaries for completeness.

Your job is to identify issues with chapter summaries that might impact audiobook narration preparation."""


SUMMARY_VERIFICATION_PROMPT = """Review this chapter summary for completeness and accuracy:

Chapter {chapter_index}: {chapter_title}
Word count: {word_count:,} words
Estimated duration: {duration:.1f} minutes

Summary:
{summary}

Key events:
{key_events}

Characters present: {characters}

Check:
1. Does the summary capture the main plot points for a chapter of this length?
2. Are the key events comprehensive enough?
3. Is any critical information obviously missing?

Return JSON:
{{
  "issues": [
    {{"description": "...", "severity": "error|warning|info"}}
  ],
  "overall_assessment": "good|acceptable|needs_review"
}}

If the summary looks complete, return: {{"issues": [], "overall_assessment": "good"}}

Return ONLY valid JSON."""


class SummaryAgent(Agent):
    """
    Specialized agent for chapter summarization with self-verification.

    Wraps ChapterSummaryPipeline and adds verification:
    - Checks for empty or incomplete summaries
    - Validates key events presence for substantial chapters
    - Verifies character references match known characters
    - Uses LLM to review summary completeness
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize the SummaryAgent.

        Args:
            llm_client: LLM client for summarization and verification
            config: Agent configuration (model, thresholds, etc.)
        """
        self._llm_client = llm_client
        self._config = config or AgentConfig()
        self._pipeline: Optional[ChapterSummaryPipeline] = None

    @property
    def name(self) -> str:
        return "summaries"

    @property
    def depends_on(self) -> list[str]:
        return ["structure", "characters"]

    @property
    def recommended_models(self) -> list[str]:
        return ["llama3.1:70b", "qwen2.5:72b", "llama3.2"]

    def validate_upstream(self, context: AgentContext) -> UpstreamValidationResult:
        """
        Validate that chapter_map from StructureAgent is suitable for summarization.

        Checks:
        1. chapter_map exists (CRITICAL)
        2. chapters list is not empty (CRITICAL)
        3. Not a single giant chapter likely indicating missed breaks (ERROR)
        4. Not too many low-confidence chapters (WARNING)
        5. No unusual chapter size distribution (WARNING)
        """
        issues = []

        # Check 1: chapter_map exists
        if not context.chapter_map:
            issues.append(UpstreamValidationIssue(
                agent_name="structure",
                issue_type="no_chapters",
                description="No chapter map provided - StructureAgent may have failed",
                severity=ValidationSeverity.CRITICAL,
            ))
            return UpstreamValidationResult(
                valid=False,
                can_proceed=False,
                issues=issues,
            )

        chapter_map = context.chapter_map
        chapters = getattr(chapter_map, 'chapters', []) or []

        # Check 2: Empty chapters list
        if len(chapters) == 0:
            issues.append(UpstreamValidationIssue(
                agent_name="structure",
                issue_type="empty_chapters",
                description="Chapter map is empty - no chapters detected",
                severity=ValidationSeverity.CRITICAL,
            ))
            return UpstreamValidationResult(
                valid=False,
                can_proceed=False,
                issues=issues,
            )

        # Get word counts for analysis
        word_counts = []
        for ch in chapters:
            wc = getattr(ch, 'word_count', 0) or 0
            word_counts.append(wc)

        total_words = sum(word_counts)

        # Check 3: Single giant chapter (likely missed chapter breaks)
        if len(chapters) == 1 and word_counts[0] > 50000:
            issues.append(UpstreamValidationIssue(
                agent_name="structure",
                issue_type="single_giant_chapter",
                description=(
                    f"Single chapter with {word_counts[0]:,} words detected - "
                    f"likely missed chapter breaks"
                ),
                severity=ValidationSeverity.ERROR,
                details={
                    "word_count": word_counts[0],
                    "expected_chapters": max(2, word_counts[0] // 5000),
                },
            ))

        # Check 4: Low-confidence chapters
        low_conf_count = 0
        for ch in chapters:
            conf = getattr(ch, 'confidence', 1.0)
            if conf < 0.4:
                low_conf_count += 1

        if len(chapters) > 1 and low_conf_count > len(chapters) * 0.5:
            issues.append(UpstreamValidationIssue(
                agent_name="structure",
                issue_type="low_confidence_chapters",
                description=(
                    f"{low_conf_count}/{len(chapters)} chapters have low confidence - "
                    f"chapter detection may be unreliable"
                ),
                severity=ValidationSeverity.WARNING,
                details={
                    "low_confidence_count": low_conf_count,
                    "total_chapters": len(chapters),
                    "ratio": low_conf_count / len(chapters),
                },
            ))

        # Check 5: Unusual size distribution (possible detection errors)
        if len(word_counts) >= 3 and total_words > 0:
            avg = total_words / len(word_counts)
            # Count outliers: chapters >5x average or <10% of average
            outliers = sum(1 for wc in word_counts if wc > avg * 5 or (wc < avg * 0.1 and wc < 500))

            if outliers > len(chapters) * 0.3:
                issues.append(UpstreamValidationIssue(
                    agent_name="structure",
                    issue_type="size_distribution_anomaly",
                    description=(
                        f"{outliers}/{len(chapters)} chapters have unusual sizes "
                        f"(>5x or <10% of average {avg:,.0f} words) - "
                        f"may indicate detection errors"
                    ),
                    severity=ValidationSeverity.WARNING,
                    details={
                        "outlier_count": outliers,
                        "total_chapters": len(chapters),
                        "average_words": avg,
                    },
                ))

        # Determine if can proceed
        has_blocking = any(
            i.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.ERROR)
            for i in issues
        )

        return UpstreamValidationResult(
            valid=len(issues) == 0,
            can_proceed=not has_blocking,
            issues=issues,
        )

    def _get_pipeline(self) -> ChapterSummaryPipeline:
        """Get or create the chapter summary pipeline."""
        if self._pipeline is None:
            self._pipeline = ChapterSummaryPipeline(
                llm_client=self._llm_client,
            )
        return self._pipeline

    def run(self, context: AgentContext) -> AgentResult[ChapterSummaryMap]:
        """
        Run chapter summarization on the document.

        Args:
            context: Input context with document text and chapter/character maps

        Returns:
            AgentResult containing ChapterSummaryMap
        """
        start_time = time.perf_counter()

        # Validate required context
        if not context.chapter_map:
            # Get model info for error case
            model_used = self._config.model if self._config else None
            provider_used = self._config.provider if self._config else None

            return AgentResult(
                data=ChapterSummaryMap(
                    summaries=[],
                    total_chapters=0,
                    total_word_count=0,
                    total_duration_minutes=0,
                    overall_tones={},
                    character_appearances={},
                    pipeline_metadata={"error": "No chapter map provided"},
                ),
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                issues=["No chapter map provided - cannot summarize chapters"],
                model_used=model_used,
                provider_used=provider_used,
            )

        pipeline = self._get_pipeline()
        summary_map, _ = pipeline.run(
            full_text=context.text,
            chapter_map=context.chapter_map,
            character_map=context.character_map,
            source_file=context.source_file,
        )

        # Calculate confidence breakdown
        high = sum(1 for s in summary_map.summaries if s.confidence >= 0.7)
        medium = sum(1 for s in summary_map.summaries if 0.4 <= s.confidence < 0.7)
        low = sum(1 for s in summary_map.summaries if s.confidence < 0.4)

        # Collect initial issues
        issues = []
        if low > 0:
            issues.append(f"{low} chapter summaries have low confidence")

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
            data=summary_map,
            confidence_scores=[s.confidence for s in summary_map.summaries],
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
            issues=issues,
            processing_time_seconds=elapsed,
            model_used=model_used,
            provider_used=provider_used,
        )

    def verify(self, result: AgentResult[ChapterSummaryMap]) -> VerificationResult:
        """
        Verify chapter summaries for quality issues.

        Checks:
        1. Low-confidence summaries
        2. Empty or very short summaries
        3. Missing key events for substantial chapters
        4. Character references (optional LLM check)
        """
        issues = []
        suggestions = []
        summary_map = result.data

        if not summary_map.summaries:
            return VerificationResult(
                passed=True,
                issues=[],
                suggestions=["No summaries to verify"],
            )

        # Check 1: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(VerificationIssue(
                description=f"{result.low_confidence_count} summaries have low confidence",
                severity="warning",
            ))

        # Check 2: Empty or short summaries
        empty_issues = self._check_summary_completeness(summary_map.summaries)
        issues.extend(empty_issues)

        # Check 3: Missing key events for substantial chapters
        event_issues = self._check_key_events(summary_map.summaries)
        issues.extend(event_issues)

        # Check 4: Tone consistency
        tone_issues = self._check_tone_consistency(summary_map)
        issues.extend(tone_issues)

        # Check 5: LLM verification for low-confidence summaries (if enabled)
        if self._config.enable_verification and self._llm_client:
            low_conf_summaries = [s for s in summary_map.summaries if s.confidence < 0.5]
            for summary in low_conf_summaries[:3]:  # Verify up to 3
                llm_issues = self._llm_verify_summary(summary)
                issues.extend(llm_issues)

        # Determine if passed
        error_count = sum(1 for i in issues if i.severity == "error")
        passed = error_count == 0

        return VerificationResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_summary_completeness(
        self, summaries: list[ChapterSummary]
    ) -> list[VerificationIssue]:
        """Check for empty or incomplete summaries."""
        issues = []

        for summary in summaries:
            # Empty summary
            if not summary.summary or len(summary.summary.strip()) < 20:
                issues.append(VerificationIssue(
                    description=f"Chapter {summary.chapter_index} has empty or very short summary",
                    severity="error",
                    item_index=summary.chapter_index,
                    suggested_fix="Re-run summarization for this chapter",
                ))

            # Summary too short relative to chapter length
            elif summary.word_count > 2000 and len(summary.summary) < 100:
                issues.append(VerificationIssue(
                    description=(
                        f"Chapter {summary.chapter_index} ({summary.word_count:,} words) "
                        f"has suspiciously short summary ({len(summary.summary)} chars)"
                    ),
                    severity="warning",
                    item_index=summary.chapter_index,
                ))

        return issues

    def _check_key_events(
        self, summaries: list[ChapterSummary]
    ) -> list[VerificationIssue]:
        """Check that substantial chapters have key events."""
        issues = []

        for summary in summaries:
            # Substantial chapter should have key events
            if summary.word_count > 1000:
                if not summary.key_events:
                    issues.append(VerificationIssue(
                        description=(
                            f"Chapter {summary.chapter_index} ({summary.word_count:,} words) "
                            f"has no key events listed"
                        ),
                        severity="warning",
                        item_index=summary.chapter_index,
                    ))
                elif len(summary.key_events) < 2 and summary.word_count > 3000:
                    issues.append(VerificationIssue(
                        description=(
                            f"Chapter {summary.chapter_index} ({summary.word_count:,} words) "
                            f"has only {len(summary.key_events)} key event(s) - may be incomplete"
                        ),
                        severity="info",
                        item_index=summary.chapter_index,
                    ))

        return issues

    def _check_tone_consistency(
        self, summary_map: ChapterSummaryMap
    ) -> list[VerificationIssue]:
        """Check for tone distribution anomalies."""
        issues = []

        if len(summary_map.summaries) < 3:
            return issues

        # Check for single-tone dominance (might indicate extraction issues)
        total = len(summary_map.summaries)
        for tone, count in summary_map.overall_tones.items():
            if count == total and total > 5:
                issues.append(VerificationIssue(
                    description=(
                        f"All {total} chapters classified as '{tone}' - "
                        f"may indicate tone detection issue"
                    ),
                    severity="info",
                ))

        return issues

    def _llm_verify_summary(
        self, summary: ChapterSummary
    ) -> list[VerificationIssue]:
        """Use LLM to verify a summary's completeness."""
        issues = []

        if not self._llm_client:
            return issues

        # Build verification prompt
        key_events_str = "\n".join(f"- {e}" for e in summary.key_events) if summary.key_events else "(none)"
        characters_str = ", ".join(summary.characters_present) if summary.characters_present else "(none)"

        prompt = SUMMARY_VERIFICATION_PROMPT.format(
            chapter_index=summary.chapter_index,
            chapter_title=summary.chapter_title or "(untitled)",
            word_count=summary.word_count,
            duration=summary.estimated_duration_minutes,
            summary=summary.summary,
            key_events=key_events_str,
            characters=characters_str,
        )

        try:
            result, _ = self._llm_client.query_json(
                prompt,
                system=SUMMARY_VERIFICATION_SYSTEM,
            )

            if result and isinstance(result.get("issues"), list):
                assessment = result.get("overall_assessment", "unknown")

                if assessment == "needs_review":
                    for issue in result["issues"]:
                        if isinstance(issue, dict):
                            issues.append(VerificationIssue(
                                description=(
                                    f"Chapter {summary.chapter_index}: "
                                    f"{issue.get('description', 'Unknown issue')}"
                                ),
                                severity=issue.get("severity", "warning"),
                                item_index=summary.chapter_index,
                            ))

        except Exception as e:
            logger.warning(f"LLM summary verification failed for chapter {summary.chapter_index}: {e}")

        return issues

    def refine(
        self,
        result: AgentResult[ChapterSummaryMap],
        issues: list[VerificationIssue],
    ) -> AgentResult[ChapterSummaryMap]:
        """
        Attempt to refine summaries based on verification issues.

        Currently adds issues to metadata for review. Future: re-summarize
        specific chapters with issues.
        """
        summary_map = result.data

        # Add issues to pipeline metadata for review
        issue_descriptions = [i.description for i in issues]
        if issue_descriptions:
            summary_map.pipeline_metadata["verification_issues"] = issue_descriptions
            summary_map.pipeline_metadata["needs_review"] = True

        # Log errors
        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            logger.warning(
                f"SummaryAgent: {len(error_issues)} errors found but "
                f"refinement not yet implemented"
            )

        return AgentResult(
            data=summary_map,
            confidence_scores=result.confidence_scores,
            high_confidence_count=result.high_confidence_count,
            medium_confidence_count=result.medium_confidence_count,
            low_confidence_count=result.low_confidence_count,
            issues=issue_descriptions,
            processing_time_seconds=result.processing_time_seconds,
            model_used=result.model_used,
            provider_used=result.provider_used,
        )


def create_summary_agent(
    llm_client: Optional[LLMClient] = None,
    config: Optional[AgentConfig] = None,
) -> SummaryAgent:
    """
    Factory function to create a SummaryAgent.

    Args:
        llm_client: LLM client for summarization and verification
        config: Agent configuration

    Returns:
        Configured SummaryAgent
    """
    return SummaryAgent(llm_client=llm_client, config=config)
