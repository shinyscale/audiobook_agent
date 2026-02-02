#!/usr/bin/env python3
"""
Focused Structure Detection Experiment

Tests chapter detection across multiple models on texts with REAL chapters.
This isolates structure detection from the rest of the pipeline.
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.chapter_detection.models import ChapterMap


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


def main():
    results = {}

    # Parse command line args
    models_to_test = MODELS
    texts_to_test = list(TEST_TEXTS.keys())

    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            # Quick mode: just gatsby + frankenstein with 2 models
            texts_to_test = ["gatsby", "frankenstein"]
            models_to_test = ["qwen3-next:80b-a3b-instruct-q8_0", "qwen2.5:14b"]
        elif sys.argv[1] in TEST_TEXTS:
            texts_to_test = [sys.argv[1]]

    print("=" * 70)
    print("STRUCTURE DETECTION EXPERIMENT")
    print("=" * 70)
    print(f"Texts: {texts_to_test}")
    print(f"Models: {len(models_to_test)} models + regex baseline")
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
        print(f"Size: {text_size:,} characters ({text_size // 1000}KB)")

        results[text_name] = {"expected": expected, "models": {}}

        # Run regex-only baseline first
        print(f"\n[BASELINE] Regex-only...")
        try:
            result, elapsed = run_regex_only(text)
            score = score_result(result, expected)
            results[text_name]["models"]["regex_only"] = {
                **score,
                "time_seconds": round(elapsed, 2),
                "chapters": [c.title for c in result.chapters[:10]],  # First 10 titles
            }
            print(f"  Detected: {score['detected']} chapters | {score['status']} | Time: {elapsed:.1f}s")
            print(f"  First 5: {[c.title for c in result.chapters[:5]]}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results[text_name]["models"]["regex_only"] = {"error": str(e)}

        # Run each model
        for model in models_to_test:
            model_short = model.split(":")[0]
            print(f"\n[{model_short}] Running...")

            try:
                result, elapsed = run_structure_detection(text, model)
                score = score_result(result, expected)
                results[text_name]["models"][model] = {
                    **score,
                    "time_seconds": round(elapsed, 2),
                    "chapters": [c.title for c in result.chapters[:10]],
                }
                print(f"  Detected: {score['detected']} chapters | {score['status']} | Time: {elapsed:.1f}s")
                print(f"  First 5: {[c.title for c in result.chapters[:5]]}")
            except Exception as e:
                print(f"  ERROR: {e}")
                results[text_name]["models"][model] = {"error": str(e)}

    # Summary
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
            if text_name in results and model in results[text_name]["models"]:
                r = results[text_name]["models"][model]
                if "error" in r:
                    scores.append("ERR")
                else:
                    scores.append(f"{r['detected']}")
            else:
                scores.append("-")
        print(f"{model_short:<40} | {scores[0]:>8} | {scores[1]:>8} | {scores[2]:>8} | {scores[3]:>8}")

    # Save full results
    output_path = Path(__file__).parent / "state" / "structure_experiment_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    main()
