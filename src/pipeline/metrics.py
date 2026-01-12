"""
Pipeline metrics collection for profiling analysis performance.

Provides a context manager-based approach to collecting timing, token usage,
and quality metrics for each stage of the analysis pipeline.
"""

from __future__ import annotations
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Generator
import logging

from .llm import LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    stage_name: str
    duration_seconds: float = 0.0
    llm_calls: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    latency_total_ms: float = 0.0
    items_processed: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0

    # Model tracking (for per-stage model logging)
    model_used: Optional[str] = None
    provider_used: Optional[str] = None

    @property
    def items_per_second(self) -> float:
        """Calculate processing rate."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.items_processed / self.duration_seconds

    @property
    def avg_latency_ms(self) -> float:
        """Average latency per LLM call."""
        if self.llm_calls <= 0:
            return 0.0
        return self.latency_total_ms / self.llm_calls

    @property
    def confidence_summary(self) -> str:
        """Format confidence counts as H/M/L."""
        return f"{self.high_confidence_count}H/{self.medium_confidence_count}M/{self.low_confidence_count}L"


@dataclass
class ProfilingReport:
    """Aggregated profiling report for the entire analysis."""
    stages: list[StageMetrics] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_llm_calls: int = 0
    total_tokens: int = 0
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    def add_stage(self, metrics: StageMetrics) -> None:
        """Add stage metrics to the report."""
        self.stages.append(metrics)
        self.total_duration_seconds += metrics.duration_seconds
        self.total_llm_calls += metrics.llm_calls
        self.total_tokens += metrics.tokens_total

    def get_bottleneck(self) -> Optional[tuple[str, float]]:
        """Find the stage that took the most time."""
        if not self.stages:
            return None
        slowest = max(self.stages, key=lambda s: s.duration_seconds)
        if self.total_duration_seconds > 0:
            pct = (slowest.duration_seconds / self.total_duration_seconds) * 100
        else:
            pct = 0.0
        return slowest.stage_name, pct

    def get_quality_concerns(self) -> list[tuple[str, int]]:
        """Find stages with low-confidence items."""
        concerns = []
        for stage in self.stages:
            if stage.low_confidence_count > 0:
                concerns.append((stage.stage_name, stage.low_confidence_count))
        return concerns

    def format_table(self) -> str:
        """Format as a text table for console output."""
        lines = []
        lines.append("=== Pipeline Profiling Report ===")
        lines.append("")

        # Header
        header = f"{'Stage':<24} | {'Time':>8} | {'LLM Calls':>9} | {'Tokens':>8} | {'Items':>5} | {'Confidence':<12}"
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for stage in self.stages:
            time_str = self._format_duration(stage.duration_seconds)
            lines.append(
                f"{stage.stage_name:<24} | {time_str:>8} | {stage.llm_calls:>9} | "
                f"{stage.tokens_total:>8,} | {stage.items_processed:>5} | {stage.confidence_summary:<12}"
            )

        # Total row
        lines.append("-" * len(header))
        total_time = self._format_duration(self.total_duration_seconds)
        lines.append(
            f"{'TOTAL':<24} | {total_time:>8} | {self.total_llm_calls:>9} | "
            f"{self.total_tokens:>8,} | {'-':>5} | {'-':<12}"
        )

        lines.append("")

        # Bottleneck
        bottleneck = self.get_bottleneck()
        if bottleneck:
            lines.append(f"Bottleneck: {bottleneck[0]} ({bottleneck[1]:.1f}% of time)")

        # Quality concerns
        concerns = self.get_quality_concerns()
        if concerns:
            concern_strs = [f"{count} low-confidence {stage.lower().replace('_', ' ')}s"
                          for stage, count in concerns]
            lines.append(f"Quality concerns: {', '.join(concern_strs)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "stages": [
                {
                    "name": s.stage_name,
                    "duration_seconds": round(s.duration_seconds, 2),
                    "llm_calls": s.llm_calls,
                    "tokens_prompt": s.tokens_prompt,
                    "tokens_completion": s.tokens_completion,
                    "tokens_total": s.tokens_total,
                    "avg_latency_ms": round(s.avg_latency_ms, 2),
                    "items_processed": s.items_processed,
                    "high_confidence": s.high_confidence_count,
                    "medium_confidence": s.medium_confidence_count,
                    "low_confidence": s.low_confidence_count,
                    "model_used": s.model_used,
                    "provider_used": s.provider_used,
                }
                for s in self.stages
            ],
            "totals": {
                "duration_seconds": round(self.total_duration_seconds, 2),
                "llm_calls": self.total_llm_calls,
                "tokens": self.total_tokens,
            },
            "bottleneck": self.get_bottleneck(),
            "quality_concerns": self.get_quality_concerns(),
            "timestamps": {
                "started": self.start_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.start_timestamp else None,
                "ended": self.end_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.end_timestamp else None,
            },
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m{secs:.0f}s"


class StageContext:
    """Context for collecting metrics during a pipeline stage."""

    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.start_time: Optional[float] = None
        self._metrics = StageMetrics(stage_name=stage_name)

    def record_llm_call(self, response: LLMResponse) -> None:
        """Record metrics from an LLM call."""
        self._metrics.llm_calls += 1

        if response.usage:
            prompt = response.usage.get("prompt_tokens", 0)
            completion = response.usage.get("completion_tokens", 0)
            self._metrics.tokens_prompt += prompt
            self._metrics.tokens_completion += completion
            self._metrics.tokens_total += prompt + completion

        if response.latency_ms:
            self._metrics.latency_total_ms += response.latency_ms

    def record_items(
        self,
        total: int = 0,
        high_confidence: int = 0,
        medium_confidence: int = 0,
        low_confidence: int = 0,
    ) -> None:
        """Record processed items with confidence breakdown."""
        self._metrics.items_processed = total or (high_confidence + medium_confidence + low_confidence)
        self._metrics.high_confidence_count = high_confidence
        self._metrics.medium_confidence_count = medium_confidence
        self._metrics.low_confidence_count = low_confidence

    def set_model(self, model: Optional[str], provider: Optional[str] = None) -> None:
        """Set the model used for this stage."""
        self._metrics.model_used = model
        self._metrics.provider_used = provider

    def finalize(self) -> StageMetrics:
        """Finalize and return the metrics."""
        if self.start_time:
            self._metrics.duration_seconds = time.perf_counter() - self.start_time
        return self._metrics


class MetricsCollector:
    """
    Collects and aggregates pipeline metrics.

    Usage:
        collector = MetricsCollector()

        with collector.stage("chapter_detection") as ctx:
            # Do work...
            response = llm.query(prompt)
            ctx.record_llm_call(response)
            ctx.record_items(high_confidence=10, medium_confidence=2, low_confidence=0)

        report = collector.get_report()
        print(report.format_table())
    """

    def __init__(self):
        self._stages: list[StageMetrics] = []
        self._current_context: Optional[StageContext] = None
        self._analysis_start: Optional[float] = None
        self._analysis_start_dt: Optional[datetime] = None
        self._lock = threading.Lock()  # Thread safety for parallel execution

    def start_analysis(self) -> None:
        """Mark the start of the analysis."""
        self._analysis_start = time.perf_counter()
        self._analysis_start_dt = datetime.now()
        self._stages = []

    @contextmanager
    def stage(self, name: str) -> Generator[StageContext, None, None]:
        """
        Context manager for measuring a pipeline stage.

        Args:
            name: Human-readable name for the stage

        Yields:
            StageContext for recording metrics
        """
        context = StageContext(name)
        context.start_time = time.perf_counter()
        self._current_context = context

        try:
            yield context
        finally:
            metrics = context.finalize()
            with self._lock:  # Thread-safe append for parallel stages
                self._stages.append(metrics)
            self._current_context = None
            logger.debug(
                f"Stage '{name}' completed: {metrics.duration_seconds:.2f}s, "
                f"{metrics.llm_calls} LLM calls, {metrics.tokens_total} tokens"
            )

    def record_llm_call(self, response: LLMResponse) -> None:
        """
        Record an LLM call in the current stage context.

        This is a convenience method - can also use ctx.record_llm_call() directly.
        """
        if self._current_context:
            self._current_context.record_llm_call(response)

    def get_report(self) -> ProfilingReport:
        """Generate the profiling report."""
        report = ProfilingReport()
        for stage in self._stages:
            report.add_stage(stage)

        # Use actual total time if we tracked it
        if self._analysis_start:
            report.total_duration_seconds = time.perf_counter() - self._analysis_start

        # Add datetime timestamps
        if self._analysis_start_dt:
            report.start_timestamp = self._analysis_start_dt
            report.end_timestamp = datetime.now()

        return report

    @property
    def current_stage(self) -> Optional[StageContext]:
        """Get the current stage context if in a stage."""
        return self._current_context
