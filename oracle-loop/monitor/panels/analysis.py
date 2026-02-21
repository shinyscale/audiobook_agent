"""OllamaActivityPanel, CompetitiveConsensusPanel, and IdentityGraphPanel."""

from textual.widgets import Static
from rich.text import Text

from ..state import OracleState, format_tokens


class OllamaActivityPanel(Static):
    """Panel showing local LLM (Ollama) activity during analysis."""

    def __init__(self, state: OracleState):
        super().__init__()
        self.state = state

    def render(self) -> Text:
        text = Text()

        text.append("LOCAL LLM ACTIVITY\n", style="bold white")

        # Only show when we have an active analysis stage
        if not self.state.current_stage:
            # No active stage - determine why
            if self.state.phase in ('awaiting_evaluation', 'evaluate', 'awaiting_fix', 'fix'):
                # Claude is working
                text.append("  Analysis complete - idle\n", style="dim green")
                text.append("  Claude is now evaluating (see Claude Activity below)", style="bold magenta")
            elif self.state.phase == 'complete':
                text.append("  Analysis complete - all done!", style="bold green")
            else:
                text.append("  No active analysis", style="dim")
            return text

        # Stage progress with item counts
        text.append(f"  Stage: ", style="cyan")
        text.append(f"{self.state.current_stage}", style="bold yellow")

        # Item progress (e.g., "5/9 chapters")
        if self.state.ollama_items_total:
            pct = (self.state.ollama_items_processed / self.state.ollama_items_total) * 100
            text.append(f"  [{self.state.ollama_items_processed}/{self.state.ollama_items_total}]", style="white")
            text.append(f" {pct:.0f}%", style="cyan")
        elif self.state.ollama_items_processed > 0:
            text.append(f"  [{self.state.ollama_items_processed} processed]", style="white")

        text.append("\n")

        # Progress bar (if we have total)
        if self.state.ollama_items_total and self.state.ollama_items_total > 0:
            pct = self.state.ollama_items_processed / self.state.ollama_items_total
            filled = int(pct * 40)
            empty = 40 - filled
            text.append("  ")
            text.append("█" * filled, style="green")
            text.append("░" * empty, style="dim")
            text.append("\n")

        # LLM metrics
        text.append("\n")
        text.append("  LLM Calls: ", style="cyan")
        text.append(f"{self.state.ollama_llm_calls}", style="white")
        text.append("  │  ", style="dim")

        # Token throughput
        text.append("Tokens: ", style="cyan")
        text.append(f"{format_tokens(self.state.input_tokens)} in", style="white")
        text.append(" / ", style="dim")
        text.append(f"{format_tokens(self.state.output_tokens)} out", style="white")
        text.append("\n")

        # Latency metrics
        text.append("  Last Latency: ", style="cyan")
        if self.state.ollama_last_latency_ms > 0:
            # Format latency nicely
            latency = self.state.ollama_last_latency_ms
            if latency >= 1000:
                text.append(f"{latency/1000:.1f}s", style="white")
            else:
                text.append(f"{latency:.0f}ms", style="white")
        else:
            text.append("--", style="dim")

        text.append("  │  ", style="dim")

        text.append("Avg Latency: ", style="cyan")
        if self.state.ollama_avg_latency_ms > 0:
            avg_latency = self.state.ollama_avg_latency_ms
            if avg_latency >= 1000:
                text.append(f"{avg_latency/1000:.1f}s", style="white")
            else:
                text.append(f"{avg_latency:.0f}ms", style="white")
        else:
            text.append("--", style="dim")

        # Model name
        if self.state.model:
            text.append("\n")
            text.append("  Model: ", style="cyan")
            model_name = self.state.model.split('/')[-1] if self.state.model else "(none)"
            if len(model_name) > 40:
                model_name = model_name[:37] + "..."
            text.append(model_name, style="white")

        return text

    def update_state(self, state: OracleState):
        self.state = state
        self.refresh()


class CompetitiveConsensusPanel(Static):
    """Panel showing competitive consensus mode and live voting."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()

        # Header shows expand/collapse hint
        if self.expanded:
            text.append("COMPETITIVE CONSENSUS [EXPANDED - Press 'v' to collapse]\n", style="bold white")
        else:
            text.append("COMPETITIVE CONSENSUS [Press 'v' to expand]\n", style="bold white")

        # Mode indicator
        mode = self.state.competitive_mode
        if mode == "multi":
            text.append("  Mode: ", style="cyan")
            text.append("MULTI-MODEL", style="bold green")
            text.append(" (diverse models voting)\n", style="dim")
        elif mode == "single":
            text.append("  Mode: ", style="cyan")
            text.append("SINGLE-MODEL", style="bold yellow")
            text.append(" (same model, 3 temps)\n", style="dim")
        else:
            text.append("  Mode: ", style="cyan")
            text.append("DISABLED", style="dim")
            text.append("\n")
            return text

        # Stages enabled
        stages = self.state.competitive_stages
        if stages:
            text.append("  Stages: ", style="cyan")
            stage_strs = []
            for stage in stages:
                if stage == "characters":
                    stage_strs.append("👥 characters")
                elif stage == "structure":
                    stage_strs.append("📖 structure")
                elif stage == "summaries":
                    stage_strs.append("📝 summaries")
                else:
                    stage_strs.append(stage)
            text.append(", ".join(stage_strs), style="white")
            text.append("\n")

        # Models (for multi mode)
        models = self.state.competitive_models
        if models and mode == "multi":
            text.append("  Models: ", style="cyan")
            for i, model_spec in enumerate(models):
                if i > 0:
                    text.append(", ", style="dim")
                # Parse model:temp format
                parts = model_spec.split(":")
                model_name = ":".join(parts[:-1]) if len(parts) > 1 else parts[0]
                temp = parts[-1] if len(parts) > 1 else "0.7"
                # Shorten model name
                if len(model_name) > 15:
                    model_name = model_name[:12] + "..."
                text.append(f"{model_name}", style="white")
                text.append(f"@{temp}", style="dim cyan")
            text.append("\n")

        # Recent votes
        votes = self.state.recent_votes
        if votes:
            text.append("\n")
            # Show all votes when expanded, last 5 when collapsed
            if self.expanded:
                votes_to_show = votes
                text.append(f"  All Votes ({len(votes)}):\n", style="bold cyan")
            else:
                votes_to_show = votes[-5:]
                text.append(f"  Recent Votes ({len(votes_to_show)}/{len(votes)}):\n", style="bold cyan")

            for vote in votes_to_show:
                vote_type = vote.get('vote_type', '?')
                subject = vote.get('subject', '?')
                outcome = vote.get('outcome', '?')
                yes_count = vote.get('yes_count', 0)
                vote_count = vote.get('vote_count', 0)
                reason = vote.get('reason', '')
                context = vote.get('context', '')

                # Type icon
                if vote_type == "alias":
                    icon = "🔗"
                elif vote_type == "boundary":
                    icon = "📍"
                elif vote_type == "summary_merge":
                    icon = "📝"
                else:
                    icon = "🗳️"

                # Outcome style
                if outcome == "accepted":
                    outcome_style = "green"
                    outcome_icon = "✓"
                elif outcome == "rejected":
                    outcome_style = "red"
                    outcome_icon = "✗"
                elif outcome == "merged":
                    outcome_style = "cyan"
                    outcome_icon = "⊕"
                else:
                    outcome_style = "yellow"
                    outcome_icon = "~"

                text.append(f"    {icon} ", style="dim")

                # Subject display depends on vote type - NO truncation when expanded
                if vote_type == "alias":
                    # For alias votes, show: "alias → canonical_name"
                    text.append(f"{subject}", style="white")
                    text.append(" → ", style="dim")
                    text.append(f"{context}", style="cyan")
                else:
                    # Other vote types - just show subject
                    text.append(f"{subject}", style="white")

                # Display vote info based on type
                if vote_type == "summary_merge":
                    # Summary merges don't have binary votes - show reason instead
                    if reason:
                        text.append(f" ({reason}) ", style="dim cyan")
                    else:
                        text.append(" (merged) ", style="dim cyan")
                else:
                    # Binary votes show yes/total count
                    text.append(f" [{yes_count}/{vote_count}] ", style="dim")
                    if self.expanded and reason:
                        text.append(f"\n      → {reason}", style="dim yellow")

                if not self.expanded or vote_type != "summary_merge" or not reason:
                    text.append(f" {outcome_icon}", style=outcome_style)
                else:
                    text.append(f"  {outcome_icon}", style=outcome_style)
                text.append("\n")
        elif self.state.analysis_running:
            text.append("\n")
            text.append("  Votes: ", style="cyan")
            text.append("waiting for voting...", style="dim")
            text.append("\n")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()


class IdentityGraphPanel(Static):
    """Panel showing identity graph resolution summary."""

    def __init__(self, state: OracleState, expanded: bool = False):
        super().__init__()
        self.state = state
        self.expanded = expanded

    def render(self) -> Text:
        text = Text()
        data = self.state.identity_graph

        if not data:
            text.append("IDENTITY GRAPH ", style="bold white")
            text.append("[no data]", style="dim")
            return text

        stats = data.get("stats", {})
        groups = data.get("merge_groups", [])
        graph = data.get("graph", {})

        # Header
        if self.expanded:
            text.append("IDENTITY GRAPH [EXPANDED - Press 'g' to collapse]\n", style="bold white")
        else:
            text.append("IDENTITY GRAPH [Press 'g' to expand]\n", style="bold white")

        # Stats line
        text.append(f"  Nodes: ", style="dim")
        text.append(f"{stats.get('nodes', 0)}", style="bold cyan")
        text.append(f"  Merge edges: ", style="dim")
        text.append(f"{stats.get('merge_edges', 0)}", style="bold green")
        text.append(f"  Constraints: ", style="dim")
        text.append(f"{stats.get('constraint_edges', 0)}", style="bold red")
        text.append("\n")

        # Merge groups with actual merges
        active_groups = [g for g in groups if len(g.get("members", [])) > 1]
        if active_groups:
            text.append(f"\n  Merge Groups ({len(active_groups)} active):\n", style="bold white")
            max_groups = len(active_groups) if self.expanded else 8
            for g in active_groups[:max_groups]:
                canonical = g.get("canonical_name", "?")
                aliases = g.get("aliases", [])
                ev_count = g.get("evidence_count", 0)
                overrides = g.get("constraints_overridden", 0)

                text.append("    ✓ ", style="green")
                text.append(canonical, style="bold white")
                if aliases:
                    alias_str = ", ".join(aliases[:5])
                    if len(aliases) > 5:
                        alias_str += f" (+{len(aliases)-5})"
                    text.append(f" ← [{alias_str}]", style="dim cyan")
                text.append(f" ({ev_count} ev", style="dim")
                if overrides > 0:
                    text.append(f", {overrides} ov", style="dim yellow")
                text.append(")\n", style="dim")

            if len(active_groups) > max_groups:
                text.append(f"    ... {len(active_groups) - max_groups} more\n", style="dim")
        else:
            text.append("\n  No merge groups (all characters distinct)\n", style="dim")

        # Constraint edges
        constraint_edges = graph.get("constraint_edges", [])
        if constraint_edges and (self.expanded or len(constraint_edges) <= 5):
            text.append(f"\n  Key Constraints:\n", style="bold white")
            max_constraints = len(constraint_edges) if self.expanded else 5
            # Build node name lookup
            node_names = {n["id"]: n["name"] for n in graph.get("nodes", [])}
            for c in constraint_edges[:max_constraints]:
                src = node_names.get(c["source"], c["source"])
                tgt = node_names.get(c["target"], c["target"])
                ctype = c.get("type", "?")
                text.append("    ✗ ", style="red")
                text.append(f"{src}", style="white")
                text.append(" ≠ ", style="red")
                text.append(f"{tgt}", style="white")
                text.append(f" ({ctype})\n", style="dim")
            if len(constraint_edges) > max_constraints:
                text.append(f"    ... {len(constraint_edges) - max_constraints} more\n", style="dim")
        elif constraint_edges:
            text.append(f"\n  Constraints: {len(constraint_edges)} ", style="dim")
            text.append("[press 'g' to show]\n", style="dim cyan")

        return text

    def update_state(self, state: OracleState, expanded: bool = None):
        self.state = state
        if expanded is not None:
            self.expanded = expanded
        self.refresh()
