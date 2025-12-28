"""
Specialized Agent Architecture for Audiobook Analysis.

This module provides the foundation for task-specific agents that can:
- Use optimal models for their domain
- Self-verify their work
- Refine low-confidence results

Core Components:
- Agent: Abstract base class for all agents
- AgentContext: Input to agents (text, previous results)
- AgentResult: Output from agents with confidence metrics
- AgentConfig: Per-agent configuration
- OrchestratorConfig: Global orchestrator settings

Example:
    from src.agents import Agent, AgentContext, AgentResult

    class MyAgent(Agent):
        @property
        def name(self) -> str:
            return "my_agent"

        def run(self, context: AgentContext) -> AgentResult:
            # Do analysis...
            return AgentResult(data=my_data)
"""

from .base import (
    Agent,
    AgentContext,
    AgentResult,
    ConfidenceItem,
    ConfidenceLevel,
    VerificationIssue,
    VerificationResult,
)

from .config import (
    AgentConfig,
    OrchestratorConfig,
    RECOMMENDED_AGENT_MODELS,
    create_optimized_config,
)

__all__ = [
    # Base classes and types
    "Agent",
    "AgentContext",
    "AgentResult",
    "ConfidenceItem",
    "ConfidenceLevel",
    "VerificationIssue",
    "VerificationResult",
    # Configuration
    "AgentConfig",
    "OrchestratorConfig",
    "RECOMMENDED_AGENT_MODELS",
    "create_optimized_config",
]
