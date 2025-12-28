"""
Agent base classes and core types for the specialized agent architecture.

This module provides the foundation for creating task-specific agents that can:
- Use optimal models for their domain
- Self-verify their work
- Refine low-confidence results
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Generic, TypeVar
import logging

logger = logging.getLogger(__name__)

# Type variable for agent-specific result data
T = TypeVar('T')


class ConfidenceLevel(Enum):
    """Confidence levels for agent outputs."""
    HIGH = "high"      # >= 0.7
    MEDIUM = "medium"  # 0.4 - 0.7
    LOW = "low"        # < 0.4


@dataclass
class AgentContext:
    """
    Input context provided to an agent.

    Contains the document text, any previously computed results from
    upstream agents, and metadata about the analysis.
    """
    # Document content
    text: str
    source_file: str = ""

    # Results from upstream agents (keyed by agent name)
    previous_results: dict[str, Any] = field(default_factory=dict)

    # Analysis metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_result(self, agent_name: str) -> Optional[Any]:
        """Get result from a previous agent, if available."""
        return self.previous_results.get(agent_name)

    def has_result(self, agent_name: str) -> bool:
        """Check if a previous agent's result is available."""
        return agent_name in self.previous_results


@dataclass
class ConfidenceItem:
    """A single item with its confidence score."""
    item: Any
    confidence: float
    issues: list[str] = field(default_factory=list)

    @property
    def level(self) -> ConfidenceLevel:
        """Get the confidence level."""
        if self.confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.4:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


@dataclass
class AgentResult(Generic[T]):
    """
    Output from an agent's run() method.

    Contains the primary result data, confidence information, and any
    issues or warnings discovered during processing.
    """
    # The primary result data (type depends on agent)
    data: T

    # Confidence breakdown
    confidence_scores: list[float] = field(default_factory=list)
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0

    # Issues and warnings
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Processing metadata
    processing_time_seconds: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0

    @property
    def total_items(self) -> int:
        """Total number of items processed."""
        return self.high_confidence_count + self.medium_confidence_count + self.low_confidence_count

    @property
    def quality_score(self) -> float:
        """Overall quality score (0-1) based on confidence distribution."""
        if self.total_items == 0:
            return 1.0
        # Weight: high=1.0, medium=0.6, low=0.2
        weighted = (
            self.high_confidence_count * 1.0 +
            self.medium_confidence_count * 0.6 +
            self.low_confidence_count * 0.2
        )
        return weighted / self.total_items

    @property
    def has_quality_concerns(self) -> bool:
        """Check if there are quality concerns that might need attention."""
        return self.low_confidence_count > 0 or len(self.issues) > 0


@dataclass
class VerificationIssue:
    """A specific issue found during verification."""
    description: str
    severity: str = "warning"  # "error", "warning", "info"
    item_index: Optional[int] = None
    suggested_fix: Optional[str] = None


@dataclass
class VerificationResult:
    """
    Result of an agent's self-verification.

    Used to determine if refinement is needed.
    """
    passed: bool
    issues: list[VerificationIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Check if verification passed with no issues."""
        return self.passed and len(self.issues) == 0

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == "warning")


class Agent(ABC):
    """
    Abstract base class for specialized analysis agents.

    Each agent is responsible for a specific task in the analysis pipeline
    (e.g., structure detection, character extraction). Agents can:

    1. Run their core analysis task
    2. Verify their own output for quality issues
    3. Refine results when verification identifies problems

    Subclasses must implement:
    - name: Unique identifier for this agent
    - depends_on: List of agent names that must run first
    - run(): Core analysis logic
    - verify(): Self-verification logic (optional but recommended)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this agent.

        Used as a key in AgentContext.previous_results.
        """
        ...

    @property
    def depends_on(self) -> list[str]:
        """
        Names of agents that must run before this one.

        Override to declare dependencies. The orchestrator uses this
        to determine execution order.
        """
        return []

    @property
    def recommended_models(self) -> list[str]:
        """
        Models known to work well for this agent's task, in preference order.

        Override to suggest optimal models. The first available model
        will be used if no specific model is configured.
        """
        return []

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's primary task.

        Args:
            context: Input context with document text and previous results

        Returns:
            AgentResult containing the output data and quality metrics
        """
        ...

    def verify(self, result: AgentResult) -> VerificationResult:
        """
        Self-verify the result for quality issues.

        Override to add task-specific verification logic. The default
        implementation passes if there are no low-confidence items.

        Args:
            result: The result from run() to verify

        Returns:
            VerificationResult indicating if the result is acceptable
        """
        issues = []

        if result.low_confidence_count > 0:
            issues.append(VerificationIssue(
                description=f"{result.low_confidence_count} items have low confidence",
                severity="warning",
            ))

        for issue in result.issues:
            issues.append(VerificationIssue(
                description=issue,
                severity="warning",
            ))

        return VerificationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
        )

    def refine(self, result: AgentResult, issues: list[VerificationIssue]) -> AgentResult:
        """
        Refine the result to address verification issues.

        Override to add task-specific refinement logic. The default
        implementation returns the result unchanged.

        Args:
            result: The result to refine
            issues: Issues identified by verify()

        Returns:
            Refined AgentResult
        """
        logger.warning(f"{self.name}: refine() not implemented, returning original result")
        return result

    def run_with_refinement(
        self,
        context: AgentContext,
        max_passes: int = 3,
    ) -> AgentResult:
        """
        Run with automatic refinement for quality issues.

        Executes run(), then verify(), and if issues are found,
        calls refine() up to max_passes times.

        Args:
            context: Input context
            max_passes: Maximum number of run/verify/refine cycles

        Returns:
            Final AgentResult after refinement
        """
        result = self.run(context)

        for pass_num in range(max_passes - 1):
            verification = self.verify(result)

            if verification.all_passed:
                logger.debug(f"{self.name}: Verification passed on pass {pass_num + 1}")
                break

            if verification.error_count == 0:
                # Only warnings, acceptable to proceed
                logger.debug(f"{self.name}: {verification.warning_count} warnings, proceeding")
                break

            logger.info(
                f"{self.name}: Refining (pass {pass_num + 2}/{max_passes}), "
                f"{verification.error_count} errors, {verification.warning_count} warnings"
            )
            result = self.refine(result, verification.issues)

        return result
