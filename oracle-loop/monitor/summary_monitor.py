#!/usr/bin/env python3
"""
Summary Experiment Monitor (End-to-End)

Lightweight TUI monitor for the two-phase summary experiment.
Reads from summary_results.json as it's being updated.

Phase 1: Summary generation (each model generates summaries for all texts)
Phase 2: Character extraction scoring (fixed extraction model scores all summaries)

Usage:
    python oracle-loop/monitor/summary_monitor.py

Keybindings:
    q - Quit
    r - Refresh now
    p - Pause/resume auto-refresh
"""

import json
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Footer, Header
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.console import Group


RESULTS_FILE = Path(__file__).parent.parent / "state" / "summary_results.json"

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

ALL_TEXTS = [
    "cask_of_amontillado", "gift_of_the_magi", "monkeys_paw",
    "berenice", "masque_of_red_death", "i_have_no_mouth",
]

ALL_MODELS = [
    "qwen2.5:7b", "qwen2.5:14b", "qwen3:14b", "mistral-small3.2:24b",
    "qwen3:30b-instruct", "qwen2.5:32b", "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]


def get_recall(result: dict) -> float:
    """Get recall score, handling both old and new field names."""
    return result.get("recall", result.get("char_recall", 0))


def get_precision(result: dict) -> float:
    """Get precision score, handling both old and new field names."""
    return result.get("precision", result.get("char_precision", 0))


def get_hallucinations(result: dict) -> list:
    """Get hallucinations list, handling both old and new field names."""
    return result.get("hallucinations", result.get("forbidden_found", []))


def get_summary_time(result: dict) -> float:
    """Get summary generation time, handling both old and new field names."""
    return result.get("summary_time", result.get("time_seconds", 0))


def get_extraction_time(result: dict) -> float:
    """Get extraction time, handling both old and new field names."""
    return result.get("extraction_time", result.get("load_time_seconds", 0))


class SummaryState:
    """Parsed state from summary_results.json."""

    def __init__(self):
        self.experiment_date: str = ""
        self.experiment_timestamp: str = ""
        self.extraction_model: str = ""
        self.is_end_to_end: bool = False
        self.texts: dict = {}
        self.summary: dict = {}
        self.file_exists: bool = False
        self.last_error: str = ""

    @classmethod
    def load(cls) -> "SummaryState":
        state = cls()
        if not RESULTS_FILE.exists():
            state.last_error = f"Waiting for {RESULTS_FILE.name}..."
            return state

        try:
            state.file_exists = True
            with open(RESULTS_FILE) as f:
                data = json.load(f)
            state.experiment_date = data.get("experiment_date", "")
            state.experiment_timestamp = data.get("experiment_timestamp", "")
            state.extraction_model = data.get("extraction_model", "")
            state.is_end_to_end = "extraction_model" in data
            state.texts = data.get("texts", {})
            state.summary = data.get("summary", {})
        except Exception as e:
            state.last_error = f"Error: {e}"
        return state

    def get_progress(self) -> dict:
        """Get progress counters for both phases."""
        texts_loaded = len(self.texts)
        total_combos = len(ALL_TEXTS) * len(ALL_MODELS)

        # Count entries by status
        load_failed = 0
        scored = 0
        errors = 0
        pending = 0

        for text_name in ALL_TEXTS:
            if text_name not in self.texts:
                pending += len(ALL_MODELS)
                continue
            models = self.texts[text_name].get("models", {})
            for model in ALL_MODELS:
                if model not in models:
                    pending += 1
                    continue
                result = models[model]
                status = result.get("status", "")
                if status == "LOAD_FAILED":
                    load_failed += 1
                elif status == "ERROR" or "error" in result:
                    errors += 1
                elif "overall" in result:
                    scored += 1
                else:
                    pending += 1

        return {
            "texts_loaded": texts_loaded,
            "total_combos": total_combos,
            "load_failed": load_failed,
            "scored": scored,
            "errors": errors,
            "pending": pending,
        }

    def get_phase(self) -> str:
        """Determine which phase is active."""
        progress = self.get_progress()
        if not self.texts:
            return "waiting"
        if progress["scored"] == 0 and progress["load_failed"] == 0 and progress["errors"] == 0:
            return "loading_texts"
        if progress["scored"] > 0:
            non_failed = progress["total_combos"] - progress["load_failed"] - progress["errors"]
            if progress["scored"] >= non_failed:
                return "done"
            return "phase2"
        # Only LOAD_FAILED/ERROR entries exist, no scored yet
        return "phase1"


class StatusPanel(Static):
    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[SummaryState] = None

    def update_state(self, state: SummaryState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state:
            return Text("Loading...")
        state = self.state
        progress = state.get_progress()
        phase = state.get_phase()

        lines = []

        # Phase indicator
        if phase == "done":
            mode = Text("  COMPLETE ", style="bold green")
        elif phase == "phase2":
            mode = Text("  PHASE 2: SCORING ", style="bold yellow")
        elif phase == "phase1":
            mode = Text("  PHASE 1: GENERATING ", style="bold cyan")
        elif phase == "loading_texts":
            mode = Text("  LOADING TEXTS ", style="bold cyan")
        else:
            mode = Text("  WAITING ", style="dim")

        scored = progress["scored"]
        failed = progress["load_failed"]
        errors = progress["errors"]
        total = progress["total_combos"]
        done = scored + failed + errors

        lines.append(Text.assemble(mode, Text(f"  Scored: {scored}  Failed: {failed}  Errors: {errors}  Total: {done}/{total}")))

        if state.extraction_model:
            lines.append(Text(f"Extraction model: {MODEL_SHORT_NAMES.get(state.extraction_model, state.extraction_model)}", style="dim"))

        if state.last_error:
            lines.append(Text(state.last_error, style="red"))
        elif phase == "done":
            lines.append(Text("All experiments complete!", style="green"))

        if state.experiment_timestamp:
            lines.append(Text(f"Started: {state.experiment_timestamp}", style="dim"))

        title = "Summary Experiment (End-to-End)" if state.is_end_to_end else "Summary Experiment (Legacy)"
        return Panel(Group(*lines), title=title, border_style="blue")


class ResultsTable(Static):
    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[SummaryState] = None

    def update_state(self, state: SummaryState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting for results...", style="dim"), title="Results Matrix")

        table = Table(title="End-to-End Summary Results", expand=True)
        table.add_column("Model", style="cyan", width=14)
        for text_name in ALL_TEXTS:
            table.add_column(text_name[:6], justify="center", width=8)
        table.add_column("Avg", justify="right", width=6)
        table.add_column("Rcl", justify="right", width=5)
        table.add_column("Prc", justify="right", width=5)

        for model in ALL_MODELS:
            model_short = MODEL_SHORT_NAMES.get(model, model[:12])
            cells = [model_short]
            scores = []
            recall_scores = []
            precision_scores = []

            for text_name in ALL_TEXTS:
                if text_name not in self.state.texts:
                    cells.append(Text("-", style="dim"))
                    continue
                models = self.state.texts[text_name].get("models", {})
                if model not in models:
                    cells.append(Text("...", style="dim yellow"))
                    continue
                result = models[model]
                status = result.get("status", "")
                if status == "LOAD_FAILED":
                    cells.append(Text("LOAD", style="red dim"))
                elif "error" in result:
                    cells.append(Text("ERR", style="red"))
                elif "overall" in result:
                    overall = result["overall"]
                    scores.append(overall)
                    recall_scores.append(get_recall(result))
                    precision_scores.append(get_precision(result))
                    if status == "PASS":
                        cells.append(Text(f"{overall:.1f}+", style="green"))
                    elif status == "PARTIAL":
                        cells.append(Text(f"{overall:.1f}~", style="yellow"))
                    else:
                        cells.append(Text(f"{overall:.1f}-", style="red"))
                else:
                    cells.append(Text("?", style="dim"))

            if scores:
                avg = sum(scores) / len(scores)
                avg_rcl = sum(recall_scores) / len(recall_scores)
                avg_prc = sum(precision_scores) / len(precision_scores)
                cells.append(Text(f"{avg:.1f}", style="bold"))
                cells.append(Text(f"{avg_rcl:.0f}", style="cyan"))
                cells.append(Text(f"{avg_prc:.0f}", style="cyan"))
            else:
                cells.append(Text("-", style="dim"))
                cells.append(Text("-", style="dim"))
                cells.append(Text("-", style="dim"))

            table.add_row(*cells)
        return table


class SummaryPanel(Static):
    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[SummaryState] = None

    def update_state(self, state: SummaryState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.summary:
            return Panel(Text("Waiting for summary...", style="dim"), title="Key Findings")

        summary = self.state.summary
        lines = []

        extraction = summary.get("extraction_model", "")
        if extraction:
            lines.append(Text.assemble(Text("Extraction model: ", style="bold"), Text(MODEL_SHORT_NAMES.get(extraction, extraction), style="dim")))

        champion = summary.get("champion_model")
        if champion:
            lines.append(Text.assemble(Text("Best summary model: ", style="bold"), Text(MODEL_SHORT_NAMES.get(champion, champion), style="green bold")))

        perfect = summary.get("perfect_models", [])
        if perfect:
            lines.append(Text.assemble(Text("Perfect models: ", style="bold"), Text(", ".join(MODEL_SHORT_NAMES.get(m, m) for m in perfect), style="green")))

        rankings = summary.get("model_rankings", {})
        if rankings:
            lines.append(Text(""))
            lines.append(Text("Rankings (Score | Time 1 | Time 2 | Pass):", style="bold underline"))
            sorted_models = sorted(rankings.items(), key=lambda x: x[1].get("avg_score", 0), reverse=True)
            for model, data in sorted_models:
                model_short = MODEL_SHORT_NAMES.get(model, model)
                avg = data.get("avg_score", 0)
                passes = data.get("pass_count", 0)
                total = data.get("total_texts", 0)
                # Handle both old (avg_analysis_time/avg_load_time) and new (avg_summary_time/avg_extraction_time)
                t1 = data.get("avg_summary_time", data.get("avg_analysis_time", 0))
                t2 = data.get("avg_extraction_time", data.get("avg_load_time", 0))
                size = data.get("size_gb", "?")
                style = "green" if passes == total and total > 0 else ("yellow" if passes > 0 else "red")
                time_str = f"{t1:>6.1f}s | {t2:>6.1f}s" if t1 or t2 else "     -  |      - "
                lines.append(Text(f"  {model_short:<14} {avg:>4.1f} | {time_str} | {passes}/{total}  ({size}GB)", style=style))

        return Panel(Group(*lines) if lines else Text("No summary yet"), title="Key Findings", border_style="green")


class DetailsPanel(Static):
    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[SummaryState] = None

    def update_state(self, state: SummaryState):
        self.state = state
        self.refresh()

    def render(self):
        if not self.state or not self.state.texts:
            return Panel(Text("Waiting...", style="dim"), title="Latest Result")

        # Find the most recently scored result
        latest_text = latest_model = latest_result = None
        for text_name in reversed(ALL_TEXTS):
            if text_name not in self.state.texts:
                continue
            models = self.state.texts[text_name].get("models", {})
            for model in reversed(ALL_MODELS):
                if model not in models:
                    continue
                result = models[model]
                if "overall" in result:
                    latest_text, latest_model, latest_result = text_name, model, result
                    break
            if latest_result:
                break

        if not latest_result:
            return Panel(Text("No scored results yet", style="dim"), title="Latest Result")

        lines = []
        model_short = MODEL_SHORT_NAMES.get(latest_model, latest_model)
        lines.append(Text(f"{latest_text} | {model_short}", style="bold cyan"))

        status = latest_result.get("status", "?")
        style = "green" if status == "PASS" else ("yellow" if status == "PARTIAL" else "red")
        lines.append(Text(f"Status: {status}", style=style))
        lines.append(Text(""))

        lines.append(Text("Scores:", style="underline"))
        lines.append(Text(f"  Recall:        {get_recall(latest_result):>5.1f}/10"))
        lines.append(Text(f"  Precision:     {get_precision(latest_result):>5.1f}/10"))
        lines.append(Text(f"  Alias Quality: {latest_result.get('alias_quality', 0):>5.1f}/10"))
        # Show event coverage if present (old format)
        if "event_coverage" in latest_result:
            lines.append(Text(f"  Event Cov:     {latest_result['event_coverage']:>5.1f}/10"))
        lines.append(Text(f"  Overall:       {latest_result.get('overall', 0):>5.1f}/10", style="bold"))

        lines.append(Text(""))
        lines.append(Text("Timing:", style="underline"))
        sum_t = get_summary_time(latest_result)
        ext_t = get_extraction_time(latest_result)
        lines.append(Text(f"  Summary/Analysis: {sum_t:>6.1f}s"))
        lines.append(Text(f"  Extract/Load:     {ext_t:>6.1f}s"))
        lines.append(Text(f"  Total:            {sum_t + ext_t:>6.1f}s", style="bold"))

        # Summary quality info (new format only)
        num_sums = latest_result.get("num_summaries", 0)
        total_chars = latest_result.get("total_summary_chars", 0)
        if num_sums:
            lines.append(Text(""))
            lines.append(Text(f"  Summaries: {num_sums} ({total_chars:,} chars)", style="dim"))

        chars = latest_result.get("characters_found", [])
        if chars:
            lines.append(Text(""))
            lines.append(Text(f"Characters: {', '.join(chars)}", style="dim cyan"))

        missing = latest_result.get("required_missing", [])
        if missing:
            lines.append(Text(f"Missing: {', '.join(missing)}", style="red"))

        halls = get_hallucinations(latest_result)
        if halls:
            lines.append(Text(f"Hallucinations: {', '.join(halls)}", style="red bold"))

        return Panel(Group(*lines), title="Latest Result", border_style="cyan")


class SummaryMonitorApp(App):
    CSS = """
    Screen { layout: grid; grid-size: 2 3; grid-columns: 1fr 1fr; grid-rows: auto 1fr auto; }
    #status { column-span: 2; height: auto; max-height: 8; }
    #results { column-span: 2; height: 100%; }
    #summary { height: auto; min-height: 18; }
    #details { height: auto; min-height: 18; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh"), ("p", "toggle_pause", "Pause")]
    paused = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusPanel(id="status")
        yield ResultsTable(id="results")
        yield SummaryPanel(id="summary")
        yield DetailsPanel(id="details")
        yield Footer()

    def on_mount(self):
        self.refresh_state()
        self.set_interval(2.0, self.refresh_state)

    def refresh_state(self):
        if self.paused:
            return
        state = SummaryState.load()
        self.query_one("#status", StatusPanel).update_state(state)
        self.query_one("#results", ResultsTable).update_state(state)
        self.query_one("#summary", SummaryPanel).update_state(state)
        self.query_one("#details", DetailsPanel).update_state(state)

    def action_refresh(self):
        self.refresh_state()

    def action_toggle_pause(self):
        self.paused = not self.paused
        self.notify(f"Auto-refresh: {'PAUSED' if self.paused else 'RUNNING'}")


def main():
    SummaryMonitorApp().run()


if __name__ == "__main__":
    main()
