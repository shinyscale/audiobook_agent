"""ScorePanel and OverallProgress panels."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState


class ScorePanel(Static):
    """Panel showing all scores with progress bars."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()
        threshold = self.state.threshold

        # Prominent total score at top
        text.append("═" * 56, style="dim cyan")
        text.append("\n")
        text.append("  TOTAL SCORE:  ", style="bold white")
        if self.state.overall_score is not None:
            overall = self.state.overall_score
            # Color based on threshold comparison
            if overall >= threshold:
                score_style = "bold green"
            elif overall >= threshold - 1.0:
                score_style = "bold yellow"
            else:
                score_style = "bold red"
            text.append(f"{overall:.2f}", style=score_style)
            text.append(" / 10", style="white")
            text.append(f"   [Threshold: {threshold:.1f}]", style="dim cyan")
        else:
            text.append("--", style="dim")
            text.append(" / 10", style="dim")
            text.append(f"   [Threshold: {threshold:.1f}]", style="dim cyan")
        text.append("\n")
        text.append("═" * 56, style="dim cyan")
        text.append("\n\n")

        scores = [
            ("Structure", self.state.structure_score, "structure"),
            ("Characters", self.state.characters_score, "characters"),
            ("Profiles", self.state.profiles_score, "profiles"),
            ("Summaries", self.state.summaries_score, "summaries"),
            ("Pronunciation", self.state.pronunciation_score, "pronunciation"),
            ("Presentation", self.state.presentation_score, "presentation"),
        ]

        for name, value, key in scores:
            # Pad name to fixed width
            padded_name = f"{name}:".ljust(14)
            text.append(padded_name, style="white")

            if value is None:
                text.append("  --/10  ", style="dim")
                text.append("░" * 24, style="dim")
                text.append("      ", style="dim")  # Space for delta
            else:
                # Score value
                score_str = f"{value:4.1f}/10  "
                passing = value >= threshold
                text.append(score_str, style="green" if passing else "red")

                # Progress bar (shorter to make room for delta)
                filled = int((value / 10.0) * 24)
                empty = 24 - filled
                bar_style = "green" if passing else "yellow" if value >= 6 else "red"
                text.append("█" * filled, style=bar_style)
                text.append("░" * empty, style="dim")

                # Pass/fail indicator
                if passing:
                    text.append(" ✓", style="green")
                else:
                    text.append(" ✗", style="red")

                # Delta from baseline (if available)
                delta = self.state.category_deltas.get(key)
                if delta is not None:
                    if delta > 0.05:  # Small threshold to avoid showing 0.0
                        text.append(f" ↑{delta:.1f}", style="green")
                    elif delta < -0.05:
                        # Check if this is a regression
                        if abs(delta) > self.state.category_regression_tolerance:
                            text.append(f" ↓{abs(delta):.1f}", style="bold red")
                            text.append("!", style="bold red")
                        else:
                            text.append(f" ↓{abs(delta):.1f}", style="yellow")
                    else:
                        text.append("  ═", style="dim cyan")  # No change
                else:
                    text.append("     ", style="dim")  # No baseline

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
