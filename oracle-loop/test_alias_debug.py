#!/usr/bin/env python3
"""
Alias Debug Replay

Replays MainCastExtractor on cached summaries with DEBUG logging to identify
exactly which alias-blocking rules fire and why alias_quality scores 0/10.

Uses existing cached summaries from oracle-loop/state/summary_cache/ so no
summary generation is needed. Requires the extraction model (qwen2.5:32b).

Usage:
    python oracle-loop/test_alias_debug.py
"""

import json
import logging
import sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor, MainCastProfile

# Reuse ground truth and scoring from summary_experiment
from summary_experiment import EXPECTED_CHARACTERS, find_character, names_match, score_extraction

EXTRACTION_MODEL = "qwen2.5:32b"
SUMMARY_CACHE_DIR = Path(__file__).parent / "state" / "summary_cache"

# Texts with known alias failures
TARGET_TEXTS = ["cask_of_amontillado", "berenice", "monkeys_paw", "masque_of_red_death"]


def load_cached_summaries(text_name: str) -> list[str] | None:
    """Load cached summaries for a text."""
    cache_path = SUMMARY_CACHE_DIR / f"{text_name}.json"
    if not cache_path.exists():
        print(f"  No cache found: {cache_path}")
        return None
    with open(cache_path) as f:
        data = json.load(f)
    return data.get("summaries", [])


def run_debug_extraction(text_name: str, summaries: list[str], llm_client: LLMClient) -> list[MainCastProfile]:
    """Run extraction with DEBUG logging, capturing alias-related messages."""
    # Enable DEBUG logging for main_cast module
    mc_logger = logging.getLogger("src.pipeline.character_extraction_v2.main_cast")
    mc_logger.setLevel(logging.DEBUG)

    # Capture log messages
    captured = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            msg = record.getMessage()
            keywords = ["BLOCKED", "ALLOWED", "merge", "co-occur", "meta-reference",
                        "alias", "narrator", "descriptive", "semantic overlap"]
            if any(kw.lower() in msg.lower() for kw in keywords):
                captured.append(msg)

    handler = CaptureHandler()
    handler.setLevel(logging.DEBUG)
    mc_logger.addHandler(handler)

    # Also add a stream handler so we see DEBUG output live
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter("  [DEBUG] %(message)s"))
    mc_logger.addHandler(stream_handler)

    try:
        extractor = MainCastExtractor(llm_client=llm_client)
        profiles = extractor.extract(
            chapter_summaries=summaries,
            use_two_pass=True,
        )
        return profiles, captured
    finally:
        mc_logger.removeHandler(handler)
        mc_logger.removeHandler(stream_handler)


def analyze_alias_results(text_name: str, profiles: list[MainCastProfile], captured_logs: list[str]):
    """Analyze which expected aliases were found/blocked."""
    expected = EXPECTED_CHARACTERS.get(text_name, {})
    expected_aliases = expected.get("aliases", {})

    print(f"\n{'='*70}")
    print(f"  {text_name}")
    print(f"{'='*70}")

    # Show extracted profiles
    print(f"\n  Extracted {len(profiles)} characters:")
    for p in profiles:
        aliases_str = f" aliases={p.aliases}" if p.aliases else ""
        print(f"    - {p.canonical_name} ({p.role}){aliases_str}")

    # Check each expected alias
    print(f"\n  Expected alias checks:")
    total_expected = 0
    total_found = 0

    for char_name, expected_char_aliases in expected_aliases.items():
        if not expected_char_aliases:
            continue

        profile = find_character(profiles, char_name)
        if not profile:
            print(f"    {char_name}: CHARACTER NOT FOUND")
            total_expected += len(expected_char_aliases)
            continue

        for exp_alias in expected_char_aliases:
            total_expected += 1
            found = any(names_match(a, exp_alias) for a in profile.aliases)
            status = "FOUND" if found else "MISSING"
            if found:
                total_found += 1
            print(f"    {char_name} <- '{exp_alias}': {status}")

            if not found:
                # Search captured logs for why it was blocked
                relevant = [log for log in captured_logs
                            if exp_alias.lower() in log.lower() or
                            (char_name.lower() in log.lower() and "block" in log.lower())]
                if relevant:
                    for log in relevant[:3]:
                        print(f"      -> {log}")
                else:
                    print(f"      -> No blocking log found (may not have been proposed by LLM)")

    # Score
    scores = score_extraction(profiles, expected)
    print(f"\n  Scores: recall={scores['recall']}, precision={scores['precision']}, "
          f"alias_quality={scores['alias_quality']}, overall={scores['overall']}")
    print(f"  Alias match: {total_found}/{total_expected}")

    # Show relevant captured logs
    if captured_logs:
        print(f"\n  Alias-related log messages ({len(captured_logs)} total):")
        for log in captured_logs:
            print(f"    {log}")

    return scores


def main():
    from ollama_manager import load_model

    print(f"Loading extraction model: {EXTRACTION_MODEL}")
    success, load_time, msg = load_model(EXTRACTION_MODEL)
    if not success:
        print(f"Failed to load model: {msg}")
        sys.exit(1)
    print(f"Model loaded in {load_time:.1f}s")

    llm_config = LLMConfig.ollama(model=EXTRACTION_MODEL)
    llm_client = LLMClient(llm_config)

    all_scores = {}

    for text_name in TARGET_TEXTS:
        summaries = load_cached_summaries(text_name)
        if not summaries:
            print(f"\nSkipping {text_name}: no cached summaries")
            continue

        print(f"\n{'#'*70}")
        print(f"  Running extraction: {text_name} ({len(summaries)} chapters)")
        print(f"{'#'*70}")

        profiles, captured = run_debug_extraction(text_name, summaries, llm_client)
        scores = analyze_alias_results(text_name, profiles, captured)
        all_scores[text_name] = scores

    # Summary
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    for text_name, scores in all_scores.items():
        print(f"  {text_name:30s} alias_quality={scores['alias_quality']:5.2f}  overall={scores['overall']:5.2f}")


if __name__ == "__main__":
    main()
