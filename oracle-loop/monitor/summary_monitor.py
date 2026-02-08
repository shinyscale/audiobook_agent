#!/usr/bin/env python3
"""
Summary Experiment Monitor

Lightweight TUI monitor for summary experiments.
Reads from summary_results.json as it's being updated.

Supports two formats:
  - Legacy: direct character-list scoring (old experiment)
  - End-to-End: generate summaries, then score via fixed extraction model

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
    "gatsby",
    "frankenstein",
    "dracula",
]

TEXT_SHORT_NAMES = {
    "gatsby": "gatsby",
    "frankenstein": "franken",
    "dracula": "dracula",
}

ALL_MODELS = [
    "qwen2.5:7b", "qwen2.5:14b", "qwen3:14b", "mistral-small3.2:24b",
    "qwen3:30b-instruct", "qwen2.5:32b", "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]


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

    def get_result_field(self, result: dict, new_key: str, old_key: str, default=0):
        """Get a field from a result dict, trying new key first, then old."""
        if self.is_end_to_end:
            return result.get(new_key, default)
        return result.get(old_key, result.get(new_key, default))

    def get_progress(self) -> dict:
        """Get progress counters."""
        total_combos = len(ALL_TEXTS) * len(ALL_MODELS)
        load_failed = 0
        summarized = 0
        scored = 0
        errors = 0

        for text_name in ALL_TEXTS:
            if text_name not in self.texts:
                continue
            models = self.texts[text_name].get("models", {})
            for model in ALL_MODELS:
                if model not in models:
                    continue
                result = models[model]
                status = result.get("status", "")
                if status == "LOAD_FAILED":
                    load_failed += 1
                elif status == "ERROR" or "error" in result:
                    errors += 1
                elif status == "SUMMARIZED":
                    summarized += 1
                elif "overall" in result:
                    scored += 1

        return {
            "total_combos": total_combos,
            "load_failed": load_failed,
            "summarized": summarized,
            "scored": scored,
            "errors": errors,
        }

    def get_phase(self) -> str:
        """Determine current status."""
        progress = self.get_progress()
        if not self.texts:
            return "waiting"
        activity = progress["scored"] + progress["summarized"] + progress["load_failed"] + progress["errors"]
        if activity == 0:
            return "loading_texts"
        non_failed = progress["total_combos"] - progress["load_failed"] - progress["errors"]
        if non_failed > 0 and progress["scored"] >= non_failed:
            return "done"
        if self.is_end_to_end:
            if progress["scored"] > 0:
                return "phase2"
            return "phase1"
        return "running"

    def get_current_model(self) -> Optional[str]:
        """Infer which model is currently being processed.

        Looks for the first model in order that has some but not all texts done.
        """
        for model in ALL_MODELS:
            has_any = False
            has_all = True
            for text_name in ALL_TEXTS:
                if text_name not in self.texts:
                    has_all = False
                    continue
                models = self.texts[text_name].get("models", {})
                if model in models:
                    has_any = True
                else:
                    has_all = False
            if has_any and not has_all:
                return model
        # Check for first model with no entries at all
        for model in ALL_MODELS:
            has_any = False
            for text_name in ALL_TEXTS:
                if text_name in self.texts:
                    models = self.texts[text_name].get("models", {})
                    if model in models:
                        has_any = True
                        break
            if not has_any:
                return model
        return None

    def find_latest_entry(self) -> Optional[tuple[str, str, dict]]:
        """Find the most recently added result entry (any status).

        Walks models in order, then texts in order, returns the last
        entry that exists. This approximates "most recent" since the
        experiment writes results sequentially.
        """
        latest = None
        for model in ALL_MODELS:
            for text_name in ALL_TEXTS:
                if text_name not in self.texts:
                    continue
                models = self.texts[text_name].get("models", {})
                if model in models:
                    latest = (text_name, model, models[model])
        return latest


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

        if phase == "done":
            mode = Text("COMPLETE", style="bold green")
        elif phase == "phase2":
            mode = Text("PHASE 2: EXTRACTING + SCORING", style="bold yellow")
        elif phase == "phase1":
            mode = Text("PHASE 1: GENERATING SUMMARIES", style="bold cyan")
        elif phase == "running":
            mode = Text("RUNNING", style="bold yellow")
        elif phase == "loading_texts":
            mode = Text("LOADING TEXTS", style="bold cyan")
        else:
            mode = Text("WAITING", style="dim")

        lines.append(mode)

        summarized = progress["summarized"]
        scored = progress["scored"]
        failed = progress["load_failed"]
        errors = progress["errors"]
        total = progress["total_combos"]

        if phase == "phase1":
            scorable = total - failed - errors
            lines.append(Text(f"Summaries generated: {summarized}/{scorable}"))
        elif phase in ("phase2", "done"):
            scorable = total - failed - errors
            parts = [f"Scored: {scored}/{scorable}"]
            if summarized:
                parts.append(f"Awaiting scoring: {summarized}")
            lines.append(Text("  ".join(parts)))
        else:
            parts = []
            if summarized:
                parts.append(f"Summaries: {summarized}")
            if scored:
                parts.append(f"Scored: {scored}")
            if failed:
                parts.append(f"Failed: {failed}")
            if errors:
                parts.append(f"Errors: {errors}")
            if parts:
                lines.append(Text("  ".join(parts)))

        # Show current model being worked on
        current = state.get_current_model()
        if current and phase in ("phase1", "running"):
            current_short = MODEL_SHORT_NAMES.get(current, current)
            lines.append(Text(f"Current model: {current_short}", style="cyan"))

        if state.is_end_to_end and state.extraction_model:
            ext_short = MODEL_SHORT_NAMES.get(state.extraction_model, state.extraction_model)
            lines.append(Text(f"Extraction model: {ext_short} (fixed)", style="dim"))
        elif not state.is_end_to_end and state.file_exists:
            lines.append(Text("STALE DATA - old experiment format (run new experiment to refresh)", style="bold red"))

        if state.last_error:
            lines.append(Text(state.last_error, style="red"))

        if state.experiment_timestamp:
            lines.append(Text(f"Started: {state.experiment_timestamp}", style="dim"))

        title = "Summary Experiment — Tier 2 (Novels)"
        if state.is_end_to_end:
            title += " — End-to-End"
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
            return Panel(Text("Waiting for results...", style="dim"), title="Results")

        state = self.state
        phase = state.get_phase()

        if state.is_end_to_end:
            if phase == "phase1":
                title = "Phase 1: Summary Generation Time (seconds)"
            else:
                title = "Results: Which summary model helps character extraction most? (0-10)"
        else:
            title = "Results: Summary char-list quality (0-10, OLD scoring - run new experiment)"

        table = Table(title=title, expand=True)
        table.add_column("Summary Model", style="cyan", width=14)

        for text_name in ALL_TEXTS:
            short = TEXT_SHORT_NAMES.get(text_name, text_name[:8])
            table.add_column(short, justify="center", width=12)

        table.add_column("AVG", justify="right", width=6, style="bold")

        for model in ALL_MODELS:
            model_short = MODEL_SHORT_NAMES.get(model, model[:12])
            cells = [model_short]
            scores = []       # for scored results (0-10)
            gen_times = []     # for SUMMARIZED results (seconds)

            for text_name in ALL_TEXTS:
                if text_name not in state.texts:
                    cells.append(Text("-", style="dim"))
                    continue
                models = state.texts[text_name].get("models", {})
                if model not in models:
                    cells.append(Text("...", style="dim yellow"))
                    continue
                result = models[model]
                status = result.get("status", "")
                if status == "LOAD_FAILED":
                    cells.append(Text("FAIL", style="red dim"))
                elif "error" in result:
                    cells.append(Text("ERR", style="red"))
                elif status == "SUMMARIZED":
                    # Show generation time + chapter count
                    t = result.get("summary_time", 0)
                    n = result.get("num_summaries", 0)
                    gen_times.append(t)
                    label = f"{t:.0f}s {n}ch" if n else f"{t:.0f}s"
                    cells.append(Text(label, style="cyan"))
                elif "overall" in result:
                    overall = result["overall"]
                    scores.append(overall)
                    # Show R(ecall)/A(lias) breakdown alongside score
                    r = state.get_result_field(result, "recall", "char_recall", 0)
                    a = result.get("alias_quality", 0)
                    detail = f"{overall:.1f} R{r:.0f}A{a:.0f}"
                    if status == "PASS":
                        cells.append(Text(detail, style="green"))
                    elif status == "PARTIAL":
                        cells.append(Text(detail, style="yellow"))
                    else:
                        cells.append(Text(detail, style="red"))
                else:
                    cells.append(Text("?", style="dim"))

            # AVG column: show score average if available, else time average
            if scores:
                avg = sum(scores) / len(scores)
                cells.append(Text(f"{avg:.1f}", style="bold white"))
            elif gen_times:
                avg_t = sum(gen_times) / len(gen_times)
                cells.append(Text(f"{avg_t:.0f}s", style="cyan"))
            else:
                cells.append(Text("-", style="dim"))

            table.add_row(*cells)

        # Footer row: text metadata (word count, expected chars)
        meta_cells = [Text("chars/expect", style="dim italic")]
        for text_name in ALL_TEXTS:
            if text_name in state.texts:
                text_data = state.texts[text_name]
                char_count = text_data.get("char_count", 0)
                expected = text_data.get("expected", {})
                n_required = len(expected.get("required", []))
                if char_count:
                    words = char_count // 5  # rough word estimate
                    label = f"{words // 1000}kw {n_required}exp"
                else:
                    label = f"{n_required}exp"
                meta_cells.append(Text(label, style="dim"))
            else:
                meta_cells.append(Text("-", style="dim"))
        meta_cells.append(Text("", style="dim"))
        table.add_row(*meta_cells, end_section=False)

        return table


class RankingsPanel(Static):
    def __init__(self, id: str = None):
        super().__init__(id=id)
        self.state: Optional[SummaryState] = None

    def update_state(self, state: SummaryState):
        self.state = state
        self.refresh()

    def render(self):
        state = self.state
        if not state:
            return Panel(Text("Waiting...", style="dim"), title="Rankings")

        phase = state.get_phase()

        # During Phase 1, show generation time summary instead of empty rankings
        if phase == "phase1" and state.is_end_to_end:
            return self._render_phase1_summary()

        if not state.summary:
            return Panel(Text("Waiting for Phase 2 scoring...", style="dim"), title="Rankings")

        return self._render_rankings()

    def _render_phase1_summary(self):
        """Show per-model summary generation stats during Phase 1."""
        state = self.state
        lines = []
        lines.append(Text("Summary generation progress by model:", style="bold underline"))
        lines.append(Text(""))
        lines.append(Text(f"{'Model':<14}  {'Texts':>5}  {'Avg Time':>8}  {'Chapters':>8}  {'Total Chars':>11}", style="bold"))

        for model in ALL_MODELS:
            model_short = MODEL_SHORT_NAMES.get(model, model[:12])
            times = []
            total_chars = 0
            total_chapters = 0
            status = None

            for text_name in ALL_TEXTS:
                if text_name not in state.texts:
                    continue
                models = state.texts[text_name].get("models", {})
                if model not in models:
                    continue
                result = models[model]
                s = result.get("status", "")
                if s == "SUMMARIZED":
                    times.append(result.get("summary_time", 0))
                    total_chars += result.get("total_summary_chars", 0)
                    total_chapters += result.get("num_summaries", 0)
                elif s == "LOAD_FAILED":
                    status = "FAIL"

            if status == "FAIL":
                lines.append(Text(f"{model_short:<14}  {'LOAD FAILED':>5}", style="red dim"))
            elif times:
                avg_t = sum(times) / len(times)
                style = "cyan"
                lines.append(Text(
                    f"{model_short:<14}  {len(times):>5}  {avg_t:>7.0f}s  {total_chapters:>8}  {total_chars:>11,}",
                    style=style,
                ))
            # Skip models with no entries yet (still waiting)

        return Panel(Group(*lines) if lines else Text("Waiting..."), title="Phase 1 Progress", border_style="cyan")

    def _render_rankings(self):
        """Show scored rankings (Phase 2 / done)."""
        state = self.state
        summary = state.summary
        lines = []

        champion = summary.get("champion_model")
        if champion:
            champ_short = MODEL_SHORT_NAMES.get(champion, champion)
            lines.append(Text.assemble(
                Text("BEST: ", style="bold"),
                Text(champ_short, style="green bold"),
            ))

        perfect = summary.get("perfect_models", [])
        if perfect:
            lines.append(Text.assemble(
                Text("Perfect (all PASS): ", style="bold"),
                Text(", ".join(MODEL_SHORT_NAMES.get(m, m) for m in perfect), style="green"),
            ))

        rankings = summary.get("model_rankings", {})
        if rankings:
            lines.append(Text(""))

            if state.is_end_to_end:
                lines.append(Text(f"{'':>2} {'Model':<14} {'Score':>5}  {'R':>2} {'P':>2} {'A':>2}  {'SumGen':>6}  {'Pass':>4}", style="bold underline"))
            else:
                lines.append(Text(f"{'':>2} {'Model':<14} {'Score':>5}  {'Analys':>6}  {'Load':>7}  {'Pass':>4}", style="bold underline"))

            sorted_models = sorted(rankings.items(), key=lambda x: x[1].get("avg_score", 0), reverse=True)
            for i, (model, data) in enumerate(sorted_models):
                model_short = MODEL_SHORT_NAMES.get(model, model)
                avg = data.get("avg_score", 0)
                passes = data.get("pass_count", 0)
                total = data.get("total_texts", 0)

                if passes == total and total > 0:
                    style = "green"
                elif passes > 0:
                    style = "yellow"
                else:
                    style = "red"

                rank = f"#{i+1}"

                if state.is_end_to_end:
                    t1 = data.get("avg_summary_time", 0)
                    # Compute avg R/P/A across texts for this model
                    r_vals, p_vals, a_vals = [], [], []
                    for text_name in ALL_TEXTS:
                        if text_name not in state.texts:
                            continue
                        models = state.texts[text_name].get("models", {})
                        if model not in models:
                            continue
                        result = models[model]
                        if "overall" in result:
                            r_vals.append(state.get_result_field(result, "recall", "char_recall", 0))
                            p_vals.append(state.get_result_field(result, "precision", "char_precision", 0))
                            a_vals.append(result.get("alias_quality", 0))
                    avg_r = sum(r_vals) / len(r_vals) if r_vals else 0
                    avg_p = sum(p_vals) / len(p_vals) if p_vals else 0
                    avg_a = sum(a_vals) / len(a_vals) if a_vals else 0
                    t1_s = f"{t1:>5.0f}s" if t1 else "    -"
                    lines.append(Text(
                        f"{rank:>2} {model_short:<14} {avg:>5.1f}  {avg_r:>2.0f} {avg_p:>2.0f} {avg_a:>2.0f}  {t1_s}   {passes}/{total}",
                        style=style,
                    ))
                else:
                    t1 = data.get("avg_analysis_time", 0)
                    t2 = data.get("avg_load_time", 0)
                    t1_s = f"{t1:>5.0f}s" if t1 else "    -"
                    t2_s = f"{t2:>6.0f}s" if t2 else "     -"
                    lines.append(Text(
                        f"{rank:>2} {model_short:<14} {avg:>5.1f}  {t1_s}  {t2_s}   {passes}/{total}",
                        style=style,
                    ))

        if not lines:
            lines.append(Text("No rankings yet", style="dim"))

        return Panel(Group(*lines), title="Rankings", border_style="green")


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

        state = self.state

        # Find the latest entry - prefer scored, fall back to any
        latest = state.find_latest_entry()
        if not latest:
            return Panel(Text("No results yet", style="dim"), title="Latest Result")

        latest_text, latest_model, latest_result = latest
        status = latest_result.get("status", "?")

        lines = []
        model_short = MODEL_SHORT_NAMES.get(latest_model, latest_model)
        lines.append(Text(f"{latest_text} | {model_short}", style="bold cyan"))

        if status == "SUMMARIZED":
            # Phase 1 detail view
            lines.append(Text(f"Status: SUMMARIZED (awaiting extraction)", style="cyan"))
            lines.append(Text(""))
            t = latest_result.get("summary_time", 0)
            n = latest_result.get("num_summaries", 0)
            chars = latest_result.get("total_summary_chars", 0)
            lines.append(Text(f"  Generation time: {t:.1f}s"))
            lines.append(Text(f"  Summaries: {n}"))
            lines.append(Text(f"  Total chars: {chars:,}"))
            if n > 0:
                lines.append(Text(f"  Avg chars/summary: {chars // n:,}"))

        elif status == "LOAD_FAILED":
            lines.append(Text(f"Status: LOAD FAILED", style="red"))
            t = latest_result.get("load_time_seconds", 0)
            lines.append(Text(f"  Load time: {t:.1f}s"))

        elif "overall" in latest_result:
            # Scored result detail view
            style = "green" if status == "PASS" else ("yellow" if status == "PARTIAL" else "red")
            lines.append(Text(f"Status: {status}  Overall: {latest_result.get('overall', 0):.1f}/10", style=style))
            lines.append(Text(""))

            recall = state.get_result_field(latest_result, "recall", "char_recall")
            precision = state.get_result_field(latest_result, "precision", "char_precision")
            alias = latest_result.get("alias_quality", 0)

            lines.append(Text(f"  Recall:    {recall:>5.1f}/10  (found required characters?)"))
            lines.append(Text(f"  Precision: {precision:>5.1f}/10  (no hallucinated characters?)"))
            lines.append(Text(f"  Alias:     {alias:>5.1f}/10  (aliases grouped correctly?)"))
            if "event_coverage" in latest_result:
                lines.append(Text(f"  Events:    {latest_result['event_coverage']:>5.1f}/10  (key plot events mentioned?)"))

            # Timing info
            sum_t = latest_result.get("summary_time", 0)
            ext_t = latest_result.get("extraction_time", 0)
            n_ch = latest_result.get("num_summaries", 0)
            if sum_t or ext_t:
                timing_parts = []
                if sum_t:
                    timing_parts.append(f"Summary: {sum_t:.0f}s")
                if ext_t:
                    timing_parts.append(f"Extract: {ext_t:.0f}s")
                if n_ch:
                    timing_parts.append(f"Chapters: {n_ch}")
                lines.append(Text(f"  {' | '.join(timing_parts)}", style="dim"))

            lines.append(Text(""))
            chars = latest_result.get("characters_found", [])
            if chars:
                lines.append(Text(f"Found: {', '.join(chars)}", style="cyan"))
            missing = latest_result.get("required_missing", [])
            if missing:
                lines.append(Text(f"Missing: {', '.join(missing)}", style="red"))
            halls = latest_result.get("hallucinations", latest_result.get("forbidden_found", []))
            if halls:
                lines.append(Text(f"Hallucinated: {', '.join(halls)}", style="red bold"))

        elif "error" in latest_result:
            lines.append(Text(f"Status: ERROR", style="red"))
            lines.append(Text(f"  {latest_result['error'][:200]}", style="red dim"))

        return Panel(Group(*lines), title="Latest Result", border_style="cyan")


class SummaryMonitorApp(App):
    CSS = """
    Screen { layout: grid; grid-size: 2 3; grid-columns: 1fr 1fr; grid-rows: auto 1fr auto; }
    #status { column-span: 2; height: auto; max-height: 9; }
    #results { column-span: 2; height: 100%; }
    #rankings { height: auto; min-height: 18; }
    #details { height: auto; min-height: 18; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh"), ("p", "toggle_pause", "Pause")]
    paused = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusPanel(id="status")
        yield ResultsTable(id="results")
        yield RankingsPanel(id="rankings")
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
        self.query_one("#rankings", RankingsPanel).update_state(state)
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
