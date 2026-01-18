"""
Rich terminal progress display for CLI analysis.

Provides a live-updating progress panel during analysis,
showing stage progress, timing, token usage, and costs.
"""

import sys
import threading
from typing import Optional

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from ..pipeline.metrics import MetricsCollector, ProgressSnapshot, StageMetrics
from ..pipeline.pricing import format_cost


def format_duration(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    if seconds < 0:
        return "0:00"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_eta(seconds: Optional[float]) -> str:
    """Format ETA remaining as human-readable string."""
    if seconds is None:
        return "calculating..."
    if seconds < 0:
        return "almost done"
    return f"~{format_duration(seconds)} remaining"


class RichProgressDisplay:
    """
    Rich terminal progress display for CLI analysis.

    Uses Rich's Live context manager to show real-time progress updates
    by polling the MetricsCollector's progress snapshot.

    Usage:
        display = RichProgressDisplay(metrics_collector)
        display.run_until_complete(analysis_complete_event)
    """

    def __init__(self, collector: MetricsCollector, poll_interval: float = 0.15):
        """
        Initialize the progress display.

        Args:
            collector: MetricsCollector instance to poll for progress
            poll_interval: Seconds between progress updates (default 150ms)
        """
        self.collector = collector
        self.poll_interval = poll_interval
        self.console = Console()
        self._last_snapshot: Optional[ProgressSnapshot] = None

    def _build_completed_stages_table(self, stages: list[StageMetrics]) -> Table:
        """Build a table showing completed stages."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            collapse_padding=True,
        )
        table.add_column("check", style="green", width=2)
        table.add_column("name", style="dim")
        table.add_column("time", style="dim", justify="right")
        table.add_column("items", style="dim", justify="right")
        table.add_column("confidence", style="dim")

        for stage in stages:
            table.add_row(
                "[green]✓[/green]",
                stage.stage_name,
                format_duration(stage.duration_seconds),
                f"{stage.items_processed} items" if stage.items_processed > 0 else "",
                stage.confidence_summary if stage.items_processed > 0 else "",
            )

        return table

    def _build_progress_panel(self, snapshot: ProgressSnapshot) -> Panel:
        """Build the Rich panel for current progress state."""
        # Determine panel title
        if snapshot.current_stage_name:
            title = f"[bold cyan]Analyzing: {snapshot.current_stage_name}[/bold cyan]"
        else:
            title = "[bold cyan]Analyzing...[/bold cyan]"

        # Build content
        content_parts = []

        # Progress bar section
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
            expand=False,
        )

        # Calculate progress percentage
        pct = snapshot.progress_percentage
        if pct is None:
            # If we don't know total items, show indeterminate
            # Use stage elapsed vs typical duration as rough progress
            pct = min(95, snapshot.current_stage_elapsed_seconds / 30.0 * 100)

        task_id = progress.add_task("Progress", total=100)
        progress.update(task_id, completed=pct)

        # Create a table for the progress bar
        progress_table = Table(show_header=False, box=None, padding=0)
        progress_table.add_column()
        progress_table.add_row(progress)
        content_parts.append(progress_table)
        content_parts.append("")

        # Timing row
        timing_text = Text()
        timing_text.append("  Stage: ", style="dim")
        timing_text.append(format_duration(snapshot.current_stage_elapsed_seconds), style="bold")
        timing_text.append("    Total: ", style="dim")
        timing_text.append(format_duration(snapshot.total_elapsed_seconds), style="bold")
        timing_text.append("    ", style="dim")
        timing_text.append(format_eta(snapshot.estimated_remaining_seconds), style="yellow")
        content_parts.append(timing_text)

        # Items processed row (if available)
        if snapshot.current_stage_items_processed > 0:
            items_text = Text()
            items_text.append("  ", style="dim")
            items_text.append(f"{snapshot.current_stage_items_processed} items", style="bold")
            if snapshot.current_stage_items_total:
                items_text.append(f" / {snapshot.current_stage_items_total}", style="dim")

            # Confidence breakdown
            conf_parts = []
            if snapshot.current_stage_high_confidence > 0:
                conf_parts.append(f"[green]{snapshot.current_stage_high_confidence}H[/green]")
            if snapshot.current_stage_medium_confidence > 0:
                conf_parts.append(f"[yellow]{snapshot.current_stage_medium_confidence}M[/yellow]")
            if snapshot.current_stage_low_confidence > 0:
                conf_parts.append(f"[red]{snapshot.current_stage_low_confidence}L[/red]")

            if conf_parts:
                items_text.append("  (")
                items_text.append(Text.from_markup("/".join(conf_parts)))
                items_text.append(")")

            content_parts.append(items_text)

        # Model info row
        if snapshot.current_stage_model:
            model_text = Text()
            model_text.append("  Model: ", style="dim")
            model_text.append(snapshot.current_stage_model, style="cyan bold")
            if snapshot.current_stage_provider:
                model_text.append(f" ({snapshot.current_stage_provider})", style="dim")
            content_parts.append(model_text)

        # Token/cost row
        if snapshot.total_tokens > 0:
            token_text = Text()
            token_text.append("  Tokens: ", style="dim")
            token_text.append(f"In: {snapshot.total_prompt_tokens:,}", style="")
            token_text.append(" | ", style="dim")
            token_text.append(f"Out: {snapshot.total_completion_tokens:,}", style="")
            token_text.append(" | ", style="dim")
            token_text.append(f"Cost: {format_cost(snapshot.estimated_cost_usd)}", style="green")
            content_parts.append(token_text)

        # Completed stages section
        if snapshot.completed_stages:
            content_parts.append("")
            content_parts.append(Text("  Completed:", style="dim bold"))
            completed_table = self._build_completed_stages_table(snapshot.completed_stages)
            content_parts.append(completed_table)

        # Combine content
        from rich.console import Group
        panel_content = Group(*content_parts)

        return Panel(
            panel_content,
            title=title,
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        )

    def _build_completion_panel(self, snapshot: ProgressSnapshot) -> Panel:
        """Build the final completion panel."""
        content_parts = []

        # Summary row
        summary_text = Text()
        summary_text.append("Analysis complete in ", style="")
        summary_text.append(format_duration(snapshot.total_elapsed_seconds), style="bold green")
        content_parts.append(summary_text)
        content_parts.append("")

        # Build completed stages table
        if snapshot.completed_stages:
            table = Table(
                show_header=True,
                box=box.SIMPLE,
                padding=(0, 1),
            )
            table.add_column("Stage", style="cyan")
            table.add_column("Time", justify="right")
            table.add_column("Items", justify="right")
            table.add_column("Confidence")
            table.add_column("Tokens", justify="right")

            for stage in snapshot.completed_stages:
                table.add_row(
                    stage.stage_name,
                    format_duration(stage.duration_seconds),
                    str(stage.items_processed) if stage.items_processed > 0 else "-",
                    stage.confidence_summary if stage.items_processed > 0 else "-",
                    f"{stage.tokens_total:,}" if stage.tokens_total > 0 else "-",
                )

            content_parts.append(table)

        # Totals
        content_parts.append("")
        totals_text = Text()
        totals_text.append("Total tokens: ", style="dim")
        totals_text.append(f"{snapshot.total_tokens:,}", style="bold")
        totals_text.append("  |  Cost: ", style="dim")
        totals_text.append(format_cost(snapshot.estimated_cost_usd), style="bold green")
        content_parts.append(totals_text)

        from rich.console import Group
        panel_content = Group(*content_parts)

        return Panel(
            panel_content,
            title="[bold green]Analysis Complete[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )

    def run_until_complete(
        self,
        complete_event: threading.Event,
        error_container: Optional[list] = None
    ) -> None:
        """
        Run the progress display until analysis completes.

        Args:
            complete_event: Event that signals analysis completion
            error_container: Optional list to check for errors (first element is exception)
        """
        # Check if we're in a TTY - if not, use simpler output
        if not sys.stdout.isatty():
            self._run_simple_output(complete_event, error_container)
            return

        try:
            with Live(
                self._build_progress_panel(ProgressSnapshot()),
                console=self.console,
                refresh_per_second=1 / self.poll_interval,
                transient=True,
            ) as live:
                while not complete_event.is_set():
                    # Check for errors
                    if error_container and error_container:
                        break

                    # Get current progress
                    snapshot = self.collector.get_progress_snapshot()
                    self._last_snapshot = snapshot

                    # Update display
                    live.update(self._build_progress_panel(snapshot))

                    # Wait for next update or completion
                    complete_event.wait(timeout=self.poll_interval)

            # Show final completion panel
            if error_container and error_container:
                # Error occurred - don't show completion
                pass
            else:
                # Get final snapshot and show completion
                final_snapshot = self.collector.get_progress_snapshot()
                self.console.print(self._build_completion_panel(final_snapshot))

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Analysis interrupted[/yellow]")
            raise

    def _run_simple_output(
        self,
        complete_event: threading.Event,
        error_container: Optional[list] = None
    ) -> None:
        """Run with simple text output for non-TTY environments."""
        last_stage = None

        while not complete_event.is_set():
            if error_container and error_container:
                break

            snapshot = self.collector.get_progress_snapshot()

            # Print stage changes
            if snapshot.current_stage_name and snapshot.current_stage_name != last_stage:
                print(f"[Stage] {snapshot.current_stage_name}...")
                last_stage = snapshot.current_stage_name

            complete_event.wait(timeout=self.poll_interval)

        # Print completion
        if not (error_container and error_container):
            final_snapshot = self.collector.get_progress_snapshot()
            print(f"\nAnalysis complete in {format_duration(final_snapshot.total_elapsed_seconds)}")
            print(f"Total tokens: {final_snapshot.total_tokens:,}")
            print(f"Cost: {format_cost(final_snapshot.estimated_cost_usd)}")
