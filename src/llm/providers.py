"""
LLM provider utilities for connection testing and model detection.
"""

import time
from enum import Enum
from typing import Optional

import requests


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# Default base URLs for each provider
DEFAULT_URLS = {
    LLMProvider.OLLAMA: "http://localhost:11434",
    LLMProvider.LM_STUDIO: "http://localhost:1234/v1",
    LLMProvider.OPENAI: "https://api.openai.com/v1",
    LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
}


def get_default_url(provider: LLMProvider) -> str:
    """Get the default base URL for a provider."""
    return DEFAULT_URLS.get(provider, DEFAULT_URLS[LLMProvider.LM_STUDIO])


def detect_available_models(provider: LLMProvider, base_url: str) -> list[str]:
    """
    Fetch available models from a local provider.

    Args:
        provider: The LLM provider
        base_url: The base URL of the provider

    Returns:
        List of model identifiers
    """
    from ..logging_config import get_llm_logger

    llm_logger = get_llm_logger()

    if provider not in (LLMProvider.OLLAMA, LLMProvider.LM_STUDIO):
        return []  # Cloud providers don't support model listing this way

    url = ""
    try:
        if provider == LLMProvider.OLLAMA:
            # Ollama uses /api/tags for listing models
            url = f"{base_url.rstrip('/')}/api/tags"
            llm_logger.log_request(url=url, method="GET", provider=provider.value)
            start_time = time.perf_counter()
            response = requests.get(url, timeout=5)
            latency_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                body=response.json() if response.ok else response.text[:200],
                error=None if response.ok else f"HTTP {response.status_code}",
            )
            if response.ok:
                data = response.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        else:
            # LM Studio uses OpenAI-compatible /v1/models
            url = f"{base_url.rstrip('/')}/models"
            llm_logger.log_request(url=url, method="GET", provider=provider.value)
            start_time = time.perf_counter()
            response = requests.get(url, timeout=5)
            latency_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                body=response.json() if response.ok else response.text[:200],
                error=None if response.ok else f"HTTP {response.status_code}",
            )
            if response.ok:
                data = response.json()
                models = data.get("data", [])
                return [m.get("id", "") for m in models if m.get("id")]
    except Exception as e:
        if url:
            llm_logger.log_response(url=url, status_code=0, latency_ms=0, error=str(e))

    return []


def detect_context_length(
    provider: LLMProvider,
    model: str,
    base_url: str,
) -> Optional[int]:
    """
    Auto-detect context length for a model from the provider.

    Args:
        provider: The LLM provider
        model: The model identifier
        base_url: The base URL of the provider

    Returns:
        Context length in tokens, or None if not detectable
    """
    import re

    if provider == LLMProvider.OLLAMA:
        try:
            # Ollama has a /api/show endpoint for model details
            # Convert /v1 URL to base Ollama URL
            ollama_base = base_url.replace("/v1", "")
            response = requests.post(f"{ollama_base}/api/show", json={"name": model}, timeout=5)
            if response.ok:
                data = response.json()
                # Context length is in model_info or parameters
                model_info = data.get("model_info", {})
                for key, value in model_info.items():
                    if "context" in key.lower() and isinstance(value, int):
                        return value
                # Also check parameters
                params = data.get("parameters", "")
                if "num_ctx" in params:
                    # Parse num_ctx from parameters string
                    match = re.search(r"num_ctx\s+(\d+)", params)
                    if match:
                        return int(match.group(1))
        except Exception:
            pass

    elif provider == LLMProvider.LM_STUDIO:
        try:
            # LM Studio returns context info in /v1/models response
            url = f"{base_url.rstrip('/')}/models"
            response = requests.get(url, timeout=5)
            if response.ok:
                data = response.json()
                for m in data.get("data", []):
                    if m.get("id") == model:
                        # LM Studio may include context_length in model data
                        ctx = m.get("context_length") or m.get("max_context_length")
                        if ctx:
                            return int(ctx)
        except Exception:
            pass

    return None


def test_connection(
    provider: LLMProvider,
    base_url: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Test connection to an LLM provider.

    Args:
        provider: The LLM provider
        base_url: The base URL of the provider
        api_key: API key (required for cloud providers)
        model: Model to test with (optional)

    Returns:
        Tuple of (success, message)
    """
    from ..logging_config import get_llm_logger

    llm_logger = get_llm_logger()

    try:
        if provider == LLMProvider.ANTHROPIC:
            # Anthropic uses /v1/messages endpoint
            url = f"{base_url.rstrip('/')}/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key or "",
                "anthropic-version": "2023-06-01",
            }
            body = {"model": model or "claude-3-haiku-20240307", "max_tokens": 1, "messages": []}
            llm_logger.log_request(
                url=url, method="POST", headers=headers, body=body, provider=provider.value
            )
            start_time = time.perf_counter()
            response = requests.post(url, json=body, headers=headers, timeout=10)
            latency_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                body=response.text[:200],
                error=(
                    None
                    if response.ok or response.status_code == 400
                    else f"HTTP {response.status_code}"
                ),
            )
            if response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 400:
                # API reached, just bad request (expected with empty messages)
                return True, "Connection successful"
            elif response.ok:
                return True, "Connection successful"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"

        elif provider == LLMProvider.OLLAMA:
            # Ollama uses /api/tags for listing models
            url = f"{base_url.rstrip('/')}/api/tags"
            llm_logger.log_request(url=url, method="GET", provider=provider.value)
            start_time = time.perf_counter()
            response = requests.get(url, timeout=10)
            latency_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                body=response.json() if response.ok else response.text[:200],
                error=None if response.ok else f"HTTP {response.status_code}",
            )

            if response.ok:
                data = response.json()
                model_count = len(data.get("models", []))
                return True, f"Connected - {model_count} model(s) available"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"

        else:
            # OpenAI-compatible providers (LM Studio, OpenAI)
            url = f"{base_url.rstrip('/')}/models"
            headers = {"Content-Type": "application/json"}
            if api_key and provider == LLMProvider.OPENAI:
                headers["Authorization"] = f"Bearer {api_key}"

            llm_logger.log_request(url=url, method="GET", headers=headers, provider=provider.value)
            start_time = time.perf_counter()
            response = requests.get(url, headers=headers, timeout=10)
            latency_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                body=response.json() if response.ok else response.text[:200],
                error=None if response.ok else f"HTTP {response.status_code}",
            )

            if response.status_code == 401:
                return False, "Invalid API key"
            elif response.ok:
                data = response.json()
                model_count = len(data.get("data", []))
                return True, f"Connected - {model_count} model(s) available"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"

    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {base_url}"
    except Exception as e:
        return False, f"Error: {str(e)}"
