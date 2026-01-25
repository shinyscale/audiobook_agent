"""
F28/F29: Pronunciation Dialog with paragraph context and navigation.

Provides a tkinter dialog for viewing pronunciation entries with:
- Full paragraph context (F28)
- Word highlighting in context (F28)
- Navigation between word occurrences (F28)
- Jump to full document position (F29)
"""

import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Callable, Optional

from ..models import PronunciationEntry
from ..pipeline.pronunciation_guide.word_index import WordIndex


class PronunciationDialog:
    """
    F28: Dialog showing pronunciation with paragraph context.

    Features:
    - Full paragraph context with highlighted word
    - Navigate between multiple occurrences
    - Copy pronunciation/IPA to clipboard
    - F29: Jump to position in full document
    """

    def __init__(
        self,
        parent: tk.Tk,
        entry: PronunciationEntry,
        word_index: Optional[WordIndex] = None,
        full_text: Optional[str] = None,
        on_navigate: Optional[Callable[[int], None]] = None,
    ):
        """
        Args:
            parent: Parent tkinter window
            entry: Pronunciation entry to display
            word_index: Optional WordIndex for paragraph context
            full_text: Optional full document text for F29 navigation
            on_navigate: Optional callback when jumping to position (F29)
        """
        self.entry = entry
        self.word_index = word_index
        self.full_text = full_text
        self.on_navigate = on_navigate
        self.current_occurrence = 0

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Pronunciation: {entry.word}")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)

        self._create_widgets()
        self._update_display()

    def _create_widgets(self):
        """Build the dialog UI."""
        # Header: Word and IPA
        header = ttk.Frame(self.dialog, padding=10)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text=self.entry.word,
            font=("TkDefaultFont", 18, "bold"),
        ).pack(side=tk.LEFT)

        if self.entry.ipa:
            ttk.Label(
                header,
                text=f"  [{self.entry.ipa}]",
                font=("TkDefaultFont", 14),
            ).pack(side=tk.LEFT)

        # Notes section
        if self.entry.notes:
            notes_frame = ttk.Frame(self.dialog, padding=(10, 0, 10, 10))
            notes_frame.pack(fill=tk.X)
            ttk.Label(
                notes_frame,
                text=self.entry.notes,
                wraplength=660,
            ).pack(anchor=tk.W)

        # Context section
        context_frame = ttk.LabelFrame(
            self.dialog,
            text="Paragraph Context (F28)",
            padding=10,
        )
        context_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.context_text = scrolledtext.ScrolledText(
            context_frame,
            wrap=tk.WORD,
            height=12,
            font=("TkDefaultFont", 11),
        )
        self.context_text.pack(fill=tk.BOTH, expand=True)

        # Configure highlight tag
        self.context_text.tag_configure(
            "highlight",
            background="#ffeb3b",
            foreground="black",
            font=("TkDefaultFont", 11, "bold"),
        )

        # Navigation
        nav_frame = ttk.Frame(self.dialog, padding=10)
        nav_frame.pack(fill=tk.X)

        self.prev_btn = ttk.Button(
            nav_frame,
            text="< Previous",
            command=self._prev_occurrence,
        )
        self.prev_btn.pack(side=tk.LEFT)

        self.occurrence_label = ttk.Label(nav_frame, text="1 of 1")
        self.occurrence_label.pack(side=tk.LEFT, padx=20)

        self.next_btn = ttk.Button(
            nav_frame,
            text="Next >",
            command=self._next_occurrence,
        )
        self.next_btn.pack(side=tk.LEFT)

        # F29: Navigate to full document
        if self.on_navigate and self.full_text:
            ttk.Button(
                nav_frame,
                text="Show in Document (F29)",
                command=self._jump_to_document,
            ).pack(side=tk.RIGHT)

        # Chapter info
        self.chapter_label = ttk.Label(nav_frame, text="")
        self.chapter_label.pack(side=tk.RIGHT, padx=20)

        # Buttons
        btn_frame = ttk.Frame(self.dialog, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="Copy Word",
            command=lambda: self._copy_to_clipboard(self.entry.word),
        ).pack(side=tk.LEFT)

        if self.entry.ipa:
            ttk.Button(
                btn_frame,
                text="Copy IPA",
                command=lambda: self._copy_to_clipboard(self.entry.ipa),
            ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Close",
            command=self.dialog.destroy,
        ).pack(side=tk.RIGHT)

    def _update_display(self):
        """Update context display for current occurrence."""
        mentions = self.entry.mentions
        total = len(mentions)

        # Update navigation
        self.occurrence_label.config(text=f"{self.current_occurrence + 1} of {total}")
        self.prev_btn.config(state=tk.NORMAL if self.current_occurrence > 0 else tk.DISABLED)
        self.next_btn.config(
            state=tk.NORMAL if self.current_occurrence < total - 1 else tk.DISABLED
        )

        if not mentions:
            self.context_text.config(state=tk.NORMAL)
            self.context_text.delete(1.0, tk.END)
            self.context_text.insert(tk.END, "No context available.")
            self.context_text.config(state=tk.DISABLED)
            return

        mention = mentions[self.current_occurrence]
        self.chapter_label.config(text=f"Chapter {mention.chapter}")

        # Get paragraph context
        context_text = ""
        highlight_start = 0
        highlight_end = 0

        if self.word_index:
            para_ctx = self.word_index.extract_paragraph_context(
                mention.position,
                len(self.entry.word),
            )
            if para_ctx:
                context_text, highlight_start, highlight_end = para_ctx
                highlight_end = highlight_start + len(self.entry.word)
        else:
            # Fallback to mention context
            context_text = mention.context or f"...{self.entry.word}..."
            highlight_start = context_text.lower().find(self.entry.word.lower())
            if highlight_start >= 0:
                highlight_end = highlight_start + len(self.entry.word)

        # Update text widget
        self.context_text.config(state=tk.NORMAL)
        self.context_text.delete(1.0, tk.END)
        self.context_text.insert(tk.END, context_text)

        # Apply highlight
        if highlight_start >= 0 and highlight_end > highlight_start:
            start_idx = f"1.0+{highlight_start}c"
            end_idx = f"1.0+{highlight_end}c"
            self.context_text.tag_add("highlight", start_idx, end_idx)
            # Scroll to highlight
            self.context_text.see(start_idx)

        self.context_text.config(state=tk.DISABLED)

    def _prev_occurrence(self):
        """Navigate to previous occurrence."""
        if self.current_occurrence > 0:
            self.current_occurrence -= 1
            self._update_display()

    def _next_occurrence(self):
        """Navigate to next occurrence."""
        if self.current_occurrence < len(self.entry.mentions) - 1:
            self.current_occurrence += 1
            self._update_display()

    def _jump_to_document(self):
        """F29: Jump to position in full document."""
        if self.on_navigate and self.entry.mentions:
            mention = self.entry.mentions[self.current_occurrence]
            self.on_navigate(mention.position)

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(text)

    def show(self):
        """Show the dialog and wait for it to close."""
        self.dialog.grab_set()
        self.dialog.wait_window()


def show_pronunciation_dialog(
    parent: tk.Tk,
    entry: PronunciationEntry,
    word_index: Optional[WordIndex] = None,
    full_text: Optional[str] = None,
    on_navigate: Optional[Callable[[int], None]] = None,
):
    """
    Convenience function to show a pronunciation dialog.

    Args:
        parent: Parent tkinter window
        entry: Pronunciation entry to display
        word_index: Optional WordIndex for paragraph context
        full_text: Optional full document text for F29 navigation
        on_navigate: Optional callback when jumping to position (F29)
    """
    dialog = PronunciationDialog(
        parent=parent,
        entry=entry,
        word_index=word_index,
        full_text=full_text,
        on_navigate=on_navigate,
    )
    dialog.show()
