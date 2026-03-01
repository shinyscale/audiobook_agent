"""
Configuration for the agent architecture.

Provides per-agent configuration (model selection, parameters) and
orchestrator-level settings (quality gates, parallel execution).
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Union


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
    temperature: float = 0.7  # Model-recommended default for local LLMs
    max_tokens: int = 32768  # 32k - large enough for complex JSON responses without truncation
    context_length: int = 65536  # Context window size (num_ctx for Ollama) - 64k for larger models

    # Behavior
    enable_verification: bool = True
    max_refinement_passes: int = 3
    retry_on_low_confidence: bool = True

    # Quality thresholds
    min_acceptable_confidence: float = 0.4
    target_high_confidence_ratio: float = 0.8  # Target 80% high confidence

    # Reasoning control (for Qwen3, GPT-OSS, Nemotron)
    think_mode: Optional[Union[bool, str]] = False  # False, True, "low", "medium", "high"
    system_prompt: Optional[str] = None  # Agent-specific system prompt override

    # Additional sampling parameters (Qwen3 recommended: top_p=0.8, top_k=20)
    top_p: Optional[float] = None  # Nucleus sampling threshold
    top_k: Optional[int] = None  # Top-k sampling limit
    presence_penalty: Optional[float] = None  # 0-2, reduces repetition

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
class CompetitorModelConfig:
    """
    Configuration for a single competitor in multi-model consensus.

    Allows each competitor to use a different model (not just different temperatures),
    enabling model diversity in voting to reduce single-model bias.

    Example configurations:
        - Competitor 1: qwen3:30b-instruct @ temp 0.5 (strict)
        - Competitor 2: qwen2.5:32b @ temp 0.7 (contextual)
        - Competitor 3: llama3.1:70b @ temp 0.9 (inclusive)
    """

    model: str
    provider: str = "ollama"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    prompt_style: str = "contextual"  # strict, contextual, inclusive
    temperature: float = 0.7
    name: Optional[str] = None  # Display name for logging

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
class CompetitiveConfig:
    """
    Configuration for competitive multi-LLM execution.

    The competitive approach runs multiple LLM configurations in parallel
    and uses voting to determine consensus, preventing single-LLM hallucinations.

    This is particularly effective for alias resolution where false merges
    (e.g., "Mr. Sloane" + "Mr. McKee") can be prevented by requiring
    supermajority agreement.

    Multi-model support:
        If competitor_models is provided, each competitor can use a different model
        (not just different temperatures), enabling model diversity in voting.
    """

    # Master enable/disable
    enabled: bool = False

    # Number of parallel LLM competitors (each with different temperature + prompt style)
    num_competitors: int = 3

    # Temperature range for competitors (spread evenly)
    temperature_range: tuple[float, float] = (0.5, 0.9)

    # Multi-model configuration: explicit per-competitor models
    # If empty, falls back to single-model with different temperatures
    competitor_models: list["CompetitorModelConfig"] = field(default_factory=list)

    # Which stages use competitive approach
    competitive_proposer: bool = False  # Not yet implemented
    competitive_validation: bool = False  # Not yet implemented
    competitive_consensus: bool = True  # Most impactful - character merge decisions
    competitive_structure: bool = False  # Structure detection boundary voting
    competitive_summaries: bool = False  # Chapter summary generation (Phase 3)

    # Voting thresholds
    proposer_pool_strategy: str = "weighted"  # "union", "intersection", "weighted"
    validation_vote_threshold: float = 0.5  # Majority for validation
    consensus_merge_threshold: float = 2 / 3  # Supermajority (exactly 2/3) for character merges
    structure_vote_threshold: float = 2 / 3  # Supermajority (exactly 2/3) for boundary decisions
    summary_consensus_strategy: str = "union"  # "union", "intersection", "best" for summaries

    # Minimum text length to enable competitive mode (skip for small texts)
    min_text_length_chars: int = 10000

    def get_competitor_temperatures(self) -> list[float]:
        """
        Generate evenly spaced temperatures for competitors.

        Returns list of temperatures from temperature_range[0] to temperature_range[1].
        """
        if self.num_competitors == 1:
            return [(self.temperature_range[0] + self.temperature_range[1]) / 2]

        low, high = self.temperature_range
        step = (high - low) / (self.num_competitors - 1)
        return [low + i * step for i in range(self.num_competitors)]

    def get_competitor_configs(
        self,
        base_model: str,
        base_provider: str = "ollama",
        base_url: Optional[str] = None,
        base_api_key: Optional[str] = None,
    ) -> list["CompetitorModelConfig"]:
        """
        Return competitor configurations for multi-model consensus.

        If competitor_models is specified, returns those with automatic
        multi-model detection:
        - If all models are the same: uses strict/contextual/inclusive styles
        - If models differ: uses "neutral" style for all (model diversity is enough)

        Otherwise, generates configs using the base model with different
        temperatures and prompt styles (backward compatible behavior).

        Args:
            base_model: Default model to use if no competitor_models specified
            base_provider: Default provider
            base_url: Default base URL for API calls
            base_api_key: Default API key

        Returns:
            List of CompetitorModelConfig objects for each competitor
        """
        if self.competitor_models:
            # Check if this is true multi-model (different models)
            unique_models = set(cfg.model for cfg in self.competitor_models)
            is_multi_model = len(unique_models) > 1

            if is_multi_model:
                # Multi-model mode: override all styles to "neutral"
                # Different model architectures provide natural diversity,
                # so we don't need artificial prompt bias
                return [
                    CompetitorModelConfig(
                        model=cfg.model,
                        provider=cfg.provider,
                        base_url=cfg.base_url,
                        api_key=cfg.api_key,
                        prompt_style="neutral",  # Override to neutral
                        temperature=cfg.temperature,
                        name=cfg.name or f"{cfg.model}_neutral",
                    )
                    for cfg in self.competitor_models
                ]
            else:
                # Same model with different temps: use original styles
                return self.competitor_models

        # Fall back to single-model with different temps (backward compatible)
        # Uses the same prompt styles as COMPETITOR_CONFIGS from prompts.py
        default_styles = [
            ("precise", 0.5, "strict"),
            ("balanced", 0.7, "contextual"),
            ("inclusive", 0.9, "inclusive"),
        ]

        configs = []
        temperatures = self.get_competitor_temperatures()

        for i, temp in enumerate(temperatures):
            if i < len(default_styles):
                name, _, prompt_style = default_styles[i]
            else:
                name = f"competitor_{i}"
                prompt_style = "contextual"

            configs.append(
                CompetitorModelConfig(
                    model=base_model,
                    provider=base_provider,
                    base_url=base_url,
                    api_key=base_api_key,
                    prompt_style=prompt_style,
                    temperature=temp,
                    name=name,
                )
            )

        return configs


@dataclass
class PipelineTuningConfig:
    """
    User-tunable knobs for chunking and local context windows.

    These are deliberately independent of model context length: the goal is to let
    users empirically find a "sweet spot" for speed vs quality on their hardware/model.
    """

    # Chapter detection (LLM proposers) - character counts
    chapter_marker_chunk_chars: int = 15000
    chapter_marker_chunk_overlap_chars: int = 1000
    chapter_narrative_chunk_chars: int = 20000
    chapter_narrative_chunk_overlap_chars: int = 2000

    # Character extraction - LLM chunk size and mention context window (characters)
    character_llm_chunk_chars: int = (
        5000  # Reduced from 8000 to avoid LLM response truncation with large JSON arrays
    )
    character_mention_context_chars: int = (
        250  # Increased from 200 to 250 to capture death scenes where both entities appear (e.g., "fell prostrate in death the Prince Prospero... seizing the mummer" = 221 chars)
    )

    # Chapter summaries - chunk sizes in words
    summary_chunk_words: int = 2500
    summary_chunk_overlap_words: int = 200


@dataclass
class OrchestratorConfig:
    """
    Configuration for the agent orchestrator.

    Controls global behavior like parallel execution, quality gates,
    and default model settings.
    """

    # Default model (used when agent doesn't specify one)
    default_model: str = "qwen2.5:32b"
    default_provider: str = "ollama"
    default_base_url: str = "http://localhost:11434"
    context_length: int = 32768  # Default context window size

    # Per-agent configs (keyed by agent name)
    agent_configs: dict[str, AgentConfig] = field(default_factory=dict)

    # Experimental tuning knobs (chunk sizes, context windows)
    tuning: PipelineTuningConfig = field(default_factory=PipelineTuningConfig)

    # Execution settings
    parallel_execution: bool = False  # Enable parallel agent execution
    max_parallel_workers: int = 4  # Max threads for parallel execution
    parallel_chapter_summaries: bool = True  # Parallelize per-chapter summaries
    checkpoint_between_agents: bool = True

    # Quality gates
    enable_quality_gates: bool = True
    quality_gate_threshold: float = 0.7  # Min quality score to proceed
    max_quality_gate_retries: int = 2

    # Logging
    verbose: bool = False

    # Competitive multi-LLM configuration
    competitive: CompetitiveConfig = field(default_factory=CompetitiveConfig)

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
            default_model=os.environ.get("AUDIOBOOK_LLM_MODEL", "qwen2.5:32b"),
            default_provider=os.environ.get("AUDIOBOOK_LLM_PROVIDER", "ollama"),
            default_base_url=os.environ.get("AUDIOBOOK_LLM_BASE_URL", "http://localhost:11434"),
            parallel_execution=os.environ.get("AUDIOBOOK_PARALLEL", "").lower() == "true",
            max_parallel_workers=int(os.environ.get("AUDIOBOOK_PARALLEL_WORKERS", "4")),
            parallel_chapter_summaries=os.environ.get(
                "AUDIOBOOK_PARALLEL_SUMMARIES", "true"
            ).lower()
            != "false",
            verbose=os.environ.get("AUDIOBOOK_VERBOSE", "").lower() == "true",
        )


# Recommended model configurations for different agents
# These are suggestions based on model characteristics
# Models are listed in preference order - first available will be used
#
# NOTE on Qwen3 Instruct models:
# - Qwen3-30B-A3B-Instruct-2507 and Qwen3-Next-80B-A3B-Instruct are NON-THINKING
# - They do NOT produce <think> tags (different from base Qwen3 models)
# - LLMClient auto-applies when model contains "qwen3":
#   top_p=0.8, top_k=20, max_tokens=16384, presence_penalty=1.0
# - We still favor qwen2.5 and llama3 for stability, but Qwen3 Instruct variants are viable
RECOMMENDED_AGENT_MODELS = {
    "structure": {
        "description": "Fast model for pattern recognition and chapter detection",
        "models": ["qwen2.5:14b", "qwen2.5:7b", "llama3.2", "mistral", "gpt-oss:20b"],
        "temperature": 0.7,  # Model-recommended temperature for local LLMs
        "think_mode": False,  # Disable reasoning for speed
        "system_prompt": "You are a document structure analyzer. Extract chapter boundaries and titles from text. Return ONLY valid JSON. No commentary or explanation.",
    },
    "characters": {
        "description": "Deep narrative model for character understanding",
        "models": ["qwen2.5:32b", "qwen2.5:72b", "llama3.1:70b", "llama3.3:70b", "gpt-oss:120b"],
        "temperature": 0.7,  # Model-recommended temperature for local LLMs
        "think_mode": False,  # JSON extraction doesn't benefit from reasoning chains
        "system_prompt": "You are a literary analyst extracting character information for audiobook narration. Identify characters, aliases, and relationships. Return ONLY valid JSON with no additional text.",
    },
    "summaries": {
        "description": "Narrative-focused model for story comprehension",
        "models": ["qwen2.5:32b", "qwen2.5:72b", "llama3.1:70b", "llama3.3:70b", "llama3.2"],
        "temperature": 0.7,  # Model-recommended temperature for local LLMs
        "think_mode": False,  # Summaries should be direct
        "system_prompt": "You are a literary analyst creating chapter summaries for audiobook narration preparation. Your summaries should help a narrator understand plot, tone, and character presence. Return ONLY valid JSON.",
    },
    "pronunciation": {
        "description": "Phonetically-aware model for pronunciation",
        "models": ["qwen2.5:14b", "qwen2.5:32b", "llama3.2", "llama3.1:8b"],
        "temperature": 0.7,  # Model-recommended temperature for local LLMs
        "think_mode": False,  # Phonetic analysis is pattern-based
        "system_prompt": "You are a pronunciation expert for audiobook narration. Identify words requiring special pronunciation guidance (names, places, foreign words). Return ONLY valid JSON.",
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
            config.set_agent_config(
                agent_name,
                AgentConfig(
                    model=selected_model,
                    provider=provider,
                    base_url=base_url,
                    temperature=recommendations.get("temperature", 0.7),
                    think_mode=recommendations.get("think_mode", False),
                    system_prompt=recommendations.get("system_prompt"),
                ),
            )

    # Set default model (first available from any recommendation, or first available)
    if available_models:
        config.default_model = available_models[0]

    return config
