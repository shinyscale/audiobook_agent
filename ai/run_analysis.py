#!/usr/bin/env python3
"""
Run the audiobook analysis pipeline and save results for evaluation.

This script runs the pipeline only. Evaluation is performed by Claude Code
directly, using its literary knowledge to assess output quality.

Usage:
    python ai/run_analysis.py gatsby
    python ai/run_analysis.py frankenstein --model qwen2.5:72b
    python ai/run_analysis.py Test_Texts/custom_book.txt
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer import AudiobookAnalyzer
from src.agents.config import OrchestratorConfig


# Book name to path mapping
BOOK_PATHS = {
    "gatsby": "Test_Texts/gatsby.txt",
    "frankenstein": "Test_Texts/frankenstein.txt",
}


def run_analysis(
    book_path: str,
    model: str = "qwen2.5:14b",
    output_dir: str = "ai/eval_results",
    verbose: bool = False,
) -> str:
    """
    Run the full analysis pipeline on a book.

    Returns path to the output JSON file.
    """
    config = OrchestratorConfig(default_model=model)

    analyzer = AudiobookAnalyzer(
        llm_refine=True,
        orchestrator_config=config,
    )

    book_name = Path(book_path).stem
    print(f"{'='*60}")
    print(f"AUDIOBOOK ANALYSIS")
    print(f"{'='*60}")
    print(f"Book: {book_path}")
    print(f"Model: {model}")
    print(f"Output: {output_dir}/")
    print(f"{'='*60}")
    print()

    start_time = datetime.now()
    result = analyzer.analyze(book_path)
    duration = (datetime.now() - start_time).total_seconds()

    # Convert result to dict
    if hasattr(result, "to_dict"):
        result_dict = result.to_dict()
    elif hasattr(result, "__dict__"):
        # Fallback for dataclasses
        import dataclasses
        if dataclasses.is_dataclass(result):
            result_dict = dataclasses.asdict(result)
        else:
            result_dict = result.__dict__
    else:
        result_dict = {"error": "Could not serialize result"}

    # Add metadata
    result_dict["_harness_metadata"] = {
        "book_path": str(book_path),
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration,
    }

    # Save output
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/{book_name}_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)

    # Also save as "latest" for easy access
    latest_path = f"{output_dir}/{book_name}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)

    # Print summary
    print()
    print(f"{'='*60}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Output: {output_path}")
    print(f"Latest: {latest_path}")

    # Quick stats
    structure = result_dict.get("structure", [])
    characters = result_dict.get("characters", [])
    pronunciations = result_dict.get("pronunciations", [])

    print()
    print(f"Quick stats:")
    print(f"  Chapters/sections: {len(structure)}")
    print(f"  Characters: {len(characters)}")
    print(f"  Pronunciations: {len(pronunciations)}")

    print()
    print(f"{'='*60}")
    print(f"NEXT STEP: Ask Claude Code to evaluate")
    print(f"{'='*60}")
    print()
    print(f"Example prompts:")
    print(f"  'Evaluate {latest_path} for chapter detection'")
    print(f"  'Evaluate character extraction in {latest_path}'")
    print(f"  'Run full evaluation on {book_name}'")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Run audiobook analysis pipeline for harness evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai/run_analysis.py gatsby
  python ai/run_analysis.py frankenstein --model qwen2.5:72b
  python ai/run_analysis.py Test_Texts/my_book.txt --model llama3.2
        """,
    )
    parser.add_argument(
        "book",
        help="Book name (gatsby, frankenstein) or path to text file",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:14b",
        help="LLM model for analysis (default: qwen2.5:14b)",
    )
    parser.add_argument(
        "--output",
        default="ai/eval_results",
        help="Output directory (default: ai/eval_results)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output",
    )

    args = parser.parse_args()

    # Resolve book path
    book_path = args.book
    if args.book.lower() in BOOK_PATHS:
        book_path = BOOK_PATHS[args.book.lower()]

    if not os.path.exists(book_path):
        print(f"ERROR: Book not found: {book_path}")
        print()
        print("Available books:")
        for name, path in BOOK_PATHS.items():
            exists = "OK" if os.path.exists(path) else "MISSING"
            print(f"  {name}: {path} [{exists}]")
        sys.exit(1)

    try:
        output_path = run_analysis(
            book_path,
            args.model,
            args.output,
            args.verbose,
        )
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
