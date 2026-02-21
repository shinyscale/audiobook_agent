"""ExperimentStatusPanel."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState


class ExperimentStatusPanel(Static):
    """Panel showing experiment framework status."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()

        # Check if experiment mode is active
        if not self.state.experiment_mode and not self.state.experiment_running:
            text.append("EXPERIMENT MODE: ", style="bold white")
            text.append("OFF", style="dim")
            text.append(" (oracle loop active)\n", style="dim")
            return text

        # Header
        text.append("═" * 60, style="bold cyan")
        text.append("\n")

        # Experiment info
        text.append("  EXPERIMENT: ", style="bold cyan")
        text.append(f"{self.state.active_experiment_id}", style="bold yellow")

        # Status badge
        status = self.state.active_experiment_status
        if status == "in_progress":
            text.append("  [", style="dim")
            text.append("RUNNING", style="bold green")
            text.append("]", style="dim")
        elif status == "pending":
            text.append("  [", style="dim")
            text.append("PENDING", style="bold yellow")
            text.append("]", style="dim")
        elif status == "passed":
            text.append("  [", style="dim")
            text.append("PASSED", style="bold green")
            text.append("]", style="dim")
        elif status.startswith("failed"):
            text.append("  [", style="dim")
            text.append(status.upper(), style="bold red")
            text.append("]", style="dim")

        text.append("\n")

        # Description
        if self.state.active_experiment_desc:
            text.append("  ", style="")
            text.append(f"{self.state.active_experiment_desc}\n", style="white")

        text.append("═" * 60, style="bold cyan")
        text.append("\n\n")

        # Phase progress: screening → validation → regression
        phases = ["screening", "validation", "regression"]
        current_phase = self.state.experiment_phase

        text.append("  Phase: ", style="bold white")

        for i, phase in enumerate(phases):
            current_idx = phases.index(current_phase) if current_phase in phases else -1

            if phase == current_phase:
                text.append(f"● {phase.upper()}", style="bold green")
            elif i < current_idx:
                text.append(f"✓ {phase}", style="dim green")
            else:
                text.append(f"○ {phase}", style="dim")

            if i < len(phases) - 1:
                text.append("  →  ", style="dim")

        text.append("\n\n")

        # Book progress within phase
        if self.state.experiment_phase:
            text.append(f"  Progress: ", style="cyan")
            text.append(f"{self.state.experiment_book_index}", style="bold white")
            text.append(f"/{self.state.experiment_books_in_phase}", style="white")
            text.append(f" books in {self.state.experiment_phase}\n", style="white")

            # Current book being tested
            if self.state.experiment_current_book:
                text.append(f"  Current:  ", style="cyan")
                text.append(f"{self.state.experiment_current_book}", style="bold yellow")
                text.append("\n")

            # Progress bar
            if self.state.experiment_books_in_phase > 0:
                pct = self.state.experiment_book_index / self.state.experiment_books_in_phase
                filled = int(pct * 40)
                empty = 40 - filled
                text.append("  ")
                text.append("█" * filled, style="green")
                text.append("░" * empty, style="dim")
                text.append(f" {pct * 100:.0f}%\n", style="white")

        # Thresholds
        text.append("\n")
        text.append("  Thresholds: ", style="cyan")
        text.append(f"screening≥{self.state.screening_threshold}", style="yellow")
        text.append("  ", style="")
        text.append(f"validation≥{self.state.validation_threshold}", style="yellow")
        text.append("  ", style="")
        text.append(f"regression±{self.state.category_regression_tolerance}", style="yellow")

        # Show results (all when expanded, last 4 when collapsed)
        if self.state.experiment_results:
            text.append("\n\n")
            results_list = list(self.state.experiment_results.items())

            if self.expanded:
                text.append(f"  All Results ({len(results_list)}) [Press 'e' to collapse]:\n", style="bold white")
                results_to_show = results_list
            else:
                text.append(f"  Recent Results [Press 'e' to expand]:\n", style="bold white")
                results_to_show = results_list[-4:]

            for book, result in results_to_show:
                status = result.get('status', 'unknown')
                overall = result.get('overall', 0)
                category_scores = result.get('category_scores', {})

                text.append(f"    {book}: ", style="white")
                text.append(f"{overall:.1f}/10 ", style="cyan")

                if 'passed' in status:
                    text.append("✓", style="green")
                elif 'failed' in status:
                    text.append(f"✗ ({status})", style="red")
                else:
                    text.append(status, style="yellow")

                # Show category breakdown when expanded
                if self.expanded and category_scores:
                    text.append("\n")
                    text.append("      ", style="")
                    cats = ['structure', 'characters', 'profiles', 'summaries', 'pronunciation', 'presentation']
                    for cat in cats:
                        score = category_scores.get(cat, 0)
                        abbrev = cat[:3].upper()
                        if score >= 8.0:
                            text.append(f"{abbrev}:{score:.0f} ", style="green")
                        elif score >= 7.0:
                            text.append(f"{abbrev}:{score:.0f} ", style="yellow")
                        else:
                            text.append(f"{abbrev}:{score:.0f} ", style="red")

                text.append("\n")

            if not self.expanded and len(results_list) > 4:
                text.append(f"    ... and {len(results_list) - 4} more\n", style="dim")
        else:
            if self.expanded:
                text.append("\n  [Press 'e' to collapse]\n", style="dim")
            else:
                text.append("\n  [Press 'e' to expand]\n", style="dim")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()
