# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 9
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_112239/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 7.98/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

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

## What Worked in Attempt 9
1. **Fix 1 (plot_summary safety net) — WORKED**: AM now present with id `plot_summary_am`, 74 mentions, role "supporting". The `_plot_summary_safety_net` in analyzer.py successfully found "AM" (8 occurrences in plot_summary) and added it as a character. This resolved the 8-attempt-long stuck pattern.
2. **Fix 2 (HTML title underscores) — WORKED**: Title now displays "I Have No Mouth And I Must Scream" (no underscores).
3. **Fix 3 (HTML timing table) — WORKED**: started_at/ended_at rows no longer render in timing table.
4. **Fix 4 (URL token filter) — WORKED**: "hermiene" no longer in pronunciation list (was from hermiene.net URL).
5. **Age validation (from attempt 8) — PARTIALLY WORKED**: Top-level `age` field is now null for all characters, but `appearance.age_indication` still has the wrong values ("five years", "nine years"), and the HTML template renders from the nested field.

## What Did NOT Fully Work
1. **Age validation — INCOMPLETE**: The fix nulled top-level `age_indication` but not `appearance.age_indication`. HTML still shows "Age: five years" for Benny/Ellen/Gorrister and "Age: nine years" for Ted.
2. **AM's profile — EMPTY**: The safety net creates a minimal entry (name, role, mentions) but AM has no personality, relationships, appearance, voice guidance, or backstory. For the story's central antagonist, this is a significant gap.
3. **AM's role — WRONG**: Listed as "supporting" when AM is clearly the primary antagonist driving the entire plot.

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **appearance.age_indication still has wrong ages — showing in HTML** [Profiles]
   - Problem: HTML shows "Age: five years" for Benny/Ellen/Gorrister and "Age: nine years" for Ted (4 occurrences: lines 1001, 1233, 1441, 1819). These are nonsensical — the characters have been trapped for 109 years.
   - Evidence: `jq '.characters[].appearance.age_indication'` returns "five years", "five years", "five years", null, "nine years", null. Top-level `age` is correctly null.
   - Root cause: The age validation in `extract_deterministic_age()` cleaned the top-level field but the HTML template reads from `appearance.age_indication` which was never cleaned.
   - Location: `src/pipeline/character_extraction_v2/post_corrections.py` (OutputCharacterCorrector) OR `src/export/html_report.py`
   - Fix: Either (a) clean `appearance.age_indication` in the post-correction step when the age is implausible (non-numeric or < 18 for characters with adult context), OR (b) in the HTML template, skip rendering age_indication when it matches implausible patterns. Option (a) is preferred — fix the data, not the template.

2. **AM has zero profile** [Profiles]
   - Problem: AM (the sentient AI antagonist driving the entire story) has: no personality, no relationships, no appearance, no voice, no backstory. The safety net creates a minimal entry but doesn't generate profile data.
   - Evidence: `jq '.characters[] | select(.canonical_name == "AM") | {personality, voice, backstory, relationships, appearance}'` → all null/empty.
   - Location: `src/analyzer.py` (`_plot_summary_safety_net` method)
   - Fix: When the safety net adds a character, extract basic profile information from the plot_summary. The plot_summary says "the sadistic, omnipotent AI known as AM" — use this to populate: personality (sadistic, omnipotent, hateful), role (change to "antagonist"), and at minimum a description. Also add relationships to all 5 humans (AM tortures them all). This doesn't need LLM calls — simple regex extraction from plot_summary sentences mentioning AM.

3. **~10 common English words as pronunciation false positives** [Pronunciation]
   - Problem: These standard English words don't need pronunciation help: tinfoil, firelight, snowdrifts, eternities, deckplates, floorplates, palette, puckerings, loonie, piteously, shoal, downdropping, spastically.
   - Evidence: 13 of 37 entries (35%) are common words or obvious compounds. A narrator doesn't need IPA for "tinfoil" or "firelight."
   - Location: `src/pipeline/pronunciation_guide/` — the false positive filtering needs strengthening.
   - Fix: Add a compound-word filter (if a word can be split into two common English words, skip it: tin+foil, fire+light, snow+drifts, floor+plates, deck+plates). Also expand the common-word exclusion list to include standard dictionary words like palette, eternities, puckerings, piteously, shoal, loonie.

### MEDIUM
4. **Physical descriptions all null at top level** [Profiles]
   - Problem: 0/6 characters have `physical_description` populated. But Benny has `appearance.summary`: "monkey-like face, enlarged genitalia, radiation scars" and Nimdok has "resembling a chimpanzee."
   - Fix: In post-correction or output conversion, copy `appearance.summary` to `physical_description` when summary is not "unknown"/"Unknown". Generic fix — applies to all texts.

5. **AM role="supporting" should be "antagonist"** [Characters]
   - Problem: The safety net assigns role="supporting" by default. AM is clearly the primary antagonist.
   - Fix: In the safety net, if the plot_summary context around a character name includes negative descriptors (sadistic, malevolent, cruel, antagonist, villain, evil), assign role="antagonist" instead of "supporting."

6. **choir IPA wrong** [Pronunciation]
   - Problem: Listed as /kwɑːr/, correct is /kwaɪər/.
   - Evidence: Standard English pronunciation; this appears to be a CMU dictionary error or LLM hallucination.
   - Location: Could be in CMU proposer or LLM pronunciation generation.
   - Fix: Lower priority — one wrong IPA among 31 is not a threshold blocker.

7. **6 homographs with null IPA** [Pronunciation]
   - Problem: wind, read, lead, does, close, subject all listed as homographs without IPA, only text disambiguation notes.
   - Evidence: The entries show e.g., "Multiple pronunciations: air movement (WIND); to turn (WYND)" which is actually useful for a narrator even without IPA.
   - Fix: Lower priority — the disambiguation notes are useful even without IPA. The homograph detection is working correctly.

### LOW
8. **Themes too generic** [Summaries]
   - Current: "identity, loss, powerlessness"
   - Better: hatred/revenge, dehumanization, suffering, mercy killing, AI tyranny
   - Impact: Minor — themes are supplementary information.

9. **Ted's personality too flat** [Profiles]
   - "detached, resigned, observant, decisive" — misses paranoid, cynical, unreliable narrator.
   - Impact: LLM profiling quality issue — not easily fixed generically.

10. **Some relationship descriptions inaccurate** [Profiles]
    - Ellen → Gorrister: "abuser, physically assaults her" — strong wording for text evidence
    - Gorrister → Ted: "victim" — ambiguous direction (Ted kills Gorrister, not vice versa)
    - Impact: LLM hallucination in relationship phrasing. Hard to fix generically.

## Fix Priority for Attempt 10

**To cross 8.0 in Profiles (currently 6.5):**
- Fix #1 (age_indication cleanup) — removes wrong ages from HTML (+0.5)
- Fix #2 (AM profile from plot_summary) — fills the biggest profile gap (+0.5)
- Fix #4 (physical_description from appearance.summary) — populates descriptions (+0.5)

**To cross 8.0 in Pronunciation (currently 7.0):**
- Fix #3 (false positive filtering) — removing ~10 false positives drops from 37→~24 entries with much better signal-to-noise (+1.0)

**These 4 fixes should be sufficient to pass both failing categories.**

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

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls for 5 supporting characters (AM not profiled — safety net bypass)
- 0 low-confidence items, 0 LLM retries, 0 JSON parse failures
- Pronunciation: 34 LLM calls for 37 items
- Runtime: 17m 45s analysis
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority)

### Attempt 10 Fixes Applied
- **Fix 1**: `_age_extract_pat` — require "old" for written-number forms → prevents re-extracting duration "five years" after clearing. Root cause: extraction pattern was inconsistent with validation pattern. File: `post_corrections.py:114-119`.
- **Fix 2**: Safety net profile enrichment — expand role detection keywords (sadistic, hateful, cruel, torment, torturer); collect original-case context sentences; populate `personality.summary` from context; populate `relationships` to co-mentioned characters. File: `analyzer.py:_plot_summary_safety_net`.
- **Fix 3**: `clean_unknown_appearance()` — new step in `OutputCharacterCorrector.run_all()` that clears "unknown"/"not described"/"n/a" placeholder values from `appearance.summary`, `appearance.age_indication`, `appearance.distinguishing_features`. Absence of data is better than noise. File: `post_corrections.py`.
- **Fix 4**: `_is_closed_compound()` — new method in CMU proposer that skips words that split into two known CMU words (e.g., "tinfoil"→tin+foil, "firelight"→fire+light, "deckplates"→deck+plates). Universal invariant: closed compounds of known words are fully predictable. File: `cmu_proposer.py`.

## Next Action
Run PROMPT_analyze.md — Re-run analysis for attempt 10.
