"""
GUI module for audiobook analysis.
Provides both a Textual-based TUI and a tkinter-based desktop GUI.
"""

from .tui import AudiobookPrepApp, run_tui

try:
    from .desktop import AudiobookPrepGUI
    from .desktop import main as desktop_main
    from .pronunciation_dialog import PronunciationDialog, show_pronunciation_dialog

    __all__ = [
        "run_tui",
        "AudiobookPrepApp",
        "AudiobookPrepGUI",
        "desktop_main",
        "PronunciationDialog",
        "show_pronunciation_dialog",
    ]
except ImportError:
    __all__ = ["run_tui", "AudiobookPrepApp"]
