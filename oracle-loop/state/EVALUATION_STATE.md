# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 17
- **Phase:** analysis_running
- **baseline_score:** 7.35

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 2 | 7.75 | Profiles improved |
| 3 | 7.58 | Profiles regressed |
| 4 | 7.08 | Summaries regressed (narrator substitution undid fix) |
| 5 | ~7.08 | Same root cause |
| 6 | ~5.5 | Regression: LLM hallucinated Elizabeth Lavenza as narrator |
| 7 | ~7.9 | Major recovery: 28 chapters ✓, letters/creature chapters misattributed |
| 8 | ~5.0 | REGRESSION: Step 4.5 early sub → all chapters attributed to outer narrator |
| 9-11 | ~1.5 | All chapters "Robert Walton" — Step 4.5 early sub regression |
| 12 | ~7.9 | Fix M: Victor chapters correct, creature chapters wrong, letters wrong |
| 13 | ~4.0 | Fix N/O/P: creature chapters fixed but Victor chapters still "Robert Walton" (narrator detection fragile) |

## Attempt 14 Fixes (commit 8d474af) — RESULT: ~7.35 (Step 6.9 picked Walton, not Victor)

### Root cause of attempt 14 failure
- Step 5.8.6 in characters.py fires for `pov="epistolary"` (not blocked by old exclusion list)
- It picks Walton (lowest mention count) as narrator via heuristic → sets Walton.is_narrator=True
- Step 6.9 preamble then finds Walton first in character list → narrator_detected="Robert Walton"

## Attempt 15 Fixes

### Fix T: characters.py Step 5.8.6 — exclude epistolary POV from heuristic
- Added "epistolary" to the `pov not in (...)` exclusion list
- Added guard: skip heuristic if any character ALREADY has is_narrator=True
- Rationale: epistolary/frame narratives have secondary narrators set by narrator.py (Fix Q);
  the heuristic incorrectly overwrites that by picking the lowest-mention char (Walton)

### Fix U: analyzer.py Step 6.9 preamble — pick most prominent is_narrator character
- When multiple is_narrator characters exist (e.g. Victor + creature as secondary narrators),
  previously picked the FIRST one in the list (nondeterministic)
- Now counts appearances in non-letter chapter summaries and picks the most frequent one
- Victor (appears in ~24/24 non-letter chapters) wins over creature (appears in ~6/24)
- Fallback: highest mention_count if no summary data

## Attempt 16 Fixes (commit c711e2c) — RESULT: ~7.5/10 (Narration improved but chars/pronunciation still <8)

### Fix V: narrator.py secondary path — skip symbolic entities (is_symbolic=True)
### Fix W: narrator.py secondary path — block ≤5 mention characters

### Attempt 16 Score Breakdown
- Structure: 8/10 ✓ (28 chapters)
- Characters: 7/10 ✗ — Mr. Kirwin + Magistrate Kirwin duplicate; Alphonse gender=female; Chamounix is a place
- Profiles: 7.5/10 ✗ — Victor missing Elizabeth/creature relationships
- Summaries: 8/10 ✓ — narrator attribution mostly correct; Ch15 says Victor instead of creature
- Pronunciation: 7/10 ✗ — "dæmon" not indexed (æ=non-ASCII, old regex missed it); missing Prometheus/Lucerne/Arveiron
- HTML: 8/10 ✓

## Attempt 17 Fixes

### Fix X: analyzer.py _is_likely_alias_of_existing TITLE_PATTERNS
- Added: `mr.`, `mr`, `mrs.`, `mrs`, `ms.`, `ms`, `miss`, `sir`, `lord`, `lady`, `judge`, `magistrate`, `inspector`, `constable`, `sheriff`, `detective`, `officer`
- Fixes: "Magistrate Kirwin" now blocked when "Mr. Kirwin" exists (identity resolution)

### Fix Y: word_index.py _build_index Unicode tokenization
- Changed: ASCII-only `[a-zA-Z]` pattern → Latin Extended `[a-zA-Z\xc0-\xd6\xd8-\xf6\xf8-\xff]`
- Uses lookahead/lookbehind for word boundaries (not \b which fails on non-ASCII)
- Fixes: "dæmon" now indexed and flagged for pronunciation (æ=U+00E6 in range)

### Fix AA: analyzer.py narrator_character_id selection
- Previously: picked FIRST is_narrator character (Robert Walton, main_cast_0)
- Now: prefers character whose name matches narrator_detected (Victor Frankenstein)
- Fallback: first is_narrator character if no narrator_detected match

## Expected Chapter Attribution After Fixes
- Letters 1-4: "Robert Walton" (correct — his narrative frame)
- Chapters 1-10: "Victor Frankenstein" (inner narrator confirmed from is_narrator flag)
- Chapters 11-16: "The narrator" (creature's narration, fixed by Fix N/6)
- Chapters 17-24: "Victor Frankenstein" (back to Victor)
- Chapter 25+: "Robert Walton" (back to outer frame, not present in this text)
