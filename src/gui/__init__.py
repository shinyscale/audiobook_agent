"""
GUI module for audiobook analysis.
Provides both a Textual-based TUI and a tkinter-based desktop GUI.
"""

from .tui import run_tui, AudiobookPrepApp
from .oracle_monitor import run_oracle_monitor, OracleMonitorApp

try:
    from .desktop import AudiobookPrepGUI, main as desktop_main
    from .pronunciation_dialog import PronunciationDialog, show_pronunciation_dialog
    __all__ = [
        "run_tui", "AudiobookPrepApp", "AudiobookPrepGUI", "desktop_main",
        "PronunciationDialog", "show_pronunciation_dialog",
        "run_oracle_monitor", "OracleMonitorApp",
    ]
except ImportError:
    __all__ = ["run_tui", "AudiobookPrepApp", "run_oracle_monitor", "OracleMonitorApp"]
