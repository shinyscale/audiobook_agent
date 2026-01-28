"""
Opt-in JSONL debug logging.

Several pipeline components emit rich debug events during development. Writing to a
hardcoded path is brittle and can create unexpected side effects in production runs.

This module centralizes debug logging behind an environment variable:

  AUDIOBOOK_AGENT_DEBUG_LOG=/abs/path/to/debug.jsonl

When unset, debug logging is a no-op.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_debug_log_path() -> Optional[Path]:
    raw = os.getenv("AUDIOBOOK_AGENT_DEBUG_LOG")
    if not raw:
        return None
    try:
        return Path(raw)
    except Exception:
        return None


def _get_debug_log_mirrors() -> list[Path]:
    """
    Optional comma-separated mirror paths.

    Example:
      AUDIOBOOK_AGENT_DEBUG_LOG_MIRRORS=/tmp/a.jsonl,/tmp/b.jsonl
    """
    raw = os.getenv("AUDIOBOOK_AGENT_DEBUG_LOG_MIRRORS", "").strip()
    if not raw:
        return []
    mirrors: list[Path] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            mirrors.append(Path(part))
        except Exception:
            continue
    return mirrors


def append_debug_event(event: dict[str, Any], path: Optional[str | Path] = None) -> None:
    """
    Append a single JSON event as a line to the configured debug log.

    Args:
        event: JSON-serializable dict to write.
        path: Optional override path; when not provided, uses AUDIOBOOK_AGENT_DEBUG_LOG.
    """

    paths: list[Path] = []

    if path is not None:
        paths = [Path(path)]
    else:
        primary = _get_debug_log_path()
        if primary is None:
            return
        paths = [primary] + _get_debug_log_mirrors()

    payload = json.dumps(event, ensure_ascii=False) + "\n"
    for p in paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(payload)
        except Exception:
            # Never fail the pipeline due to debug logging
            logger.debug("Failed to write debug event", exc_info=True)

