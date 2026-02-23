# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 12
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_125544/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓ (UP from 7.5 — Nimdok restored!)
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7.5/10 ✗ (FAILING — up from 7.0, still below threshold)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — improved from 2 failing in attempt 11)

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

## What Worked in Attempt 12
1. **Fix 1 (Nimdok restoration) — WORKED**: mention_count > 5 guard in evidence filter preserved Nimdok despite failed JSON profile parse. 6 characters now in output. Nimdok has full profile: physical_description, personality, relationships all populated. Character Profiles stage shows 5H/0M/0L (all high confidence — Nimdok's profile parsed successfully this run).
2. **Fix 3 (physical_description from distinguishing_features) — WORKED**: Ellen, Gorrister, and Nimdok all received physical_description synthesized from appearance.distinguishing_features. 4/6 characters now have physical_description (was 1/6 in attempt 11). Benny retains description from appearance.summary.

## What Did NOT Work in Attempt 12
1. **Fix 2 (AM personality subject-sentence extraction) — DID NOT WORK (3rd consecutive failure)**: AM's personality.summary is STILL: "Five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—traverse a nightmarish underground labyrinth controlled by the malevolent AI known as AM, driven by the faint hope of finding food in rumored…" — unchanged from attempts 10 and 11. The subject-sentence selection code apparently did not execute or was overridden. **This fix has now failed 3 times on the same file (analyzer.py:_plot_summary_safety_net). ESCALATION REQUIRED.**

## New Issues Found in Attempt 12
1. **Nimdok physical_description factual error**: "Was altered by am to resemble a chimpanzee" — this is BENNY who was altered to be apelike, not Nimdok. The error originates in the LLM profiling (distinguishing_features contains the wrong attribution). The propagation fix correctly copied the features, but the features themselves are wrong. This is an LLM hallucination in profiling, not a pipeline bug.

## Current Issues (Priority Order)

### CRITICAL
1. **AM personality.summary is STILL the plot_summary dump — 3 FAILED ATTEMPTS** [Profiles]
   - Problem: AM's personality reads: "Five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—traverse a nightmarish underground labyrinth controlled by the malevolent AI known as AM…" — this is narrative, not personality traits.
   - Evidence: `jq '.characters[] | select(.canonical_name == "AM") | .personality.summary'` → plot_summary text with "…" truncation
   - **STUCK PATTERN**: `analyzer.py:_plot_summary_safety_net()` modified in attempts 10, 11, and 12 — none took effect. The personality field always contains the same plot_summary text regardless of code changes to sentence selection.
   - **Root cause hypothesis**: The personality is being set ELSEWHERE and overwriting the safety net's value, OR the safety net code path for personality is never reached because personality is set before the safety net runs. The fix phase MUST debug the actual execution flow — print statements or check if the safety net's personality assignment is being overwritten downstream.
   - **ESCALATION**: Do NOT modify `_plot_summary_safety_net()` again. Instead: (a) Add a **post-correction** in `post_corrections.py` that detects plot-summary-like personality text (starts with character count like "Five survivors", contains "labyrinth", is >200 chars of narrative) and replaces it with a concise personality description derived from the character's role. OR (b) Debug the execution flow to find where personality is overwritten after the safety net sets it.
   - Target: AM's personality should be something like: "Sadistic, omnipotent AI; torments five humans for over a century; controls their environment and bodies; motivated by hatred for humanity."

### HIGH
2. **Nimdok physical_description factual error** [Profiles]
   - Problem: Nimdok's physical_description says "Was altered by am to resemble a chimpanzee" — this is Benny's transformation, not Nimdok's. Benny is the character who was given a simian/apelike appearance by AM.
   - Evidence: In the source text, Benny is described with "monkey-like face" and simian features. Nimdok's appearance is vague — he returns "white, drained of blood" from solitary excursions.
   - Root cause: LLM profiling hallucination in `appearance.distinguishing_features`. The profiling model attributed Benny's physical transformation to Nimdok.
   - Location: `src/pipeline/character_profiling/` — profiling prompts or post-correction cross-validation
   - Fix: This is hard to fix generically. Options: (a) Add cross-character consistency check in post-corrections — if the same distinguishing feature appears on two characters, flag/remove the duplicate. (b) Accept as LLM quality issue. Given that this is the ONLY blocker difference between 7.5 and 8.0, consider approach (a).

3. **Ted missing physical_description** [Profiles]
   - Problem: Ted has no physical_description and empty distinguishing_features. As the first-person narrator, he rarely describes himself, but the text does mention AM altering his perception of his own appearance.
   - Evidence: `appearance.distinguishing_features: []`, `physical_description: null`
   - Impact: Minor — first-person narrators commonly lack self-description. Not a threshold blocker alone.

### MEDIUM
4. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words. ~4 of 17 non-homograph entries are mild false positives.
   - Not a threshold blocker (Pronunciation at 8.0).

5. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - One wrong IPA entry. Not a threshold blocker.

6. **AM relationships too generic** [Profiles]
   - All 5 relationships say "adversary". While accurate, more specific descriptions would help narrators.
   - Not a threshold blocker.

7. **Summary says "three companions" — should be four** [Summaries]
   - Ted kills all four (Benny, Ellen, Gorrister, Nimdok), not three. Minor factual error in summary text.
   - Not a threshold blocker (Summaries at 8.5).

### LOW
8. **Ted's personality too flat** [Profiles]
   - "emotional numbing, resignation, pragmatic passivity" misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue, hard to fix generically.

## Fix Priority for Attempt 13

**APPLIED (Attempt 13):**

1. **Fix CRITICAL #1 via post-correction (IMPLEMENTED)**: Added `clean_plot_summary_personality()` method to `OutputCharacterCorrector` in `post_corrections.py`. Detects when a character's `personality.summary` mentions 3+ other character names (or 2+ names AND another character leads the sentence) — indicating a plot-synopsis dump. Replaces with character-subject sentences from source text (sentences starting with the character's canonical name). Falls back to clearing to None if no subject sentences found. Added to `run_all()` after `clean_unknown_appearance()`. Expected impact: +0.5 on Profiles → 8.0.

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
| 13 | AM personality post-correction | post_corrections.py (clean_plot_summary_personality) | Pending verification |

**⚠️ STUCK PATTERN DETECTED:** `analyzer.py:_plot_summary_safety_net()` has been modified 3 times (attempts 10, 11, 12) for AM personality with NO SUCCESS. Fix phase MUST use a different approach — post-correction in `post_corrections.py` recommended.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls, 5 items processed, 5H/0M/0L (all high confidence)
- 0 LLM retries, 0 JSON parse failures
- Pronunciation: 23 entries (unchanged from attempt 10)
- Runtime: 16m 52s

## Pipeline Notes (Attempt 12)
- 6 characters found: Benny (35), Ellen (30), Gorrister (29), Nimdok (17), Ted (5), AM via safety net (74 mentions) ✓
- Character Profiles: 5 items processed, 5H/0M/0L (all high confidence — Nimdok parsed successfully!)
- AM safety net fired: role=antagonist, 74 mentions ✓
- Nimdok FIX WORKED — 6 chars in output (was 5 in attempt 11)
- physical_description populated for 4/6 characters (was 1/6)
- AM personality STILL plot_summary dump despite code change (3rd failure)
- 23 pronunciation entries (unchanged)

## Next Action
Re-run analysis to verify fix. AM personality should now be either: (a) extracted from source-text sentences where AM is the grammatical subject, or (b) null (cleared). Either is better than the plot-synopsis dump.
