"""
Quality report generation for post-run analysis.

Generates structured markdown reports summarizing analysis quality,
confidence distributions, and recommendations for review.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..models import AnalysisResult
    from ..pipeline.metrics import ProfilingReport


@dataclass
class AgentQualityMetrics:
    """Quality metrics for a single agent's output."""

    agent_name: str
    total_items: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    verification_issues: list[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0
    model_used: Optional[str] = None
    provider_used: Optional[str] = None

    @property
    def quality_score(self) -> float:
        """Calculate quality score (0-1) based on confidence distribution."""
        if self.total_items == 0:
            return 1.0
        weighted = (
            self.high_confidence_count * 1.0
            + self.medium_confidence_count * 0.6
            + self.low_confidence_count * 0.2
        )
        return weighted / self.total_items

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "total_items": self.total_items,
            "high_confidence_count": self.high_confidence_count,
            "medium_confidence_count": self.medium_confidence_count,
            "low_confidence_count": self.low_confidence_count,
            "quality_score": round(self.quality_score, 3),
            "verification_issues": self.verification_issues,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "llm_calls": self.llm_calls,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "provider_used": self.provider_used,
        }


@dataclass
class QualityReport:
    """Complete quality report for an analysis run."""

    # Metadata
    source_file: str
    analysis_timestamp: str
    total_duration_seconds: float
    llm_model: str
    llm_provider: str

    # Per-agent metrics
    agent_metrics: list[AgentQualityMetrics]

    # Overall quality
    overall_quality_score: float
    passed_quality_gates: bool

    # Issues and recommendations
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Low-confidence items for review
    low_confidence_chapters: list[dict] = field(default_factory=list)
    low_confidence_characters: list[dict] = field(default_factory=list)
    low_confidence_pronunciations: list[dict] = field(default_factory=list)

    # Profiling data
    profiling_summary: dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Generate markdown quality report."""
        lines = []

        # Header
        source_name = Path(self.source_file).stem
        lines.append(f"# Quality Report: {source_name}")
        lines.append("")
        lines.append(f"**Analyzed:** {self.analysis_timestamp}")
        lines.append(f"**Duration:** {self._format_duration(self.total_duration_seconds)}")
        lines.append(f"**Model:** {self.llm_model} ({self.llm_provider})")
        lines.append("")

        # Overall score
        score_label = self._score_label(self.overall_quality_score)
        lines.append(f"## Overall Quality: {score_label} ({self.overall_quality_score:.0%})")
        lines.append("")

        if not self.passed_quality_gates:
            lines.append("> **WARNING:** Analysis did not pass quality gates. Review issues below.")
            lines.append("")

        # Per-agent breakdown
        lines.append("## Agent Performance")
        lines.append("")
        lines.append(
            "| Agent | Model | Items | Quality | H/M/L | LLM Calls | Tokens | Time | Issues |"
        )
        lines.append(
            "|-------|-------|-------|---------|-------|-----------|--------|------|--------|"
        )

        for m in self.agent_metrics:
            conf_str = (
                f"{m.high_confidence_count}H/{m.medium_confidence_count}M/{m.low_confidence_count}L"
            )
            issue_count = len(m.verification_issues)
            time_str = f"{m.processing_time_seconds:.1f}s"
            model_str = m.model_used or "-"
            # Truncate long model names
            if len(model_str) > 20:
                model_str = model_str[:17] + "..."
            tokens_str = f"{m.tokens_used:,}" if m.tokens_used else "-"
            llm_calls_str = str(m.llm_calls) if m.llm_calls else "-"
            lines.append(
                f"| {m.agent_name} | {model_str} | {m.total_items} | {m.quality_score:.0%} | "
                f"{conf_str} | {llm_calls_str} | {tokens_str} | {time_str} | {issue_count} |"
            )
        lines.append("")

        # Critical issues
        if self.critical_issues:
            lines.append("## Critical Issues")
            lines.append("")
            for issue in self.critical_issues:
                lines.append(f"- **CRITICAL:** {issue}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Low confidence chapters
        if self.low_confidence_chapters:
            lines.append("## Low-Confidence Chapters (Review Recommended)")
            lines.append("")
            for ch in self.low_confidence_chapters:
                title = ch.get("title") or "(untitled)"
                conf = ch.get("confidence", 0)
                idx = ch.get("index", "?")
                lines.append(f"- **Chapter {idx}:** {title} ({conf:.0%} confidence)")
            lines.append("")

        # Low confidence characters
        if self.low_confidence_characters:
            lines.append("## Low-Confidence Characters (Review Recommended)")
            lines.append("")
            for char in self.low_confidence_characters[:10]:
                name = char.get("name", "Unknown")
                mentions = char.get("mentions", 0)
                conf = char.get("confidence", 0)
                lines.append(f"- **{name}:** {mentions} mentions ({conf:.0%} confidence)")
            if len(self.low_confidence_characters) > 10:
                remaining = len(self.low_confidence_characters) - 10
                lines.append(f"- ...and {remaining} more")
            lines.append("")

        # Low confidence pronunciations
        if self.low_confidence_pronunciations:
            lines.append("## Low-Confidence Pronunciations (Review Recommended)")
            lines.append("")
            for pron in self.low_confidence_pronunciations[:10]:
                word = pron.get("word", "Unknown")
                reason = pron.get("reason", "unknown")
                conf = pron.get("confidence", 0)
                lines.append(f"- **{word}:** {reason} ({conf:.0%} confidence)")
            if len(self.low_confidence_pronunciations) > 10:
                remaining = len(self.low_confidence_pronunciations) - 10
                lines.append(f"- ...and {remaining} more")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Profiling summary
        if self.profiling_summary:
            lines.append("## Performance Breakdown")
            lines.append("")
            if self.profiling_summary.get("bottleneck"):
                name, pct = self.profiling_summary["bottleneck"]
                lines.append(f"**Bottleneck:** {name} ({pct:.1f}% of time)")
            lines.append(f"**Total LLM calls:** {self.profiling_summary.get('total_llm_calls', 0)}")
            lines.append(f"**Total tokens:** {self.profiling_summary.get('total_tokens', 0):,}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by Audiobook Prep*")

        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    def _score_label(self, score: float) -> str:
        """Get label for quality score."""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.5:
            return "Fair"
        else:
            return "Poor"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_file": self.source_file,
            "analysis_timestamp": self.analysis_timestamp,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "llm_model": self.llm_model,
            "llm_provider": self.llm_provider,
            "agent_metrics": [m.to_dict() for m in self.agent_metrics],
            "overall_quality_score": round(self.overall_quality_score, 3),
            "passed_quality_gates": self.passed_quality_gates,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "low_confidence_chapters": self.low_confidence_chapters,
            "low_confidence_characters": self.low_confidence_characters,
            "low_confidence_pronunciations": self.low_confidence_pronunciations,
            "profiling_summary": self.profiling_summary,
        }


def generate_quality_report(
    result: "AnalysisResult",
    profiling_report: Optional["ProfilingReport"],
    llm_model: str,
    llm_provider: str,
    duration_seconds: float,
    halted: bool = False,
) -> QualityReport:
    """
    Generate a quality report from analysis results.

    Args:
        result: The AnalysisResult to analyze
        profiling_report: Profiling data (if available)
        llm_model: LLM model used for analysis
        llm_provider: LLM provider used
        duration_seconds: Total analysis duration
        halted: Whether pipeline was halted due to validation

    Returns:
        QualityReport with quality metrics and recommendations
    """
    from ..models import ConfidenceLevel

    # Build agent metrics from profiling report
    agent_metrics = []
    if profiling_report:
        for stage in profiling_report.stages:
            agent_metrics.append(
                AgentQualityMetrics(
                    agent_name=stage.stage_name,
                    total_items=stage.items_processed,
                    high_confidence_count=stage.high_confidence_count,
                    medium_confidence_count=stage.medium_confidence_count,
                    low_confidence_count=stage.low_confidence_count,
                    processing_time_seconds=stage.duration_seconds,
                    llm_calls=stage.llm_calls,
                    tokens_used=stage.tokens_total,
                    model_used=stage.model_used,
                    provider_used=stage.provider_used,
                )
            )

    # Calculate overall quality score
    total_items = sum(m.total_items for m in agent_metrics)
    if total_items > 0:
        total_high = sum(m.high_confidence_count for m in agent_metrics)
        total_med = sum(m.medium_confidence_count for m in agent_metrics)
        total_low = sum(m.low_confidence_count for m in agent_metrics)
        weighted = total_high * 1.0 + total_med * 0.6 + total_low * 0.2
        overall_quality = weighted / total_items
    else:
        overall_quality = 1.0

    # Collect low-confidence items
    low_conf_chapters = []
    low_conf_characters = []
    low_conf_pronunciations = []

    for elem in result.structure:
        if elem.confidence == ConfidenceLevel.LOW:
            low_conf_chapters.append(
                {
                    "index": elem.index,
                    "title": elem.title,
                    "confidence": 0.3,  # LOW maps to ~0.3
                }
            )

    for char in result.characters:
        if char.confidence == ConfidenceLevel.LOW:
            low_conf_characters.append(
                {
                    "name": char.canonical_name,
                    "mentions": char.mention_count,
                    "confidence": 0.3,
                }
            )

    for pron in result.pronunciations:
        if pron.confidence == ConfidenceLevel.LOW:
            low_conf_pronunciations.append(
                {
                    "word": pron.word,
                    "reason": pron.flag_reason.value if pron.flag_reason else "unknown",
                    "confidence": 0.3,
                }
            )

    # Generate recommendations
    recommendations = []
    extra_warnings: list[str] = []

    if low_conf_chapters:
        recommendations.append(
            f"Review {len(low_conf_chapters)} low-confidence chapters - "
            "chapter boundaries may be incorrect"
        )

    if low_conf_characters:
        recommendations.append(
            f"Review {len(low_conf_characters)} low-confidence characters - "
            "may include false positives or missed aliases"
        )

    if low_conf_pronunciations:
        recommendations.append(
            f"Review {len(low_conf_pronunciations)} low-confidence pronunciations - "
            "IPA may need manual verification"
        )

    if halted:
        recommendations.insert(0, "Pipeline was halted - see halt report for details")

    # Check for common issues
    if len(result.structure) == 1:
        chapters_word_count = result.structure[0].word_count if result.structure else 0
        if chapters_word_count > 20000:
            recommendations.append(
                "Only 1 chapter detected with high word count - "
                "consider trying a different model for chapter detection"
            )

    if not result.characters:
        recommendations.append(
            "No characters extracted - verify document contains narrative content"
        )

    # Detect missing rich character profiles for prominent characters
    # (these show up in the HTML report as "No detailed profile available.")
    MIN_MENTIONS_FOR_PROFILE = 5
    missing_profiles = [
        c
        for c in result.characters
        if c.mention_count >= MIN_MENTIONS_FOR_PROFILE and not c.descriptions
    ]
    if missing_profiles:
        # Keep the warning compact; names can be inspected in the HTML report
        extra_warnings.append(
            f"{len(missing_profiles)} characters have no detailed profile despite "
            f"{MIN_MENTIONS_FOR_PROFILE}+ mentions"
        )
        recommendations.append(
            "Re-run character profiling or inspect LLM/profile-generation logs for missing profiles"
        )

    # Build profiling summary
    profiling_summary = {}
    if profiling_report:
        bottleneck = profiling_report.get_bottleneck()
        if bottleneck:
            profiling_summary["bottleneck"] = bottleneck
        profiling_summary["total_llm_calls"] = sum(s.llm_calls for s in profiling_report.stages)
        profiling_summary["total_tokens"] = sum(s.tokens_total for s in profiling_report.stages)

    return QualityReport(
        source_file=result.metadata.source_file,
        analysis_timestamp=datetime.now().isoformat(),
        total_duration_seconds=duration_seconds,
        llm_model=llm_model,
        llm_provider=llm_provider,
        agent_metrics=agent_metrics,
        overall_quality_score=overall_quality,
        passed_quality_gates=not halted and overall_quality >= 0.5,
        critical_issues=[],
        warnings=(result.warnings + extra_warnings)[:10],  # Limit warnings
        recommendations=recommendations[:5],  # Limit recommendations
        low_confidence_chapters=low_conf_chapters,
        low_confidence_characters=low_conf_characters[:20],  # Limit
        low_confidence_pronunciations=low_conf_pronunciations[:20],  # Limit
        profiling_summary=profiling_summary,
    )
