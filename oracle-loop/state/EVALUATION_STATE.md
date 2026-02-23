# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 10
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_115856/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

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

## What Worked in Attempt 10
1. **Fix 1 (age pattern fix) — WORKED**: `appearance.age_indication` is now null for all characters. The `_age_extract_pat` fix requiring "old" for written-number forms prevented re-extraction of "five years" duration strings. Combined with Fix 3 (`clean_unknown_appearance()`), all spurious age data is gone from both data and HTML.
2. **Fix 2 (AM safety net profile enrichment) — PARTIALLY WORKED**: AM now has:
   - `role: "antagonist"` ✓ (keyword detection working)
   - `personality.summary` populated ✓ (but it's the full plot_summary text, not actual personality traits — see issues below)
   - `relationships` to all 5 humans ✓ (but all say "see plot summary" — lazy placeholder)
3. **Fix 3 (clean_unknown_appearance) — WORKED**: "unknown"/"not described" placeholder values cleared from appearance fields. Absence > noise.
4. **Fix 4 (compound word filter) — WORKED**: Pronunciation entries dropped from 37→23. Compounds like tinfoil, firelight, snowdrifts, deckplates, floorplates all correctly filtered out.

## What Did NOT Fully Work
1. **AM's personality is the plot_summary itself**: Instead of extracting personality traits (sadistic, omnipotent, hateful), the safety net copied the entire plot_summary paragraph into `personality.summary`. It's truncated and reads as narrative ("Five survivors—Ted, Ellen, Nimdok..."), not personality description. The context sentence extraction likely captured the entire plot_summary rather than just AM-relevant sentences.
2. **AM's relationships are all "see plot summary"**: All 5 relationships just say "see plot summary" rather than describing the actual relationship (e.g., "captor and torturer", "transforms into mouthless blob"). The safety net's relationship population is too simplistic.
3. **physical_description still null for all 6 characters**: Benny has `appearance.summary` = "monkey-like face with radiation scars..." and Nimdok has distinguishing features, but `physical_description` at top level is never populated. The attempt 9 plan mentioned this (Fix #4) but it was not implemented in attempt 10's fixes.

## Current Issues (Priority Order)

### HIGH
1. **AM's personality.summary is the full plot_summary, not actual personality traits** [Profiles]
   - Problem: AM's personality reads: "Five survivors—Ted, Ellen, Nimdok, Gorrister, and Benny—trudge through the nightmarish..." — this is the entire plot summary, not personality traits. It's truncated mid-sentence.
   - Evidence: `jq '.characters[] | select(.canonical_name == "AM") | .personality.summary' analysis.json` returns the full plot_summary text.
   - Root cause: The safety net's context sentence extraction captured the entire plot_summary paragraph instead of extracting personality-relevant descriptors.
   - Location: `src/analyzer.py` (`_plot_summary_safety_net`)
   - Fix: Instead of dumping context sentences verbatim, extract short descriptor phrases from plot_summary sentences that mention the character. For AM: find "sadistic", "sentient supercomputer", "tormented", "manipulations", "cruel", "silent cruelty" in context and build a personality summary like "Sadistic, omnipotent sentient supercomputer; endlessly creative in devising torments; motivated by hatred of humanity." Cap personality.summary at ~200 chars.

2. **AM's relationships are all "see plot summary"** [Profiles]
   - Problem: All 5 relationships say "see plot summary" — useless for a narrator.
   - Evidence: `jq '.characters[] | select(.canonical_name == "AM") | .relationships'` → all values "see plot summary"
   - Root cause: Safety net creates relationships with placeholder text instead of extracting actual relationship descriptions.
   - Location: `src/analyzer.py` (`_plot_summary_safety_net`)
   - Fix: Use the plot_summary context to generate meaningful relationship descriptions. For a character detected as "antagonist" who appears with other characters, the relationship is likely "captor/torturer" or "antagonist" by default. At minimum: "AM tortures and controls [character], keeping them alive indefinitely as objects of hatred."

3. **physical_description null for all characters** [Profiles]
   - Problem: 0/6 characters have `physical_description` at top level, but `appearance.summary` and `appearance.distinguishing_features` are populated for some (Benny, Nimdok, Gorrister).
   - Evidence: `jq '[.characters[] | select(.physical_description != null)] | length'` → 0. But Benny's `appearance.summary` = "Benny has a monkey-like face with radiation scars..."
   - Location: `src/pipeline/character_extraction_v2/post_corrections.py` (OutputCharacterCorrector)
   - Fix: Add a step in `OutputCharacterCorrector.run_all()` that copies `appearance.summary` to `physical_description` when `physical_description` is null and `appearance.summary` is not null/empty/"unknown". Generic fix, helps all texts.

### MEDIUM
4. **Remaining pronunciation false positives** [Pronunciation]
   - Problem: "palette", "piteously", "eternities", "shoal" are standard English words that a narrator shouldn't need help with. 4 of 17 non-homograph entries (~24%) are mild false positives.
   - Impact: Not a threshold blocker (Pronunciation is at 8.0), but could be better.
   - Fix: Lower priority — these are borderline and some narrators might actually appreciate the notes.

5. **"choir" IPA wrong** [Pronunciation]
   - Problem: Listed as /kwɑːr/, correct is /kwaɪər/.
   - Impact: One wrong IPA among 17 entries with IPA. Not a threshold blocker.

6. **Themes too generic** [Summaries]
   - Current: "identity", "ambition", "loss"
   - "ambition" is particularly wrong for this story. Better: dehumanization, technological tyranny, mercy/suffering, hatred.
   - Impact: Minor — themes are supplementary.

### LOW
7. **Ted's personality too flat** [Profiles]
   - "emotional detachment and resignation" — misses paranoid, cynical, unreliable narrator traits.
   - Impact: LLM profiling quality; hard to fix generically.

8. **Some relationship descriptions questionable** [Profiles]
   - Ellen → Gorrister: "abuser" — strong for text evidence.
   - Ted's relationships list others as "murder victim" — technically correct (Ted mercy-kills them) but misleading without context.
   - Impact: LLM phrasing issue; hard to fix generically.

## Fix Priority for Attempt 11

**To cross 8.0 in Profiles (currently 7.5):**
- Fix #1 (AM personality — extract traits, don't dump plot_summary) — fixes the most jarring profile issue (+0.3)
- Fix #2 (AM relationships — generate meaningful descriptions) — eliminates "see plot summary" placeholders (+0.2)
- Fix #3 (physical_description from appearance.summary) — populates top-level field for narrator reference (+0.3)

**These 3 fixes should push Profiles from 7.5 → 8.0-8.5.**

The other 5 categories are all ≥ 8.0 and should not regress from these targeted profile fixes.

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
- **Fix 1**: `_plot_summary_safety_net()` personality — sentence-level extraction (split by `.!?;`) instead of 200-char windows. Takes the first 3 AM-containing sentences, caps at 200 chars. Root cause: window overlap was capturing entire plot_summary. Modified: `src/analyzer.py`
- **Fix 2**: `_plot_summary_safety_net()` relationships — replaced "see plot summary" placeholder with role-based defaults: "adversary" for antagonist, "ally" for protagonist, "associate" for supporting. Universal, no book-specific logic. Modified: `src/analyzer.py`
- **Fix 3**: `physical_description` field — added `physical_description: Optional[str] = None` to `Character` model. Added `OutputCharacterCorrector.propagate_physical_description()` that copies `appearance.summary` → `physical_description` when the latter is absent (skips "unknown"/"not described" placeholders). Called in `run_all()` after `clean_unknown_appearance()`. Modified: `src/models.py`, `src/pipeline/character_profiling/post_corrections.py`
- **Smoke test**: PASS — AM personality now "a sentient supercomputer that has tormented them for over a century" (196 chars); relationships will be "adversary" for all 5 humans; Benny will have physical_description populated from appearance.summary

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

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls for 5 supporting characters (AM not profiled — safety net bypass)
- 0 low-confidence items, 0 LLM retries, 0 JSON parse failures
- Pronunciation: 23 entries (down from 37), compound filter working
- Runtime: 16m 6s analysis

## Next Action
Run PROMPT_analyze.md — Re-analyze i_have_no_mouth to verify attempt 11 fixes. Target: Profiles 7.5 → 8.0+.
