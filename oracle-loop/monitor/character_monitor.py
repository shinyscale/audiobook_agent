#!/usr/bin/env python3
"""
Character Experiment Monitor

Lightweight TUI monitor for character extraction experiments.
Reads from character_results.json as it's being updated.

Usage:
    python oracle-loop/monitor/character_monitor.py

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
RESULTS_FILE = Path(__file__).parent.parent / "state" / "character_results.json"

# Expected characters for reference
EXPECTED_CHARACTERS = {
    "cask_of_amontillado": ["Montresor", "Fortunato"],
    "gift_of_the_magi": ["Della", "Jim"],
    "monkeys_paw": ["Mr. White", "Mrs. White", "Herbert White", "Sergeant-Major Morris"],
    "berenice": ["Egaeus", "Berenice"],
    "masque_of_red_death": ["Prince Prospero", "the Red Death"],
    "i_have_no_mouth": ["AM", "Ted", "Gorrister", "Benny", "Nimdok", "Ellen"],
}

# Model display names (shorter versions)
MODEL_SHORT_NAMES = {
    "qwen2.5:7b": "qwen2.5-7b",
    "qwen2.5:14b": "qwen2.5-14b",
    "qwen3:14b": "qwen3-14b",
    "mistral-small3.2:24b": "mistral-24b",
    "qwen3:30b-instruct": "qwen3-30b",
    "qwen2.5:32b": "qwen2.5-32b",
    "qwen3-next:80b-a3b-instruct-q8_0": "qwen3-80b",
    "gpt-oss:120b": "gpt-oss-120b",
}

# All texts in order
ALL_TEXTS = [
    "cask_of_amontillado",
    "gift_of_the_magi",
    "monkeys_paw",
    "berenice",
    "masque_of_red_death",
    "i_have_no_mouth",
]

# All models in order
ALL_MODELS = [
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen3:14b",
    "mistral-small3.2:24b",
    "qwen3:30b-instruct",
    "qwen2.5:32b",
    "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]


class CharacterState:
    """Parsed state from character_results.json."""

    def __init__(self):
        self.experiment_date: str = ""
        self.experiment_timestamp: str = ""
        self.texts: dict = {}
        self.summary: dict = {}
        self.file_exists: bool = False
        self.file_mtime: float = 0
        self.last_error: str = ""

    @classmethod
    def load(cls) -> "CharacterState":
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
        texts_total = len(ALL_TEXTS)
        models_total = len(ALL_MODELS)

        texts_started = len(self.texts)

        # Count total model runs completed
        models_done = 0
        for text_data in self.texts.values():
            models_done += len(text_data.get("models", {}))

        return texts_started, texts_total, models_done, texts_total * models_total

    def get_current_activity(self) -> tuple[str, str, str]:
        """Infer current activity from partial results. Returns (text, model, status)."""
        if not self.texts:
            return "Starting...", "", "waiting"

        # Find the text with incomplete models
        for text in ALL_TEXTS:
            if text not in self.texts:
                return text, "loading text", "running"

            text_models = self.texts[text].get("models", {})
            for model in ALL_MODELS:
                if model not in text_models:
                    return text, model, "running"

        return "Complete", "", "done"


class StatusPanel(Static):
    """Top status bar showing current activity."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[CharacterState] = None

    def update_state(self, state: CharacterState):
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
            title="Character Extraction Experiment",
            border_style="blue"
        )


class ResultsTable(Static):
    """Matrix showing model × text results."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[CharacterState] = None

    def update_state(self, state: CharacterState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting for results...", style="dim"), title="Results Matrix")

        state = self.state

        # Build table
        table = Table(title="Character Extraction Results", expand=True)

        # Columns: Model | texts...
        table.add_column("Model", style="cyan", width=14)

        # Add text columns with expected character counts
        for text_name in ALL_TEXTS:
            short_name = text_name[:8]
            char_count = len(EXPECTED_CHARACTERS.get(text_name, []))
            table.add_column(f"{short_name}\n({char_count})", justify="center", width=10)

        table.add_column("Avg", justify="right", width=6)
        table.add_column("Time", justify="right", width=8)

        for model in ALL_MODELS:
            model_short = MODEL_SHORT_NAMES.get(model, model[:12])
            cells = [model_short]
            total_time = 0
            scores = []

            for text_name in ALL_TEXTS:
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
                    overall = result.get("overall", 0)
                    status = result.get("status", "")
                    time_s = result.get("time_seconds", 0)
                    total_time += time_s
                    scores.append(overall)

                    if status == "PASS":
                        cells.append(Text(f"{overall:.1f} ✓", style="green"))
                    elif status == "PARTIAL":
                        cells.append(Text(f"{overall:.1f} ~", style="yellow"))
                    else:
                        cells.append(Text(f"{overall:.1f} ✗", style="red"))

            # Add average score
            if scores:
                avg = sum(scores) / len(scores)
                cells.append(Text(f"{avg:.1f}", style="bold"))
            else:
                cells.append(Text("-", style="dim"))

            # Add total time
            if total_time > 0:
                cells.append(Text(f"{total_time:.0f}s", style="dim"))
            else:
                cells.append(Text("-", style="dim"))

            table.add_row(*cells)

        return table


class SummaryPanel(Static):
    """Summary findings panel."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[CharacterState] = None

    def update_state(self, state: CharacterState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.summary:
            return Panel(Text("Waiting for summary...", style="dim"), title="Key Findings")

        summary = self.state.summary
        lines = []

        # Champion model
        champion = summary.get("champion_model")
        if champion:
            model_short = MODEL_SHORT_NAMES.get(champion, champion)
            lines.append(Text.assemble(
                Text("Champion model: ", style="bold"),
                Text(model_short, style="green bold")
            ))

        # Smallest passing model
        smallest = summary.get("smallest_passing_model")
        if smallest:
            model_short = MODEL_SHORT_NAMES.get(smallest, smallest)
            lines.append(Text.assemble(
                Text("Smallest passing all: ", style="bold"),
                Text(model_short, style="cyan bold")
            ))

        # Perfect models
        perfect = summary.get("perfect_models", [])
        if perfect:
            perfect_short = [MODEL_SHORT_NAMES.get(m, m) for m in perfect]
            lines.append(Text.assemble(
                Text("Perfect models: ", style="bold"),
                Text(", ".join(perfect_short), style="green")
            ))

        # Model rankings
        rankings = summary.get("model_rankings", {})
        if rankings:
            lines.append(Text(""))
            lines.append(Text("Rankings (Score | Load | Analysis):", style="bold underline"))

            # Sort by average score
            sorted_models = sorted(
                rankings.items(),
                key=lambda x: x[1].get("avg_score", 0),
                reverse=True
            )

            for model, data in sorted_models:
                model_short = MODEL_SHORT_NAMES.get(model, model)
                avg = data.get("avg_score", 0)
                passes = data.get("pass_count", 0)
                total = data.get("total_texts", 0)
                size = data.get("size_gb", "?")
                load_t = data.get("avg_load_time", 0)
                analysis_t = data.get("avg_analysis_time", 0)

                if passes == total and total > 0:
                    style = "green"
                elif passes > 0:
                    style = "yellow"
                else:
                    style = "red"

                time_str = f"{load_t:>5.1f}s | {analysis_t:>5.1f}s" if load_t or analysis_t else "    -  |     - "
                lines.append(Text(f"  {model_short:<14} {avg:.1f}/10 | {time_str}  ({passes}/{total})", style=style))

        return Panel(
            Group(*lines) if lines else Text("No summary yet"),
            title="Key Findings",
            border_style="green"
        )


class DetailsPanel(Static):
    """Shows details for the most recent result."""

    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[CharacterState] = None

    def update_state(self, state: CharacterState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting...", style="dim"), title="Latest Extraction")

        # Find most recent result
        latest_text = None
        latest_model = None
        latest_result = None

        for text_name in reversed(ALL_TEXTS):
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
            return Panel(Text("No results yet", style="dim"), title="Latest Extraction")

        lines = []
        model_short = MODEL_SHORT_NAMES.get(latest_model, latest_model)
        lines.append(Text(f"{latest_text} → {model_short}", style="bold cyan"))

        status = latest_result.get("status", "?")
        status_style = "green" if status == "PASS" else ("yellow" if status == "PARTIAL" else "red")
        lines.append(Text(f"Status: {status}", style=status_style))
        lines.append(Text(""))

        # Scores breakdown
        lines.append(Text("Scores:", style="underline"))
        lines.append(Text(f"  Recall:    {latest_result.get('recall', 0):.1f}/10"))
        lines.append(Text(f"  Precision: {latest_result.get('precision', 0):.1f}/10"))
        lines.append(Text(f"  Aliases:   {latest_result.get('alias_quality', 0):.1f}/10"))
        lines.append(Text(f"  Narrator:  {latest_result.get('narrator', 0):.1f}/10"))
        lines.append(Text(f"  Overall:   {latest_result.get('overall', 0):.1f}/10", style="bold"))
        lines.append(Text(""))

        # Timing information
        lines.append(Text("Timing:", style="underline"))
        load_t = latest_result.get("load_time_seconds", 0)
        analysis_t = latest_result.get("time_seconds", 0)
        total_t = latest_result.get("total_time_seconds", load_t + analysis_t)
        load_ok = latest_result.get("load_success", True)
        load_status = "✓" if load_ok else "✗"
        lines.append(Text(f"  Model Load:  {load_t:>6.1f}s {load_status}"))
        lines.append(Text(f"  Analysis:    {analysis_t:>6.1f}s"))
        lines.append(Text(f"  Total:       {total_t:>6.1f}s", style="bold"))
        lines.append(Text(""))

        # Characters found
        chars = latest_result.get("characters_found", [])
        if chars:
            lines.append(Text("Characters found:", style="underline"))
            for char in chars[:6]:
                lines.append(Text(f"  • {char}", style="dim"))
            if len(chars) > 6:
                lines.append(Text(f"  ... and {len(chars) - 6} more", style="dim"))

        # Missing characters
        missing = latest_result.get("required_missing", [])
        if missing:
            lines.append(Text(""))
            lines.append(Text("Missing:", style="red underline"))
            for char in missing:
                lines.append(Text(f"  ✗ {char}", style="red"))

        # Hallucinations
        halluc = latest_result.get("hallucinations", [])
        if halluc:
            lines.append(Text(""))
            lines.append(Text("Hallucinations:", style="red bold underline"))
            for char in halluc:
                lines.append(Text(f"  ⚠ {char}", style="red bold"))

        return Panel(
            Group(*lines),
            title="Latest Extraction",
            border_style="cyan"
        )


class CharacterMonitorApp(App):
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
        min-height: 18;
    }

    #details {
        height: auto;
        min-height: 18;
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
        yield DetailsPanel(id="details")
        yield Footer()

    def on_mount(self):
        """Start the refresh timer."""
        self.refresh_state()
        self.set_interval(2.0, self.refresh_state)

    def refresh_state(self):
        """Load state and update all widgets."""
        if self.paused:
            return

        state = CharacterState.load()

        # Update all panels
        self.query_one("#status", StatusPanel).update_state(state)
        self.query_one("#results", ResultsTable).update_state(state)
        self.query_one("#summary", SummaryPanel).update_state(state)
        self.query_one("#details", DetailsPanel).update_state(state)

    def action_refresh(self):
        """Manual refresh."""
        self.refresh_state()

    def action_toggle_pause(self):
        """Toggle auto-refresh."""
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.notify(f"Auto-refresh: {status}")


def main():
    app = CharacterMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
