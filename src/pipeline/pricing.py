"""
LLM pricing calculator for cost estimation.

Pricing data is based on publicly available pricing as of January 2025.
Prices are in USD per million tokens.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ModelPricing:
    """Pricing information for a specific model."""

    input_price_per_mtok: float  # USD per million input tokens
    output_price_per_mtok: float  # USD per million output tokens
    provider: Literal["openai", "anthropic", "ollama"]

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for given token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_mtok
        return input_cost + output_cost


# Anthropic Claude pricing (as of January 2025)
# Source: https://www.anthropic.com/pricing
ANTHROPIC_PRICING = {
    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00, "anthropic"),
    "claude-3-5-sonnet-latest": ModelPricing(3.00, 15.00, "anthropic"),
    # Claude 3.5 Haiku
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00, "anthropic"),
    "claude-3-5-haiku-latest": ModelPricing(0.80, 4.00, "anthropic"),
    # Claude 3 Opus
    "claude-3-opus-20240229": ModelPricing(15.00, 75.00, "anthropic"),
    "claude-3-opus-latest": ModelPricing(15.00, 75.00, "anthropic"),
    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": ModelPricing(3.00, 15.00, "anthropic"),
    # Claude 3 Haiku
    "claude-3-haiku-20240307": ModelPricing(0.25, 1.25, "anthropic"),
}

# OpenAI pricing (as of January 2025)
# Source: https://openai.com/api/pricing/
OPENAI_PRICING = {
    # GPT-4o
    "gpt-4o": ModelPricing(2.50, 10.00, "openai"),
    "gpt-4o-2024-11-20": ModelPricing(2.50, 10.00, "openai"),
    "gpt-4o-2024-08-06": ModelPricing(2.50, 10.00, "openai"),
    # GPT-4o mini
    "gpt-4o-mini": ModelPricing(0.150, 0.600, "openai"),
    "gpt-4o-mini-2024-07-18": ModelPricing(0.150, 0.600, "openai"),
    # GPT-4 Turbo
    "gpt-4-turbo": ModelPricing(10.00, 30.00, "openai"),
    "gpt-4-turbo-2024-04-09": ModelPricing(10.00, 30.00, "openai"),
    # GPT-4
    "gpt-4": ModelPricing(30.00, 60.00, "openai"),
    "gpt-4-0613": ModelPricing(30.00, 60.00, "openai"),
    # GPT-3.5 Turbo
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50, "openai"),
    "gpt-3.5-turbo-0125": ModelPricing(0.50, 1.50, "openai"),
    # o1 models (reasoning models)
    "o1": ModelPricing(15.00, 60.00, "openai"),
    "o1-preview": ModelPricing(15.00, 60.00, "openai"),
    "o1-mini": ModelPricing(3.00, 12.00, "openai"),
}

# Ollama models are free (run locally)
# We return zero cost but track that it's Ollama
OLLAMA_PRICING = ModelPricing(0.0, 0.0, "ollama")


def get_model_pricing(model_name: str, provider: str) -> Optional[ModelPricing]:
    """
    Get pricing information for a model.

    Args:
        model_name: Name of the model (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
        provider: Provider name ("openai", "anthropic", "ollama")

    Returns:
        ModelPricing object if found, None otherwise
    """
    if provider == "ollama":
        return OLLAMA_PRICING

    if provider == "anthropic":
        return ANTHROPIC_PRICING.get(model_name)

    if provider == "openai":
        return OPENAI_PRICING.get(model_name)

    return None


def calculate_cost(
    model_name: str, provider: str, input_tokens: int, output_tokens: int
) -> Optional[float]:
    """
    Calculate cost for LLM usage.

    Args:
        model_name: Name of the model
        provider: Provider name ("openai", "anthropic", "ollama")
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Cost in USD, or None if pricing not available
    """
    pricing = get_model_pricing(model_name, provider)
    if pricing is None:
        return None

    return pricing.calculate_cost(input_tokens, output_tokens)


def format_cost(cost_usd: Optional[float]) -> str:
    """
    Format cost for display.

    Args:
        cost_usd: Cost in USD, or None if unavailable

    Returns:
        Formatted string like "$0.0234" or "Free" or "Unknown"
    """
    if cost_usd is None:
        return "Unknown"

    if cost_usd == 0.0:
        return "Free"

    if cost_usd < 0.01:
        # Show 4 decimal places for very small costs
        return f"${cost_usd:.4f}"
    else:
        # Show 2 decimal places for normal costs
        return f"${cost_usd:.2f}"
