# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 13
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_132726/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7/10 ✗ (FAILING — down from 7.5 in attempt 12; Ellen profile REGRESSED, AM still broken)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles regressed from 7.5 to 7.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |
| 2 | 7.40 | +0.05 | bush removed, roles improved, but AM still missing, narrator still undetected |
| 3 | CRASH | - | Pipeline crash: KeyError in MAIN_CAST_PROMPT format() due to unescaped JSON braces |
| 4 | 6.80 | -0.55 | Artifacts fixed but AM STILL missing, narrator STILL undetected, profiles empty, "Age: five years" bug |
| 5 | 6.80 | -0.55 | No change from attempt 4 |
| 6 | 6.80 | -0.55 | Fallback fired but AM not grounded. Heuristic narrator didn't fire (type mismatch). |
| 7 | 6.80 | -0.55 | Fix 3 worked (Jesus removed). Fixes 1+2 did NOT take effect despite correct code in codebase. |
| 8 | 7.43 | +0.08 | Narrator detection FIXED (Ted is_narrator: true). Orphaned relationships cleaned. AM still missing. Ages still wrong. |
| 9 | 7.98 | +0.63 | **AM ADDED via safety net!** Title/timing HTML fixes. hermiene removed. Ages null at top level but still in appearance. 4→2 failing categories. |
| 10 | 8.40 | +1.05 | Ages GONE. AM=antagonist with personality. Pronunciation 37→23. **1 failing category remaining (Profiles 7.5).** |
| 11 | 8.03 | +0.68 | **REGRESSION.** Nimdok DROPPED (6→5 chars). AM personality still plot_summary dump. 1→2 failing categories. |
| 12 | 8.53 | +1.18 | Nimdok RESTORED. 4/6 physical_desc (up from 1/6). AM personality STILL broken (3rd failed attempt). 2→1 failing category. |
| 13 | 8.45 | +1.10 | **MINOR REGRESSION.** AM personality post-correction DID NOT WORK (4th failure — root cause found: execution ordering). Ellen profile REGRESSED (stochastic LLM failure). 3/6 physical_desc (was 4/6). |

## What Happened in Attempt 13

### Fix Applied
1. **`clean_plot_summary_personality()` post-correction (IMPLEMENTED)**: Added to `OutputCharacterCorrector` in `post_corrections.py`. Detects personality summaries mentioning 3+ other character names. Should replace with character-subject sentences from source text or clear to None.

### Result: DID NOT WORK — ROOT CAUSE IDENTIFIED

**The post-correction code is correct but NEVER SEES AM due to execution ordering:**
- `OutputCharacterCorrector().run_all(characters, doc.text)` runs at `analyzer.py:2071`
- `_plot_summary_safety_net()` adds AM at `analyzer.py:2077`
- The post-correction runs 6 lines BEFORE AM is added to the characters list
- Therefore `clean_plot_summary_personality()` cannot detect or fix AM's personality — AM doesn't exist yet

This is the root cause of ALL 4 consecutive failures (attempts 10-13). Every approach that runs in OutputCharacterCorrector or before the safety net will fail because AM is added AFTER all post-corrections.

### Stochastic Regression
- **Ellen profile REGRESSED**: Character Profiles stage shows 4H/0M/1L (was 5H/0M/0L in attempt 12). Ellen's profile parse FAILED (low confidence 0.30, "Failed to parse JSON response for Ellen"). This is LLM variance, not caused by code changes.
- **physical_description dropped from 4/6 to 3/6**: Ellen lost her physical_description along with her entire profile.

## Current Issues (Priority Order)

### CRITICAL
1. **AM personality.summary is STILL the plot_summary dump — 4 FAILED ATTEMPTS, ROOT CAUSE FOUND** [Profiles]
   - Problem: AM's personality reads: "In the desolate, subterranean ruins of a post-apocalyptic world, five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—trudge through caverns…" — narrative text, not personality traits.
   - **ROOT CAUSE**: `OutputCharacterCorrector().run_all()` at `analyzer.py:2071` runs BEFORE `_plot_summary_safety_net()` at `analyzer.py:2077`. The `clean_plot_summary_personality()` method works correctly but AM doesn't exist in the character list when it runs.
   - **FIX**: Move `OutputCharacterCorrector().run_all(characters, doc.text)` to AFTER `_plot_summary_safety_net()`. Specifically, swap lines 2071 and 2077 so the safety net adds AM first, then post-corrections clean up all characters including AM. This is a 2-line change in `analyzer.py`.
   - **ALTERNATIVE**: Call `OutputCharacterCorrector().clean_plot_summary_personality(characters, doc.text)` a SECOND time after the safety net. But the move is cleaner.
   - Target: AM's personality should be replaced with subject sentences from the source text or cleared to None.

### HIGH
2. **Nimdok physical_description factual error** [Profiles]
   - Problem: "resembling a chimpanzee AM intended him to resemble" — this is Benny, not Nimdok.
   - Root cause: LLM profiling hallucination in `appearance.distinguishing_features`.
   - Not addressable with a simple code fix — would need cross-character consistency checking.
   - **Deprioritize**: Fixing CRITICAL #1 should be sufficient to reach 8.0. Nimdok's error is minor compared to AM's broken personality.

3. **Ellen profile empty (stochastic)** [Profiles]
   - Problem: Ellen has null personality, null physical_description, null appearance. Profile parse failed this run.
   - Root cause: Stochastic LLM failure ("Failed to parse JSON response for Ellen", confidence 0.30).
   - This is LLM variance — re-running may restore it. Not a code fix issue.
   - Impact: Contributes to 3/6 physical descriptions (was 4/6).

### MEDIUM
4. **AM missing Ellen from relationships** [Profiles]
   - AM's relationships list Ted, Nimdok, Benny, Gorrister as "adversary" but omits Ellen.
   - Minor — relationships are generic anyway.

5. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words.
   - Not a threshold blocker (Pronunciation at 8.0).

6. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - Not a threshold blocker.

### LOW
7. **Ted's personality too flat** [Profiles]
   - Misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue.

8. **AM relationships too generic** [Profiles]
   - All say "adversary". More specific descriptions would help narrators.

## Fix Priority for Attempt 14

**The ONLY fix needed is CRITICAL #1 — move OutputCharacterCorrector to run AFTER the safety net.**

In `analyzer.py`, change the order so that:
1. `_plot_summary_safety_net()` runs FIRST (adds AM to characters)
2. `OutputCharacterCorrector().run_all(characters, doc.text)` runs SECOND (cleans up all characters including AM)

This is a ~5 line reorder. The `clean_plot_summary_personality()` code is already correct and tested — it just needs to see AM in the character list.

Expected impact: AM personality cleaned → +1.0 on Profiles → 8.0. Combined with existing passing scores, this should PASS.

## Fix History

### Attempt 1 Fixes Applied
- **Fix 1**: Move supporting cast mention search to BEFORE promotion (STEP 5.7.5) → **WORKED**
- **Fix 2**: Add narrator re-detection after promotion (STEP 5.8.5) → **DID NOT WORK**
- **Fix 3**: Fix narrator prompt to account for 3rd-person summaries → **DID NOT WORK**
- **Fix 4**: Proper names must start with uppercase → **WORKED** ("bush" removed)
- **Bug fix**: Variable shadowing in STEP 5.10.5 → **Fixed**

### Attempt 3 Fixes Applied
- **Fix 1**: Robust LLM JSON parsing (accept "name" key, try wrapper keys) → **DID NOT WORK** (main_cast still 0)
- **Fix 2**: Two-pass → single-pass fallback in extract() → **Fires but still 0 characters**
- **Fix 3**: STEP 5.8.5 re-detection condition fix → **DID NOT WORK**
- **Fix 4**: Include plot_summary in narrator detection prompt → **DID NOT WORK**
- **Fix 5**: Pronunciation artifact detection improvements → **PARTIALLY WORKED**

### Attempt 4 Fix Applied
- **Fix**: Escape JSON example braces in MAIN_CAST_PROMPT → **Fixed crash**

### Attempt 5 Fixes Applied
- **Fix 1-3**: Added `[DIAG]` debug logging → **NOT VISIBLE** (DEBUG level)
- **Fix 4**: Fixed `_get_plot_summary()` — was always returning None → **WORKED**
- **Fix 5**: Improved NARRATOR_DETECTION_PROMPT rule #2 → **DID NOT WORK**

### Attempt 6 Fixes Applied
- **Fix 1**: Plot summary character fallback (STEP 3.1) → **FIRED but AM not grounded** — GroundingGate rejects "AM"
- **Fix 2**: Heuristic narrator fallback (STEP 5.8.6) → **DID NOT FIRE** — `_get_narrative_style()` returns None

### Attempt 7 Fixes Applied
- **Fix 1**: Skip GroundingGate for plot_summary fallback → **CODE PRESENT BUT NO EFFECT**
- **Fix 2**: Fix `_get_narrative_style()` type check (hasattr for Pydantic) → **CODE PRESENT BUT NO EFFECT**
- **Fix 3**: Post-profiling evidence filter (discard 0-evidence chars) → **WORKED** (Jesus removed)

### Attempt 8 Fixes Applied
- **Fix 1**: Fallback prompt includes "AI, non-human beings, sentient entities" → **FAILED** — 0 main_cast again
- **Fix 2**: `_get_narrative_style()` complete rewrite → **WORKED** — Ted is now narrator
- **Fix 3**: `clean_orphaned_relationships()` → **WORKED** — Jesus references cleaned from all characters
- **Fix 4**: Age validation in `extract_deterministic_age()` → **PARTIALLY WORKED** — top-level age null, but nested appearance.age_indication unchanged
- **Refactor**: PipelineCharacterCorrector + OutputCharacterCorrector with 49 tests → **WORKED**

### Attempt 9 Fixes Applied
- **Fix 1**: Plot_summary safety net in `analyzer.py` → **WORKED** — AM now present (74 mentions)
- **Fix 2**: HTML title underscores fix → **WORKED**
- **Fix 3**: HTML timing table empty rows fix → **WORKED**
- **Fix 4**: URL token filter in CMU pronunciation proposer → **WORKED** — "hermiene" removed

### Attempt 10 Fixes Applied
- **Fix 1**: `_age_extract_pat` — require "old" for written-number forms → **WORKED** — ages gone from HTML
- **Fix 2**: Safety net profile enrichment (role detection, context sentences, personality, relationships) → **PARTIALLY WORKED** — role=antagonist ✓, but personality=plot_summary dump, relationships="see plot summary"
- **Fix 3**: `clean_unknown_appearance()` → **WORKED** — placeholder values cleared
- **Fix 4**: `_is_closed_compound()` → **WORKED** — 37→23 pronunciation entries

### Attempt 11 Fixes Applied
- **Fix 1**: AM personality sentence extraction → **DID NOT WORK** — personality.summary still full plot_summary dump, unchanged from attempt 10
- **Fix 2**: AM relationships role-based defaults → **WORKED** — "adversary" replaces "see plot summary" for all 4 humans
- **Fix 3**: physical_description propagation from appearance.summary → **PARTIALLY WORKED** — Benny gets physical_description, but Ellen/Gorrister/Ted have null appearance.summary so nothing propagated

### Attempt 12 Fixes Applied
- **Fix 1**: Nimdok mention_count > 5 guard in evidence filter → **WORKED** — 6 characters restored (was 5)
- **Fix 2**: AM personality subject-sentence selection in _plot_summary_safety_net → **DID NOT WORK** (3rd failure) — personality.summary unchanged
- **Fix 3**: physical_description from distinguishing_features fallback → **WORKED** — 4/6 characters have physical_description (was 1/6)

### Attempt 13 Fix Applied
- **Fix 1**: `clean_plot_summary_personality()` post-correction in OutputCharacterCorrector → **DID NOT WORK** (4th failure) — ROOT CAUSE: OutputCharacterCorrector runs BEFORE safety net adds AM. Code is correct but never sees AM.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Characters not promoted due to late mention search | characters.py (STEP 5.7.5) | Fixed |
| 1 | Narrator undetected due to empty main_cast | characters.py (STEP 5.8.5) | No change |
| 1 | Narrator prompt assumes first-person in summaries | narrator.py | No change |
| 1 | Lowercase false positive "bush" | supporting.py | Fixed |
| 1 | Variable shadowing bug | characters.py | Fixed |
| 3 | Main cast JSON parsing too strict | main_cast.py | No change — still 0 chars |
| 3 | No single-pass fallback | main_cast.py | Fallback fires but still 0 chars |
| 3 | STEP 5.8.5 condition too restrictive | characters.py | No change |
| 3 | Narrator prompt missing plot_summary | narrator.py | No change |
| 3 | Pronunciation concatenation artifacts | cmu_proposer.py | Partially fixed |
| 4 | MAIN_CAST_PROMPT crash (unescaped braces) | main_cast.py | Fixed crash |
| 5 | main_cast [DIAG] logging | main_cast.py | Not visible (DEBUG) |
| 5 | Narrator [DIAG] logging | narrator.py | Not visible (DEBUG) |
| 5 | _get_plot_summary() always returns None | characters.py | Fixed |
| 5 | Narrator prompt exact name rule | narrator.py | No change |
| 6 | Plot summary fallback (STEP 3.1) | characters.py | Fired but AM rejected by grounding |
| 6 | Heuristic narrator (STEP 5.8.6) | characters.py | Did not fire — type check bug |
| 7 | Grounding bypass for fallback | characters.py | Code correct, no effect |
| 7 | _get_narrative_style() type check | characters.py | Code correct, no effect |
| 7 | Evidence filter for false positives | analyzer.py | **WORKED** (Jesus removed) |
| 8 | Fallback prompt for sentient entities | characters.py | **FAILED** — 0 main_cast again |
| 8 | _get_narrative_style() complete rewrite | characters.py | **WORKED** — Ted is narrator |
| 8 | clean_orphaned_relationships() | post_corrections.py | **WORKED** — Jesus refs cleaned |
| 8 | Age validation in extract_deterministic_age() | post_corrections.py | **PARTIAL** — top-level only |
| 8 | Refactor post-corrections into classes | analyzer.py, post_corrections.py | **WORKED** |
| 9 | AM missing → plot_summary safety net | analyzer.py | **WORKED** — AM present |
| 9 | HTML title underscores | html_report.py | **WORKED** |
| 9 | HTML timing empty rows | html_report.py | **WORKED** |
| 9 | Pronunciation URL artifact (hermiene) | cmu_proposer.py | **WORKED** |
| 10 | Age pattern re-extraction | post_corrections.py | **WORKED** — ages gone |
| 10 | AM personality from plot_summary | analyzer.py (_plot_summary_safety_net) | **PARTIAL** — dumped full plot_summary instead of traits |
| 10 | Unknown appearance cleanup | post_corrections.py | **WORKED** |
| 10 | Compound word filter | cmu_proposer.py | **WORKED** — 37→23 entries |
| 11 | AM personality sentence extraction | analyzer.py (_plot_summary_safety_net) | **DID NOT WORK** — still plot_summary dump |
| 11 | AM relationships role defaults | analyzer.py | **WORKED** — "adversary" replaces placeholders |
| 11 | physical_description propagation | post_corrections.py, models.py | **PARTIAL** — Benny only |
| 12 | Nimdok evidence filter guard | analyzer.py (_convert_characters) | **WORKED** — 6 chars restored |
| 12 | AM personality subject-sentence | analyzer.py (_plot_summary_safety_net) | **DID NOT WORK** (3rd failure) |
| 12 | physical_description from features | post_corrections.py | **WORKED** — 4/6 chars have desc |
| 13 | AM personality post-correction | post_corrections.py (clean_plot_summary_personality) | **DID NOT WORK** — correct code but runs before AM exists |

**⚠️ ROOT CAUSE FOUND:** The issue is execution ordering in `analyzer.py`. `OutputCharacterCorrector().run_all()` at line 2071 runs BEFORE `_plot_summary_safety_net()` at line 2077. Moving post-corrections to AFTER the safety net will fix AM's personality on the next run.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls, 5 items processed, 4H/0M/1L (Ellen failed parse)
- 0 LLM retries, 0 JSON parse failures (in extraction — profile parse failure is separate)
- Pronunciation: 23 entries (unchanged from attempt 10)
- Runtime: 16m 48s

## Pipeline Notes (Attempt 13)
- 6 characters found: Benny (35), Ellen (30), Gorrister (29), Nimdok (17), Ted (5), AM via safety net (74 mentions) ✓
- Character Profiles: 4H/0M/1L — Ellen profile parse FAILED (low confidence 0.30), "Failed to parse JSON response for Ellen"
- AM safety net fired: role=antagonist, 74 mentions ✓
- LLM marker proposer returned non-list (dict) × 3 during structure detection → fell back to "No valid proposals - returning single chapter" → found 1 chapter
- 23 pronunciation entries (unchanged)
- Runtime: 16m 48s

## Next Action
Run PROMPT_fix.md. The fix is a simple reorder in `analyzer.py`: move `OutputCharacterCorrector().run_all()` to AFTER `_plot_summary_safety_net()`. This ensures `clean_plot_summary_personality()` can see and fix AM's personality.
