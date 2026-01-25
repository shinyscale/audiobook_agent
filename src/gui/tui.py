"""
Terminal-based UI using Textual.
Provides a browsable interface for analysis results.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from ..models import AnalysisResult, StructureType


class StructureTree(Tree):
    """Tree view of book structure."""

    def __init__(self, result: AnalysisResult):
        super().__init__(f"📖 {result.metadata.title or 'Untitled'}")
        self.result = result
        self._build_tree()

    def _build_tree(self):
        root = self.root
        root.expand()

        # Group by type
        chapters = [e for e in self.result.structure if e.type == StructureType.CHAPTER]
        other = [e for e in self.result.structure if e.type != StructureType.CHAPTER]

        # Add chapters
        if chapters:
            for elem in chapters:
                hours = int(elem.estimated_duration_minutes // 60)
                mins = int(elem.estimated_duration_minutes % 60)
                duration = f"{hours}h {mins}m" if hours else f"{mins}m"
                label = f"Ch {elem.index}: {elem.title or '(Untitled)'} ({elem.word_count:,} words, {duration})"
                root.add(label, data=elem)

        # Add other structural elements
        if other:
            other_node = root.add("📄 Other Elements", data=None)
            for elem in other:
                label = f"{elem.type.value}: {elem.title or '(Untitled)'}"
                other_node.add(label, data=elem)


class CharacterTable(DataTable):
    """Table of characters."""

    def __init__(self, result: AnalysisResult):
        super().__init__()
        self.result = result
        self.cursor_type = "row"
        self._populate()

    def _populate(self):
        self.add_columns("Character", "Mentions", "Aliases", "First Ch.")

        for char in self.result.characters:
            aliases = ", ".join(char.aliases[:3])
            if len(char.aliases) > 3:
                aliases += f" (+{len(char.aliases) - 3})"

            self.add_row(
                char.canonical_name,
                str(char.mention_count),
                aliases or "—",
                str(char.first_appearance_chapter or "?"),
                key=char.id,
            )


class PronunciationTable(DataTable):
    """Table of pronunciation flags."""

    def __init__(self, result: AnalysisResult):
        super().__init__()
        self.result = result
        self.cursor_type = "row"
        self._populate()

    def _populate(self):
        self.add_columns("Word", "Reason", "Count", "Context")

        for pron in self.result.pronunciations[:200]:  # Limit for performance
            context = ""
            if pron.context_examples:
                context = pron.context_examples[0][:50] + "..."
            self.add_row(
                pron.word,
                pron.flag_reason.value,
                str(pron.occurrences),
                context,
                key=pron.word,
            )


class ConsensusTable(DataTable):
    """Table of consensus voting decisions."""

    def __init__(self, result: AnalysisResult):
        super().__init__()
        self.result = result
        self.cursor_type = "row"
        self._votes = []  # Store vote records for detail view
        self._populate()

    def _populate(self):
        self.add_columns("Type", "Subject", "Votes", "Outcome")

        if not self.result.consensus_log:
            self.add_row("—", "No consensus voting recorded", "—", "—", key="none")
            return

        log = self.result.consensus_log
        idx = 0

        # Add alias votes
        for vote in log.alias_votes:
            vote_str = f"{vote.get('yes_count', 0)}/{vote.get('vote_count', 0)}"
            outcome = vote.get("outcome", "unknown")
            outcome_icon = "✓" if outcome == "accepted" else "✗"
            self._votes.append(vote)
            self.add_row(
                "Alias",
                f"{vote.get('subject', '')} → {vote.get('context', '')}",
                vote_str,
                f"{outcome_icon} {outcome}",
                key=f"alias_{idx}",
            )
            idx += 1

        # Add boundary votes
        for vote in log.boundary_votes:
            vote_str = f"{vote.get('yes_count', 0)}/{vote.get('vote_count', 0)}"
            outcome = vote.get("outcome", "unknown")
            outcome_icon = "✓" if outcome == "accepted" else "✗"
            self._votes.append(vote)
            self.add_row(
                "Boundary",
                vote.get("subject", "")[:40],
                vote_str,
                f"{outcome_icon} {outcome}",
                key=f"boundary_{idx}",
            )
            idx += 1

        # Add summary votes
        for vote in log.summary_votes:
            self._votes.append(vote)
            self.add_row(
                "Summary",
                vote.get("subject", "")[:40],
                f"{vote.get('vote_count', 0)} models",
                "✓ merged",
                key=f"summary_{idx}",
            )
            idx += 1

    def get_vote_by_key(self, key: str) -> dict | None:
        """Get vote record by row key."""
        try:
            parts = key.split("_")
            if len(parts) >= 2:
                idx = int(parts[-1])
                if 0 <= idx < len(self._votes):
                    return self._votes[idx]
        except (ValueError, IndexError):
            pass
        return None


class DetailPanel(Static):
    """Panel showing details of selected item."""

    def __init__(self):
        super().__init__("")
        self.current_item = None

    def show_chapter(self, elem):
        """Display chapter details."""
        hours = int(elem.estimated_duration_minutes // 60)
        mins = int(elem.estimated_duration_minutes % 60)

        content = f"""## {elem.title or elem.type.value}

**Type:** {elem.type.value}
**Word Count:** {elem.word_count:,}
**Est. Duration:** {hours}h {mins}m
**Confidence:** {elem.confidence.value}

### Characters Present
{chr(10).join(f"• {c}" for c in elem.characters_present) if elem.characters_present else "_Not yet analyzed_"}
"""
        self.update(Markdown(content))

    def show_character(self, char):
        """Display character details."""
        descriptions = (
            "\n".join(f"• {d.text}" for d in char.descriptions[:5])
            if char.descriptions
            else "_None extracted_"
        )
        relationships = (
            "\n".join(f"• {k}: {v}" for k, v in char.relationships.items())
            if char.relationships
            else "_None extracted_"
        )
        aliases = ", ".join(char.aliases) if char.aliases else "_None_"

        content = f"""## {char.canonical_name}

**Mentions:** {char.mention_count}
**First Appears:** Chapter {char.first_appearance_chapter or "?"}
**Aliases:** {aliases}
**Confidence:** {char.confidence.value}

### Descriptions
{descriptions}

### Relationships
{relationships}
"""
        self.update(Markdown(content))

    def show_pronunciation(self, pron):
        """Display pronunciation details."""
        contexts = (
            "\n".join(f"> {ex}" for ex in pron.context_examples)
            if pron.context_examples
            else "_None_"
        )

        content = f"""## {pron.word}

**Reason:** {pron.flag_reason.value}
**Occurrences:** {pron.occurrences}
**Confidence:** {pron.confidence.value if hasattr(pron, 'confidence') else "N/A"}

### Context Examples
{contexts}

### Pronunciation Info
**IPA:** {pron.ipa or "_Not looked up_"}
**Notes:** {pron.notes or "_None_"}
"""
        self.update(Markdown(content))

    def show_consensus(self, vote: dict):
        """Display consensus vote details."""
        vote_type = vote.get("vote_type", "unknown")
        subject = vote.get("subject", "Unknown")
        context = vote.get("context", "")
        votes = vote.get("votes", [])
        threshold = vote.get("threshold", 0.67)
        outcome = vote.get("outcome", "unknown")
        reason = vote.get("reason", "")

        yes_count = vote.get("yes_count", sum(votes) if votes else 0)
        vote_count = vote.get("vote_count", len(votes) if votes else 0)
        vote_ratio = yes_count / vote_count if vote_count > 0 else 0

        outcome_emoji = "✅" if outcome == "accepted" else "❌" if outcome == "rejected" else "🔄"

        votes_str = ", ".join(["Yes" if v else "No" for v in votes]) if votes else "N/A"

        content = f"""## {outcome_emoji} {vote_type.title()} Vote

**Subject:** {subject}
{"**Context:** " + context if context else ""}

### Voting Results
- **Votes:** {yes_count}/{vote_count} ({vote_ratio:.0%})
- **Threshold:** {threshold:.0%}
- **Outcome:** {outcome.upper()}

### Individual Votes
{votes_str}

{f"**Reason:** {reason}" if reason else ""}
"""
        self.update(Markdown(content))

    def show_welcome(self, result: AnalysisResult):
        """Display welcome/overview."""
        hours = int(result.metadata.estimated_total_duration_minutes // 60)
        mins = int(result.metadata.estimated_total_duration_minutes % 60)

        chapter_count = sum(1 for e in result.structure if e.type == StructureType.CHAPTER)

        # Consensus info
        consensus_info = ""
        if result.consensus_log and result.consensus_log.enabled:
            log = result.consensus_log
            consensus_info = f"""
### Consensus Voting
- **Mode:** {log.mode}
- **Models:** {', '.join(log.models) if log.models else 'N/A'}
- **Stages:** {', '.join(log.stages) if log.stages else 'N/A'}
- **Total Votes:** {log.total_votes} ({log.accepted_count} accepted, {log.rejected_count} rejected)
"""

        content = f"""## {result.metadata.title or "Untitled"}
{"_by " + result.metadata.author + "_" if result.metadata.author else ""}

### Overview
- **Word Count:** {result.metadata.total_word_count:,}
- **Est. Duration:** {hours}h {mins}m (at {result.metadata.words_per_minute} WPM)
- **Chapters:** {chapter_count}
- **Characters:** {len(result.characters)}
- **Pronunciation Flags:** {len(result.pronunciations)}
{consensus_info}
### Navigation
- Use the **Structure** tab to browse chapters
- Use the **Characters** tab to see character details
- Use the **Pronunciation** tab to review flagged words
- Use the **Consensus** tab to review voting decisions

Select an item from any tab to see details here.
"""
        self.update(Markdown(content))


class AudiobookPrepApp(App):
    """Main TUI application."""

    CSS = """
    #sidebar {
        width: 45;
        dock: left;
        background: $surface;
        border-right: solid $primary;
    }

    #main {
        padding: 1;
    }

    Tree {
        padding: 1;
    }

    DataTable {
        height: 100%;
    }

    #detail {
        padding: 1;
        border: solid $primary;
        height: 100%;
        overflow-y: auto;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        height: 100%;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "toggle_sidebar", "Toggle Sidebar"),
    ]

    def __init__(self, result: AnalysisResult):
        super().__init__()
        self.result = result
        self.title = f"Audiobook Prep - {result.metadata.title or 'Analysis'}"

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="sidebar"):
                with TabbedContent():
                    with TabPane("Structure", id="tab-structure"):
                        yield StructureTree(self.result)
                    with TabPane("Characters", id="tab-chars"):
                        yield CharacterTable(self.result)
                    with TabPane("Pronunciation", id="tab-pron"):
                        yield PronunciationTable(self.result)
                    with TabPane("Consensus", id="tab-consensus"):
                        yield ConsensusTable(self.result)

            with ScrollableContainer(id="main"):
                yield DetailPanel()

        yield Footer()

    def on_mount(self):
        """Show welcome message on mount."""
        detail = self.query_one(DetailPanel)
        detail.show_welcome(self.result)

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle tree selection."""
        if event.node.data:
            self.query_one(DetailPanel).show_chapter(event.node.data)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle table row selection."""
        table = event.data_table

        if isinstance(table, CharacterTable):
            # Find character by ID
            char_id = event.row_key.value
            for char in self.result.characters:
                if char.id == char_id:
                    self.query_one(DetailPanel).show_character(char)
                    break

        elif isinstance(table, PronunciationTable):
            # Find pronunciation by word
            word = event.row_key.value
            for pron in self.result.pronunciations:
                if pron.word == word:
                    self.query_one(DetailPanel).show_pronunciation(pron)
                    break

        elif isinstance(table, ConsensusTable):
            # Get vote record by key
            vote = table.get_vote_by_key(event.row_key.value)
            if vote:
                self.query_one(DetailPanel).show_consensus(vote)

    def action_toggle_sidebar(self):
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display


def run_tui(result: AnalysisResult):
    """Launch the TUI with analysis results."""
    app = AudiobookPrepApp(result)
    app.run()


# CLI integration
if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python -m src.gui.tui <analysis.json>")
        sys.exit(1)

    # Load analysis from JSON file
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)

    # Convert to AnalysisResult
    result = AnalysisResult(**data)
    run_tui(result)
