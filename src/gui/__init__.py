"""
GUI module for audiobook analysis.
Provides both a Textual-based TUI and a tkinter-based desktop GUI.
"""

from .tui import run_tui, AudiobookPrepApp

try:
    from .desktop import AudiobookPrepGUI, main as desktop_main
    __all__ = ["run_tui", "AudiobookPrepApp", "AudiobookPrepGUI", "desktop_main"]
except ImportError:
    __all__ = ["run_tui", "AudiobookPrepApp"]
