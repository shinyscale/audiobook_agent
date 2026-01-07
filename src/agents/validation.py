"""
Cross-agent validation types for upstream data quality checking.

This module provides types for downstream agents to validate upstream results
and trigger pipeline halts when data quality is insufficient.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"  # Pipeline must halt - cannot proceed at all
    ERROR = "error"        # Agent cannot produce meaningful output
    WARNING = "warning"    # Agent can proceed with degraded quality


@dataclass
class UpstreamValidationIssue:
    """An issue found when validating upstream agent results."""
    agent_name: str           # Which upstream agent produced problematic data
    issue_type: str           # e.g., "no_chapters", "single_giant_chapter"
    description: str          # Human-readable description
    severity: ValidationSeverity
    details: dict = field(default_factory=dict)  # Additional context for debugging

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "issue_type": self.issue_type,
            "description": self.description,
            "severity": self.severity.value,
            "details": self.details,
        }


@dataclass
class UpstreamValidationResult:
    """Result of validating upstream agent outputs."""
    valid: bool              # True if no issues found
    can_proceed: bool        # True if agent can proceed (only warnings, no errors/critical)
    issues: list[UpstreamValidationIssue] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        """Check if any critical issues exist."""
        return any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)

    @property
    def has_errors(self) -> bool:
        """Check if any error-level issues exist."""
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if any warning-level issues exist."""
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    @property
    def critical_count(self) -> int:
        """Count of critical issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        """Count of error issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "valid": self.valid,
            "can_proceed": self.can_proceed,
            "critical_count": self.critical_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class PipelineHaltReport:
    """Diagnostic report generated when pipeline halts due to validation failure."""
    halted_at: str                          # Agent name that triggered halt
    halted_reason: str                      # Primary reason for halt
    upstream_issues: list[UpstreamValidationIssue]  # All issues found
    partial_results: dict[str, Any]         # Results completed before halt
    recommendations: list[str]              # Actionable recommendations
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_markdown(self) -> str:
        """Generate markdown diagnostic report."""
        lines = []

        # Header
        lines.append("# Pipeline Halt Report")
        lines.append("")
        lines.append(f"**Halted at:** {self.halted_at} agent")
        lines.append(f"**Timestamp:** {self.timestamp}")
        lines.append("")

        # Primary reason
        lines.append("## Reason")
        lines.append("")
        lines.append(f"> {self.halted_reason}")
        lines.append("")

        # All issues
        lines.append("## Validation Issues")
        lines.append("")

        for issue in self.upstream_issues:
            severity_icon = {
                ValidationSeverity.CRITICAL: "CRITICAL",
                ValidationSeverity.ERROR: "ERROR",
                ValidationSeverity.WARNING: "WARNING",
            }.get(issue.severity, "")

            lines.append(f"### [{severity_icon}] {issue.issue_type}")
            lines.append(f"**Source:** {issue.agent_name} agent")
            lines.append(f"**Description:** {issue.description}")

            if issue.details:
                lines.append("**Details:**")
                for key, value in issue.details.items():
                    lines.append(f"  - {key}: {value}")
            lines.append("")

        # Partial results
        if self.partial_results:
            lines.append("## Completed Before Halt")
            lines.append("")
            for agent_name, result in self.partial_results.items():
                if result is not None:
                    lines.append(f"- **{agent_name}**: Completed")
                else:
                    lines.append(f"- **{agent_name}**: Not run")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by Audiobook Prep validation system*")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "halted_at": self.halted_at,
            "halted_reason": self.halted_reason,
            "timestamp": self.timestamp,
            "upstream_issues": [i.to_dict() for i in self.upstream_issues],
            "partial_results": {k: v is not None for k, v in self.partial_results.items()},
            "recommendations": self.recommendations,
        }


# Common recommendation generators
def get_recommendations_for_issue(issue: UpstreamValidationIssue) -> list[str]:
    """Generate recommendations based on issue type."""
    recommendations = []

    if issue.issue_type == "no_chapters":
        recommendations.append("Try a different LLM model for structure detection")
        recommendations.append("Check if the document format is properly supported")
        recommendations.append("Verify the document contains chapter markers")

    elif issue.issue_type == "empty_chapters":
        recommendations.append("The document may use non-standard chapter formatting")
        recommendations.append("Try enabling LLM-based chapter detection")
        recommendations.append("Check if the document is a short story without chapters")

    elif issue.issue_type == "single_giant_chapter":
        recommendations.append("Chapter markers may be in an unusual format")
        recommendations.append("Try a larger/more capable model for structure detection")
        recommendations.append("Manually inspect the document for chapter breaks")

    elif issue.issue_type == "low_confidence_chapters":
        recommendations.append("Consider using a larger model for structure detection")
        recommendations.append("Review detected chapters in TUI before proceeding")
        recommendations.append("The book may have unconventional chapter organization")

    elif issue.issue_type == "size_distribution_anomaly":
        recommendations.append("Some detected chapters may be incorrect")
        recommendations.append("Check for merged or split chapters in the output")
        recommendations.append("Review the document structure manually")

    elif issue.issue_type == "missing_result":
        recommendations.append(f"Ensure the {issue.agent_name} agent runs before this agent")
        recommendations.append("Check for errors in the upstream agent")

    return recommendations
