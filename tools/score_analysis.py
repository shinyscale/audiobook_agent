#!/usr/bin/env python3
"""
Score analysis outputs against golden ground truth.

Usage:
  # Single book
  python tools/score_analysis.py output/run_X/book.analysis.json validation/golden/gatsby.json

  # Batch: score every golden book that has a matching analysis in a directory
  # (matches <key>.analysis.json or <key>/<anything>.analysis.json by golden filename key)
  python tools/score_analysis.py --batch <analyses_dir>
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.golden_score import format_score, score_files  # noqa: E402

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "validation" / "golden"


def batch(analyses_dir: Path) -> int:
    scores = []
    for truth_path in sorted(GOLDEN_DIR.glob("*.json")):
        key = truth_path.stem
        candidates = list(analyses_dir.glob(f"{key}*.analysis.json")) + list(
            analyses_dir.glob(f"{key}*/*.analysis.json")
        )
        if not candidates:
            print(f"-- {key}: no analysis found, skipped")
            continue
        s = score_files(candidates[0], truth_path)
        scores.append(s)
        print(format_score(s))
        print()

    if scores:
        f1s = [s["character_f1"] for s in scores if s["character_f1"] is not None]
        if f1s:
            print(f"== CORPUS ==  books: {len(scores)}  mean character F1: {sum(f1s)/len(f1s)*100:.0f}%")
        forb = sum(len(s["forbidden_hits"]) for s in scores)
        if forb:
            print(f"  forbidden-name hits across corpus: {forb}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis", nargs="?", help="analysis.json path")
    ap.add_argument("truth", nargs="?", help="golden truth json path")
    ap.add_argument("--batch", metavar="DIR", help="score all golden books against analyses in DIR")
    args = ap.parse_args()

    if args.batch:
        return batch(Path(args.batch))
    if not (args.analysis and args.truth):
        ap.error("provide ANALYSIS and TRUTH paths, or --batch DIR")
    s = score_files(args.analysis, args.truth)
    print(format_score(s))
    print()
    print(json.dumps(s, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
