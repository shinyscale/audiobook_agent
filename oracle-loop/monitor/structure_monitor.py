#!/usr/bin/env python3
"""
Structure Experiment Monitor

Lightweight TUI monitor for structure detection experiments.
Reads from structure_results.json as it's being updated.

Usage:
    python oracle-loop/monitor/structure_monitor.py

Keybindings:
    q - Quit
    r - Refresh now
    p - Pause/resume auto-refresh
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static, Footer, Header
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.console import Group


# Path to results file
RESULTS_FILE = Path(__file__).parent.parent / "state" / "structure_results.json"

# Expected chapters for reference
EXPECTED_CHAPTERS = {
    "gatsby": {"min": 9, "max": 9},
    "frankenstein": {"min": 28, "max": 32},
    "dracula": {"min": 27, "max": 27},
    "don_quixote": {"min": 120, "max": 130},
}

# Model display names (shorter versions)
MODEL_SHORT_NAMES = {
    "regex_only": "regex",
    "qwen3:4b-instruct": "qwen3-4b",
    "qwen2.5:7b": "qwen2.5-7b",
    "qwen3:8b": "qwen3-8b",
    "qwen2.5:14b": "qwen2.5-14b",
    "qwen3:14b": "qwen3-14b",
    "gpt-oss:20b": "gpt-oss-20b",
    "mistral-small3.2:24b": "mistral-24b",
    "gemma3:27b": "gemma3-27b",
    "qwen3:30b-instruct": "qwen3-30b",
    "qwen3-next:80b-a3b-instruct-q8_0": "qwen3-80b",
}


class StructureState:
    """Parsed state from structure_results.json."""

    def __init__(self):
        self.experiment_date: str = ""
        self.experiment_timestamp: str = ""
        self.texts: dict = {}
        self.summary: dict = {}
        self.file_exists: bool = False
        self.file_mtime: float = 0
        self.last_error: str = ""

    @classmethod
    def load(cls) -> "StructureState":
        """Load state from results file."""
        state = cls()

        if not RESULTS_FILE.exists():
            state.last_error = f"Waiting for {RESULTS_FILE.name}..."
            return state

        try:
            state.file_exists = True
            state.file_mtime = RESULTS_FILE.stat().st_mtime

            with open(RESULTS_FILE) as f:
                data = json.load(f)

            state.experiment_date = data.get("experiment_date", "")
            state.experiment_timestamp = data.get("experiment_timestamp", "")
            state.texts = data.get("texts", {})
            state.summary = data.get("summary", {})
            state.last_error = ""

        except json.JSONDecodeError as e:
            state.last_error = f"JSON parse error: {e}"
        except Exception as e:
            state.last_error = f"Error: {e}"

        return state

    def get_progress(self) -> tuple[int, int, int, int]:
        """Return (texts_done, texts_total, models_done, models_total)."""
        texts_total = 4  # gatsby, frankenstein, dracula, don_quixote
        models_total = 11  # regex + 10 LLM models

        texts_done = len(self.texts)

        # Count total model runs completed
        models_done = 0
        for text_data in self.texts.values():
            models_done += len(text_data.get("models", {}))

        return texts_done, texts_total, models_done, texts_total * models_total

    def get_current_activity(self) -> tuple[str, str, str]:
        """Infer current activity from partial results. Returns (text, model, status)."""
        if not self.texts:
            return "Starting...", "", "waiting"

        # Find the text with incomplete models
        all_texts = ["gatsby", "frankenstein", "dracula", "don_quixote"]
        all_models = ["regex_only", "qwen3:4b-instruct", "qwen2.5:7b", "qwen3:8b",
                      "qwen2.5:14b", "qwen3:14b", "gpt-oss:20b", "mistral-small3.2:24b",
                      "gemma3:27b", "qwen3:30b-instruct", "qwen3-next:80b-a3b-instruct-q8_0"]

        for text in all_texts:
            if text not in self.texts:
                return text, "loading text", "running"

            text_models = self.texts[text].get("models", {})
            for model in all_models:
                if model not in text_models:
                    return text, model, "running"

        return "Complete", "", "done"


class StatusPanel(Static):
    """Top status bar showing current activity."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[StructureState] = None

    def update_state(self, state: StructureState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state:
            return Text("Loading...")

        state = self.state
        text, model, status = state.get_current_activity()
        texts_done, texts_total, models_done, models_total = state.get_progress()

        # Build status line
        lines = []

        # Line 1: Mode and progress
        if status == "done":
            mode = Text("● COMPLETE ", style="bold green")
        elif status == "running":
            mode = Text("● RUNNING ", style="bold yellow")
        else:
            mode = Text("○ WAITING ", style="dim")

        progress = Text(f"Texts: {texts_done}/{texts_total}  Models: {models_done}/{models_total}")
        lines.append(Text.assemble(mode, progress))

        # Line 2: Current activity
        if state.last_error:
            lines.append(Text(state.last_error, style="red"))
        elif status == "running":
            model_short = MODEL_SHORT_NAMES.get(model, model)
            lines.append(Text(f"Processing: {text} → {model_short}", style="cyan"))
        elif status == "done":
            lines.append(Text("All experiments complete!", style="green"))

        # Line 3: Timestamp
        if state.experiment_timestamp:
            lines.append(Text(f"Started: {state.experiment_timestamp}", style="dim"))

        return Panel(
            Group(*lines),
            title="Structure Detection Experiment",
            border_style="blue"
        )


class ResultsTable(Static):
    """Matrix showing model × text results."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[StructureState] = None

    def update_state(self, state: StructureState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting for results...", style="dim"), title="Results Matrix")

        state = self.state

        # Build table
        table = Table(title="Chapter Detection Results", expand=True)

        # Columns: Model | gatsby | frankenstein | dracula | don_quixote
        table.add_column("Model", style="cyan", width=14)
        table.add_column("gatsby\n(9)", justify="center", width=10)
        table.add_column("franken\n(28-32)", justify="center", width=10)
        table.add_column("dracula\n(27)", justify="center", width=10)
        table.add_column("quixote\n(120-130)", justify="center", width=10)
        table.add_column("Time", justify="right", width=8)

        # All models in order
        all_models = ["regex_only", "qwen3:4b-instruct", "qwen2.5:7b", "qwen3:8b",
                      "qwen2.5:14b", "qwen3:14b", "gpt-oss:20b", "mistral-small3.2:24b",
                      "gemma3:27b", "qwen3:30b-instruct", "qwen3-next:80b-a3b-instruct-q8_0"]

        text_names = ["gatsby", "frankenstein", "dracula", "don_quixote"]

        for model in all_models:
            model_short = MODEL_SHORT_NAMES.get(model, model[:12])
            cells = [model_short]
            total_time = 0

            for text_name in text_names:
                if text_name not in state.texts:
                    cells.append(Text("-", style="dim"))
                    continue

                models = state.texts[text_name].get("models", {})
                if model not in models:
                    cells.append(Text("...", style="dim yellow"))
                    continue

                result = models[model]
                if "error" in result:
                    cells.append(Text("ERR", style="red"))
                else:
                    detected = result.get("detected", 0)
                    status = result.get("status", "")
                    time_s = result.get("time_seconds", 0)
                    total_time += time_s

                    if status == "PASS":
                        cells.append(Text(f"{detected} ✓", style="green"))
                    else:
                        cells.append(Text(f"{detected} ✗", style="red"))

            # Add total time
            if total_time > 0:
                cells.append(Text(f"{total_time:.1f}s", style="dim"))
            else:
                cells.append(Text("-", style="dim"))

            table.add_row(*cells)

        return table


class SummaryPanel(Static):
    """Summary findings panel."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[StructureState] = None

    def update_state(self, state: StructureState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.summary:
            return Panel(Text("Waiting for summary...", style="dim"), title="Key Findings")

        summary = self.state.summary
        lines = []

        # Smallest passing model
        smallest = summary.get("smallest_passing_model")
        if smallest:
            model_short = MODEL_SHORT_NAMES.get(smallest, smallest)
            lines.append(Text.assemble(
                Text("Smallest passing all: ", style="bold"),
                Text(model_short, style="green bold")
            ))
        else:
            lines.append(Text("No model passed all texts yet", style="yellow"))

        # Regex sufficient for
        regex_texts = summary.get("regex_sufficient_for", [])
        if regex_texts:
            lines.append(Text.assemble(
                Text("Regex-only works for: ", style="bold"),
                Text(", ".join(regex_texts), style="cyan")
            ))

        # Perfect models
        perfect = summary.get("perfect_models", [])
        if perfect:
            perfect_short = [MODEL_SHORT_NAMES.get(m, m) for m in perfect]
            lines.append(Text.assemble(
                Text("Perfect models: ", style="bold"),
                Text(", ".join(perfect_short), style="green")
            ))

        # Pass counts
        pass_counts = summary.get("model_pass_counts", {})
        if pass_counts:
            lines.append(Text(""))
            lines.append(Text("Pass counts:", style="bold underline"))
            for model, data in pass_counts.items():
                model_short = MODEL_SHORT_NAMES.get(model, model)
                passes = data.get("passes", 0)
                total = data.get("total", 0)
                size = data.get("size_gb", "?")

                if passes == total and total > 0:
                    style = "green"
                elif passes > 0:
                    style = "yellow"
                else:
                    style = "red"

                lines.append(Text(f"  {model_short:<14} {passes}/{total}  ({size}GB)", style=style))

        return Panel(
            Group(*lines) if lines else Text("No summary yet"),
            title="Key Findings",
            border_style="green"
        )


class ChapterDetailsPanel(Static):
    """Shows chapter titles for the most recent result."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[StructureState] = None

    def update_state(self, state: StructureState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting...", style="dim"), title="Latest Chapter Detection")

        # Find most recent result
        latest_text = None
        latest_model = None
        latest_result = None

        for text_name in reversed(["gatsby", "frankenstein", "dracula", "don_quixote"]):
            if text_name not in self.state.texts:
                continue
            models = self.state.texts[text_name].get("models", {})
            if models:
                latest_text = text_name
                # Get last model
                for model in reversed(list(models.keys())):
                    if "error" not in models[model]:
                        latest_model = model
                        latest_result = models[model]
                        break
                if latest_model:
                    break

        if not latest_result:
            return Panel(Text("No results yet", style="dim"), title="Latest Chapter Detection")

        lines = []
        model_short = MODEL_SHORT_NAMES.get(latest_model, latest_model)
        lines.append(Text(f"{latest_text} → {model_short}", style="bold cyan"))
        lines.append(Text(f"Detected: {latest_result.get('detected', 0)} chapters", style="bold"))
        lines.append(Text(f"Status: {latest_result.get('status', '?')}",
                         style="green" if latest_result.get('status') == 'PASS' else "red"))
        lines.append(Text(""))

        # Show first 8 chapters
        chapters = latest_result.get("chapters", [])[:8]
        if chapters:
            lines.append(Text("First chapters:", style="underline"))
            for i, ch in enumerate(chapters, 1):
                lines.append(Text(f"  {i}. {ch[:40]}", style="dim"))
            if len(latest_result.get("chapters", [])) > 8:
                lines.append(Text(f"  ... and {len(latest_result.get('chapters', [])) - 8} more", style="dim"))

        return Panel(
            Group(*lines),
            title="Latest Detection",
            border_style="cyan"
        )


class StructureMonitorApp(App):
    """Main TUI application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-columns: 1fr 1fr;
        grid-rows: auto 1fr auto;
    }

    #status {
        column-span: 2;
        height: auto;
        max-height: 7;
    }

    #results {
        column-span: 2;
        height: 100%;
    }

    #summary {
        height: auto;
        min-height: 15;
    }

    #details {
        height: auto;
        min-height: 15;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("p", "toggle_pause", "Pause"),
    ]

    paused = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusPanel(id="status")
        yield ResultsTable(id="results")
        yield SummaryPanel(id="summary")
        yield ChapterDetailsPanel(id="details")
        yield Footer()

    def on_mount(self):
        """Start the refresh timer."""
        self.refresh_state()
        self.set_interval(2.0, self.refresh_state)

    def refresh_state(self):
        """Load state and update all widgets."""
        if self.paused:
            return

        state = StructureState.load()

        # Update all panels
        self.query_one("#status", StatusPanel).update_state(state)
        self.query_one("#results", ResultsTable).update_state(state)
        self.query_one("#summary", SummaryPanel).update_state(state)
        self.query_one("#details", ChapterDetailsPanel).update_state(state)

    def action_refresh(self):
        """Manual refresh."""
        self.refresh_state()

    def action_toggle_pause(self):
        """Toggle auto-refresh."""
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.notify(f"Auto-refresh: {status}")


def main():
    app = StructureMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
