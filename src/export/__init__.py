"""
Export module for audiobook analysis.
Provides HTML report generation.
"""

from .html_report import export_html_report
from .pronunciation_html import generate_pronunciation_html

__all__ = ["export_html_report", "generate_pronunciation_html"]
