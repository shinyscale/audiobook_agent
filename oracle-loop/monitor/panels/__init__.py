"""Re-export all panel classes for convenient importing."""

from .status import StatusBar, FooterInfo
from .scores import ScorePanel, OverallProgress
from .experiment import ExperimentStatusPanel
from .analysis import OllamaActivityPanel, CompetitiveConsensusPanel, IdentityGraphPanel
from .claude import ClaudeActivityPanel, ClaudeThinkingPanel
from .diagnostics import DiagnosticMatrixPanel, StderrPanel, IssuesPanel, CommitsPanel

__all__ = [
    "StatusBar",
    "FooterInfo",
    "ScorePanel",
    "OverallProgress",
    "ExperimentStatusPanel",
    "OllamaActivityPanel",
    "CompetitiveConsensusPanel",
    "IdentityGraphPanel",
    "ClaudeActivityPanel",
    "ClaudeThinkingPanel",
    "DiagnosticMatrixPanel",
    "StderrPanel",
    "IssuesPanel",
    "CommitsPanel",
]
