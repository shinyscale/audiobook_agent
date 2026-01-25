"""
Pipeline metrics collection for profiling analysis performance.

Provides a context manager-based approach to collecting timing, token usage,
and quality metrics for each stage of the analysis pipeline.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generator, Optional

from .llm import LLMResponse
from .pricing import calculate_cost

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
    last_latency_ms: float = 0.0  # Latency of most recent LLM call
    items_processed: int = 0
    items_total: Optional[int] = None  # Total items to process (if known)
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0

    # Model tracking (for per-stage model logging)
    model_used: Optional[str] = None
    provider_used: Optional[str] = None

    # Retry/failure tracking (for config auditing)
    llm_retries: int = 0  # Retries due to parse/validation failures
    json_parse_failures: int = 0  # JSON schema validation failures

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
            concern_strs = [
                f"{count} low-confidence {stage.lower().replace('_', ' ')}s"
                for stage, count in concerns
            ]
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
                    "llm_retries": s.llm_retries,
                    "json_parse_failures": s.json_parse_failures,
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
                "started": (
                    self.start_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if self.start_timestamp
                    else None
                ),
                "ended": (
                    self.end_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.end_timestamp else None
                ),
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
            self._metrics.last_latency_ms = response.latency_ms

    def record_items(
        self,
        total: int = 0,
        high_confidence: int = 0,
        medium_confidence: int = 0,
        low_confidence: int = 0,
    ) -> None:
        """Record processed items with confidence breakdown."""
        self._metrics.items_processed = total or (
            high_confidence + medium_confidence + low_confidence
        )
        self._metrics.high_confidence_count = high_confidence
        self._metrics.medium_confidence_count = medium_confidence
        self._metrics.low_confidence_count = low_confidence

    def set_model(self, model: Optional[str], provider: Optional[str] = None) -> None:
        """Set the model used for this stage."""
        self._metrics.model_used = model
        self._metrics.provider_used = provider

    def record_retry(self) -> None:
        """Record an LLM retry due to parse/validation failure."""
        self._metrics.llm_retries += 1

    def record_json_failure(self) -> None:
        """Record a JSON schema validation failure."""
        self._metrics.json_parse_failures += 1

    def finalize(self) -> StageMetrics:
        """Finalize and return the metrics."""
        if self.start_time:
            self._metrics.duration_seconds = time.perf_counter() - self.start_time
        return self._metrics


@dataclass
class ProgressSnapshot:
    """Real-time snapshot of analysis progress for GUI display."""

    # Current stage
    current_stage_name: Optional[str] = None
    current_stage_start_time: Optional[float] = None

    # Timing
    total_elapsed_seconds: float = 0.0
    current_stage_elapsed_seconds: float = 0.0
    estimated_remaining_seconds: Optional[float] = None

    # Current stage metrics
    current_stage_items_processed: int = 0
    current_stage_items_total: Optional[int] = None
    current_stage_high_confidence: int = 0
    current_stage_medium_confidence: int = 0
    current_stage_low_confidence: int = 0

    # Model info
    current_stage_model: Optional[str] = None
    current_stage_provider: Optional[str] = None

    # Cumulative metrics
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    # Cost estimation
    estimated_cost_usd: Optional[float] = None

    # Completed stages
    completed_stages: list[StageMetrics] = field(default_factory=list)

    @property
    def progress_percentage(self) -> Optional[float]:
        """Progress within current stage (0-100), if items_total known."""
        if self.current_stage_items_total and self.current_stage_items_total > 0:
            return (self.current_stage_items_processed / self.current_stage_items_total) * 100
        return None


class ETAEstimator:
    """Estimates time remaining based on historical stage durations."""

    def __init__(self):
        self._stage_history: dict[str, list[float]] = {}
        self._typical_pipeline = [
            "Chapter Detection",
            "Character Extraction",
            "Character Profiles",
            "Chapter Summaries",
            "Pronunciation Guide",
        ]
        # Fallback heuristics (seconds) when no historical data
        self._fallback_durations = {
            "Chapter Detection": 15.0,
            "Character Extraction": 30.0,
            "Character Profiles": 60.0,
            "Chapter Summaries": 120.0,
            "Pronunciation Guide": 20.0,
        }

    def record_completion(self, stage_name: str, duration: float) -> None:
        """Record completed stage for future estimates."""
        if stage_name not in self._stage_history:
            self._stage_history[stage_name] = []
        self._stage_history[stage_name].append(duration)
        # Keep only last 10 runs per stage
        if len(self._stage_history[stage_name]) > 10:
            self._stage_history[stage_name] = self._stage_history[stage_name][-10:]

    def estimate(
        self, current_stage: str, elapsed: float, completed_stages: list[str]
    ) -> Optional[float]:
        """
        Estimate remaining time.

        Strategy:
        1. Use median of historical data if available
        2. Otherwise use fallback heuristics
        3. Assume current stage is 50% done if no progress data
        """
        # Estimate remaining time for current stage (assume 50% done)
        current_stage_estimate = self._estimate_stage_duration(current_stage)
        current_remaining = max(0, current_stage_estimate * 0.5)

        # Estimate time for remaining stages
        remaining_stages = [
            s for s in self._typical_pipeline if s not in completed_stages and s != current_stage
        ]

        future_time = sum(self._estimate_stage_duration(s) for s in remaining_stages)

        total_estimate = current_remaining + future_time

        # Don't return estimate if it seems unreasonable (too small)
        if total_estimate < 1.0:
            return None

        return total_estimate

    def _estimate_stage_duration(self, stage_name: str) -> float:
        """Get estimated duration for a stage."""
        if stage_name in self._stage_history and self._stage_history[stage_name]:
            # Use median of historical data
            sorted_durations = sorted(self._stage_history[stage_name])
            return sorted_durations[len(sorted_durations) // 2]
        else:
            # Fallback heuristics
            return self._fallback_durations.get(stage_name, 30.0)


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
        self._current_stage_info: dict = {}  # Real-time updates for current stage
        self._eta_estimator = ETAEstimator()
        self._output_dir: Optional[str] = None  # For heartbeat file
        self._last_heartbeat: float = 0  # Rate limit heartbeat writes
        self._phase_start_time: Optional[datetime] = None  # When current phase started

    def set_output_dir(self, output_dir: str) -> None:
        """Set output directory for heartbeat file."""
        self._output_dir = output_dir

    def _write_heartbeat(self, activity: str = "working") -> None:
        """Write heartbeat file for external monitoring.

        Rate-limited to once per second to avoid excessive I/O.
        """
        if not self._output_dir:
            return

        now = time.time()
        if now - self._last_heartbeat < 1.0:  # Rate limit to 1Hz
            return
        self._last_heartbeat = now

        try:
            import json
            from pathlib import Path

            heartbeat_file = Path(self._output_dir) / "HEARTBEAT.json"

            # Get current stage info
            stage_name = None
            stage_elapsed = 0.0
            llm_calls = 0
            model = None

            if self._current_context:
                stage_name = self._current_context.stage_name
                if self._current_context.start_time:
                    stage_elapsed = time.perf_counter() - self._current_context.start_time
                llm_calls = self._current_context._metrics.llm_calls
                model = self._current_context._metrics.model_used

            # Total elapsed
            total_elapsed = 0.0
            if self._analysis_start:
                total_elapsed = time.perf_counter() - self._analysis_start

            heartbeat_data = {
                "timestamp": datetime.now().isoformat(),
                "unix_time": now,
                "activity": activity,
                "stage": stage_name,
                "stage_elapsed_seconds": round(stage_elapsed, 1),
                "total_elapsed_seconds": round(total_elapsed, 1),
                "llm_calls_this_stage": llm_calls,
                "model": model,
                "phase_started": (
                    self._phase_start_time.isoformat() if self._phase_start_time else None
                ),
            }

            with open(heartbeat_file, "w") as f:
                json.dump(heartbeat_data, f)
        except Exception:
            pass  # Non-critical

    def start_analysis(self) -> None:
        """Mark the start of the analysis."""
        self._analysis_start = time.perf_counter()
        self._analysis_start_dt = datetime.now()
        self._phase_start_time = datetime.now()
        self._stages = []
        self._write_heartbeat("analysis_started")

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
        self._write_heartbeat(f"stage_started:{name}")

        try:
            yield context
        finally:
            metrics = context.finalize()
            with self._lock:  # Thread-safe append for parallel stages
                self._stages.append(metrics)
                # Record completion for ETA estimation
                self._eta_estimator.record_completion(name, metrics.duration_seconds)
                # Clear current stage info
                self._current_stage_info = {}
            self._current_context = None
            self._write_heartbeat(f"stage_completed:{name}")
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
            self._write_heartbeat("llm_call")

    def record_llm_call_starting(self) -> None:
        """
        Record that an LLM call is about to start.

        This writes a heartbeat BEFORE the blocking LLM request,
        so external monitors know the process is still active even
        if the LLM takes a long time to respond.
        """
        self._write_heartbeat("llm_call_starting")

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

    def update_stage_progress(
        self,
        items_processed: int = None,
        items_total: int = None,
        high: int = None,
        medium: int = None,
        low: int = None,
    ) -> None:
        """
        Update real-time progress within current stage.
        Called by pipelines/agents during processing.
        """
        with self._lock:
            if items_processed is not None:
                self._current_stage_info["items_processed"] = items_processed
            if items_total is not None:
                self._current_stage_info["items_total"] = items_total
                # Also store in current context metrics for PROGRESS.json
                if self._current_context:
                    self._current_context._metrics.items_total = items_total
            if high is not None:
                self._current_stage_info["high_confidence"] = high
            if medium is not None:
                self._current_stage_info["medium_confidence"] = medium
            if low is not None:
                self._current_stage_info["low_confidence"] = low

    def get_progress_snapshot(self) -> ProgressSnapshot:
        """
        Get thread-safe snapshot of current progress.
        Called by GUI polling loop every 100ms.
        """
        with self._lock:
            # Current stage info
            current_stage_name = None
            current_stage_start_time = None
            current_stage_elapsed = 0.0
            current_stage_model = None
            current_stage_provider = None

            if self._current_context:
                current_stage_name = self._current_context.stage_name
                current_stage_start_time = self._current_context.start_time
                if current_stage_start_time:
                    current_stage_elapsed = time.perf_counter() - current_stage_start_time
                current_stage_model = self._current_context._metrics.model_used
                current_stage_provider = self._current_context._metrics.provider_used

            # Total elapsed time
            total_elapsed = 0.0
            if self._analysis_start:
                total_elapsed = time.perf_counter() - self._analysis_start

            # Current stage metrics from real-time updates
            items_processed = self._current_stage_info.get("items_processed", 0)
            items_total = self._current_stage_info.get("items_total")
            high_conf = self._current_stage_info.get("high_confidence", 0)
            medium_conf = self._current_stage_info.get("medium_confidence", 0)
            low_conf = self._current_stage_info.get("low_confidence", 0)

            # If no real-time updates, use current context's recorded items
            if items_processed == 0 and self._current_context:
                items_processed = self._current_context._metrics.items_processed
                high_conf = self._current_context._metrics.high_confidence_count
                medium_conf = self._current_context._metrics.medium_confidence_count
                low_conf = self._current_context._metrics.low_confidence_count

            # Also check items_total from current context
            if items_total is None and self._current_context:
                items_total = self._current_context._metrics.items_total

            # Cumulative metrics
            total_llm_calls = sum(s.llm_calls for s in self._stages)
            total_tokens = sum(s.tokens_total for s in self._stages)
            total_prompt_tokens = sum(s.tokens_prompt for s in self._stages)
            total_completion_tokens = sum(s.tokens_completion for s in self._stages)

            # Add current stage's tokens
            if self._current_context:
                total_llm_calls += self._current_context._metrics.llm_calls
                total_tokens += self._current_context._metrics.tokens_total
                total_prompt_tokens += self._current_context._metrics.tokens_prompt
                total_completion_tokens += self._current_context._metrics.tokens_completion

            # ETA estimation
            completed_stage_names = [s.stage_name for s in self._stages]
            estimated_remaining = None
            if current_stage_name:
                estimated_remaining = self._eta_estimator.estimate(
                    current_stage_name, current_stage_elapsed, completed_stage_names
                )

            # Cost calculation (stub for now, will be implemented in Phase 4)
            estimated_cost = self._calculate_cost()

            return ProgressSnapshot(
                current_stage_name=current_stage_name,
                current_stage_start_time=current_stage_start_time,
                total_elapsed_seconds=total_elapsed,
                current_stage_elapsed_seconds=current_stage_elapsed,
                estimated_remaining_seconds=estimated_remaining,
                current_stage_items_processed=items_processed,
                current_stage_items_total=items_total,
                current_stage_high_confidence=high_conf,
                current_stage_medium_confidence=medium_conf,
                current_stage_low_confidence=low_conf,
                current_stage_model=current_stage_model,
                current_stage_provider=current_stage_provider,
                total_llm_calls=total_llm_calls,
                total_tokens=total_tokens,
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
                estimated_cost_usd=estimated_cost,
                completed_stages=list(self._stages),  # Copy list
            )

    def _calculate_cost(self) -> Optional[float]:
        """
        Calculate estimated cost based on provider pricing.

        Sums costs from all completed stages plus the current stage (if any).
        Returns None if no pricing information is available for any used models.
        """
        total_cost = 0.0
        has_cost_data = False

        # Calculate cost for completed stages
        for stage in self._stages:
            if stage.model_used and stage.provider_used:
                stage_cost = calculate_cost(
                    model_name=stage.model_used,
                    provider=stage.provider_used,
                    input_tokens=stage.tokens_prompt,
                    output_tokens=stage.tokens_completion,
                )
                if stage_cost is not None:
                    total_cost += stage_cost
                    has_cost_data = True

        # Calculate cost for current stage
        if self._current_context:
            metrics = self._current_context._metrics
            if metrics.model_used and metrics.provider_used:
                current_cost = calculate_cost(
                    model_name=metrics.model_used,
                    provider=metrics.provider_used,
                    input_tokens=metrics.tokens_prompt,
                    output_tokens=metrics.tokens_completion,
                )
                if current_cost is not None:
                    total_cost += current_cost
                    has_cost_data = True

        return total_cost if has_cost_data else None
