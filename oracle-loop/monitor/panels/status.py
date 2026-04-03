"""StatusBar and FooterInfo panels."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState, format_tokens


class StatusBar(Static):
    """Status bar showing current text, attempt, phase, model, tokens."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        # Mode and status indicator (prominent, at start of first line)
        if self.state.experiment_running or self.state.experiment_mode:
            text.append("● EXPERIMENT", style="bold magenta")
            if self.state.active_experiment_id:
                text.append(f" ({self.state.active_experiment_id})", style="magenta")
        elif self.state.loop_running and self.state.loop_stale:
            text.append("● STALE", style="bold yellow")
        elif self.state.loop_running:
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

        # Make phase very obvious with colors and context
        phase_style = "white"
        phase_label = self.state.phase
        if self.state.phase in ("awaiting_evaluation", "evaluate"):
            phase_style = "bold magenta"
            phase_label = f"{self.state.phase} (Claude working)"
        elif self.state.phase in ("awaiting_fix", "fix"):
            phase_style = "bold yellow"
            phase_label = f"{self.state.phase} (Claude fixing)"
        elif self.state.phase == "complete":
            phase_style = "bold green"
        elif self.state.phase == "running_analysis":
            phase_style = "bold cyan"
            phase_label = f"{self.state.phase} (Local LLM)"
        elif self.state.phase == "awaiting_analysis":
            phase_style = "cyan"
            phase_label = f"{self.state.phase} (starting)"
        text.append(phase_label, style=phase_style)

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
            text.append(f"{self.state.current_stage}", style="bold yellow")

            # Show stage elapsed time from heartbeat
            if self.state.heartbeat_stage_elapsed > 0:
                elapsed = self.state.heartbeat_stage_elapsed
                if elapsed >= 60:
                    mins = int(elapsed // 60)
                    secs = int(elapsed % 60)
                    text.append(f" ({mins}m {secs}s)", style="dim cyan")
                else:
                    text.append(f" ({int(elapsed)}s)", style="dim cyan")

            # Show LLM calls in current stage
            if self.state.heartbeat_llm_calls > 0:
                text.append(f"  [{self.state.heartbeat_llm_calls} LLM calls]", style="dim")
        elif self.state.phase in ('evaluate', 'awaiting_evaluation', 'fix', 'awaiting_fix'):
            # No active stage but in Claude phase - make it clear
            text.append("\n")
            text.append("STAGE: ", style="bold cyan")
            text.append("Analysis Complete - Claude Evaluating", style="bold magenta")

        # Show heartbeat status (activity indicator for local LLM)
        text.append("\n")
        if self.state.heartbeat_age_seconds is not None:
            age = self.state.heartbeat_age_seconds
            text.append("LLM HEARTBEAT: ", style="bold cyan")
            if age < 5:
                text.append("●", style="bold green")
                text.append(f" {age:.0f}s ago (active)", style="green")
            elif age < 30:
                text.append("●", style="bold yellow")
                text.append(f" {age:.0f}s ago", style="yellow")
            elif age < 60:
                text.append("○", style="yellow")
                text.append(f" {age:.0f}s ago (idle)", style="yellow")
            elif age < 300:
                mins = int(age // 60)
                text.append("○", style="dim")
                # Don't show as error - might be between stages or Claude is working
                if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
                    text.append(f" {mins}m ago (analysis complete)", style="dim green")
                else:
                    text.append(f" {mins}m ago (inactive)", style="dim")
            else:
                mins = int(age // 60)
                text.append("○", style="dim")
                text.append(f" {mins}m ago (inactive)", style="dim")

            # Show total analysis time if available
            if self.state.heartbeat_total_elapsed > 0:
                total = self.state.heartbeat_total_elapsed
                text.append("  │  ", style="dim")
                text.append("TOTAL TIME: ", style="bold cyan")
                if total >= 3600:
                    hours = int(total // 3600)
                    mins = int((total % 3600) // 60)
                    text.append(f"{hours}h {mins}m", style="white")
                elif total >= 60:
                    mins = int(total // 60)
                    secs = int(total % 60)
                    text.append(f"{mins}m {secs}s", style="white")
                else:
                    text.append(f"{int(total)}s", style="white")
        else:
            text.append("HEARTBEAT: ", style="bold cyan")
            text.append("○", style="dim")
            text.append(" no data", style="dim")

        # Show Ollama service heartbeat (for when debug.log is stale but Ollama is still working)
        if self.state.ollama_last_request_age is not None:
            text.append("  │  ", style="dim")
            age = self.state.ollama_last_request_age
            text.append("OLLAMA: ", style="bold cyan")
            if age < 5:
                text.append("●", style="bold green")
                text.append(f" {age:.0f}s ago", style="green")
            elif age < 30:
                text.append("●", style="bold yellow")
                text.append(f" {age:.0f}s ago", style="yellow")
            elif age < 60:
                text.append("○", style="yellow")
                text.append(f" {age:.0f}s ago", style="yellow")
            elif age < 300:
                mins = int(age // 60)
                text.append("○", style="dim")
                text.append(f" {mins}m ago", style="dim")
            else:
                mins = int(age // 60)
                text.append("○", style="dim")
                text.append(f" {mins}m ago", style="dim")

            # Show last request duration if available
            if self.state.ollama_last_request_duration:
                dur = self.state.ollama_last_request_duration
                text.append(f" (last: {dur:.0f}s)", style="dim cyan")

        # Show analysis process status
        text.append("  │  ", style="dim")
        text.append("ANALYSIS: ", style="bold cyan")
        if self.state.analysis_running:
            text.append("●", style="bold green")
            text.append(f" running", style="green")
            if self.state.analysis_pid:
                text.append(f" (PID {self.state.analysis_pid})", style="dim")
        else:
            text.append("○", style="dim")
            text.append(" not running", style="dim")

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
