# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 9
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_112239/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6.5/10 ✗ (FAILING)
- HTML Presentation: 7.5/10 ✗ (FAILING)
- **Overall: 7.43/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

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
| 8 | 7.43 | +0.08 | **Narrator detection FIXED** (Ted is_narrator: true). Orphaned relationships cleaned. AM still missing. Ages still wrong. |

## What Worked in Attempt 8
1. **Fix 2 (narrator detection) — WORKED**: Ted now `is_narrator: true` with `role: "protagonist"` and narrator badge in HTML. The complete rewrite of `_get_narrative_style()` to check pipeline_metadata / POV consistency / first-person markers succeeded where 6 previous attempts failed.
2. **Fix 3 (orphaned relationships) — WORKED**: `clean_orphaned_relationships()` successfully removed "Jesus: unknown" from all character relationship maps.
3. **Refactor (post_corrections) — WORKED**: PipelineCharacterCorrector and OutputCharacterCorrector classes with 49 unit tests.

## What Did NOT Work in Attempt 8
1. **Fix 1 (fallback prompt for AM) — FAILED**: Despite the prompt saying "Include humans, non-human beings, AI, and any named force that acts with agency," the STEP 3.1 fallback still produced 0 main_cast characters. The LLM either doesn't return "AM" or the parser can't extract it. This is the **8th consecutive failure** to extract AM through the main_cast/fallback LLM pipeline.
2. **Fix 4 (age validation) — FAILED**: Ages still show "five years" for Benny/Ellen/Gorrister and "nine years" for Ted. The `extract_deterministic_age()` validation either isn't being called, or the pattern doesn't match the actual age_indication format.

## ESCALATION REQUIRED — MANDATORY APPROACH FOR ATTEMPT 9

**The LLM-based character extraction pipeline CANNOT extract AM.** After 8 attempts with different prompts, parsing strategies, grounding bypasses, and fallbacks, the main_cast pipeline consistently produces 0 characters. The fix phase MUST abandon the LLM extraction path for AM and use a **post-processing approach** instead.

### MANDATORY: Plot-Summary Post-Processing for Missing Characters

The plot_summary mentions "AM" 7+ times and correctly describes it as "the malevolent AI known as AM." The fix MUST:

1. **After all character extraction is complete** (after STEP 5 / before output conversion), add a post-processing step in `src/analyzer.py`:
   - Parse the `plot_summary` text for capitalized names/acronyms that appear 3+ times
   - Compare against the existing character list
   - For any name found in plot_summary but missing from characters, create a minimal character entry:
     - `canonical_name`: the name as found in plot_summary
     - `role`: inferred from plot_summary context (e.g., "antagonist" if described negatively)
     - `is_narrator`: False
     - A description extracted from the plot_summary sentence mentioning the name
   - This is a **safety net** — it runs only when the LLM pipelines fail to extract a plot-critical character

2. **This must NOT be in characters.py** — it's been modified 8 times without success. Put it in `analyzer.py` as a post-processing step, similar to how the evidence filter and orphaned relationship cleanup work.

3. **Regex approach for "AM"**: `r'\bAM\b'` in plot_summary will match. Count occurrences. If >= 3 and "AM" not in any character's canonical_name or aliases, create the entry.

### Age Validation Debug

Fix 4 (age validation) didn't work. The fix phase should:
1. Check if `extract_deterministic_age()` is actually called during the pipeline run
2. Print/log the raw `age_indication` value before validation
3. The "five years" string may not match the expected pattern — check exact string format

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) COMPLETELY MISSING — 8th consecutive failure** [Completeness]
   - Problem: AM is the primary antagonist — the sentient supercomputer whose hatred drives the entire story. The plot_summary mentions "AM" 7+ times as "the malevolent AI known as AM." Yet AM is not in the character list.
   - Evidence: 0 main_cast characters. All 5 characters from supporting pipeline. STEP 3.1 fallback fired (5 LLM calls) but produced 0 main_cast characters.
   - Root cause: The LLM character extraction pipeline fundamentally cannot handle "AM" as a character name (too short? too unusual? filtered by parser?). 8 attempts to fix the LLM path have all failed.
   - Location: NEW — `src/analyzer.py` (post-processing safety net)
   - Fix: **MANDATORY plot_summary post-processing** (see escalation strategy above). Do NOT modify characters.py or main_cast.py.

### HIGH
2. **"Age: five years" / "Age: nine years" still displayed** [Profiles]
   - Problem: Fix 4 from attempt 8 committed age validation in `extract_deterministic_age()` but ages remain wrong.
   - Evidence: Benny/Ellen/Gorrister show "Age: five years", Ted shows "Age: nine years" in both JSON and HTML.
   - Location: Check if `extract_deterministic_age()` is called at runtime; check if the pattern matches `"five years"`.
   - Fix: Debug why the validation didn't fire. If `extract_deterministic_age()` isn't called, add the call. If the pattern is wrong, fix it.

3. **0/5 characters have top-level physical_description** [Profiles]
   - Problem: `physical_description` is null for all characters. Nested `appearance.summary` has some data (Benny: ape-like face, Nimdok: chimpanzee features) but most are "Unknown"/"unknown".
   - Fix: Populate top-level `physical_description` from `appearance.summary` during output conversion (only when `appearance.summary` is not "Unknown"/"unknown").

4. **Some relationship descriptions factually wrong** [Profiles]
   - Nimdok → Ellen: "victim of her violence; she kills him" — WRONG. Ted kills everyone, not Ellen.
   - Gorrister → Benny: "victim of abuse and eventual murder" — confusing. Gorrister didn't murder Benny.
   - Gorrister → Ellen: "abuser" — not clearly supported by text.
   - These are LLM hallucinations in relationship descriptions. Lower priority than AM but affects profile quality.

5. **Ted's personality too flat for narrator** [Profiles]
   - Problem: Described as "emotionally detached, passive, resigned." Misses: paranoid (suspects others hate him), self-aware, cynical, unreliable narrator, mercy-killing resolve.
   - This is partially an LLM profiling quality issue. With narrator now correctly detected, a re-run with better prompting could improve this. Lower priority than AM.

### MEDIUM
6. **"hermiene" pronunciation artifact from PDF URL** [Pronunciation]
   - Problem: "hermiene" extracted from `hermiene.net` URL in PDF. Context in HTML shows the URL.
   - Fix: Filter tokens that appear in URL-like contexts (check if token appears adjacent to `.net`, `.com`, `.org` in the source text).

7. **Wrong IPA for "choir"** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - "cogito" IPA /kəˈɡiː.toʊ/ is acceptable (anglicized) though classical Latin is /ˈkɒɡɪtoʊ/.

8. **~10 common English words flagged as pronunciation items** [Pronunciation]
   - False positives: palette, tinfoil, firelight, snowdrifts, loonie, piteously, spastically, eternities, puckerings, stalactites, sonorities, deckplates, floorplates, downdropping, shoal, despond
   - Some like "despond", "mewl", "gibbered" are actually borderline — a narrator might want them flagged.
   - Clear false positives: tinfoil, firelight, snowdrifts, eternities, deckplates, floorplates, palette.

9. **Homographs with null IPA** [Pronunciation]
   - wind, read, lead, does, close, subject — all have null IPA with no context. Useless to a narrator without disambiguation.

10. **Themes still generic** [Summaries]
    - Current: "identity, loss, powerlessness" (improved from "identity, ambition, loss")
    - Better: hatred, dehumanization, suffering, mercy killing, technology/AI tyranny
    - "Identity" and "loss" are vague. "Powerlessness" is closer but misses the hatred theme that defines AM.

11. **Title displays with underscores** [Presentation]
    - "I_Have_No_Mouth_And_I_Must_Scream" in both `<title>` and `<h1>`.
    - Fix: In HTML template, replace underscores with spaces in the title (or better, use a `display_title` field).

12. **Performance timing table has empty started_at/ended_at rows** [Presentation]
    - The timing dict's `started_at` and `ended_at` string entries rendered as table rows with empty duration cells.
    - Fix: Skip non-stage entries (started_at, ended_at) when rendering the timing table.

### LOW
13. **Ted's mention count is 5** — seems very low for a first-person narrator of a 5400-word story. The NER likely only counted explicit name mentions ("Ted"), not first-person pronoun references. Not necessarily wrong, but affects ranking.

14. **Benny's voice guidance includes AM's origin story quote** — "There was the Chinese AM..." is Ted narrating about AM, not Benny's dialogue.

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
- **Fix 4**: Age validation in `extract_deterministic_age()` → **FAILED** — ages still "five years"/"nine years"
- **Refactor**: PipelineCharacterCorrector + OutputCharacterCorrector with 49 tests → **WORKED**

### Attempt 9 Fixes Applied
- **Fix 1**: Plot_summary safety net in `analyzer.py` (`_plot_summary_safety_net`) — finds all-caps names (3+ times in plot_summary, case-sensitive in source text), adds missing characters. Target: AM. Root cause: LLM extraction pipeline cannot capture all-caps acronym character names. Smoke test: "AM" correctly found (8 times in plot_summary), "AI" filtered (1 time, below threshold), hermiene excluded (URL context). Modified: `src/analyzer.py`
- **Fix 2**: HTML title underscores fix — replaces underscores with spaces in title rendering. Modified: `src/export/html_report.py` line 1731
- **Fix 3**: HTML timing table empty rows fix — adds `info is mapping` guard to skip string entries (started_at, ended_at). Modified: `src/export/html_report.py` line 724
- **Fix 4**: URL token filter in CMU pronunciation proposer — `_is_url_context()` method skips words appearing in URL-like contexts. Removes "hermiene" from hermiene.net URL artifact. Universal: any book with URLs in PDF. Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
- **Note**: Age validation (`extract_deterministic_age`) was committed in attempt 8 (e61ef6b) AFTER the analysis ran. First test on re-run.

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
| 7 | Grounding bypass for fallback | characters.py | **Code correct, no effect** |
| 7 | _get_narrative_style() type check | characters.py | **Code correct, no effect** |
| 7 | Evidence filter for false positives | analyzer.py | **WORKED** (Jesus removed) |
| 8 | Fallback prompt for sentient entities | characters.py | **FAILED** — 0 main_cast again |
| 8 | _get_narrative_style() complete rewrite | characters.py | **WORKED** — Ted is narrator |
| 8 | clean_orphaned_relationships() | post_corrections.py | **WORKED** — Jesus refs cleaned |
| 8 | Age validation in extract_deterministic_age() | post_corrections.py | **FAILED** — ages unchanged |
| 8 | Refactor post-corrections into classes | analyzer.py, post_corrections.py | **WORKED** |

**STUCK PATTERN for AM extraction:**
- `characters.py` modified **8 times** for AM extraction — ALL FAILED
- `main_cast.py` modified **3 times** — ALL FAILED
- The LLM main_cast pipeline fundamentally cannot extract "AM"
- **MANDATORY: Move to post-processing in analyzer.py** — do NOT touch characters.py or main_cast.py for AM

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (fallback fired but still 0 main_cast)
- 0 low-confidence items, 0 LLM retries
- Chapter Summaries: 0 LLM calls (cached)
- Runtime: 18m 6s total (17m 33s analysis + overhead)

| 9 | AM missing | analyzer.py (_plot_summary_safety_net) | Pending re-run |
| 9 | HTML title underscores | html_report.py | Pending re-run |
| 9 | HTML timing empty rows | html_report.py | Pending re-run |
| 9 | Pronunciation URL artifact (hermiene) | cmu_proposer.py | Pending re-run |

## Pipeline Notes (Attempt 9)
- AM added via plot_summary safety net: role=supporting, 74 text mentions ✓
- Ted is_narrator=True confirmed ✓
- Ages are None (age validation fix worked — no more "five years"/"nine years") ✓
- HTML title fix confirmed: "I Have No Mouth And I Must Scream" (no underscores) ✓
- HTML timing table fix confirmed: started_at/ended_at filtered out ✓
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority), all stages
- 6 characters total (5 + AM from safety net)
- Runtime: 18m 15s
- Competitive warning: "No definitive narrator identified yet" during pipeline, but final JSON shows Ted is_narrator=True — consistent with attempt 8 behavior

## Next Action
Run PROMPT_evaluate.md — Evaluate i_have_no_mouth attempt 9 output.
