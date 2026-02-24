# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 16
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_142521/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7.5/10 ✗ (FAILING — two-part fix changed AM personality from garbled fragments to coherent plot summary, but it's STILL a plot narrative, not personality traits)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 7.5)

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
| 14 | 8.53 | +1.18 | Execution ordering fix WORKED — plot dump gone! But replacement is garbled sentence fragments. Ellen restored. Nimdok improved. AM personality still not useful. |
| 15 | 8.53 | +1.18 | Two-part fix changed AM personality form (garbled fragments → coherent plot narrative) but STILL not personality traits. Nimdok chimpanzee cross-contamination returned (stochastic). **6th failed AM personality attempt.** |

## What Happened in Attempt 15

### Fixes Applied
1. **Part A — Intro-phrase extraction in `_plot_summary_safety_net()`**: Instead of extracting full sentences with AM as subject, extract adjective/descriptor phrases from the plot_summary context.
2. **Part B — Quality filter in `clean_plot_summary_personality()`**: Filter out garbled fragments (name-only sentences, text artifacts, too-short content) and fall back to None.

### Result: DID NOT WORK — Plot summary content changed form but is still narrative

**AM personality is now:** `"As time and space warp under AM's control, their fragile camaraderie fractures; AM weaponizes their memories, fears, and relationships, turning trust into paranoia and love into resentment. The story…"`

**Analysis of what happened:**
- Part A produced a plot summary narrative instead of adjective-based personality traits. The output describes story events ("camaraderie fractures", "turning trust into paranoia") not personality characteristics ("sadistic", "omnipotent", "hateful").
- Part B quality filter likely did NOT trigger because the personality text is coherent prose (not garbled) and uses pronouns ("their") instead of naming 3+ characters by name. `clean_plot_summary_personality()` checks for named character mentions, not pronouns.
- Net result: the personality text changed from garbled fragments to coherent narrative, but it's still fundamentally a plot summary rather than personality traits.

### Stochastic Changes (not from code fixes)
- **Nimdok chimpanzee cross-contamination RETURNED**: Physical description says "resembling a chimpanzee in posture and movement" — this is Benny's ape-like description incorrectly attributed to Nimdok. Was GONE in attempt 14, back now (stochastic regression).
- **Other profiles stable**: Benny, Ellen, Gorrister profiles similar to attempt 14. physical_description: 4/6.

## Current Issues (Priority Order)

### CRITICAL
1. **AM personality is STILL a plot summary narrative — 6th failed fix attempt** [Profiles]
   - Problem: AM's personality reads: `"As time and space warp under AM's control, their fragile camaraderie fractures; AM weaponizes their memories, fears, and relationships, turning trust into paranoia and love into resentment. The story…"` — this describes story events, not AM's personality. It's coherent (not garbled) but fundamentally the wrong type of content. Truncated ("The story…"). Does not capture AM's key traits: sadistic, omnipotent, hateful, creative in cruelty, imprisoned by its own existence.
   - Root cause: Every heuristic approach to extract personality from LLM-generated plot_summary text has failed because the plot_summary is narrative prose — regex/pattern approaches can't distinguish "personality-relevant prose" from "plot-relevant prose" since they're interleaved in the same sentences.
   - **6 FAILED APPROACHES SO FAR:**
     1. Attempt 10: Direct dump of plot_summary → too long, mentions everyone
     2. Attempt 11: Sentence extraction → unchanged (code didn't take effect)
     3. Attempt 12: Subject-sentence selection → unchanged (code didn't take effect)
     4. Attempt 13: Post-correction cleanup → correct code but ran before AM existed
     5. Attempt 14: Execution ordering fix → garbled source-text fragments
     6. Attempt 15: Intro-phrase extraction + quality filter → coherent plot narrative (pronouns bypass name-check)
   - **RECOMMENDED APPROACH — Set personality to `None` for safety-net characters:**
     - After 6 failed heuristic extraction attempts, the simplest reliable fix is to NOT set personality at all for safety-net characters. A null personality is strictly better than a misleading plot summary for narrator preparation.
     - The narrator still gets: role="antagonist", 74 mentions, 5 adversary relationships — this is functionally useful.
     - Null personality is honest (says "I don't have detailed personality info") vs. plot narrative (misleads the narrator with story events presented as personality).
     - Implementation: In `_plot_summary_safety_net()`, simply don't set `personality` (or set it to `None`). Remove the personality extraction logic that has failed 6 times.
   - **ALTERNATIVE — Minimal hardcoded personality from role:**
     - For safety-net characters with role="antagonist", set personality to: `{"summary": "Primary antagonist.", "traits": [], "temperament": null, "emotional_range": null}`
     - This is one step above null — tells the narrator "this is the antagonist" without any risk of plot summary contamination.
   - Location: `analyzer.py` (`_plot_summary_safety_net` personality generation logic)
   - Expected impact: AM gets clean minimal profile → removes the only source of deduction on Profiles score from code-fixable issues. Combined with favorable stochastic outcomes on other profiles → Profiles reaches 8.0.

### MEDIUM
2. **Nimdok physical_description cross-contamination** [Profiles — stochastic]
   - Problem: Nimdok described as "resembling a chimpanzee in posture and movement" — this is Benny's ape-like description from the text, not Nimdok's. Nimdok has minimal physical description in the source text.
   - This is a stochastic LLM profiling error — was correct in attempt 14, wrong again in attempt 15. Not code-fixable.

3. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words.
   - Not a threshold blocker (Pronunciation at 8.0).

4. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - Not a threshold blocker.

### LOW
5. **Ted's personality too flat** [Profiles]
   - Misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue, not code-fixable.

6. **AM relationships too generic** [Profiles]
   - All say "adversary". More specific descriptions would help narrators.
   - Low priority — relationships are functional.

7. **Gorrister personality partially inaccurate** [Profiles — stochastic]
   - Described as "cruel and domineering" but in the text Gorrister is more passive/nihilistic.
   - LLM profiling quality issue, not code-fixable.

## Fix Applied for Attempt 16

**CRITICAL #1 fix was applied in commit d062607 (previous session):**

### Applied Fix: LLM-profile safety-net characters
In `analyzer.py`, `_plot_summary_safety_net()` now returns the list of newly-added characters. The caller then calls `_generate_character_profile()` for each safety-net character, giving them real LLM-generated personality/appearance fields instead of heuristic extracts.

This completely replaces the 6x-failed heuristic extraction approach. AM will be profiled the same way as Ted, Ellen, Gorrister, Benny, and Nimdok.

**Status: CRASHED — `"Character" object has no field "description"`**

### Crash Details (Attempt 16)
- Pipeline ran normally through profiling 5 eligible characters
- Safety net fired: `Plot summary safety net: added 'AM' (role=antagonist, text mentions=74)`
- Then: `Profiling safety-net character: AM`
- Crashed: `Error during analysis: "Character" object has no field "description"`
- `_generate_character_profile()` tries to set a `description` field that doesn't exist on the `Character` Pydantic model
- Need to identify which field name is correct in the `Character` model (likely `summary` or `personality` or some nested structure)
- Fix: Find the correct field name in `Character` model and update `_generate_character_profile()` accordingly

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

### Attempt 14 Fix Applied
- **Fix 1**: Reordered execution in `analyzer.py:2067-2079` — moved `_plot_summary_safety_net()` BEFORE `OutputCharacterCorrector().run_all()` → **PARTIALLY WORKED** — Plot dump replaced with source sentences, but extracted sentences are garbled fragments ("AM. AM had been as ruthless with its own life aswith ours. AM had blinded him."). Ordering is now correct; replacement quality is the issue.

### Attempt 15 Fixes Applied
- **Fix 1 (Part A)**: Intro-phrase extraction in `_plot_summary_safety_net()` → **DID NOT WORK** — produced coherent plot narrative instead of adjective-based personality traits. Pronouns bypass post-correction name check.
- **Fix 2 (Part B)**: Quality filter in `clean_plot_summary_personality()` → **DID NOT TRIGGER** — personality text is coherent prose, passes length/quality heuristics despite being wrong content type.

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
| 14 | Execution ordering (safety net before post-corrections) | analyzer.py | **PARTIALLY WORKED** — ordering fixed, but replacement quality poor |
| 15 | AM personality intro-phrase extraction (Part A) | analyzer.py (_plot_summary_safety_net) | **DID NOT WORK** — produced plot narrative, not personality traits |
| 15 | AM personality quality filter (Part B) | post_corrections.py (clean_plot_summary_personality) | **DID NOT TRIGGER** — coherent prose passes heuristics |
| 16 | LLM-profile safety-net characters via _generate_character_profile() | analyzer.py | **UNTESTED** — replaces all heuristic extraction; safety net only detects, LLM profiles |

**⚠️ AM PERSONALITY — 7TH ATTEMPT (APPROACH CHANGE)**: Instead of heuristic extraction from plot_summary text, safety-net characters are now LLM-profiled via `_generate_character_profile()`, same as all other characters. Applied in commit d062607. **CRASHED** — `Character` has no field `description`. Fix needed: use correct field name from Character Pydantic model.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls, 5 items processed, **5H/0M/0L** (ALL high confidence)
- 0 LLM retries, 0 JSON parse failures
- Pronunciation: 23 entries (unchanged from attempt 10)
- Runtime: 15m 51s

## Next Action
Run PROMPT_analyze.md to evaluate attempt 16 — LLM profiling for safety-net characters (commit d062607) is applied and ready for analysis. The fix replaces all heuristic personality extraction with a proper `_generate_character_profile()` call, the same pipeline used for all other characters.
