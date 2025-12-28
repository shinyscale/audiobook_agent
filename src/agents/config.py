"""
Configuration for the agent architecture.

Provides per-agent configuration (model selection, parameters) and
orchestrator-level settings (quality gates, parallel execution).
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class AgentConfig:
    """
    Configuration for a specific agent.

    Each agent can have its own model, temperature, and behavior settings.
    This allows optimizing each agent for its specific task.
    """
    # Model selection
    model: Optional[str] = None  # None = use orchestrator default
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None

    # Model parameters
    temperature: float = 0.3
    max_tokens: int = 4096

    # Behavior
    enable_verification: bool = True
    max_refinement_passes: int = 3
    retry_on_low_confidence: bool = True

    # Quality thresholds
    min_acceptable_confidence: float = 0.4
    target_high_confidence_ratio: float = 0.8  # Target 80% high confidence

    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY")
        if self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY")
        return None


@dataclass
class OrchestratorConfig:
    """
    Configuration for the agent orchestrator.

    Controls global behavior like parallel execution, quality gates,
    and default model settings.
    """
    # Default model (used when agent doesn't specify one)
    default_model: str = "llama3.2"
    default_provider: str = "ollama"
    default_base_url: str = "http://localhost:11434"

    # Per-agent configs (keyed by agent name)
    agent_configs: dict[str, AgentConfig] = field(default_factory=dict)

    # Execution settings
    parallel_execution: bool = False  # Start with sequential for simplicity
    checkpoint_between_agents: bool = True

    # Quality gates
    enable_quality_gates: bool = True
    quality_gate_threshold: float = 0.7  # Min quality score to proceed
    max_quality_gate_retries: int = 2

    # Logging
    verbose: bool = False

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Get configuration for a specific agent.

        Returns the agent-specific config if defined, otherwise
        returns a default config using orchestrator defaults.
        """
        if agent_name in self.agent_configs:
            return self.agent_configs[agent_name]

        # Return default config
        return AgentConfig(
            model=self.default_model,
            provider=self.default_provider,
            base_url=self.default_base_url,
        )

    def set_agent_config(self, agent_name: str, config: AgentConfig) -> None:
        """Set configuration for a specific agent."""
        self.agent_configs[agent_name] = config

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - AUDIOBOOK_LLM_MODEL: Default model name
        - AUDIOBOOK_LLM_PROVIDER: Provider (ollama, openai, anthropic)
        - AUDIOBOOK_LLM_BASE_URL: Base URL for Ollama
        - AUDIOBOOK_PARALLEL: Enable parallel execution (true/false)
        - AUDIOBOOK_VERBOSE: Verbose logging (true/false)
        """
        return cls(
            default_model=os.environ.get("AUDIOBOOK_LLM_MODEL", "llama3.2"),
            default_provider=os.environ.get("AUDIOBOOK_LLM_PROVIDER", "ollama"),
            default_base_url=os.environ.get("AUDIOBOOK_LLM_BASE_URL", "http://localhost:11434"),
            parallel_execution=os.environ.get("AUDIOBOOK_PARALLEL", "").lower() == "true",
            verbose=os.environ.get("AUDIOBOOK_VERBOSE", "").lower() == "true",
        )


# Recommended model configurations for different agents
# These are suggestions based on model characteristics
RECOMMENDED_AGENT_MODELS = {
    "structure": {
        "description": "Fast model for pattern recognition and chapter detection",
        "models": ["qwen2.5:7b", "llama3.2", "mistral"],
        "temperature": 0.2,  # Low for consistency
    },
    "characters": {
        "description": "Deep narrative model for character understanding",
        "models": ["qwen2.5:72b", "llama3.1:70b", "qwen2.5:32b"],
        "temperature": 0.3,
    },
    "summaries": {
        "description": "Narrative-focused model for story comprehension",
        "models": ["llama3.1:70b", "qwen2.5:72b", "llama3.2"],
        "temperature": 0.4,  # Slightly higher for natural language
    },
    "pronunciation": {
        "description": "Phonetically-aware model for pronunciation",
        "models": ["qwen2.5:32b", "qwen2.5:14b", "llama3.2"],
        "temperature": 0.2,  # Low for accuracy
    },
}


def create_optimized_config(
    available_models: list[str],
    provider: str = "ollama",
    base_url: str = "http://localhost:11434",
) -> OrchestratorConfig:
    """
    Create an orchestrator config optimized for available models.

    Attempts to assign the best available model to each agent based on
    the RECOMMENDED_AGENT_MODELS mapping.

    Args:
        available_models: List of model names available on the system
        provider: LLM provider
        base_url: Base URL for the provider

    Returns:
        OrchestratorConfig with agent-specific settings
    """
    config = OrchestratorConfig(
        default_provider=provider,
        default_base_url=base_url,
    )

    # Normalize available models for matching
    available_set = set(m.lower() for m in available_models)

    for agent_name, recommendations in RECOMMENDED_AGENT_MODELS.items():
        # Find first available recommended model
        selected_model = None
        for model in recommendations["models"]:
            if model.lower() in available_set:
                selected_model = model
                break

        if selected_model:
            config.set_agent_config(agent_name, AgentConfig(
                model=selected_model,
                provider=provider,
                base_url=base_url,
                temperature=recommendations.get("temperature", 0.3),
            ))

    # Set default model (first available from any recommendation, or first available)
    if available_models:
        config.default_model = available_models[0]

    return config
