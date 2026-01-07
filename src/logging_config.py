"""
LLM Debug Logging Configuration.

Provides comprehensive request/response logging for LLM API calls.
Outputs to both console (stderr) and rotating log file.
"""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional


# Sensitive headers that should have values redacted
SENSITIVE_HEADERS = {'authorization', 'x-api-key', 'api-key'}

# Global logger instance
_llm_logger: Optional['LLMDebugLogger'] = None


def redact_headers(headers: dict) -> dict:
    """
    Redact sensitive values from headers for safe logging.

    Shows first 4 characters of API keys, masks the rest.
    """
    if not headers:
        return {}

    result = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS and value:
            # Show first 4 chars, mask the rest
            if len(value) > 8:
                result[key] = value[:4] + '*' * (len(value) - 4)
            else:
                result[key] = '****'
        else:
            result[key] = value
    return result


def truncate_body(body: Any, max_length: int = 500) -> str:
    """
    Truncate body content for logging.

    Converts to string/JSON and truncates if needed.
    """
    if body is None:
        return ""

    if isinstance(body, (dict, list)):
        try:
            text = json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(body)
    elif isinstance(body, bytes):
        try:
            text = body.decode('utf-8')
        except UnicodeDecodeError:
            return f"[binary data, {len(body)} bytes]"
    else:
        text = str(body)

    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


class LLMDebugLogger:
    """
    Logger for LLM API requests and responses.

    Provides structured logging with request/response details,
    timing information, and token usage tracking.
    """

    def __init__(self, enabled: bool = False):
        self._enabled = enabled
        self._logger = logging.getLogger('llm_debug')
        self._logger.setLevel(logging.DEBUG)
        self._file_handler: Optional[RotatingFileHandler] = None
        self._console_handler: Optional[logging.StreamHandler] = None

        if enabled:
            self._setup_handlers()

    def _setup_handlers(self):
        """Configure file and console handlers."""
        # Avoid duplicate handlers
        if self._file_handler or self._console_handler:
            return

        # Create log directory
        log_dir = Path.home() / '.audiobook-prep'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'llm.log'

        # Format for log messages
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler with rotation (10MB max, 3 backups)
        self._file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

        # Console handler (stderr)
        self._console_handler = logging.StreamHandler(sys.stderr)
        self._console_handler.setLevel(logging.DEBUG)
        self._console_handler.setFormatter(formatter)
        self._logger.addHandler(self._console_handler)

        # Prevent propagation to root logger
        self._logger.propagate = False

    def _remove_handlers(self):
        """Remove handlers when disabling."""
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

        if self._console_handler:
            self._logger.removeHandler(self._console_handler)
            self._console_handler = None

    def enable(self):
        """Enable logging at runtime."""
        if not self._enabled:
            self._enabled = True
            self._setup_handlers()

    def disable(self):
        """Disable logging at runtime."""
        if self._enabled:
            self._enabled = False
            self._remove_handlers()

    @property
    def enabled(self) -> bool:
        """Check if logging is enabled."""
        return self._enabled

    def log_request(
        self,
        url: str,
        method: str,
        headers: Optional[dict] = None,
        body: Any = None,
        provider: str = "",
        model: str = "",
    ):
        """
        Log an outgoing LLM API request.

        Args:
            url: The request URL
            method: HTTP method (GET, POST, etc.)
            headers: Request headers (will be redacted)
            body: Request body (will be truncated)
            provider: LLM provider name (ollama, openai, anthropic)
            model: Model name being used
        """
        if not self._enabled:
            return

        redacted = redact_headers(headers or {})
        body_preview = truncate_body(body)

        lines = [f"REQUEST: {method} {url}"]
        if provider or model:
            lines.append(f"    Provider: {provider}" + (f" | Model: {model}" if model else ""))
        if redacted:
            lines.append(f"    Headers: {json.dumps(redacted)}")
        if body_preview:
            lines.append(f"    Body: {body_preview}")

        self._logger.debug('\n'.join(lines))

    def log_response(
        self,
        url: str,
        status_code: int,
        latency_ms: float,
        headers: Optional[dict] = None,
        body: Any = None,
        token_usage: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        """
        Log an LLM API response.

        Args:
            url: The request URL (for correlation)
            status_code: HTTP status code
            latency_ms: Request latency in milliseconds
            headers: Response headers
            body: Response body (will be truncated)
            token_usage: Token usage dict with prompt_tokens, completion_tokens
            error: Error message if request failed
        """
        if not self._enabled:
            return

        status_text = "OK" if 200 <= status_code < 300 else "ERROR"
        lines = [f"RESPONSE: {status_code} {status_text} ({latency_ms:.0f}ms)"]

        if token_usage:
            prompt = token_usage.get('prompt_tokens', 0)
            completion = token_usage.get('completion_tokens', 0)
            total = prompt + completion
            lines.append(f"    Tokens: prompt={prompt}, completion={completion}, total={total}")

        if error:
            lines.append(f"    Error: {error}")

        body_preview = truncate_body(body)
        if body_preview and not error:
            lines.append(f"    Body: {body_preview}")

        self._logger.debug('\n'.join(lines))


def setup_llm_logging(enabled: bool = False) -> LLMDebugLogger:
    """
    Set up LLM debug logging.

    Call this early in application startup (CLI main, GUI init).

    Args:
        enabled: Whether to enable logging immediately

    Returns:
        The global LLMDebugLogger instance
    """
    global _llm_logger

    if _llm_logger is None:
        _llm_logger = LLMDebugLogger(enabled=enabled)
    elif enabled and not _llm_logger.enabled:
        _llm_logger.enable()

    return _llm_logger


def get_llm_logger() -> LLMDebugLogger:
    """
    Get the global LLM debug logger instance.

    Creates a disabled logger if setup_llm_logging() hasn't been called.

    Returns:
        The global LLMDebugLogger instance
    """
    global _llm_logger

    if _llm_logger is None:
        _llm_logger = LLMDebugLogger(enabled=False)

    return _llm_logger


def set_llm_debug_enabled(enabled: bool):
    """
    Enable or disable LLM debug logging at runtime.

    Used by GUI checkbox to toggle logging.

    Args:
        enabled: Whether to enable logging
    """
    logger = get_llm_logger()
    if enabled:
        logger.enable()
    else:
        logger.disable()


# Pipeline logging for diagnostic output
_pipeline_handlers: list[logging.Handler] = []


def setup_pipeline_logging(level: str = "INFO", to_file: bool = True) -> None:
    """
    Configure logging for pipeline modules (chapter detection, character extraction, etc.).

    This enables the diagnostic logging we added to track chapter detection,
    character merging, and other pipeline operations.

    Args:
        level: Logging level ("DEBUG", "INFO", "WARNING")
        to_file: Also write to ~/.audiobook-prep/pipeline.log
    """
    global _pipeline_handlers

    # Remove any existing handlers first
    disable_pipeline_logging()

    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler (stderr)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(formatter)
    _pipeline_handlers.append(console)

    # File handler (optional)
    if to_file:
        log_dir = Path.home() / '.audiobook-prep'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'pipeline.log'

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(formatter)
        _pipeline_handlers.append(file_handler)

    # All pipeline loggers we added diagnostic messages to
    pipeline_loggers = [
        'src.pipeline.chapter_detection.profiler',
        'src.pipeline.chapter_detection.proposers.regex',
        'src.pipeline.chapter_detection.validator',
        'src.pipeline.chapter_detection.consensus',
        'src.pipeline.character_extraction.consensus',
        'src.ingestion.pdf_spacing',
    ]

    for logger_name in pipeline_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        for handler in _pipeline_handlers:
            logger.addHandler(handler)
        logger.propagate = False


def disable_pipeline_logging() -> None:
    """Disable pipeline logging and remove handlers."""
    global _pipeline_handlers

    pipeline_loggers = [
        'src.pipeline.chapter_detection.profiler',
        'src.pipeline.chapter_detection.proposers.regex',
        'src.pipeline.chapter_detection.validator',
        'src.pipeline.chapter_detection.consensus',
        'src.pipeline.character_extraction.consensus',
        'src.ingestion.pdf_spacing',
    ]

    for logger_name in pipeline_loggers:
        logger = logging.getLogger(logger_name)
        for handler in _pipeline_handlers:
            logger.removeHandler(handler)

    # Close file handlers
    for handler in _pipeline_handlers:
        if isinstance(handler, RotatingFileHandler):
            handler.close()

    _pipeline_handlers = []


def set_pipeline_logging_enabled(enabled: bool, level: str = "INFO") -> None:
    """
    Enable or disable pipeline logging at runtime.

    Used by GUI checkbox to toggle logging.

    Args:
        enabled: Whether to enable logging
        level: Logging level when enabling
    """
    if enabled:
        setup_pipeline_logging(level=level)
    else:
        disable_pipeline_logging()
