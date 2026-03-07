# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 23
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING — father/son merged, "American, sir" regression, Johnny fragment)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 4.5/10 ✗ (FAILING — description cross-contamination, null summaries, wrong relationships)
- Chapter Summaries: 5/10 ✗ (FAILING — Uncle Bill conflated with dying father at end)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓ (BOM fixed, title fixed)
- **Overall: 6.35/10** (reference only, from attempt 22)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (awaiting evaluation)

## Pipeline Notes (Attempt 23)
- Pipeline completed successfully in 17m 22s (exit 0)
- Characters found: 5
  - Johnny (aka his son) — 1 mention
  - John Donaldson (aka his father, John) — 31 mentions
  - Uncle Bill (aka Bill) — 18 mentions
  - 'American, sir' (aka American, sir) — 5 mentions
  - Ted Frith (aka Ted) — 5 mentions
- Key observations:
  - "John Donaldson" has alias "John" AND "his father" — 31 mentions suggests father+son may still be merged
  - "Johnny" is a 1-mention fragment (correct: should be alias of the son)
  - "'American, sir'" is still a separate character (5 mentions) — not absorbed
  - Narrator detected as "Johnny (first-person)" but FAILED low-mention invariant (1 mention) — narrator reset
  - BLOCKED: 'John Donaldson' blocked from being alias of 'John' (claimed by father) — so they WERE separate in Pass 1
  - BLOCKED: 'American, sir' blocked from being alias of John Donaldson (already claimed by another char)
  - New character "Ted Frith" appeared (not seen in prior attempts — may be Joe Barron equivalent or distinct)
  - LLM validation error: "Invalid JSON format. Expected an array of objects" (non-fatal)
  - STEP 3.95b: needs evaluator to check if it fired and produced correct split

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline |
| 2 | 6.6 | +0.05 | Narrator fix |
| 3 | 6.0 | -0.55 | REGRESSION |
| 4 | 6.4 | -0.15 | Partial fix |
| 5 | 6.7 | +0.15 | Plot summary improved |
| 6 | 7.0 | +0.45 | Uncle Bill narrator |
| 7 | 6.9 | +0.35 | Boy disappeared |
| 8 | 7.85 | +1.30 | Father/son split worked |
| 9 | 8.0 | +1.45 | Cross-character alias fix |
| 10 | 7.0 | +0.45 | REGRESSION — split didn't fire |
| 11 | 7.2 | +0.65 | Mixed |
| 12 | 7.7 | +1.15 | Split via alias contradiction |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION |
| 14 | 7.6 | +1.05 | Split worked |
| 15 | 6.85 | +0.30 | Split didn't fire |
| 16 | 6.95 | +0.40 | No parenthetical |
| 17 | 6.2 | -0.35 | Summary regression |
| 18 | 6.8 | +0.25 | Father/son merged |
| 19 | 7.7 | +1.15 | Split worked (Pattern D) |
| 20 | 5.95 | -0.60 | SEVERE REGRESSION |
| 21 | 6.5 | -0.05 | Narrator ✓, alias ✓, split ✗ |
| 22 | 6.35 | -0.20 | "American, sir" regression. HTML fixed. |
| 23 | TBD | TBD | STEP 3.95b fixes (alias iteration, Pattern E, guard removal) |

## Fix History
- Attempt 22: STEP 3.95c added (kinship-fragment split). HTML BOM/title fix. 3.95c didn't fire.
- Attempt 23: STEP 3.95b: removed `"(" in canonical_name` guard → sibling-ID check; alias iteration; Pattern E. STEP 3.95c/3.97: replaced `"(" not in canonical_name` guard with `not c.id.endswith("_parent")`.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
