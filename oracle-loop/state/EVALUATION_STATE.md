# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 26
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5.5/10
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.55/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Changed in Attempt 26

Comma alias fix worked — "American, sir" no longer appears as an alias. However:
- Narrator regressed: Johnny (2 mentions) picked as narrator instead of Uncle Bill (18 mentions)
- Father/son still merged into single "John (the boy)" entity
- Summary factual errors persist (Uncle Bill on battlefield, wrong character says "American, sir")
- Score unchanged from baseline (6.55)

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son "John Donaldson" merged into one entity** [Identity Resolution]
   - Problem: "John (the boy)" (70 mentions) combines father AND son. Two distinct characters with the same name.
   - This has been intractable for 26 attempts. Split heuristics fire ~40% of runs stochastically.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (STEP 3.95b/3.95c)
   - **ARCHITECTURALLY INTRACTABLE** with current post-extraction heuristics.

2. **Summary has major factual errors** [Chapter Summaries]
   - "Uncle Bill, mortally wounded in the same battlefield" — WRONG. Uncle Bill is the frame narrator at home.
   - "as he dies, he sits up suddenly and proclaims 'American, sir'" — WRONG. The father says this, not Uncle Bill.
   - Root cause: LLM conflates frame narrative with embedded war narrative. Character merge compounds this.

### HIGH
3. **Narrator regression: "Johnny" (2 mentions) assigned as narrator** [Identity Resolution]
   - Was FIXED in attempt 25 (Uncle Bill correctly selected). Regressed in attempt 26.
   - 5.8.5 post-guard resets narrator, but summary-based narrator detection overrides and picks "Johnny"

4. **Johnny is a fragment, not a separate character** [Identity Resolution]
   - "Johnny" (2 mentions) is Ted Frith's nickname for the boy. Should be alias of "John (the boy)".
   - STEP 3.97 should handle this (NICKNAME_TO_FORMAL maps "johnny"->"john") but isn't firing.

5. **Profile misattribution** [Character Profiles]
   - Johnny's appearance ("elderly, grizzled, small man") is Uncle Bill's description
   - Uncle Bill's appearance ("tall, dark-skinned, shabby") is likely the father's description
   - Root cause: character merge + wrong narrator assignment cascades into wrong profile attribution

### MEDIUM
6. **Joe Barron missing** [Completeness]
7. **Uncle Bill has no relationships listed** [Character Profiles]
8. **Johnny<->John listed as "cousin" — wrong** [Character Profiles]

### LOW
9. **"Bersagliari" spelling** [Pronunciation] — source text issue, not pipeline

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
| 21 | 6.5 | -0.05 | Narrator OK, alias OK, split no |
| 22 | 6.35 | -0.20 | "American, sir" regression |
| 23 | 6.3 | -0.25 | STEP 3.95b fixes no effect |
| 24 | 6.4 | -0.15 | "American, sir" FIXED, narrator/split broken |
| 25 | 6.6 | +0.05 | Narrator FIXED (Uncle Bill). Split/summary still broken. |
| 26 | 6.55 | 0 | Comma alias fix OK. Narrator REGRESSED. Score at baseline. |

## Fix History
- Attempt 22: STEP 3.95c added (kinship-fragment split). HTML BOM/title fix. 3.95c didn't fire.
- Attempt 23: STEP 3.95b: removed `"(" in canonical_name` guard; sibling-ID check; alias iteration; Pattern E.
- Attempt 24 (Fix 1): `main_cast.py:_parse_pass1_results` + `_parse_profiles` — reject canonical names with commas. WORKED.
- Attempt 24 (Fix 2): `characters.py:_heuristic_narrator_from_mention_count` — exclude <=2-mention candidates. Partial.
- Attempt 25: `characters.py:_heuristic_narrator_from_mention_count` — switched from `min` to `max` mention count. **WORKED** — Uncle Bill(19) correctly selected as narrator over "the boy"(13).
- Attempt 26: `main_cast.py:verify_aliases()` — added comma-in-alias check. Aliases containing commas (except Jr./Sr./II/III/IV suffixes) are blocked. Narrator regressed to Johnny despite attempt 25 fix.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 8 | Father/son split | main_cast.py (STEP 3.95) | Fixed (stochastic) |
| 9 | Cross-char alias | main_cast.py | Fixed |
| 10-16 | Father/son split reliability | main_cast.py (3.95, 3.95b, 3.95c) | Inconsistent — works ~40% of runs |
| 17 | Summary regression | analyzer.py | No change |
| 18-19 | Father/son split patterns | main_cast.py (Pattern D) | Inconsistent |
| 20-23 | Father/son split patterns | main_cast.py (3.95b, 3.95c, Pattern E) | No change |
| 24 | "American, sir" hallucination | main_cast.py (comma filter) | **Fixed** |
| 24 | Narrator low-mention guard | characters.py (heuristic narrator) | Partial |
| 25 | Narrator heuristic min->max | characters.py (heuristic narrator) | **Fixed** |
| 26 | "American, sir" alias | main_cast.py (verify_aliases comma check) | Fixed (no regression) |

## ESCALATION STATUS

**After 26 attempts, this text remains at 6.55/10 (equal to baseline). The score has oscillated between 5.8-8.0 across all attempts, hitting 8.0 only ONCE (attempt 9, stochastically).**

**Remaining blockers are architecturally intractable:**

1. **Father/son same-name merge** (Issue #1) — Stochastic, depends on LLM output variance. Post-extraction heuristics cannot reliably separate two characters with the exact same name. This is a fundamental limitation of the current architecture.

2. **Summary factual errors** (Issue #2) — LLM conflates frame narrator (Uncle Bill at home) with embedded war narrative. Compound error from character merge + nested narrative structure.

3. **Narrator regression** (Issue #3) — Attempt 25 fix worked but attempt 26 regressed. The summary-based narrator detection overrides the heuristic fix non-deterministically.

4. **Johnny fragment** (Issue #4) — STEP 3.97 should merge this but isn't firing. Root cause unclear across multiple attempts.

**Recommendation: SKIP this text. 26 attempts without stable convergence toward 8.0. The same-name disambiguation problem requires architectural changes (scene-level character tracking, nested narrative awareness) beyond what incremental fixes can achieve.**

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false

## Next Action
Recommend skipping american_sir and advancing to next text in manifest. Score is at baseline after 26 attempts with no stable path to 8.0.
