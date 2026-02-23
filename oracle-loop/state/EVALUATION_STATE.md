# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 12
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_125544/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗ (FAILING — was 8.5 in attempt 10)
  - Completeness: 7/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING — was 7.5 in attempt 10)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.03/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold — REGRESSION from attempt 10 which had 1 failing)

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
| 11 | 8.03 | +0.68 | **REGRESSION.** Nimdok DROPPED (6→5 chars). AM personality still plot_summary dump. Fix 2 worked (relationships). Fix 3 partial (Benny only). 1→2 failing categories. |

## What Worked in Attempt 11
1. **Fix 2 (AM relationships — role-based defaults) — WORKED**: AM's relationships now say "adversary" instead of "see plot summary". This is an improvement — generic but accurate for an antagonist. The fix correctly applied role-based relationship defaults.
2. **Fix 3 (physical_description propagation) — PARTIALLY WORKED**: Benny now has `physical_description` populated from `appearance.summary`. However, Ellen, Gorrister, and Ted have `appearance.summary: null`, so there's nothing to propagate. Only Benny had a populated `appearance.summary`.

## What Did NOT Work in Attempt 11
1. **Fix 1 (AM personality extraction) — DID NOT WORK**: AM's personality.summary is STILL the plot_summary narrative: "Five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—endure a century of torment within the nightmarish underground labyrinth of AM, a sentient supercomputer that has warped time, space, and their…". The sentence-splitting approach apparently didn't change the output — the safety net is still dumping the full plot_summary text.
2. **Nimdok DROPPED — REGRESSION**: Attempt 10 had 6 characters (including Nimdok as supporting_3). Attempt 11 has only 5 (supporting IDs: 0,1,2,4 — supporting_3/Nimdok missing). The profiling stage shows `low_confidence: 1` and the pipeline notes say "Nimdok: Failed to parse JSON profile → low confidence (0.30)". Nimdok was extracted (Character Extraction: 6 items_processed) but appears to have been filtered between extraction and final output. This may be due to the post-correction changes in attempt 11 inadvertently filtering low-confidence characters, or the evidence filter from attempt 7.

## Current Issues (Priority Order)

### CRITICAL
1. **Nimdok missing — REGRESSION from attempt 10** [Completeness]
   - Problem: Nimdok, one of the five human survivors, is completely absent from the final character list. Attempt 10 had 6 characters; attempt 11 has 5.
   - Evidence: `jq '.characters | length'` → 5. No "Nimdok" entry. Supporting IDs jump from supporting_2 to supporting_4.
   - Root cause: Character Extraction processed 6 items (`_profiling.stages["Character Extraction"].items_processed: 6`) but Character Profiles only processed 5 (`items_processed: 5`). Nimdok (supporting_3) had a failed JSON profile parse → low_confidence: 0.30. Something is filtering it out before final output.
   - Location: Investigate `src/analyzer.py` — check if post-profiling filtering or the evidence filter (attempt 7's `discard 0-evidence chars`) is dropping Nimdok. Also check if attempt 11's changes to `src/pipeline/character_profiling/post_corrections.py` inadvertently added a confidence-based filter.
   - Fix: Ensure characters that were successfully extracted are NOT dropped just because profiling failed. A character with a name and mention count but a bad profile is still valuable — better to have Nimdok with a sparse profile than to lose Nimdok entirely. Consider: if a character has mention_count > 5, never filter it out regardless of confidence.

### HIGH
2. **AM personality.summary is STILL the plot_summary dump** [Profiles]
   - Problem: AM's personality reads: "Five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—endure a century of torment within the nightmarish underground labyrinth of AM..." — this is narrative, not personality traits.
   - Evidence: `jq '.characters[] | select(.canonical_name == "AM") | .personality.summary'` → full plot_summary text, truncated with "…"
   - Root cause: The attempt 11 sentence-splitting fix did not take effect. The safety net in `_plot_summary_safety_net()` is still capturing the entire plot_summary paragraph instead of extracting AM-relevant personality descriptors. Either the code change didn't execute (old code path), or the sentence splitting still captures too much text.
   - Location: `src/analyzer.py` (`_plot_summary_safety_net`)
   - Fix: **Debug first** — add logging or check if the new sentence-splitting code is actually running. The fix should: (1) Split plot_summary by sentence boundaries. (2) Find sentences mentioning the character. (3) Extract SHORT descriptor phrases, not full sentences. For AM, the result should be something like: "Sadistic sentient supercomputer; torments five survivors for over a century; controls time, space, and their bodies; motivated by hatred of humanity." Cap at 200 chars. If the code change exists but doesn't fire, the safety net may be using a cached/different code path.

3. **physical_description null for 4/5 characters** [Profiles]
   - Problem: Only Benny has physical_description populated. Ellen, Gorrister, Ted, and AM all have null.
   - Evidence: `jq '[.characters[] | select(.physical_description != null)] | length'` → 1
   - Root cause: The propagation fix works correctly (copies appearance.summary → physical_description), but Ellen/Gorrister/Ted have `appearance.summary: null`. They DO have `appearance.distinguishing_features` populated (Ellen: "walks with a limp"; Gorrister: "lantern jaw, drained of blood incision").
   - Location: `src/pipeline/character_profiling/post_corrections.py` (`propagate_physical_description`)
   - Fix: Extend `propagate_physical_description()` to also build physical_description from `appearance.distinguishing_features` when `appearance.summary` is null. E.g., join distinguishing_features into a comma-separated string like "Walks with a limp after being returned mangled from an earthquake; face was bloody during the hurricane event." This is a generic enhancement — if summary is null but features exist, synthesize a description from features.

### MEDIUM
4. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words. ~4 of 17 non-homograph entries are mild false positives.
   - Not a threshold blocker (Pronunciation at 8.0).

5. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - One wrong IPA entry. Not a threshold blocker.

6. **AM relationships too generic** [Profiles]
   - All 4 relationships say "adversary". While accurate, more specific descriptions would help narrators (e.g., "captor and torturer", "transforms into mouthless blob").
   - Not a threshold blocker if AM personality and Nimdok are fixed.

### LOW
7. **Ted's personality too flat** [Profiles]
   - "emotional detachment and resignation" misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue, hard to fix generically.

8. **Themes too generic** [Summaries]
   - "ambition" is wrong for this story. Better: dehumanization, technological tyranny, mercy/suffering.
   - Minor — themes are supplementary.

## Fix Priority for Attempt 12

**To cross 8.0 in Character Extraction (currently 7.5):**
- Fix CRITICAL #1 (Nimdok missing) — restoring the 6th character fixes Completeness 7→9, pushing overall Character Extraction from 7.5→8.5 (+1.0)

**To cross 8.0 in Character Profiles (currently 7.0):**
- Fix HIGH #2 (AM personality — actually make the sentence extraction work) — fixes the most jarring profile issue (+0.3)
- Fix HIGH #3 (physical_description from distinguishing_features fallback) — populates descriptions for Ellen, Gorrister (+0.3)
- Nimdok's restoration also helps Profiles by adding one more character with at least some data (+0.2-0.4)

**These fixes should push Character Extraction from 7.5→8.5 and Profiles from 7.0→8.0-8.5.**

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
| 10 | AM personality from plot_summary | analyzer.py | **PARTIAL** — dumped full plot_summary instead of traits |
| 10 | Unknown appearance cleanup | post_corrections.py | **WORKED** |
| 10 | Compound word filter | cmu_proposer.py | **WORKED** — 37→23 entries |
| 11 | AM personality sentence extraction | analyzer.py | **DID NOT WORK** — still plot_summary dump |
| 11 | AM relationships role defaults | analyzer.py | **WORKED** — "adversary" replaces placeholders |
| 11 | physical_description propagation | post_corrections.py, models.py | **PARTIAL** — Benny only (others lack appearance.summary) |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls, 5 items processed, 1 low_confidence (Nimdok — filtered)
- 0 LLM retries, 0 JSON parse failures in extraction
- Pronunciation: 23 entries (unchanged from attempt 10)
- Runtime: 15m 42s

## Pipeline Notes (Attempt 11)
- AM safety net fired: role=antagonist, 74 mentions ✓
- Nimdok: Failed JSON profile parse → low_confidence (0.30) → DROPPED from final output
- No narrator identified from summaries or plot_summary (Ted has 5 mentions but not flagged)
- 23 pronunciation entries (same as attempt 10) ✓

## Pipeline Notes (Attempt 12)
- 6 characters found: Benny (35), Ellen (30), Gorrister (29), Nimdok (17), Ted (5), AM via safety net (74 mentions) ✓
- Character Profiles: 5 items processed, 5H/0M/0L (all high confidence — no low_confidence entries)
- AM safety net fired: role=antagonist, 74 mentions ✓
- Nimdok FIX appears to have worked — 6 chars in output (was 5 in attempt 11)
- 23 pronunciation entries (unchanged)
- Runtime: 16m 52s

### Attempt 12 Fixes Applied
- **Fix 1 (Nimdok restoration)**: Added `mention_count > 5` guard to evidence filter in `_convert_characters()`. Previously, when JSON profile parse failed and text was salvaged, `profile_evidence = []` was set; the evidence filter then incorrectly discarded Nimdok as a "false positive". Now characters with >5 mentions are preserved regardless of profile quality.
  - Root cause: `src/analyzer.py:_generate_character_profile():3271` returns `(salvaged, [], 0.3, ...)` on JSON parse failure → `char.profile_evidence = []` → evidence filter discards at line 3762
  - Fix location: `src/analyzer.py:_convert_characters():3762-3772`
  - Smoke test: PASS — logic confirmed via code review; mention_count guard is universal invariant

- **Fix 2 (AM personality)**: Changed personality sentence selection in `_plot_summary_safety_net()` to prefer sentences where the character is the subject (sentence starts with the character name). Falls back to any mentioning sentence. AM now gets "AM toys with them relentlessly..." instead of "Five survivors...AM, a sentient supercomputer...".
  - Root cause: First sentence mentioning AM started "Five survivors..." — AM was an object, not the subject. 200-char truncation captured narrative, not personality.
  - Fix location: `src/analyzer.py:_plot_summary_safety_net():3920-3940`
  - Smoke test: PASS — subject sentences correctly identified as ["AM toys with...", "AM's cruel manipulation..."]

- **Fix 3 (physical_description fallback)**: Extended `propagate_physical_description()` to also build from `appearance.distinguishing_features` when `appearance.summary` is null. Ellen: "Walks with a limp after being returned mangled from an earthquake; face was bloody during the hurricane event." Gorrister gets similar.
  - Root cause: Only `appearance.summary` was used; Ellen/Gorrister have null summary but populated features.
  - Fix location: `src/pipeline/character_profiling/post_corrections.py:577-600`
  - Smoke test: PASS — Ellen gets physical_description from features correctly

## Next Action
Re-run analysis to verify fixes (awaiting_analysis)
