"""
StructureAgent: Specialized agent for chapter/structure detection.

Wraps the ChapterDetectionPipeline with self-verification to ensure
high-quality chapter detection regardless of book format.
"""

import json
import logging
import re
import time
from typing import Optional

from ..pipeline.chapter_detection import ChapterDetectionPipeline, ChapterMap
from ..pipeline.llm import LLMClient
from .base import (
    Agent,
    AgentContext,
    AgentResult,
    VerificationIssue,
    VerificationLevel,
    VerificationResult,
)
from .config import AgentConfig, CompetitiveConfig, PipelineTuningConfig

logger = logging.getLogger(__name__)


# Verification prompts
SEQUENCE_CHECK_SYSTEM = """You are a document structure analyst checking chapter sequences for logical consistency.

Your job is to identify potential issues with a proposed chapter structure."""

SEQUENCE_CHECK_PROMPT = """Review this chapter structure for a book and identify any issues:

{chapter_summary}

Check for:
1. Unusual chapter sizes (one chapter much larger/smaller than others)
2. Missing chapters (gaps in numbering that seem unintentional)
3. Chapters that might be incorrectly split or merged
4. Any structural anomalies that seem wrong for a book

Return JSON:
{{
  "issues": [
    {{"description": "...", "severity": "error|warning|info", "chapter_index": null or number}}
  ],
  "overall_assessment": "good|acceptable|needs_review",
  "suggestions": ["..."]
}}

If the structure looks correct, return {{"issues": [], "overall_assessment": "good", "suggestions": []}}

Return ONLY valid JSON."""


class StructureAgent(Agent):
    """
    Agent for detecting and validating book structure (chapters).

    Wraps ChapterDetectionPipeline with additional self-verification
    to catch issues the pipeline might miss.

    Verification checks:
    - Chapter sequence logic (no out-of-order or missing chapters)
    - Chapter size consistency (flag unusually small/large chapters)
    - TOC agreement (if TOC exists, chapters should match)
    - Low-confidence boundary detection
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        tuning: Optional[PipelineTuningConfig] = None,
        competitive_config: Optional[CompetitiveConfig] = None,
    ):
        """
        Initialize the StructureAgent.

        Args:
            llm_client: LLM client for the pipeline and verification
            config: Agent configuration (model, thresholds, etc.)
            competitive_config: Optional config for multi-model boundary voting
        """
        self._llm_client = llm_client
        self._config = config or AgentConfig()
        self._tuning = tuning
        self._competitive_config = competitive_config
        self._pipeline: Optional[ChapterDetectionPipeline] = None

    @property
    def name(self) -> str:
        return "structure"

    @property
    def depends_on(self) -> list[str]:
        # Structure detection is the first step - no dependencies
        return []

    @property
    def recommended_models(self) -> list[str]:
        return ["qwen2.5:7b", "llama3.2", "mistral"]

    def _get_pipeline(self) -> ChapterDetectionPipeline:
        """Get or create the chapter detection pipeline."""
        if self._pipeline is None:
            t = self._tuning or PipelineTuningConfig()
            self._pipeline = ChapterDetectionPipeline(
                llm_client=self._llm_client,
                llm_marker_chunk_size=t.chapter_marker_chunk_chars,
                llm_marker_chunk_overlap=t.chapter_marker_chunk_overlap_chars,
                llm_narrative_chunk_size=t.chapter_narrative_chunk_chars,
                llm_narrative_chunk_overlap=t.chapter_narrative_chunk_overlap_chars,
                competitive_config=self._competitive_config,
            )
        return self._pipeline

    def run(self, context: AgentContext) -> AgentResult[ChapterMap]:
        """
        Run chapter detection on the document.

        Args:
            context: Input context with document text

        Returns:
            AgentResult containing ChapterMap
        """
        start_time = time.perf_counter()

        pipeline = self._get_pipeline()
        chapter_map = pipeline.run(
            text=context.text,
            source_file=context.source_file,
        )

        # region agent log (chapter-v-bug) - hypothesis A/C/D
        try:
            _titles = [c.title for c in chapter_map.chapters]
            _has_v = any((t or "").strip().upper() in ("V", "CHAPTER V") for t in _titles)
            _has_i = any((t or "").strip().upper() in ("I", "CHAPTER I") for t in _titles)
            _centered_v_lines = len(re.findall(r"(?m)^[ \t]{10,}V[ \t]*$", context.text))
            _standalone_v_lines = len(re.findall(r"(?m)^[ \t]*V[ \t]*$", context.text))
            _payload = (
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "chapter-v-bug-pre",
                        "hypothesisId": "D",
                        "location": "src/agents/structure.py:StructureAgent.run:post_pipeline",
                        "message": "StructureAgent produced chapter titles (presence of I/V)",
                        "data": {
                            "chapter_count": len(chapter_map.chapters),
                            "has_V": _has_v,
                            "has_I": _has_i,
                            "titles": _titles[:20],
                            "text_centered_V_lines": _centered_v_lines,
                            "text_standalone_V_lines": _standalone_v_lines,
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            for _path in (
                "/home/zacharymandrews/Tools/audiobook_agent/.cursor/debug.log",
                "/home/zacharymandrews/Tools/audiobook_agent/output/debug_mirror.ndjson",
            ):
                try:
                    with open(_path, "a", encoding="utf-8") as _f:
                        _f.write(_payload)
                except Exception:
                    pass
        except Exception:
            pass
        # endregion

        # Calculate confidence breakdown
        high = sum(1 for c in chapter_map.chapters if c.confidence >= 0.7)
        medium = sum(1 for c in chapter_map.chapters if 0.4 <= c.confidence < 0.7)
        low = sum(1 for c in chapter_map.chapters if c.confidence < 0.4)

        # Collect issues
        issues = []
        if chapter_map.low_confidence_boundaries:
            issues.append(
                f"{len(chapter_map.low_confidence_boundaries)} low-confidence boundaries flagged"
            )
        if chapter_map.toc_agreement_score >= 0 and chapter_map.toc_agreement_score < 0.8:
            issues.append(f"TOC agreement is only {chapter_map.toc_agreement_score:.0%}")

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
            data=chapter_map,
            confidence_scores=[c.confidence for c in chapter_map.chapters],
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
        result: AgentResult[ChapterMap],
        level: VerificationLevel = VerificationLevel.SELF_CHECK,
        context: Optional[AgentContext] = None,
    ) -> VerificationResult:
        """
        Verify the chapter structure for quality issues.

        Checks:
        1. Low-confidence chapters
        2. Chapter size consistency
        3. TOC agreement
        4. Sequence logic (via LLM if available)
        """
        issues = []
        suggestions = []
        chapter_map = result.data

        # Check 1: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(
                VerificationIssue(
                    description=f"{result.low_confidence_count} chapters have low confidence",
                    severity="warning",
                )
            )

        # Check 2: Chapter size consistency
        size_issues = self._check_chapter_sizes(chapter_map)
        issues.extend(size_issues)

        # Check 3: TOC agreement
        if chapter_map.toc_agreement_score >= 0:
            if chapter_map.toc_agreement_score < 0.5:
                issues.append(
                    VerificationIssue(
                        description=f"Poor TOC agreement ({chapter_map.toc_agreement_score:.0%})",
                        severity="error",
                        suggested_fix="Review chapter boundaries against table of contents",
                    )
                )
            elif chapter_map.toc_agreement_score < 0.8:
                issues.append(
                    VerificationIssue(
                        description=f"Moderate TOC agreement ({chapter_map.toc_agreement_score:.0%})",
                        severity="warning",
                    )
                )

        # Check 4: Low-confidence boundaries
        if chapter_map.low_confidence_boundaries:
            for boundary in chapter_map.low_confidence_boundaries[:3]:  # Report first 3
                issues.append(
                    VerificationIssue(
                        description=f"Low-confidence boundary at position {boundary.position}: {boundary.title or '(untitled)'}",
                        severity="info",
                    )
                )

        # Check 5: LLM sequence verification (if available)
        if self._llm_client and self._config.enable_verification:
            llm_issues = self._llm_verify_sequence(chapter_map)
            issues.extend(llm_issues)

        # Determine if passed
        error_count = sum(1 for i in issues if i.severity == "error")
        passed = error_count == 0

        return VerificationResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_chapter_sizes(self, chapter_map: ChapterMap) -> list[VerificationIssue]:
        """Check for unusual chapter sizes."""
        issues = []
        chapters = chapter_map.chapters

        if len(chapters) < 2:
            return issues

        # Calculate statistics
        word_counts = [c.word_count for c in chapters]
        avg_words = sum(word_counts) / len(word_counts)
        min(word_counts)
        max(word_counts)

        # Flag very small chapters (< 20% of average)
        for i, chapter in enumerate(chapters):
            if chapter.word_count < avg_words * 0.2 and chapter.word_count < 500:
                issues.append(
                    VerificationIssue(
                        description=f"Chapter {chapter.index} is unusually small ({chapter.word_count} words)",
                        severity="warning",
                        item_index=i,
                        suggested_fix="May be incorrectly split or a section header",
                    )
                )

        # Flag very large chapters (> 3x average)
        for i, chapter in enumerate(chapters):
            if chapter.word_count > avg_words * 3:
                issues.append(
                    VerificationIssue(
                        description=f"Chapter {chapter.index} is unusually large ({chapter.word_count} words, avg is {int(avg_words)})",
                        severity="info",
                        item_index=i,
                        suggested_fix="May contain missed chapter boundaries",
                    )
                )

        return issues

    def _llm_verify_sequence(self, chapter_map: ChapterMap) -> list[VerificationIssue]:
        """Use LLM to verify chapter sequence logic."""
        issues = []

        if not self._llm_client or len(chapter_map.chapters) < 3:
            return issues

        # Build chapter summary for LLM
        summary_lines = []
        for ch in chapter_map.chapters:
            title = ch.title or "(untitled)"
            conf = "high" if ch.confidence >= 0.7 else "medium" if ch.confidence >= 0.4 else "low"
            summary_lines.append(
                f"Chapter {ch.index}: {title} ({ch.word_count:,} words, {conf} confidence)"
            )

        chapter_summary = "\n".join(summary_lines)
        prompt = SEQUENCE_CHECK_PROMPT.format(chapter_summary=chapter_summary)

        try:
            result, response = self._llm_client.query_json(
                prompt,
                system=SEQUENCE_CHECK_SYSTEM,
            )

            if result and isinstance(result, dict):
                llm_issues = result.get("issues", [])
                for issue in llm_issues:
                    if isinstance(issue, dict):
                        issues.append(
                            VerificationIssue(
                                description=issue.get("description", "Unknown issue"),
                                severity=issue.get("severity", "warning"),
                                item_index=issue.get("chapter_index"),
                            )
                        )

        except Exception as e:
            logger.warning(f"LLM sequence verification failed: {e}")

        return issues

    def refine(
        self,
        result: AgentResult[ChapterMap],
        issues: list[VerificationIssue],
    ) -> AgentResult[ChapterMap]:
        """
        Attempt to refine the chapter structure based on verification issues.

        Currently returns the original result - refinement logic would be
        added here to address specific issues (e.g., re-running detection
        with different parameters for problem areas).
        """
        # For now, log the issues and return unchanged
        # Future: implement specific refinement strategies
        error_issues = [i for i in issues if i.severity == "error"]

        if error_issues:
            logger.warning(
                f"StructureAgent: {len(error_issues)} errors found but refinement not yet implemented"
            )

        return result


def create_structure_agent(
    llm_client: Optional[LLMClient] = None,
    config: Optional[AgentConfig] = None,
    competitive_config: Optional[CompetitiveConfig] = None,
) -> StructureAgent:
    """
    Factory function to create a StructureAgent.

    Args:
        llm_client: LLM client for detection and verification
        config: Agent configuration
        competitive_config: Optional config for multi-model boundary voting

    Returns:
        Configured StructureAgent
    """
    return StructureAgent(
        llm_client=llm_client,
        config=config,
        competitive_config=competitive_config,
    )
