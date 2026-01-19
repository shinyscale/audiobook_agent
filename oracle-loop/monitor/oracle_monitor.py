"""
Oracle Loop Monitor TUI.
Real-time monitoring of the oracle loop progress using Textual.
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text


@dataclass
class Score:
    """Individual category score."""
    name: str
    value: float
    max_value: float = 10.0
    passing: bool = True


@dataclass
class Issue:
    """An issue from evaluation."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str


@dataclass
class Commit:
    """A git commit."""
    hash: str
    message: str


@dataclass
class OracleState:
    """Combined state from all data sources."""
    # From EVALUATION_STATE.md
    text_name: str = ""
    attempt: int = 0
    max_attempts: int = 5
    phase: str = "unknown"
    threshold: float = 8.0

    # Scores
    structure_score: Optional[float] = None
    characters_score: Optional[float] = None
    profiles_score: Optional[float] = None
    summaries_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    presentation_score: Optional[float] = None
    overall_score: Optional[float] = None

    # Issues
    issues: list[Issue] = field(default_factory=list)

    # From manifest.json
    total_texts: int = 0
    completed_texts: int = 0

    # From logs / progress file
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    current_stage: str = ""  # Current analysis stage (e.g., "Chapter Detection")

    # Recent commits
    commits: list[Commit] = field(default_factory=list)

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)

    # Loop status
    loop_running: bool = False


class StateParser:
    """Parse state from various data sources."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.cwd()

    def parse_evaluation_state(self) -> dict:
        """Parse EVALUATION_STATE.md for current text, attempt, phase, scores."""
        state_file = self.base_dir / "EVALUATION_STATE.md"
        if not state_file.exists():
            return {}

        content = state_file.read_text()
        result = {}

        # Parse text name
        match = re.search(r'\*\*Name:\*\*\s*(\w+)', content)
        if match:
            result['text_name'] = match.group(1)

        # Parse attempt
        match = re.search(r'\*\*Attempt:\*\*\s*(\d+)', content)
        if match:
            result['attempt'] = int(match.group(1))

        # Parse phase
        match = re.search(r'\*\*Phase:\*\*\s*(\w+)', content)
        if match:
            result['phase'] = match.group(1)

        # Parse threshold
        match = re.search(r'threshold:\s*([\d.]+)', content)
        if match:
            result['threshold'] = float(match.group(1))

        # Parse scores - look for patterns like "Structure Detection: 10/10"
        score_patterns = [
            (r'Structure(?:\s+Detection)?:\s*([\d.]+)/10', 'structure_score'),
            (r'Character(?:\s+Extraction)?:\s*([\d.]+)/10', 'characters_score'),
            (r'(?:Character\s+)?Profiles?:\s*([\d.]+)/10', 'profiles_score'),
            (r'(?:Chapter\s+)?Summar(?:y|ies):\s*([\d.]+)/10', 'summaries_score'),
            (r'Pronunciation(?:\s+Guide)?:\s*([\d.]+)/10', 'pronunciation_score'),
            (r'(?:HTML\s+)?Presentation:\s*([\d.]+)/10', 'presentation_score'),
        ]

        for pattern, key in score_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result[key] = float(match.group(1))

        # Parse overall score
        match = re.search(r'\*\*Overall:\s*([\d.]+)/10', content)
        if match:
            result['overall_score'] = float(match.group(1))

        # Parse model from configuration (e.g., "- Structure: qwen3:30b-instruct")
        model_match = re.search(r'-\s*(?:Structure|Characters|Summaries):\s*(\S+)', content)
        if model_match:
            result['model'] = model_match.group(1)

        # Parse issues
        issues = []
        # Look for issue patterns: "CRITICAL | description" or "### CRITICAL" followed by numbered items
        issue_pattern = re.compile(r'^\d+\.\s*\*\*(.+?)\*\*', re.MULTILINE)

        # Find sections for each severity
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            section_match = re.search(rf'###\s*{severity}.*?(?=###|\Z)', content, re.DOTALL | re.IGNORECASE)
            if section_match:
                section = section_match.group(0)
                for item_match in issue_pattern.finditer(section):
                    issues.append(Issue(severity=severity, description=item_match.group(1)))

        result['issues'] = issues

        return result

    def parse_manifest(self) -> dict:
        """Parse manifest.json for overall progress."""
        manifest_file = self.base_dir / "manifest.json"
        if not manifest_file.exists():
            return {}

        try:
            with open(manifest_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

        texts = data.get('texts', [])
        total = len(texts)
        completed = sum(1 for t in texts if t.get('complete', False))
        threshold = data.get('quality_threshold', 8.0)

        return {
            'total_texts': total,
            'completed_texts': completed,
            'threshold': threshold,
        }

    def parse_git_log(self, count: int = 5) -> list[Commit]:
        """Get recent git commits."""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', f'-{count}'],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
                timeout=5
            )
            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        commits.append(Commit(hash=parts[0], message=parts[1]))
            return commits
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return []

    def parse_progress_file(self) -> dict:
        """Parse PROGRESS.json for current analysis stage."""
        output_dir = self.base_dir / "output"

        # If output dir doesn't exist, check parent directory (oracle-loop structure)
        if not output_dir.exists():
            parent_output = self.base_dir.parent / "output"
            if parent_output.exists():
                output_dir = parent_output

        progress_file = output_dir / "PROGRESS.json"
        if not progress_file.exists():
            return {}

        try:
            with open(progress_file) as f:
                data = json.load(f)
            return {
                'current_stage': data.get('stage', ''),
                'stage_model': data.get('model', ''),
            }
        except (json.JSONDecodeError, IOError):
            return {}

    def parse_analysis_output(self, text_name: str) -> dict:
        """Parse analysis.json from output directory for token usage."""
        output_dir = self.base_dir / "output" / text_name

        # If output dir doesn't exist, check parent directory (oracle-loop structure)
        if not output_dir.exists():
            parent_output = self.base_dir.parent / "output" / text_name
            if parent_output.exists():
                output_dir = parent_output

        analysis_file = output_dir / "analysis.json"

        if not analysis_file.exists():
            return {}

        try:
            with open(analysis_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

        profiling = data.get('_profiling', {})
        totals = profiling.get('totals', {})
        stages = profiling.get('stages', [])

        # Sum input/output tokens from stages
        input_tokens = sum(s.get('tokens_prompt', 0) for s in stages)
        output_tokens = sum(s.get('tokens_completion', 0) for s in stages)

        # Get model from first stage that has one
        model = ""
        for stage in stages:
            if stage.get('model_used'):
                model = stage['model_used']
                break

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'llm_calls': totals.get('llm_calls', 0),
        }

    def parse_latest_log(self) -> dict:
        """Parse latest log file for model and token usage (Claude Code logs)."""
        logs_dir = self.base_dir / "logs"

        # If logs dir doesn't exist, check parent directory (oracle-loop structure)
        if not logs_dir.exists():
            parent_logs = self.base_dir.parent / "logs"
            if parent_logs.exists():
                logs_dir = parent_logs

        if not logs_dir.exists():
            return {}

        # Find latest iteration log
        log_files = sorted(logs_dir.glob("iteration_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            return {}

        latest_log = log_files[0]
        model = ""
        input_tokens = 0
        output_tokens = 0

        try:
            with open(latest_log) as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('type') == 'assistant':
                            msg = data.get('message', {})
                            if msg.get('model'):
                                model = msg['model']
                            usage = msg.get('usage', {})
                            input_tokens += usage.get('input_tokens', 0)
                            input_tokens += usage.get('cache_read_input_tokens', 0)
                            input_tokens += usage.get('cache_creation_input_tokens', 0)
                            output_tokens += usage.get('output_tokens', 0)
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        }

    def check_loop_running(self) -> bool:
        """Check if oracle-loop.sh is currently running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'oracle-loop.sh'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_state(self) -> OracleState:
        """Get combined state from all sources."""
        state = OracleState()

        # Parse evaluation state
        eval_state = self.parse_evaluation_state()
        state.text_name = eval_state.get('text_name', '')
        state.attempt = eval_state.get('attempt', 0)
        state.phase = eval_state.get('phase', 'unknown')
        state.threshold = eval_state.get('threshold', 8.0)
        state.structure_score = eval_state.get('structure_score')
        state.characters_score = eval_state.get('characters_score')
        state.profiles_score = eval_state.get('profiles_score')
        state.summaries_score = eval_state.get('summaries_score')
        state.pronunciation_score = eval_state.get('pronunciation_score')
        state.presentation_score = eval_state.get('presentation_score')
        state.overall_score = eval_state.get('overall_score')
        state.issues = eval_state.get('issues', [])

        # Parse manifest
        manifest = self.parse_manifest()
        state.total_texts = manifest.get('total_texts', 0)
        state.completed_texts = manifest.get('completed_texts', 0)
        if 'threshold' in manifest:
            state.threshold = manifest['threshold']

        # Parse progress file for current stage (real-time during analysis)
        progress_data = self.parse_progress_file()
        state.current_stage = progress_data.get('current_stage', '')

        # Try to get model/tokens from analysis output first (local LLM usage)
        analysis_data = self.parse_analysis_output(state.text_name) if state.text_name else {}

        if analysis_data:
            # Use analysis output data (from completed/in-progress analysis)
            state.model = analysis_data.get('model', '')
            state.input_tokens = analysis_data.get('input_tokens', 0)
            state.output_tokens = analysis_data.get('output_tokens', 0)
        else:
            # Use model from progress file (current stage) if available
            state.model = progress_data.get('stage_model', '') or eval_state.get('model', '')
            # Fall back to Claude Code logs for tokens if no analysis data
            log_data = self.parse_latest_log()
            if not state.model:
                state.model = log_data.get('model', '')
            state.input_tokens = log_data.get('input_tokens', 0)
            state.output_tokens = log_data.get('output_tokens', 0)

        # Parse git log
        state.commits = self.parse_git_log(5)

        # Check if loop is running
        state.loop_running = self.check_loop_running()

        state.last_updated = datetime.now()

        return state


def format_tokens(count: int) -> str:
    """Format token count as human-readable string."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


class StatusBar(Static):
    """Status bar showing current text, attempt, phase, model, tokens."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        # Loop status indicator (prominent, at start of first line)
        if self.state.loop_running:
            text.append("● RUNNING", style="bold green")
        else:
            text.append("● STOPPED", style="bold red")
        text.append("  │  ", style="dim")

        # Line 1: TEXT, ATTEMPT, PHASE
        text.append("TEXT: ", style="bold cyan")
        text.append(self.state.text_name or "(none)", style="white")
        text.append("  │  ", style="dim")
        text.append("ATTEMPT: ", style="bold cyan")
        text.append(f"{self.state.attempt}", style="white")
        text.append("  │  ", style="dim")
        text.append("PHASE: ", style="bold cyan")

        phase_style = "white"
        if self.state.phase == "awaiting_fix":
            phase_style = "yellow"
        elif self.state.phase == "complete":
            phase_style = "green"
        elif self.state.phase == "running_analysis":
            phase_style = "cyan"
        text.append(self.state.phase, style=phase_style)

        text.append("\n")

        # Line 2: MODEL, TOKENS, STAGE
        text.append("MODEL: ", style="bold cyan")
        model_name = self.state.model.split('/')[-1] if self.state.model else "(none)"
        # Truncate model name if too long
        if len(model_name) > 25:
            model_name = model_name[:22] + "..."
        text.append(model_name, style="white")
        text.append("  │  ", style="dim")
        text.append("TOKENS: ", style="bold cyan")
        text.append(f"{format_tokens(self.state.input_tokens)} in / {format_tokens(self.state.output_tokens)} out", style="white")

        # Show current stage if running analysis
        if self.state.current_stage:
            text.append("\n")
            text.append("STAGE: ", style="bold cyan")
            text.append(self.state.current_stage, style="bold yellow")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ScorePanel(Static):
    """Panel showing all scores with progress bars."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()
        threshold = self.state.threshold

        scores = [
            ("Structure", self.state.structure_score),
            ("Characters", self.state.characters_score),
            ("Profiles", self.state.profiles_score),
            ("Summaries", self.state.summaries_score),
            ("Pronunciation", self.state.pronunciation_score),
            ("Presentation", self.state.presentation_score),
        ]

        for name, value in scores:
            # Pad name to fixed width
            padded_name = f"{name}:".ljust(16)
            text.append(padded_name, style="white")

            if value is None:
                text.append("  --/10  ", style="dim")
                text.append("░" * 30, style="dim")
            else:
                # Score value
                score_str = f"{value:4.1f}/10  "
                passing = value >= threshold
                text.append(score_str, style="green" if passing else "red")

                # Progress bar
                filled = int((value / 10.0) * 30)
                empty = 30 - filled
                bar_style = "green" if passing else "yellow" if value >= 6 else "red"
                text.append("█" * filled, style=bar_style)
                text.append("░" * empty, style="dim")

                # Pass/fail indicator
                if passing:
                    text.append(" ✓", style="green")
                else:
                    text.append(" ✗", style="red")

            text.append("\n")

        # Separator
        text.append("─" * 56, style="dim")
        text.append("\n")

        # Overall score
        text.append("OVERALL:".ljust(16), style="bold white")
        if self.state.overall_score is None:
            text.append("  --/10  ", style="dim")
            text.append(" " * 20, style="dim")
        else:
            overall = self.state.overall_score
            passing = overall >= threshold
            text.append(f"{overall:4.1f}/10  ", style="bold green" if passing else "bold red")
            text.append(" " * 13, style="dim")

        text.append(f"Threshold: {threshold:.1f}", style="cyan")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class OverallProgress(Static):
    """Overall progress bar showing texts completed."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        completed = self.state.completed_texts
        total = self.state.total_texts

        text.append("PROGRESS: ", style="bold cyan")
        text.append(f"{completed}/{total} texts complete  ", style="white")

        if total > 0:
            pct = completed / total
            filled = int(pct * 30)
            empty = 30 - filled
            text.append("█" * filled, style="green")
            text.append("░" * empty, style="dim")
            text.append(f" {pct * 100:.0f}%", style="white")
        else:
            text.append("░" * 30, style="dim")
            text.append(" 0%", style="white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class IssuesPanel(Static):
    """Panel showing issues from evaluation."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        issues = self.state.issues
        text.append(f"ISSUES ({len(issues)})\n", style="bold white")

        if not issues:
            text.append("  No issues found", style="dim")
            return text

        severity_styles = {
            'CRITICAL': 'bold red',
            'HIGH': 'red',
            'MEDIUM': 'yellow',
            'LOW': 'dim white',
        }

        # Show up to 10 issues
        for issue in issues[:10]:
            style = severity_styles.get(issue.severity, 'white')
            text.append(f"{issue.severity:8} ", style=style)
            text.append("│ ", style="dim")
            # Truncate long descriptions
            desc = issue.description
            if len(desc) > 55:
                desc = desc[:52] + "..."
            text.append(desc, style="white")
            text.append("\n")

        if len(issues) > 10:
            text.append(f"  ... and {len(issues) - 10} more", style="dim")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class CommitsPanel(Static):
    """Panel showing recent git commits."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("RECENT COMMITS\n", style="bold white")

        if not self.state.commits:
            text.append("  No commits found", style="dim")
            return text

        for commit in self.state.commits:
            text.append(commit.hash, style="yellow")
            text.append(" │ ", style="dim")
            # Truncate long messages
            msg = commit.message
            if len(msg) > 55:
                msg = msg[:52] + "..."
            text.append(msg, style="white")
            text.append("\n")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class FooterInfo(Static):
    """Footer showing last updated time and polling interval."""

    def __init__(self, state: OracleState, polling_interval: float = 2.0):
        super().__init__()
        self.state = state
        self.polling_interval = polling_interval

    def render(self) -> Text:
        text = Text()
        timestamp = self.state.last_updated.strftime("%Y-%m-%d %H:%M:%S")
        text.append(f"Last updated: {timestamp}", style="dim")
        text.append("  │  ", style="dim")
        text.append(f"Polling: {self.polling_interval:.0f}s", style="dim")
        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class OracleMonitorApp(App):
    """Main Oracle Loop Monitor application."""

    CSS = """
    Screen {
        background: $surface;
    }

    StatusBar {
        height: auto;
        max-height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    ScorePanel {
        height: 10;
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

    IssuesPanel {
        height: auto;
        max-height: 10;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    CommitsPanel {
        height: auto;
        max-height: 8;
        border: solid $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    FooterInfo {
        height: 1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "refresh", "Refresh"),
    ]

    paused = reactive(False)

    def __init__(self, base_dir: Path = None, polling_interval: float = 2.0):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
        self.polling_interval = polling_interval
        self.parser = StateParser(self.base_dir)
        self.state = self.parser.get_state()
        self.title = "Oracle Loop Monitor"

    def compose(self) -> ComposeResult:
        yield Header()

        with Container():
            yield StatusBar(self.state)
            yield ScorePanel(self.state)
            yield OverallProgress(self.state)
            yield IssuesPanel(self.state)
            yield CommitsPanel(self.state)
            yield FooterInfo(self.state, self.polling_interval)

        yield Footer()

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
        """Update all widgets with new state."""
        try:
            self.query_one(StatusBar).update_state(self.state)
            self.query_one(ScorePanel).update_state(self.state)
            self.query_one(OverallProgress).update_state(self.state)
            self.query_one(IssuesPanel).update_state(self.state)
            self.query_one(CommitsPanel).update_state(self.state)
            self.query_one(FooterInfo).update_state(self.state)
        except Exception:
            # Widget may not be ready yet
            pass

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
        default=2.0,
        help="Polling interval in seconds (default: 2.0)"
    )

    args = parser.parse_args()
    # Resolve to absolute path before Textual changes working directory
    base_dir = args.dir.resolve()
    run_oracle_monitor(base_dir=base_dir, polling_interval=args.interval)


if __name__ == "__main__":
    main()
