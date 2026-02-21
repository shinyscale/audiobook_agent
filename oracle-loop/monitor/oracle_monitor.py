"""
Oracle Loop Monitor TUI.
Real-time monitoring of the oracle loop progress using Textual.

Tabbed layout with Dashboard, Analysis, Claude, and History tabs.

Usage:
    python monitor/oracle_monitor.py [--dir DIR] [--interval INTERVAL]
    python -m monitor.oracle_monitor [--dir DIR] [--interval INTERVAL]
    python -m monitor [--dir DIR] [--interval INTERVAL]
"""

# Bootstrap package context when run directly (python monitor/oracle_monitor.py)
if __name__ == "__main__" and __package__ is None:
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    __package__ = "monitor"

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Input, TabbedContent, TabPane
from textual.binding import Binding
from textual.reactive import reactive

from .state import StateParser, OracleState
from .panels import (
    StatusBar,
    FooterInfo,
    ScorePanel,
    OverallProgress,
    ExperimentStatusPanel,
    OllamaActivityPanel,
    CompetitiveConsensusPanel,
    IdentityGraphPanel,
    ClaudeActivityPanel,
    ClaudeThinkingPanel,
    DiagnosticMatrixPanel,
    StderrPanel,
    IssuesPanel,
    CommitsPanel,
)


class OracleMonitorApp(App):
    """Main Oracle Loop Monitor application."""

    AUTO_FOCUS = None  # Don't auto-focus Input on startup

    CSS = """
    Screen {
        background: $surface;
    }

    StatusBar {
        height: auto;
        max-height: 8;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    TabbedContent {
        height: 1fr;
    }

    ContentSwitcher {
        height: 1fr;
    }

    TabPane {
        height: 1fr;
        padding: 0;
    }

    ScorePanel {
        height: 12;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    OverallProgress {
        height: 3;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ExperimentStatusPanel {
        height: auto;
        max-height: 18;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ExperimentStatusPanel.expanded {
        max-height: 50;
    }

    OllamaActivityPanel {
        height: auto;
        max-height: 9;
        border: solid $success;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    StderrPanel {
        height: auto;
        max-height: 10;
        border: solid $warning;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    IssuesPanel {
        height: auto;
        max-height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CommitsPanel {
        height: auto;
        max-height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CompetitiveConsensusPanel {
        height: auto;
        max-height: 12;
        border: solid $success;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CompetitiveConsensusPanel.expanded {
        max-height: 60;
    }

    ClaudeActivityPanel {
        height: auto;
        max-height: 10;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ClaudeThinkingPanel {
        height: auto;
        max-height: 15;
        border: solid $warning;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ClaudeThinkingPanel.expanded {
        max-height: 40;
    }

    IdentityGraphPanel {
        height: auto;
        max-height: 15;
        border: solid $success;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    IdentityGraphPanel.expanded {
        max-height: 40;
    }

    DiagnosticMatrixPanel {
        height: auto;
        max-height: 5;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    DiagnosticMatrixPanel.expanded {
        max-height: 60;
    }

    FooterInfo {
        height: 1;
        padding: 0 1;
    }

    #user-notes-input {
        margin: 0 0 1 0;
        border: solid $warning;
    }

    VerticalScroll {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("p", "toggle_pause", "Pause", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("n", "focus_notes", "Notes", show=True),
        Binding("t", "toggle_thinking", "Thinking", show=True),
        Binding("v", "toggle_votes", "Votes", show=True),
        Binding("e", "toggle_experiment", "Experiment", show=True),
        Binding("x", "export_thinking", "Export", show=True),
        Binding("g", "toggle_graph", "Graph", show=True),
        Binding("d", "toggle_diagnostic", "Diagnostic", show=True),
        Binding("1", "switch_tab('tab-dashboard')", "Dashboard", show=True),
        Binding("2", "switch_tab('tab-analysis')", "Analysis", show=True),
        Binding("3", "switch_tab('tab-claude')", "Claude", show=True),
        Binding("4", "switch_tab('tab-history')", "History", show=True),
    ]

    paused = reactive(False)
    thinking_expanded = reactive(False)
    votes_expanded = reactive(False)
    experiment_expanded = reactive(False)
    graph_expanded = reactive(False)
    diagnostic_expanded = reactive(False)

    def __init__(self, base_dir: Path = None, polling_interval: float = 2.0):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
        self.polling_interval = polling_interval
        self.parser = StateParser(self.base_dir)
        self.state = self.parser.get_state()
        self.title = "Oracle Loop Monitor"
        self.notes_file = self.base_dir / "state" / "USER_NOTES.md"

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar(self.state)

        with TabbedContent(initial="tab-dashboard"):
            with TabPane("Dashboard", id="tab-dashboard"):
                with VerticalScroll():
                    yield ScorePanel(self.state)
                    yield OverallProgress(self.state)
                    yield ExperimentStatusPanel(self.state, expanded=self.experiment_expanded)
                    yield IssuesPanel(self.state)
            with TabPane("Analysis", id="tab-analysis"):
                with VerticalScroll():
                    yield OllamaActivityPanel(self.state)
                    yield CompetitiveConsensusPanel(self.state, expanded=self.votes_expanded)
                    yield IdentityGraphPanel(self.state, expanded=self.graph_expanded)
            with TabPane("Claude", id="tab-claude"):
                with VerticalScroll():
                    yield ClaudeActivityPanel(self.state)
                    yield ClaudeThinkingPanel(self.state, expanded=self.thinking_expanded)
                    yield StderrPanel(self.state)
            with TabPane("History", id="tab-history"):
                with VerticalScroll():
                    yield DiagnosticMatrixPanel(self.state, expanded=self.diagnostic_expanded)
                    yield CommitsPanel(self.state)

        yield Input(placeholder="Send note to Claude (press Enter)...", id="user-notes-input")
        yield FooterInfo(self.state, self.polling_interval)
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user notes submission."""
        if event.input.id == "user-notes-input":
            content = event.value.strip()
            if content:
                self._save_notes(content)
                event.input.value = ""
                self.notify(f"Note sent to Claude", title="Saved")
            self.set_focus(None)  # Return focus to app for keybindings

    def _save_notes(self, content: str) -> None:
        """Save notes to USER_NOTES.md."""
        try:
            notes_content = f"""# User Notes for Oracle Loop

---

## Current Notes

{content}
"""
            self.notes_file.write_text(notes_content)
        except Exception:
            pass

    def on_mount(self):
        """Start polling when mounted."""
        self.set_interval(self.polling_interval, self._poll_state)

    def _poll_state(self):
        """Poll for state updates."""
        if self.paused:
            return

        self.state = self.parser.get_state()
        self._update_widgets()

    def _update_widgets(self):
        """Update all widgets with new state (all tabs, not just visible)."""
        try:
            self.query_one(StatusBar).update_state(self.state)
            self.query_one(ScorePanel).update_state(self.state)
            self.query_one(OverallProgress).update_state(self.state)
            self.query_one(ExperimentStatusPanel).update_state(self.state, expanded=self.experiment_expanded)
            self.query_one(IssuesPanel).update_state(self.state)
            self.query_one(OllamaActivityPanel).update_state(self.state)
            self.query_one(CompetitiveConsensusPanel).update_state(self.state, expanded=self.votes_expanded)
            self.query_one(IdentityGraphPanel).update_state(self.state, expanded=self.graph_expanded)
            self.query_one(ClaudeActivityPanel).update_state(self.state)
            self.query_one(ClaudeThinkingPanel).update_state(self.state, expanded=self.thinking_expanded)
            self.query_one(StderrPanel).update_state(self.state)
            self.query_one(DiagnosticMatrixPanel).update_state(self.state, expanded=self.diagnostic_expanded)
            self.query_one(CommitsPanel).update_state(self.state)
            self.query_one(FooterInfo).update_state(self.state)
        except Exception:
            # Widget may not be ready yet
            pass

    # --- Tab switching ---

    def action_switch_tab(self, tab_id: str):
        """Switch to the specified tab."""
        try:
            tabbed = self.query_one(TabbedContent)
            tabbed.active = tab_id
        except Exception:
            pass

    def _switch_to_tab(self, tab_id: str):
        """Switch to a tab (used by toggle actions to auto-switch)."""
        try:
            tabbed = self.query_one(TabbedContent)
            tabbed.active = tab_id
        except Exception:
            pass

    # --- Actions ---

    def action_toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            self.notify("Polling paused", severity="warning")
        else:
            self.notify("Polling resumed")
            self._poll_state()

    def action_refresh(self):
        """Manual refresh."""
        self._poll_state()
        self.notify("Refreshed")

    def action_focus_notes(self):
        """Focus the notes input."""
        try:
            notes_input = self.query_one("#user-notes-input", Input)
            notes_input.focus()
        except Exception:
            pass

    def action_toggle_thinking(self):
        """Toggle thinking panel expanded/collapsed. Auto-switches to Claude tab."""
        self._switch_to_tab("tab-claude")
        self.thinking_expanded = not self.thinking_expanded
        try:
            thinking_panel = self.query_one(ClaudeThinkingPanel)
            if self.thinking_expanded:
                thinking_panel.add_class("expanded")
            else:
                thinking_panel.remove_class("expanded")
            thinking_panel.update_state(self.state, expanded=self.thinking_expanded)
        except Exception:
            pass

    def action_toggle_votes(self):
        """Toggle votes panel expanded/collapsed. Auto-switches to Analysis tab."""
        self._switch_to_tab("tab-analysis")
        self.votes_expanded = not self.votes_expanded
        try:
            votes_panel = self.query_one(CompetitiveConsensusPanel)
            if self.votes_expanded:
                votes_panel.add_class("expanded")
            else:
                votes_panel.remove_class("expanded")
            votes_panel.update_state(self.state, expanded=self.votes_expanded)
        except Exception:
            pass

    def action_toggle_experiment(self):
        """Toggle experiment panel expanded/collapsed. Auto-switches to Dashboard tab."""
        self._switch_to_tab("tab-dashboard")
        self.experiment_expanded = not self.experiment_expanded
        try:
            experiment_panel = self.query_one(ExperimentStatusPanel)
            if self.experiment_expanded:
                experiment_panel.add_class("expanded")
            else:
                experiment_panel.remove_class("expanded")
            experiment_panel.update_state(self.state, expanded=self.experiment_expanded)
        except Exception:
            pass

    def action_toggle_graph(self):
        """Toggle identity graph panel expanded/collapsed. Auto-switches to Analysis tab."""
        self._switch_to_tab("tab-analysis")
        self.graph_expanded = not self.graph_expanded
        try:
            graph_panel = self.query_one(IdentityGraphPanel)
            if self.graph_expanded:
                graph_panel.add_class("expanded")
            else:
                graph_panel.remove_class("expanded")
            graph_panel.update_state(self.state, expanded=self.graph_expanded)
        except Exception:
            pass

    def action_toggle_diagnostic(self):
        """Toggle diagnostic matrix panel expanded/collapsed. Auto-switches to History tab."""
        self._switch_to_tab("tab-history")
        self.diagnostic_expanded = not self.diagnostic_expanded
        try:
            diag_panel = self.query_one(DiagnosticMatrixPanel)
            if self.diagnostic_expanded:
                diag_panel.add_class("expanded")
            else:
                diag_panel.remove_class("expanded")
            diag_panel.update_state(self.state, expanded=self.diagnostic_expanded)
        except Exception:
            pass

    def action_export_thinking(self):
        """Export full thinking text to file."""
        if not self.state.thinking_text:
            self.notify("No thinking text to export", severity="warning")
            return

        export_file = self.base_dir / "state" / "CLAUDE_THINKING_EXPORT.txt"

        try:
            # Create export with timestamp and all thinking blocks
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            content_parts = [
                f"# Claude Thinking Export",
                f"# Exported: {timestamp}",
                f"# Text: {self.state.text_name}",
                f"# Attempt: {self.state.attempt}",
                f"# Total blocks: {len(self.state.thinking_text)}",
                "",
                "=" * 80,
                "",
            ]

            for i, thinking in enumerate(self.state.thinking_text, 1):
                content_parts.append(f"## Block {i}/{len(self.state.thinking_text)}")
                content_parts.append("")
                content_parts.append(thinking)
                content_parts.append("")
                content_parts.append("-" * 80)
                content_parts.append("")

            export_file.write_text("\n".join(content_parts), encoding="utf-8")
            self.notify(f"Exported to {export_file.name}", title="Export Complete")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")


def run_oracle_monitor(base_dir: Path = None, polling_interval: float = 2.0):
    """Launch the Oracle Loop Monitor TUI."""
    app = OracleMonitorApp(base_dir=base_dir, polling_interval=polling_interval)
    app.run()


def main():
    """CLI entry point for oracle-monitor command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor oracle loop progress in real-time"
    )
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        default=Path.cwd(),
        help="Base directory containing EVALUATION_STATE.md, manifest.json, logs/"
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)"
    )

    args = parser.parse_args()
    # Resolve to absolute path before Textual changes working directory
    base_dir = args.dir.resolve()
    run_oracle_monitor(base_dir=base_dir, polling_interval=args.interval)


if __name__ == "__main__":
    main()
