"""ClaudeActivityPanel and ClaudeThinkingPanel."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState


class ClaudeActivityPanel(Static):
    """Panel showing Claude's recent activity (tool calls, messages)."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        # Show header with phase indicator
        if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
            text.append("CLAUDE ACTIVITY [ACTIVE - ", style="bold white")
            text.append(self.state.phase.upper(), style="bold magenta")
            text.append("]\n", style="bold white")
        else:
            text.append("CLAUDE ACTIVITY\n", style="bold white")

        activities = self.state.claude_activities
        if not activities:
            text.append("  No recent activity", style="dim")
            if self.state.phase in ('awaiting_analysis', 'running_analysis'):
                text.append("\n  (Local LLMs running - see Local LLM Activity above)", style="dim cyan")
            return text

        # Show tool icons for each tool type
        tool_icons = {
            'Read': '📖',
            'Edit': '✏️',
            'Write': '📝',
            'Bash': '💻',
            'Grep': '🔍',
            'Glob': '📂',
            'Task': '🤖',
            'TodoWrite': '✅',
        }

        for activity in activities[-12:]:  # Show last 12 activities
            icon = tool_icons.get(activity.tool_name, '🔧')
            text.append(f"  {icon} ", style="dim")
            # Show timestamp if available
            if activity.timestamp:
                text.append(f"{activity.timestamp} ", style="dim cyan")
            text.append(f"{activity.tool_name:12}", style="cyan")
            text.append("│ ", style="dim")
            # Truncate long descriptions (shorter if timestamp shown)
            desc = activity.description
            max_desc_len = 55 if activity.timestamp else 70
            if len(desc) > max_desc_len:
                desc = desc[:max_desc_len - 3] + "..."
            text.append(desc, style="white")
            text.append("\n")

        # Show last message snippet if available
        if self.state.claude_last_message:
            text.append("\n")
            text.append("  Last output: ", style="dim")
            msg = self.state.claude_last_message.replace('\n', ' ')
            if len(msg) > 500:
                msg = msg[:497] + "..."
            text.append(msg, style="italic white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class ClaudeThinkingPanel(Static):
    """Panel showing Claude's reasoning and explanations."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()

        # Header shows mode
        if self.expanded:
            text.append("CLAUDE THINKING [EXPANDED - Press 't' to collapse]\n", style="bold white")
        else:
            text.append("CLAUDE THINKING [Press 't' to expand, 'x' to export]\n", style="bold white")

        thinking_texts = self.state.thinking_text
        if not thinking_texts:
            text.append("  No reasoning captured yet", style="dim")
            if self.state.phase in ('awaiting_analysis', 'running_analysis'):
                text.append("\n  (Local LLMs running - Claude reasoning appears during evaluate/fix)", style="dim cyan")
            return text

        # In expanded mode, show ALL blocks without truncation
        # In compact mode, show last 3 blocks with truncation
        if self.expanded:
            blocks_to_show = thinking_texts  # Show all
            max_chars_per_block = None  # No truncation
            blocks_label = f"Showing all {len(thinking_texts)} blocks"
        else:
            blocks_to_show = thinking_texts[-3:]  # Show last 3
            max_chars_per_block = 800  # Truncate in compact mode
            blocks_label = f"Showing last 3 of {len(thinking_texts)} blocks"

        text.append(f"  [{blocks_label}]\n", style="dim cyan")

        # Show thinking blocks with numbering
        for i, thinking in enumerate(blocks_to_show, 1):
            # Add separator between blocks
            if i > 1:
                text.append("  ─────────────────────────────────────────\n", style="dim")

            # Show block number (relative to total if not showing all)
            if self.expanded or len(thinking_texts) <= 3:
                text.append(f"  [{i}] ", style="dim cyan")
            else:
                # Show actual position in full list
                actual_index = len(thinking_texts) - len(blocks_to_show) + i
                text.append(f"  [{actual_index}/{len(thinking_texts)}] ", style="dim cyan")

            # Word wrap and display the thinking text
            # Clean up the text - remove excessive whitespace
            cleaned = ' '.join(thinking.split())

            # Truncate in compact mode
            truncated = False
            if max_chars_per_block and len(cleaned) > max_chars_per_block:
                cleaned = cleaned[:max_chars_per_block]
                truncated = True

            # Display with word wrapping by breaking into lines
            words = cleaned.split()
            current_line = ""
            line_limit = 100 if self.expanded else 80

            for word in words:
                if len(current_line) + len(word) + 1 <= line_limit:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        text.append(current_line + "\n", style="white")
                        text.append("      ", style="")  # Indent continuation
                    current_line = word

            if current_line:
                text.append(current_line, style="white")
                if truncated:
                    text.append("... [truncated]", style="dim yellow")
                text.append("\n")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()
