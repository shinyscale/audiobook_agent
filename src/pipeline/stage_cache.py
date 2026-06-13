"""
Stage cache: persist expensive per-stage artifacts (chapters, summaries) so
downstream stages can be re-run in seconds without repeating hours of LLM work.

Layout: <root>/<book_stem>/<text_hash>.<stage>.json
The text hash invalidates the cache automatically when the source text (post-
refinement) changes. Saving is best-effort and must never break an analysis.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STAGES = ("chapters", "summaries")


def text_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:12]


class StageCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, book_stem: str, text: str, stage: str) -> Path:
        safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in book_stem)
        return self.root / safe_stem / f"{text_key(text)}.{stage}.json"

    def save(self, book_stem: str, text: str, stage: str, data: dict) -> Optional[Path]:
        """Best-effort save; returns the path or None on failure."""
        try:
            path = self._path(book_stem, text, stage)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info(f"Stage cache: saved {stage} -> {path}")
            return path
        except Exception as e:
            logger.warning(f"Stage cache: failed to save {stage}: {e}")
            return None

    def load(self, book_stem: str, text: str, stage: str) -> Optional[dict]:
        """Load a cached stage artifact, or None if absent/unreadable."""
        try:
            path = self._path(book_stem, text, stage)
            if not path.exists():
                return None
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Stage cache: loaded {stage} <- {path}")
            return data
        except Exception as e:
            logger.warning(f"Stage cache: failed to load {stage}: {e}")
            return None

    def latest(self, book_stem: str, stage: str) -> Optional[dict]:
        """Load the most recently written artifact for a stage, ignoring the
        text hash. For replay tools where the exact refined text isn't at hand."""
        try:
            safe_stem = "".join(
                c if c.isalnum() or c in "-_" else "_" for c in book_stem
            )
            candidates = sorted(
                (self.root / safe_stem).glob(f"*.{stage}.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not candidates:
                return None
            with open(candidates[0], encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Stage cache: failed to load latest {stage}: {e}")
            return None
