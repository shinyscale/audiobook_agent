#!/usr/bin/env python3
"""Regenerate a deliverable from an existing analysis JSON by re-applying the
(fixed) cast/background partition. The partition is pure post-processing, so
this avoids a full pipeline rerun and preserves the already-validated cast.

Usage:
  python tools/repartition_deliverable.py <analysis.json> <out_dir> [--golden G]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyzer import is_background_reference  # noqa: E402
from src.export.html_report import export_html_report  # noqa: E402
from src.models import AnalysisResult  # noqa: E402
from src.pipeline.cast_dedup import (  # noqa: E402
    merge_fragment_duplicates,
    reground_canonical_names,
    reject_implausible_narrator,
)
from src.pipeline.output_linter import apply_lint  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis")
    ap.add_argument("out_dir")
    ap.add_argument("--golden")
    ap.add_argument("--text", help="source text file for canonical regrounding")
    ap.add_argument("--model", default="qwen3-next:80b-a3b-instruct-q8_0")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = AnalysisResult.model_validate_json(Path(args.analysis).read_text())
    source_text = result.raw_text or ""
    if args.text and not source_text:
        source_text = Path(args.text).read_text(errors="replace")

    everyone = list(result.characters) + list(result.background_references)
    # 1) reground hallucinated canonicals, 2) merge identical-count fragments,
    # 3) re-check narrator, 4) partition.
    reground_canonical_names(everyone, source_text)
    everyone = merge_fragment_duplicates(everyone, source_text)
    result.narrator_character_id = reject_implausible_narrator(
        everyone, result.narrator_character_id
    )

    cast, background = [], []
    for ch in everyone:
        (background if is_background_reference(ch) else cast).append(ch)
    result.characters = cast
    result.background_references = background
    nid = result.narrator_character_id
    narr = next((c.canonical_name for c in everyone if getattr(c, "id", None) == nid), None)
    print(f"Re-partitioned: {len(cast)} cast, {len(background)} background "
          f"(from {len(everyone)} total) | narrator: {narr}")

    # Re-lint against the corrected cast
    if result.raw_text:
        violations = apply_lint(result, result.raw_text)
        print(f"Output lint: {len(violations)} violation(s)")

    out_json = out_dir / "see_the_light_final.analysis.json"
    out_json.write_text(result.model_dump_json(indent=2))
    print(f"Wrote {out_json}")

    try:
        export_html_report(result, out_dir / "see_the_light_final.html",
                           llm_model=args.model)
        print(f"Wrote {out_dir / 'see_the_light_final.html'}")
    except Exception as e:
        print(f"HTML export failed (JSON still valid): {e}")

    if args.golden:
        from src.pipeline.golden_score import format_score, score_against_truth
        import json
        truth = json.loads(Path(args.golden).read_text())
        analysis = json.loads(out_json.read_text())
        print()
        print(format_score(score_against_truth(analysis, truth)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
