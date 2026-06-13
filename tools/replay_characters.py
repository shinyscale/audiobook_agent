#!/usr/bin/env python3
"""
Replay the character-extraction stage from cached chapter/summary artifacts.

Skips ingestion, chapter detection, and summarization (the hours-long LLM
stages) and re-runs ONLY character extraction — turning the iteration loop on
character/alias logic from hours into seconds-to-minutes.

Usage:
  python tools/replay_characters.py <book.txt> \
      [--cache-root output/stage_cache] \
      [--model qwen3.5:35b-a3b] \
      [--golden validation/golden/<book>.json]

Requires a prior full run of the book (the analyzer persists stage artifacts
automatically), or summaries placed in the cache by other means.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.base import AgentContext  # noqa: E402
from src.agents.characters import CharacterAgent  # noqa: E402
from src.llm.client import LLMClient, LLMConfig  # noqa: E402
from src.pipeline.chapter_detection.models import ChapterMap  # noqa: E402
from src.pipeline.chapter_summary.models import ChapterSummaryMap  # noqa: E402
from src.pipeline.stage_cache import StageCache  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("book", help="source text file (txt) used in the original run")
    ap.add_argument("--cache-root", default="output/stage_cache")
    ap.add_argument("--model", default="qwen3.5:35b-a3b", help="ollama model for extraction")
    ap.add_argument("--golden", help="golden truth json to score against")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )

    book = Path(args.book)
    if book.suffix.lower() == ".txt":
        text = book.read_text(encoding="utf-8", errors="replace")
    else:
        # PDF/DOCX/EPUB: reproduce the refined text the pipeline actually saw
        from src.ingestion import get_ingester
        from src.ingestion.refine import refine_extracted_document

        doc = refine_extracted_document(get_ingester(book).extract(book))
        text = doc.text
    cache = StageCache(args.cache_root)

    summaries_data = cache.load(book.stem, text, "summaries") or cache.latest(
        book.stem, "summaries"
    )
    if not summaries_data:
        print(f"ERROR: no cached summaries for '{book.stem}' under {args.cache_root}")
        print("Run a full analysis once first — the analyzer persists stage artifacts.")
        return 1
    summary_map = ChapterSummaryMap.from_dict(summaries_data)

    chapters_data = cache.load(book.stem, text, "chapters") or cache.latest(
        book.stem, "chapters"
    )
    chapter_map = ChapterMap.from_dict(chapters_data) if chapters_data else None

    print(
        f"Replaying characters: {book.stem} | {len(summary_map.summaries)} cached "
        f"summaries | chapters: {'yes' if chapter_map else 'no'} | model: {args.model}"
    )

    llm = LLMClient(LLMConfig.ollama(model=args.model))
    agent = CharacterAgent(llm_client=llm)
    context = AgentContext(
        text=text,
        source_file=str(book),
        chapter_map=chapter_map,
        previous_results={"summaries": summary_map},
    )
    result = agent.run(context)
    char_map = result.data

    chars = list(getattr(char_map, "characters", None) or [])
    chars.sort(key=lambda c: -(getattr(c, "mention_count", 0) or 0))
    print(f"\n=== {len(chars)} characters ===")
    for c in chars[:30]:
        print(
            f"  {c.canonical_name:30} role={getattr(c, 'role', '?'):12} "
            f"mentions={getattr(c, 'mention_count', 0):4}  aliases={list(c.aliases or [])}"
        )

    if args.golden:
        from src.pipeline.golden_score import format_score, score_against_truth

        analysis = {
            "characters": [
                {
                    "id": getattr(c, "id", None),
                    "canonical_name": c.canonical_name,
                    "aliases": list(c.aliases or []),
                    "role": getattr(c, "role", None),
                    "mention_count": getattr(c, "mention_count", 0) or 0,
                }
                for c in chars
            ],
            "narrator_character_id": getattr(char_map, "narrator_character_id", None),
        }
        truth = json.loads(Path(args.golden).read_text())
        print()
        print(format_score(score_against_truth(analysis, truth)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
