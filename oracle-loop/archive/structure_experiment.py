#!/usr/bin/env python3
"""
Focused Structure Detection Experiment

Tests chapter detection across multiple models on texts with REAL chapters.
This isolates structure detection from the rest of the pipeline.

Usage:
    python oracle-loop/structure_experiment.py           # Run all models on all texts
    python oracle-loop/structure_experiment.py --quick   # Quick test: 2 models, 2 texts
    python oracle-loop/structure_experiment.py gatsby    # Run all models on one text
    python oracle-loop/structure_experiment.py --resume  # Resume from crash, skip completed

Results saved to: oracle-loop/state/structure_results.json
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.chapter_detection.models import ChapterMap


def get_chapter_titles(result: ChapterMap, limit: int = None) -> list[str]:
    """Safely extract chapter titles, handling None values."""
    if result is None or result.chapters is None:
        return []
    chapters = result.chapters[:limit] if limit else result.chapters
    return [c.title if c and c.title else "(untitled)" for c in chapters]


# Expected chapter counts (approximate - some texts have front/back matter)
# These are the ACTUAL structural divisions, not TOC entries
EXPECTED_CHAPTERS = {
    "gatsby": {"min": 9, "max": 9, "description": "9 chapters (Roman numerals)"},
    "frankenstein": {"min": 28, "max": 32, "description": "4 letters + 24 chapters + Walton conclusion"},
    "dracula": {"min": 27, "max": 27, "description": "27 chapters"},
    "don_quixote": {"min": 120, "max": 130, "description": "~126 chapters in 2 parts"},
}

# Models to test - focus on small models for structure detection
# Structure detection is mechanical (pattern matching) - may not need large models
MODELS = [
    # Tiny (< 5GB)
    "qwen3:4b-instruct",                  # 2.5 GB - can this work?
    "qwen2.5:7b",                         # 4.7 GB

    # Small (5-10 GB)
    "qwen3:8b",                           # 5.2 GB
    "qwen2.5:14b",                        # 9.0 GB
    "qwen3:14b",                          # 9.3 GB

    # Medium (13-20 GB)
    "gpt-oss:20b",                        # 13 GB
    "mistral-small3.2:24b",               # 15 GB
    "gemma3:27b",                         # 17 GB
    "qwen3:30b-instruct",                 # 18 GB

    # Large (baseline comparison)
    "qwen3-next:80b-a3b-instruct-q8_0",   # 84 GB - best overall baseline
]

# Text files to test
TEST_TEXTS = {
    "gatsby": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/gatsby.txt"),
    "frankenstein": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Frankenstein_ebook.txt"),
    "dracula": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Dracula - Bram Stoker.txt"),
    "don_quixote": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Don Quixote - Cervantes.txt"),
}


def run_structure_detection(text: str, model: str) -> tuple[ChapterMap, float]:
    """Run structure detection with a specific model, return result and time."""
    start = time.time()

    pipeline = ChapterDetectionPipeline.with_ollama(model=model)
    result = pipeline.run(text, source_file=f"test_{model}")

    elapsed = time.time() - start
    return result, elapsed


def run_regex_only(text: str) -> tuple[ChapterMap, float]:
    """Run regex-only detection (no LLM) as baseline."""
    start = time.time()

    pipeline = ChapterDetectionPipeline.deterministic_only()
    result = pipeline.run(text, source_file="test_regex")

    elapsed = time.time() - start
    return result, elapsed


def score_result(result: ChapterMap, expected: dict) -> dict:
    """Score the detection result against expected chapter count."""
    if result is None or result.chapters is None:
        return {
            "detected": 0,
            "expected": expected["description"],
            "status": "ERROR",
            "score": 0.0,
        }
    detected = len(result.chapters)
    min_expected = expected["min"]
    max_expected = expected["max"]

    if min_expected <= detected <= max_expected:
        status = "PASS"
        score = 10.0
    else:
        status = "FAIL"
        # Score based on how close we got
        if detected < min_expected:
            score = max(0, 10 * (detected / min_expected))
        else:
            score = max(0, 10 * (max_expected / detected))

    return {
        "detected": detected,
        "expected": expected["description"],
        "status": status,
        "score": round(score, 2),
    }


def generate_summary(results: dict, models_to_test: list, texts_to_test: list) -> dict:
    """Generate summary statistics from results."""
    summary = {
        "models_tested": len(models_to_test) + 1,  # +1 for regex_only
        "texts_tested": len(texts_to_test),
        "smallest_passing_model": None,
        "regex_sufficient_for": [],
        "model_pass_counts": {},
        "perfect_models": [],  # Models that pass ALL texts
    }

    all_models = ["regex_only"] + models_to_test

    # Track which texts regex passes
    for text_name in texts_to_test:
        if text_name in results:
            regex_result = results[text_name]["models"].get("regex_only", {})
            if regex_result.get("status") == "PASS":
                summary["regex_sufficient_for"].append(text_name)

    # Track pass counts and find smallest passing model
    model_sizes = {
        "regex_only": 0,
        "qwen3:4b-instruct": 2.5,
        "qwen2.5:7b": 4.7,
        "qwen3:8b": 5.2,
        "qwen2.5:14b": 9.0,
        "qwen3:14b": 9.3,
        "gpt-oss:20b": 13,
        "mistral-small3.2:24b": 15,
        "gemma3:27b": 17,
        "qwen3:30b-instruct": 18,
        "qwen3-next:80b-a3b-instruct-q8_0": 84,
    }

    for model in all_models:
        pass_count = 0
        for text_name in texts_to_test:
            if text_name in results:
                model_result = results[text_name]["models"].get(model, {})
                if model_result.get("status") == "PASS":
                    pass_count += 1

        summary["model_pass_counts"][model] = {
            "passes": pass_count,
            "total": len(texts_to_test),
            "size_gb": model_sizes.get(model, "unknown"),
        }

        # Track perfect models (pass all texts)
        if pass_count == len(texts_to_test):
            summary["perfect_models"].append(model)

    # Find smallest model that passes all tests
    if summary["perfect_models"]:
        smallest = min(
            summary["perfect_models"],
            key=lambda m: model_sizes.get(m, float("inf"))
        )
        summary["smallest_passing_model"] = smallest

    return summary


# Output path for incremental saves
OUTPUT_PATH = Path(__file__).parent / "state" / "structure_results.json"


def save_results(results: dict, models_to_test: list, texts_to_test: list):
    """Save results incrementally with updated summary."""
    # Update summary with current state
    results["summary"] = generate_summary(results["texts"], models_to_test, texts_to_test)

    # Write to file
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)


def load_existing_results() -> Optional[dict]:
    """Load existing results file if it exists."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def is_completed(results: dict, text_name: str, model: str) -> bool:
    """Check if a text/model combination has already been completed (not errored)."""
    if text_name not in results.get("texts", {}):
        return False
    model_result = results["texts"][text_name].get("models", {}).get(model)
    if model_result is None:
        return False
    # Consider it completed if it has a status that isn't ERROR
    return model_result.get("status") not in (None, "ERROR")


def main():
    # Parse command line args
    models_to_test = MODELS
    texts_to_test = list(TEST_TEXTS.keys())
    resume_mode = False

    args = sys.argv[1:]
    if "--resume" in args:
        resume_mode = True
        args.remove("--resume")

    if args:
        if args[0] == "--quick":
            # Quick mode: just gatsby + frankenstein with 2 models
            texts_to_test = ["gatsby", "frankenstein"]
            models_to_test = ["qwen3-next:80b-a3b-instruct-q8_0", "qwen2.5:14b"]
        elif args[0] in TEST_TEXTS:
            texts_to_test = [args[0]]

    # Initialize or load results
    if resume_mode:
        existing = load_existing_results()
        if existing:
            results = existing
            # Update timestamp to show when resume happened
            results["resumed_at"] = datetime.now().isoformat()
            print("Resuming from existing results...")
        else:
            print("No existing results found, starting fresh...")
            results = {
                "experiment_date": datetime.now().strftime("%Y-%m-%d"),
                "experiment_timestamp": datetime.now().isoformat(),
                "texts": {},
                "summary": {},
            }
    else:
        results = {
            "experiment_date": datetime.now().strftime("%Y-%m-%d"),
            "experiment_timestamp": datetime.now().isoformat(),
            "texts": {},
            "summary": {},
        }

    print("=" * 70)
    print("STRUCTURE DETECTION EXPERIMENT")
    print("=" * 70)
    print(f"Texts: {texts_to_test}")
    print(f"Models: {len(models_to_test)} models + regex baseline")
    if resume_mode:
        print("Mode: RESUME (skipping completed combinations)")
    print("=" * 70)

    for text_name in texts_to_test:
        text_path = TEST_TEXTS[text_name]
        expected = EXPECTED_CHAPTERS[text_name]

        print(f"\n{'='*70}")
        print(f"TEXT: {text_name}")
        print(f"Expected: {expected['description']}")
        print(f"{'='*70}")

        # Load text
        text = text_path.read_text()
        text_size = len(text)
        file_size = text_path.stat().st_size
        print(f"Size: {text_size:,} characters ({file_size // 1000}KB)")

        # Initialize or preserve existing text entry
        if text_name not in results["texts"]:
            results["texts"][text_name] = {
                "expected": expected,
                "file_size_bytes": file_size,
                "char_count": text_size,
                "models": {},
            }
        else:
            # Preserve existing models dict in resume mode
            if "models" not in results["texts"][text_name]:
                results["texts"][text_name]["models"] = {}

        # Run regex-only baseline first
        if resume_mode and is_completed(results, text_name, "regex_only"):
            print(f"\n[BASELINE] Regex-only... SKIPPED (already completed)")
        else:
            print(f"\n[BASELINE] Regex-only...")
            try:
                result, elapsed = run_regex_only(text)
                score = score_result(result, expected)
                results["texts"][text_name]["models"]["regex_only"] = {
                    **score,
                    "time_seconds": round(elapsed, 2),
                    "chapters": get_chapter_titles(result, limit=10),  # First 10 titles
                    "total_chapters_list": get_chapter_titles(result),
                }
                print(f"  Detected: {score['detected']} chapters | {score['status']} | Time: {elapsed:.1f}s")
                print(f"  First 5: {get_chapter_titles(result, limit=5)}")
            except Exception as e:
                print(f"  ERROR: {e}")
                results["texts"][text_name]["models"]["regex_only"] = {"error": str(e), "status": "ERROR"}

        # Save incrementally
        save_results(results, models_to_test, texts_to_test)

        # Run each model
        for model in models_to_test:
            model_short = model.split(":")[0]

            # Skip if already completed in resume mode
            if resume_mode and is_completed(results, text_name, model):
                print(f"\n[{model_short}] SKIPPED (already completed)")
                continue

            print(f"\n[{model_short}] Running...")

            try:
                result, elapsed = run_structure_detection(text, model)
                score = score_result(result, expected)
                results["texts"][text_name]["models"][model] = {
                    **score,
                    "time_seconds": round(elapsed, 2),
                    "chapters": get_chapter_titles(result, limit=10),
                    "total_chapters_list": get_chapter_titles(result),
                }
                print(f"  Detected: {score['detected']} chapters | {score['status']} | Time: {elapsed:.1f}s")
                print(f"  First 5: {get_chapter_titles(result, limit=5)}")
            except Exception as e:
                print(f"  ERROR: {e}")
                results["texts"][text_name]["models"][model] = {"error": str(e), "status": "ERROR"}

            # Save incrementally after each model
            save_results(results, models_to_test, texts_to_test)

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Create summary table
    print(f"\n{'Model':<40} | {'gatsby':>8} | {'franken':>8} | {'dracula':>8} | {'quixote':>8}")
    print("-" * 80)

    all_models = ["regex_only"] + models_to_test
    for model in all_models:
        model_short = model.split(":")[0][:38]
        scores = []
        for text_name in ["gatsby", "frankenstein", "dracula", "don_quixote"]:
            if text_name in results["texts"] and model in results["texts"][text_name]["models"]:
                r = results["texts"][text_name]["models"][model]
                if "error" in r:
                    scores.append("ERR")
                else:
                    status_marker = "✓" if r["status"] == "PASS" else "✗"
                    scores.append(f"{r['detected']}{status_marker}")
            else:
                scores.append("-")
        print(f"{model_short:<40} | {scores[0]:>8} | {scores[1]:>8} | {scores[2]:>8} | {scores[3]:>8}")

    # Print key findings
    print("\n" + "-" * 70)
    print("KEY FINDINGS:")
    if results["summary"].get("smallest_passing_model"):
        print(f"  Smallest model passing all texts: {results['summary']['smallest_passing_model']}")
    else:
        print(f"  No model passed all texts")

    if results["summary"].get("regex_sufficient_for"):
        print(f"  Regex-only sufficient for: {', '.join(results['summary']['regex_sufficient_for'])}")

    if results["summary"].get("perfect_models"):
        print(f"  Models passing all texts: {', '.join(results['summary']['perfect_models'])}")

    # Final save (already saved incrementally, but ensure final state is written)
    save_results(results, models_to_test, texts_to_test)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
