"""DiagnosticMatrixPanel, StderrPanel, IssuesPanel, CommitsPanel, and ScoreHistoryPanel."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState


class DiagnosticMatrixPanel(Static):
    """Panel showing cross-book diagnostic matrix from batch-diagnostic.sh."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()
        diag = self.state.diagnostic_matrix

        # No data at all
        if not diag:
            text.append("DIAGNOSTIC ", style="bold white")
            if self.state.diagnostic_running:
                text.append("[", style="dim")
                text.append("RUNNING", style="bold yellow")
                text.append("]", style="dim")
            else:
                text.append("[no data - run batch-diagnostic.sh]", style="dim")
            text.append("  [d to expand]", style="dim cyan")
            return text

        texts = diag.get('texts', {})
        column_stats = diag.get('column_stats', {})
        timestamp = self.state.diagnostic_timestamp

        # Count passing/failing
        total = len(texts)
        failing = sum(1 for t in texts.values() if not t.get('pass', True))
        passing = total - failing

        # Collapsed view: summary line
        if not self.expanded:
            text.append("DIAGNOSTIC", style="bold white")

            # Timestamp
            if timestamp:
                # Format timestamp for display
                ts_display = timestamp
                if 'T' in ts_display:
                    ts_display = ts_display.replace('T', ' ')
                    # Truncate to minutes
                    if '-' in ts_display.split(' ')[-1] or '+' in ts_display.split(' ')[-1]:
                        ts_display = ts_display[:16]
                text.append(f"  [last: {ts_display}]", style="dim cyan")

            # Running indicator
            if self.state.diagnostic_running:
                text.append("  [", style="dim")
                text.append("RUNNING", style="bold yellow")
                text.append("]", style="dim")

            text.append(f"  {total} texts scored", style="white")

            # Highlight failures
            if failing > 0:
                # Find worst categories
                worst_cats = sorted(
                    [(cat, stats.get('failing_count', 0)) for cat, stats in column_stats.items()],
                    key=lambda x: -x[1]
                )
                worst = [f"{c}: {n} failing" for c, n in worst_cats if n > 0]
                text.append("  ", style="")
                text.append(f"{failing} FAILING", style="bold red")
                if worst:
                    text.append(f" ({', '.join(worst[:2])})", style="red")
            else:
                text.append("  ", style="")
                text.append("ALL PASSING", style="bold green")

            text.append("  [d to expand]", style="dim cyan")
            return text

        # Expanded view: full matrix
        text.append("DIAGNOSTIC MATRIX", style="bold white")
        if self.state.diagnostic_running:
            text.append("  [", style="dim")
            text.append("RUNNING", style="bold yellow")
            text.append("]", style="dim")
        if timestamp:
            ts_display = timestamp
            if 'T' in ts_display:
                ts_display = ts_display.replace('T', ' ')[:16]
            text.append(f"  [last: {ts_display}]", style="dim cyan")
        text.append("  [d to collapse]\n", style="dim cyan")
        text.append("═" * 80, style="dim cyan")
        text.append("\n")

        # Category headers
        cats = ['structure', 'characters', 'profiles', 'summaries', 'pronunciation', 'presentation']
        abbrevs = ['Str', 'Chr', 'Pro', 'Sum', 'Prn', 'Prs']

        # Header row
        text.append("  ", style="")
        text.append(f"{'Text':<20}", style="bold white")
        for abbr in abbrevs:
            text.append(f"{abbr:>6}", style="bold cyan")
        text.append(f"{'  Ovr':>6}", style="bold white")
        text.append(f"  {'Status':<8}", style="bold white")
        text.append("\n")
        text.append("  " + "─" * 76, style="dim")
        text.append("\n")

        # Sort: failing first, then by overall score ascending
        sorted_texts = sorted(
            texts.items(),
            key=lambda x: (x[1].get('pass', True), x[1].get('overall', 0))
        )

        for text_name, tdata in sorted_texts:
            scores = tdata.get('scores', {})
            overall = tdata.get('overall', 0)
            is_pass = tdata.get('pass', True)
            source = tdata.get('source', '')

            # Text name (truncated)
            display_name = text_name[:18]
            if source == 'historical':
                display_name += '*'
            text.append("  ", style="")
            text.append(f"{display_name:<20}", style="white" if is_pass else "bold white")

            # Category scores
            for cat in cats:
                score = scores.get(cat)
                if score is None:
                    text.append(f"{'?':>6}", style="dim")
                else:
                    score_str = f"{score:>5.1f}"
                    if score >= 8.0:
                        text.append(f"{score_str:>6}", style="green")
                    elif score >= 7.0:
                        text.append(f"{score_str:>6}", style="yellow")
                    else:
                        text.append(f"{score_str:>6}", style="bold red")

            # Overall
            ovr_str = f"{overall:>5.1f}"
            if overall >= 8.0:
                text.append(f"{ovr_str:>6}", style="bold green")
            else:
                text.append(f"{ovr_str:>6}", style="bold red")

            # Pass/fail
            if is_pass:
                text.append("  ", style="")
                text.append("PASS", style="green")
            else:
                text.append("  ", style="")
                text.append("FAIL", style="bold red")

            text.append("\n")

        # Separator before stats
        text.append("  " + "─" * 76, style="dim")
        text.append("\n")

        # Column statistics
        text.append("  ", style="")
        text.append(f"{'Mean':<20}", style="bold cyan")
        for cat in cats:
            stats = column_stats.get(cat, {})
            mean = stats.get('mean', 0)
            mean_str = f"{mean:>5.1f}"
            if mean >= 8.0:
                text.append(f"{mean_str:>6}", style="green")
            else:
                text.append(f"{mean_str:>6}", style="yellow")
        text.append("\n")

        text.append("  ", style="")
        text.append(f"{'Min':<20}", style="bold cyan")
        for cat in cats:
            stats = column_stats.get(cat, {})
            mn = stats.get('min', 0)
            min_str = f"{mn:>5.1f}"
            if mn >= 8.0:
                text.append(f"{min_str:>6}", style="green")
            else:
                text.append(f"{min_str:>6}", style="red")
        text.append("\n")

        text.append("  ", style="")
        text.append(f"{'Failing':<20}", style="bold cyan")
        for cat in cats:
            stats = column_stats.get(cat, {})
            fc = stats.get('failing_count', 0)
            if fc == 0:
                text.append(f"{'0':>6}", style="dim green")
            else:
                text.append(f"{fc:>6}", style="bold red")
        text.append("\n")

        # Systemic pattern summary (categories sorted by severity)
        problem_cats = sorted(
            [(cat, column_stats.get(cat, {})) for cat in cats],
            key=lambda x: x[1].get('failing_count', 0),
            reverse=True
        )
        problem_cats = [(c, s) for c, s in problem_cats if s.get('failing_count', 0) > 0]
        if problem_cats:
            text.append("\n")
            text.append("  Systemic Issues:\n", style="bold white")
            for cat, stats in problem_cats:
                fc = stats.get('failing_count', 0)
                ft = stats.get('failing_texts', [])
                text.append(f"    {cat}: ", style="yellow")
                text.append(f"{fc} failing", style="red")
                if ft:
                    ft_str = ", ".join(ft[:3])
                    if len(ft) > 3:
                        ft_str += f" (+{len(ft)-3})"
                    text.append(f" ({ft_str})", style="dim")
                text.append("\n")

        # Per-text notes for failing texts
        failing_texts = [(name, tdata) for name, tdata in sorted_texts if not tdata.get('pass', True)]
        if failing_texts:
            text.append("\n")
            text.append("  Fix Priorities:\n", style="bold white")
            for text_name, tdata in failing_texts:
                notes = tdata.get('notes', '')
                text.append(f"    {text_name}: ", style="bold red")
                if notes:
                    # Truncate notes
                    if len(notes) > 80:
                        notes = notes[:77] + "..."
                    text.append(notes, style="white")
                else:
                    text.append("(no notes)", style="dim")
                text.append("\n")

        # Legend
        text.append("\n")
        text.append("  * = historical baseline", style="dim")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()


class StderrPanel(Static):
    """Panel showing recent stderr output from analysis."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("RECENT OUTPUT\n", style="bold white")

        if not self.state.recent_stderr:
            text.append("  No recent output", style="dim")
            if self.state.analysis_running:
                text.append("\n  (analysis running, waiting for output...)", style="dim cyan")
            return text

        for line in self.state.recent_stderr:
            # Color code based on content
            line_lower = line.lower()
            if 'error' in line_lower or 'fail' in line_lower:
                style = "red"
            elif 'warning' in line_lower:
                style = "yellow"
            elif 'low confidence' in line_lower:
                style = "yellow"
            else:
                style = "dim white"

            # Truncate long lines
            if len(line) > 90:
                line = line[:87] + "..."
            text.append(f"  {line}\n", style=style)

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
            # Show timestamp if available
            if commit.timestamp:
                # Pad timestamp to fixed width for alignment
                ts = commit.timestamp[:15].ljust(15)
                text.append(ts, style="dim cyan")
                text.append(" │ ", style="dim")
            # Truncate long messages
            msg = commit.message
            max_msg_len = 60 if commit.timestamp else 80
            if len(msg) > max_msg_len:
                msg = msg[:max_msg_len - 3] + "..."
            text.append(msg, style="white")
            text.append("\n")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ScoreHistoryPanel(Static):
    """Panel showing score history for current text and overall manifest progress."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def _score_style(self, score_val: float, threshold: float = 8.0) -> str:
        if score_val >= threshold:
            return "bold green"
        elif score_val >= threshold - 1.0:
            return "yellow"
        else:
            return "bold red"

    def _parse_score_float(self, score_str: str) -> float | None:
        """Parse a score string like '7.35' or '~5.0' into a float."""
        cleaned = score_str.strip().lstrip('~')
        try:
            return float(cleaned)
        except ValueError:
            return None

    def render(self) -> Text:
        text = Text()
        threshold = self.state.threshold

        has_history = bool(self.state.score_history)
        has_texts = bool(self.state.manifest_texts)

        if not has_history and not has_texts:
            text.append("SCORE HISTORY ", style="bold white")
            text.append("[no data]", style="dim")
            return text

        # --- Active text score history ---
        if has_history:
            text.append("SCORE HISTORY", style="bold white")
            if self.state.text_name:
                text.append(f"  [{self.state.text_name}]", style="bold cyan")
            text.append("\n")

            # Build a simple sparkline / table of attempts
            text.append("  ", style="")
            text.append(f"{'Att':>5}", style="bold white")
            text.append(f"{'Score':>8}", style="bold white")
            text.append(f"  {'Trend':>5}", style="bold white")
            text.append(f"  {'Notes'}", style="bold white")
            text.append("\n")
            text.append("  " + "─" * 74, style="dim")
            text.append("\n")

            prev_score = None
            best_score = None
            for entry in self.state.score_history:
                score_val = self._parse_score_float(entry.score)

                text.append("  ", style="")
                label = entry.attempt_label or str(entry.attempt)
                text.append(f"{label:>5}", style="white")

                # Score value with color
                if score_val is not None:
                    style = self._score_style(score_val, threshold)
                    text.append(f"{entry.score:>8}", style=style)

                    # Trend arrow
                    if prev_score is not None:
                        delta = score_val - prev_score
                        if delta > 0.1:
                            text.append(f"  {'▲':>5}", style="green")
                        elif delta < -0.1:
                            text.append(f"  {'▼':>5}", style="red")
                        else:
                            text.append(f"  {'─':>5}", style="dim")
                    else:
                        text.append(f"  {'':>5}", style="dim")

                    if best_score is None or score_val > best_score:
                        best_score = score_val
                    prev_score = score_val
                else:
                    text.append(f"{entry.score:>8}", style="dim")
                    text.append(f"  {'':>5}", style="dim")

                # Notes (truncated)
                notes = entry.notes.strip()
                if notes:
                    max_notes = 52
                    if len(notes) > max_notes:
                        notes = notes[:max_notes - 3] + "..."
                    text.append(f"  {notes}", style="dim white")

                text.append("\n")

            # Summary line
            text.append("  " + "─" * 74, style="dim")
            text.append("\n")
            if best_score is not None:
                text.append("  Best: ", style="bold white")
                text.append(f"{best_score:.2f}", style=self._score_style(best_score, threshold))
                if prev_score is not None:
                    text.append(f"  Latest: ", style="bold white")
                    text.append(f"{prev_score:.2f}", style=self._score_style(prev_score, threshold))
                text.append(f"  Target: ", style="bold white")
                text.append(f"{threshold:.1f}", style="cyan")
                gap = threshold - (prev_score or 0)
                if gap > 0:
                    text.append(f"  (need +{gap:.2f})", style="yellow")
                else:
                    text.append(f"  (met!)", style="bold green")
            text.append("\n\n")

        # --- All texts overview ---
        if has_texts:
            text.append("ALL TEXTS OVERVIEW", style="bold white")
            if not self.expanded:
                # Compact: just show completed/total and active
                completed = sum(1 for t in self.state.manifest_texts if t.complete)
                total = len(self.state.manifest_texts)
                skipped = sum(1 for t in self.state.manifest_texts if t.skipped)
                text.append(f"  {completed}/{total} complete", style="white")
                if skipped:
                    text.append(f"  ({skipped} skipped)", style="dim yellow")
                text.append("  [h to expand]", style="dim cyan")
            else:
                text.append("  [h to collapse]\n", style="dim cyan")
                text.append("  ", style="")
                text.append(f"{'Text':<28}", style="bold white")
                text.append(f"{'Att':>5}", style="bold white")
                text.append(f"{'Score':>8}", style="bold white")
                text.append(f"{'Baseline':>10}", style="bold white")
                text.append(f"  {'Status':<12}", style="bold white")
                text.append("\n")
                text.append("  " + "─" * 74, style="dim")
                text.append("\n")

                for mt in self.state.manifest_texts:
                    text.append("  ", style="")

                    # Name
                    display_name = mt.name.replace('_', ' ').title()[:26]
                    name_style = "white"
                    if mt.name == self.state.text_name:
                        name_style = "bold cyan"
                    text.append(f"{display_name:<28}", style=name_style)

                    # Attempts
                    text.append(f"{mt.attempts:>5}", style="white")

                    # Final score
                    if mt.final_score is not None:
                        style = self._score_style(mt.final_score, threshold)
                        text.append(f"{mt.final_score:>8.2f}", style=style)
                    else:
                        text.append(f"{'—':>8}", style="dim")

                    # Baseline
                    baseline = self.state.baseline_scores.get(mt.name, {})
                    baseline_score = baseline.get('score')
                    if baseline_score is not None:
                        text.append(f"{baseline_score:>10.2f}", style="dim cyan")
                    else:
                        text.append(f"{'—':>10}", style="dim")

                    # Status
                    text.append("  ", style="")
                    if mt.complete:
                        text.append("PASS", style="bold green")
                    elif mt.skipped:
                        text.append("SKIPPED", style="yellow")
                    elif mt.attempts > 0:
                        if mt.name == self.state.text_name:
                            text.append("ACTIVE", style="bold cyan")
                        else:
                            text.append("IN PROGRESS", style="yellow")
                    else:
                        text.append("PENDING", style="dim")

                    text.append("\n")

                # Summary
                text.append("  " + "─" * 74, style="dim")
                text.append("\n")
                completed = sum(1 for t in self.state.manifest_texts if t.complete)
                total = len(self.state.manifest_texts)
                in_progress = sum(1 for t in self.state.manifest_texts if not t.complete and t.attempts > 0 and not t.skipped)
                total_attempts = sum(t.attempts for t in self.state.manifest_texts)
                text.append(f"  {completed} passed", style="green")
                text.append(f"  {in_progress} in progress", style="yellow")
                text.append(f"  {total - completed - in_progress} pending", style="dim")
                text.append(f"  ({total_attempts} total attempts)", style="dim")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()
