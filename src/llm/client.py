"""
Simple LLM interface for the pipeline.

This provides a clean, focused interface for LLM calls without the complexity
of the original refiner.py. Supports Ollama, OpenAI, and Anthropic.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional, Union

if TYPE_CHECKING:
    from ..pipeline.metrics import MetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: Literal["ollama", "openai", "anthropic"]
    model: str
    base_url: Optional[str] = None  # For Ollama/LM Studio
    api_key: Optional[str] = None
    temperature: float = 0.7  # Model-recommended default for local LLMs
    max_tokens: int = 8192
    context_length: int = 32768  # Context window size (num_ctx for Ollama)
    think: Optional[Union[bool, str]] = (
        None  # Reasoning control: False, True, "low", "medium", "high"
    )
    # Additional sampling parameters
    # Qwen3 defaults (applied per-request, not mutated): top_p=0.8, top_k=20, presence_penalty=1.0
    top_p: Optional[float] = None  # Nucleus sampling threshold
    top_k: Optional[int] = None  # Top-k sampling limit
    presence_penalty: Optional[float] = None  # 0-2, reduces repetition

    @classmethod
    def ollama(
        cls, model: str = "llama3.2", base_url: str = "http://localhost:11434"
    ) -> "LLMConfig":
        return cls(provider="ollama", model=model, base_url=base_url)

    @classmethod
    def openai(cls, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> "LLMConfig":
        return cls(
            provider="openai",
            model=model,
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        )

    @classmethod
    def anthropic(
        cls, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None
    ) -> "LLMConfig":
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
    latency_ms: Optional[float] = None  # Time to complete the call in milliseconds

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def total_tokens(self) -> int:
        """Total tokens used (prompt + completion)."""
        if not self.usage:
            return 0
        return self.usage.get("prompt_tokens", 0) + self.usage.get("completion_tokens", 0)


class LLMClient:
    """Simple, synchronous LLM client."""

    def __init__(self, config: LLMConfig, metrics: Optional["MetricsCollector"] = None):
        self.config = config
        self.metrics = metrics
        self._client = None

    def _get_client(self):
        """Lazy initialization of the appropriate client."""
        if self._client is not None:
            return self._client

        if self.config.provider == "ollama":
            import httpx

            self._client = httpx.Client(base_url=self.config.base_url, timeout=1200.0)
            self._httpx = httpx  # Store for error handling

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

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a query to the LLM and get a response.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt
            json_mode: Whether to request JSON output
            temperature: Optional per-call temperature override (0.0-2.0).
                         If not specified, uses config.temperature.

        Returns:
            LLMResponse with the result
        """
        start_time = time.perf_counter()

        # Use override temperature if provided, else config default
        effective_temperature = temperature if temperature is not None else self.config.temperature
        # Use override max tokens if provided, else config default
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # Write heartbeat BEFORE the blocking LLM call so monitors know we're active
        if self.metrics:
            self.metrics.record_llm_call_starting()

        try:
            if self.config.provider == "ollama":
                response = self._query_ollama(
                    prompt,
                    system,
                    json_mode=json_mode,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                )
            elif self.config.provider == "openai":
                response = self._query_openai(
                    prompt,
                    system,
                    json_mode=json_mode,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                )
            elif self.config.provider == "anthropic":
                response = self._query_anthropic(
                    prompt,
                    system,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                )
            else:
                response = LLMResponse(
                    content="",
                    model=self.config.model,
                    error=f"Unknown provider: {self.config.provider}",
                )

            # Clean thinking tags from response (for reasoning models like DeepSeek-R1, QwQ)
            if response.content:
                response.content = self._clean_thinking_tags(response.content)

            # Add timing to response
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            response.latency_ms = round(elapsed_ms, 2)

            # Auto-record token usage if metrics collector provided
            if self.metrics:
                self.metrics.record_llm_call(response)

            return response
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # Extract more detailed error information for HTTP errors
            error_msg = str(e)
            if hasattr(e, "response") and hasattr(e.response, "status_code"):
                # httpx.HTTPStatusError
                status_code = e.response.status_code
                try:
                    error_detail = e.response.text[:200] if hasattr(e.response, "text") else ""
                    if error_detail:
                        error_msg = f"Server error '{status_code}' for url '{getattr(e.response, 'url', 'unknown')}': {error_detail}"
                    else:
                        error_msg = f"Server error '{status_code}' for url '{getattr(e.response, 'url', 'unknown')}'"
                except Exception:
                    error_msg = f"Server error '{status_code}' for url '{getattr(e.response, 'url', 'unknown')}'"

            # Only log at warning level to reduce noise - individual components will handle their own error messages
            logger.debug(f"LLM query failed: {error_msg}")
            return LLMResponse(
                content="",
                model=self.config.model,
                error=error_msg,
                latency_ms=round(elapsed_ms, 2),
            )

    def _query_ollama(
        self,
        prompt: str,
        system: Optional[str],
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Query Ollama API."""
        from ..logging_config import get_llm_logger

        llm_logger = get_llm_logger()

        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{self.config.base_url}/api/chat"

        # Use provided overrides or fall back to config
        effective_temp = temperature if temperature is not None else self.config.temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # Compute effective sampling params (config values take precedence)
        effective_top_p = self.config.top_p
        effective_top_k = self.config.top_k
        effective_presence_penalty = self.config.presence_penalty

        # Auto-apply Qwen3 recommended defaults for unset params (without mutating config)
        # Qwen3 Instruct: top_p=0.8, top_k=20, presence_penalty=1.0
        model_lower = self.config.model.lower()
        if "qwen3" in model_lower:
            if effective_top_p is None:
                effective_top_p = 0.8
            if effective_top_k is None:
                effective_top_k = 20
            if effective_presence_penalty is None:
                effective_presence_penalty = 1.0

        # Build options dict, only including optional params if set
        options = {
            "temperature": effective_temp,
            "num_predict": effective_max_tokens,
            "num_ctx": self.config.context_length,
        }
        if effective_top_p is not None:
            options["top_p"] = effective_top_p
        if effective_top_k is not None:
            options["top_k"] = effective_top_k
        if effective_presence_penalty is not None:
            options["presence_penalty"] = effective_presence_penalty

        body = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        # If caller expects structured JSON, ask Ollama to enforce JSON output.
        # This materially reduces malformed/truncated "almost-JSON" outputs.
        if json_mode:
            body["format"] = "json"

        # Add think parameter if specified (Ollama API expects it at top level)
        if self.config.think is not None:
            body["think"] = self.config.think

        llm_logger.log_request(
            url=url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=body,
            provider="ollama",
            model=self.config.model,
        )

        start_time = time.perf_counter()
        response = client.post("/api/chat", json=body)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Check for HTTP errors and provide detailed error information
        if response.is_error:
            error_body = ""
            try:
                error_body = response.text[:500]  # Limit error body size
            except Exception:
                pass

            error_msg = (
                f"Server error '{response.status_code} {response.reason_phrase}' for url '{url}'"
            )
            if error_body:
                error_msg += f": {error_body}"

            # Log error response
            llm_logger.log_response(
                url=url,
                status_code=response.status_code,
                latency_ms=latency_ms,
                headers=dict(response.headers),
                body={"error": error_body} if error_body else {},
                token_usage=None,
                error=error_msg,
            )

            import httpx

            raise httpx.HTTPStatusError(
                error_msg,
                request=response.request,
                response=response,
            )

        data = response.json()

        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        }

        llm_logger.log_response(
            url=url,
            status_code=response.status_code,
            latency_ms=latency_ms,
            headers=dict(response.headers),
            body=data,
            token_usage=usage,
            error=None,
        )

        return LLMResponse(
            content=data["message"]["content"],
            model=self.config.model,
            usage=usage,
        )

    def _query_openai(
        self,
        prompt: str,
        system: Optional[str],
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Query OpenAI API."""
        from ..logging_config import get_llm_logger

        llm_logger = get_llm_logger()

        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Determine URL for logging (default OpenAI or custom base_url for LM Studio)
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"

        # Use provided overrides or fall back to config
        effective_temp = temperature if temperature is not None else self.config.temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": effective_temp,
            "max_tokens": effective_max_tokens,
        }
        if json_mode:
            # OpenAI-compatible JSON mode (works on modern OpenAI models).
            body["response_format"] = {"type": "json_object"}

        llm_logger.log_request(
            url=url,
            method="POST",
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            body=body,
            provider="openai",
            model=self.config.model,
        )

        start_time = time.perf_counter()
        create_kwargs = dict(
            model=self.config.model,
            messages=messages,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
        )
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**create_kwargs)
        latency_ms = (time.perf_counter() - start_time) * 1000

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }

        llm_logger.log_response(
            url=url,
            status_code=200,  # SDK throws on non-200
            latency_ms=latency_ms,
            headers={},
            body={"content": response.choices[0].message.content},
            token_usage=usage,
            error=None,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.config.model,
            usage=usage,
        )

    def _query_anthropic(
        self,
        prompt: str,
        system: Optional[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Query Anthropic API."""
        from ..logging_config import get_llm_logger

        llm_logger = get_llm_logger()

        client = self._get_client()

        # Use provided overrides or fall back to config
        effective_temp = temperature if temperature is not None else self.config.temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        url = "https://api.anthropic.com/v1/messages"
        body = {
            "model": self.config.model,
            "max_tokens": effective_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": effective_temp,
        }
        if system:
            body["system"] = system

        llm_logger.log_request(
            url=url,
            method="POST",
            headers={"x-api-key": self.config.api_key or ""},
            body=body,
            provider="anthropic",
            model=self.config.model,
        )

        start_time = time.perf_counter()
        response = client.messages.create(**body)
        latency_ms = (time.perf_counter() - start_time) * 1000

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }

        llm_logger.log_response(
            url=url,
            status_code=200,  # SDK throws on non-200
            latency_ms=latency_ms,
            headers={},
            body={"content": response.content[0].text},
            token_usage=usage,
            error=None,
        )

        return LLMResponse(
            content=response.content[0].text,
            model=self.config.model,
            usage=usage,
        )

    def _clean_thinking_tags(self, text: str) -> str:
        """
        Remove thinking/reasoning tags from LLM responses.

        Handles multiple formats used by different reasoning models:
        - <think>...</think> (DeepSeek-R1, Qwen3)
        - <thinking>...</thinking> (some models)
        - <reasoning>...</reasoning> (some models)
        - <|think|>...<|/think|> (some Qwen variants)
        """
        # Patterns for complete blocks (closed tags)
        closed_patterns = [
            r"<think>.*?</think>",
            r"<thinking>.*?</thinking>",
            r"<reasoning>.*?</reasoning>",
            r"<\|think\|>.*?<\|/think\|>",
        ]

        # Patterns for unclosed tags (truncated output)
        unclosed_patterns = [
            r"<think>.*$",
            r"<thinking>.*$",
            r"<reasoning>.*$",
            r"<\|think\|>.*$",
        ]

        cleaned = text
        for pattern in closed_patterns + unclosed_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

        return cleaned.strip()

    def query_json(
        self, prompt: str, system: Optional[str] = None
    ) -> tuple[Optional[Union[dict, list]], LLMResponse]:
        """Query LLM and parse response as JSON (dict or list)."""
        response = self.query(prompt, system, json_mode=True)

        if not response.success:
            return None, response

        parsed = self._extract_json(response.content)

        # Record JSON parse failure if metrics context available
        if self.metrics and self.metrics.current_stage:
            if parsed is None:
                self.metrics.current_stage.record_json_failure()

        return parsed, response

    def _extract_json(self, text: str) -> Optional[Union[dict, list]]:
        """Extract JSON from LLM response, handling common formats.

        Returns either a dict or list, depending on what the LLM returned.
        """
        # Remove thinking tags (various reasoning models)
        text = self._clean_thinking_tags(text)

        # Try to find JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1)

        # Try direct parse
        text = text.strip()
        try:
            parsed = json.loads(text)
            # Accept both dict and list
            if isinstance(parsed, (dict, list)):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON object or array
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, text)
            if match:
                try:
                    parsed = json.loads(match.group())
                    # Accept both dict and list
                    if isinstance(parsed, (dict, list)):
                        return parsed
                except json.JSONDecodeError:
                    continue

        # Try to repair common JSON issues (for dicts only)
        repaired = self._repair_json(text)
        if repaired:
            return repaired

        return None

    def _repair_json(self, text: str) -> Optional[dict]:
        """Attempt to repair common JSON formatting issues from LLMs."""
        # Find potential JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None

        json_str = match.group()

        # Common repairs:
        # 1. Remove trailing commas before } or ]
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

        # 2. Fix unquoted keys (word: value -> "word": value)
        json_str = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', json_str)

        # 3. Replace single quotes with double quotes (for string values)
        # Be careful not to replace apostrophes in text
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)

        # 4. Fix boolean/null case (True -> true, False -> false, None -> null)
        json_str = re.sub(r"\bTrue\b", "true", json_str)
        json_str = re.sub(r"\bFalse\b", "false", json_str)
        json_str = re.sub(r"\bNone\b", "null", json_str)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def test_connection(self) -> tuple[bool, str]:
        """Test if the LLM connection is working."""
        response = self.query("Reply with exactly: OK")
        if response.success:
            return True, f"Connected to {self.config.provider}/{self.config.model}"
        return False, f"Connection failed: {response.error}"

    def health_check(self) -> tuple[bool, str]:
        """
        Comprehensive health check for the model.

        Tests for common failure modes:
        - Connection failures
        - Empty responses
        - Invalid/garbled responses

        Returns:
            Tuple of (is_healthy, message)
        """
        # Test 1: Basic connection
        response = self.query("Reply with exactly: OK")
        if not response.success:
            return False, f"Connection failed: {response.error}"

        # Test 2: Check for empty response (common failure mode)
        if not response.content or len(response.content.strip()) == 0:
            return False, "Model returns empty responses"

        # Test 3: Check for garbled/invalid response
        if len(response.content.strip()) < 1:
            return False, "Model returns invalid responses (too short)"

        # Test 4: Verify model can generate coherent text
        test_response = self.query("Count to three.")
        if not test_response.success:
            return False, f"Model failed generation test: {test_response.error}"

        if not test_response.content or len(test_response.content.strip()) == 0:
            return False, "Model returns empty responses on generation test"

        # All checks passed
        return True, f"Model {self.config.model} is healthy"


def create_client(provider: str = "ollama", model: Optional[str] = None, **kwargs) -> LLMClient:
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
