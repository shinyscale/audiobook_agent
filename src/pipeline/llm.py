"""
Simple LLM interface for the pipeline.

This provides a clean, focused interface for LLM calls without the complexity
of the original refiner.py. Supports Ollama, OpenAI, and Anthropic.
"""

import json
import re
import os
from dataclasses import dataclass
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: Literal["ollama", "openai", "anthropic"]
    model: str
    base_url: Optional[str] = None  # For Ollama/LM Studio
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096

    @classmethod
    def ollama(cls, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> "LLMConfig":
        return cls(provider="ollama", model=model, base_url=base_url)

    @classmethod
    def openai(cls, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> "LLMConfig":
        return cls(
            provider="openai",
            model=model,
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        )

    @classmethod
    def anthropic(cls, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None) -> "LLMConfig":
        return cls(
            provider="anthropic",
            model=model,
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    usage: Optional[dict] = None  # Token usage if available
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class LLMClient:
    """Simple, synchronous LLM client."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy initialization of the appropriate client."""
        if self._client is not None:
            return self._client

        if self.config.provider == "ollama":
            import httpx
            self._client = httpx.Client(base_url=self.config.base_url, timeout=120.0)

        elif self.config.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,  # Needed for LM Studio compatibility
            )

        elif self.config.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.config.api_key)

        return self._client

    def query(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Send a query to the LLM and get a response."""
        try:
            if self.config.provider == "ollama":
                return self._query_ollama(prompt, system)
            elif self.config.provider == "openai":
                return self._query_openai(prompt, system)
            elif self.config.provider == "anthropic":
                return self._query_anthropic(prompt, system)
            else:
                return LLMResponse(content="", model=self.config.model, error=f"Unknown provider: {self.config.provider}")
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return LLMResponse(content="", model=self.config.model, error=str(e))

    def _query_ollama(self, prompt: str, system: Optional[str]) -> LLMResponse:
        """Query Ollama API."""
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.post(
            "/api/chat",
            json={
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=self.config.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
        )

    def _query_openai(self, prompt: str, system: Optional[str]) -> LLMResponse:
        """Query OpenAI API."""
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        )

    def _query_anthropic(self, prompt: str, system: Optional[str]) -> LLMResponse:
        """Query Anthropic API."""
        client = self._get_client()

        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        )

    def query_json(self, prompt: str, system: Optional[str] = None) -> tuple[Optional[dict], LLMResponse]:
        """Query LLM and parse response as JSON."""
        response = self.query(prompt, system)

        if not response.success:
            return None, response

        parsed = self._extract_json(response.content)
        return parsed, response

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from LLM response, handling common formats."""
        # Remove thinking tags (Qwen models)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        # Try to find JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1)

        # Try direct parse
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object or array
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        return None

    def test_connection(self) -> tuple[bool, str]:
        """Test if the LLM connection is working."""
        response = self.query("Reply with exactly: OK")
        if response.success:
            return True, f"Connected to {self.config.provider}/{self.config.model}"
        return False, f"Connection failed: {response.error}"


def create_client(
    provider: str = "ollama",
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """Factory function to create an LLM client."""
    if provider == "ollama":
        config = LLMConfig.ollama(model=model or "llama3.2", **kwargs)
    elif provider == "openai":
        config = LLMConfig.openai(model=model or "gpt-4o-mini", **kwargs)
    elif provider == "anthropic":
        config = LLMConfig.anthropic(model=model or "claude-3-5-sonnet-20241022", **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return LLMClient(config)
