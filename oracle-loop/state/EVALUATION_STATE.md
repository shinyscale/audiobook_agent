# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 5)
- Runtime: 87m 33s
- Narrator: Nick Carraway confirmed ✓ (Fix I/J worked — Ella Kaye blocked by low-mention invariant)
- Characters: 33 total; Jay Gatsby 269 mentions with aliases [Gatsby, James Gatz] ✓
- "colleague" filter effectiveness: TBD (awaiting evaluation)
- LLM marker proposer returned non-list (dict) warnings during chapter detection — non-fatal
- Pronunciation: 149 flags; some json_mode validation errors (non-fatal, fallback used)

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 6/10
- Character Profiles: 3.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |
| 4 | 6.93 | +1.03 | **REGRESSION**: Gatsby promoted (Fix G ✓) but narrator BROKE AGAIN (Henry C. Gatz). Colleague filter FAILED. |

## What Improved in Attempt 4
- **Fix G PARTIALLY WORKED**: Jay Gatsby is now `main_cast_1` with role "protagonist" and 268 mentions with correct aliases ["Mr. Gatsby", "Gatsby", "James Gatz"]. He has a physical description now.
- **Wolfsheim/Wolfshiem split partially addressed**: main_cast_7 "Meyer Wolfsheim" (6 mentions) has alias "Meyer Wolfshiem". But supporting_2 "Meyer Wolfshiem" (32 mentions) still exists as a separate entry — the merge didn't fully work.

## What REGRESSED in Attempt 4
- **NARRATOR REGRESSION**: Henry C. Gatz (Gatsby's father, 13 mentions, appears only in Ch. 9) is marked as narrator and role "protagonist". Nick Carraway (34 mentions, actual first-person narrator of entire book) has `is_narrator: false`. This was FIXED in attempt 3 (Fix D) but broke again.
- **Role inflation from Fix G**: The safety net promoted characters too aggressively:
  - Doctor T. J. Eckleburg (5 mentions) → "protagonist" — this is a billboard, not a protagonist
  - the green light (10 mentions) → "protagonist" — this is a symbol, not a protagonist
  - Henry C. Gatz (13 mentions) → "protagonist" — minor character who appears only at the funeral
  - The ≥200 mentions threshold is fine for Gatsby, but something else is promoting low-mention characters
- **Fix H COMPLETELY FAILED**: "colleague" still has 198/256 relationship entries (was ~213 in attempt 3). The filter code was either not reached or not effective.

## What Did NOT Improve
- **Speech patterns still all null**: Zero speech_pattern entries across all 36 characters. Fix was not attempted in attempt 4.
- **F6 generic descriptor clutter still present**: butler (20), chauffeur (10), gardener (5), Servants (7), reporter (2), postman (1), war veteran (1), etc.
- **George B. Wilson** still canonical with fabricated middle initial "B."
- **Owl Eyes duplicated**: "Owl Eyes" (1 mention) and "Man with owl-eyed glasses" (1 mention) — same character

## Current Issues (Priority Order)

### CRITICAL

1. **NARRATOR REGRESSION: Henry C. Gatz identified as narrator instead of Nick Carraway** [Identity Resolution / Profiles]
   - Problem: `main_cast_8` Henry C. Gatz has `is_narrator: true, role: "protagonist"`. Nick Carraway has `is_narrator: false`.
   - This was FIXED in attempt 3 by Fix D (narrator.py + characters.py layered defense). Something in attempt 4 broke it.
   - **Root cause hypothesis**: Fix G's role safety net promoted Henry C. Gatz to "protagonist" (he has 13 mentions, well below the 200 threshold — so it's not the mention threshold). The promotion may have triggered narrator detection to pick him up because "Gatz" appears as a surname that matches "James Gatz" (Gatsby's real name), confusing the narrator detector.
   - **Must investigate**: Why is Henry C. Gatz role "protagonist" with only 13 mentions? Fix G threshold was 200. Something ELSE is promoting him. Check the actual role assignment logic — was the role field already "protagonist" from the V2 pipeline, not from Fix G?
   - **Fix approach**:
     (a) Debug why Henry C. Gatz has role "protagonist" — if it's from V2 pipeline, that's a separate issue from Fix G
     (b) The narrator detection in Fix D (attempt 3) needs to be verified it's still intact — check if Fix G's code runs AFTER or overwrites narrator detection
     (c) Add a hard constraint: narrator must have mentions in majority of chapters (Nick appears in all 9, Henry C. Gatz appears in 1)
   - Location: `src/analyzer.py` (Fix G safety net), `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py`
   - **Pattern alert**: `src/agents/characters.py` and narrator detection modified in attempts 2, 3, and 4. The narrator fix is fragile.

2. **"colleague" relationship spam STILL pervasive (198/256 = 77% of all relationships)** [Profiles]
   - Problem: Fix H added "colleague" to `_VAGUE_REL_LABELS` and added startswith check, but 198 "colleague" labels remain. The filter code is NOT executing or is being bypassed.
   - **Must investigate**: Read the actual code changes in `src/analyzer.py` to verify Fix H was applied correctly. Check if there's a code path that sets relationships AFTER the filter runs.
   - **Fix approach**:
     (a) Verify Fix H code is syntactically correct and in the right execution path
     (b) Add a FINAL post-processing pass that strips "colleague" from ALL character relationship dicts AFTER all profiling is complete (just before JSON export)
     (c) This must be the absolute last step — no code can add "colleague" after it
   - Location: `src/analyzer.py` — need to find where relationships are finalized and add filtering there
   - **Pattern alert**: This is attempt 2 trying to fix "colleague" filtering. Previous prompt-level approach failed (attempt 3). Code-level filter approach also failed (attempt 4). Need to verify the code is actually executing.

### HIGH

3. **Speech patterns null for ALL 36 characters** [Profiles]
   - Problem: Zero speech_pattern entries. Critical missing data for narrator prep.
   - Notable missing: Gatsby's "old sport", Wolfshiem's dialect ("Oggsford", "gonnegtion"), Tom's aggressive tone, Daisy's "low, thrilling voice"
   - Location: Profile generation in `src/analyzer.py` — the prompt may not request speech patterns, or the response parser drops the field
   - Fix: Ensure prompt explicitly asks for speech patterns and parser captures the field

4. **Wolfsheim/Wolfshiem still duplicated** [Identity Resolution]
   - `main_cast_7` "Meyer Wolfsheim" (6 mentions) and `supporting_2` "Meyer Wolfshiem" (32 mentions) — same person, different spellings
   - The main_cast entry has the alias "Meyer Wolfshiem" but they weren't merged
   - Location: V2 pipeline or post-extraction merge — need fuzzy string matching for near-identical names

5. **Role inflation: symbolic entities and minor characters as "protagonist"** [Identity Resolution]
   - Doctor T. J. Eckleburg (5 mentions): billboard eyes → "protagonist"
   - the green light (10 mentions): symbol → "protagonist"
   - Henry C. Gatz (13 mentions): appears only in Ch. 9 → "protagonist"
   - Fix G's safety net may be setting roles correctly for Gatsby but something else is inflating roles for low-mention characters
   - Location: Check V2 pipeline role assignment and Fix G's thresholds

6. **F6 generic descriptor clutter (16 F6 entries)** [Completeness]
   - butler (20), chauffeur (10), Servants (7), gardener (5), reporter (2), Lutheran minister (1), drunk man in library (1), war veteran (1), Mrs. Ulysses Swett (1), Etty (1), Ripley Snell (1), Postman (1), Owl Eyes (1), Man with owl-eyed glasses (1), Clarence Endive (1)
   - Generic descriptors (butler, chauffeur, gardener, Servants) should be filtered
   - Single-mention party guests should be filtered
   - Owl Eyes + Man with owl-eyed glasses should be merged
   - Location: F6 reconciliation in `src/analyzer.py`

7. **Incorrect relationship labels persist** [Profiles]
   - Tom→Daisy: "husband" (correct meaning, but label should be "wife" for Daisy)
   - Gatsby→Wolfshiem: "husband" (completely wrong — should be "business associate" or "protégé")
   - Gatsby→Henry C. Gatz: "son" (correct — Gatsby is Gatz's son, but confusing when Gatz is labeled narrator)
   - Nick→Gatsby: "colleague" (should be "neighbor" / "friend")

### MEDIUM

8. **"George B. Wilson" — fabricated middle initial still canonical** [Identity Resolution]
   - Canonical name is "George B. Wilson" with 86 mentions — Fitzgerald never uses a middle initial
   - Should be "George Wilson"
   - Location: V2 Pass 1 extraction hallucinated the initial

9. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Both main_cast_2 (Daisy) and main_cast_3 (Tom) have "Buchanan" as alias
   - Ambiguous surname should be removed when multiple characters claim it

10. **Nick Carraway shows only 34 mentions** [Completeness]
    - As first-person narrator using "I", his actual presence is every page
    - 34 by-name mentions is technically correct but gives a misleading picture of importance
    - Not a code issue per se — just a limitation of name-based mention counting

11. **Duplicate Daisy alias** [Alias Grouping]
    - main_cast_2 Daisy Buchanan has aliases: ['Daisy', 'Daisy Fay', 'Daisy', 'Buchanan'] — "Daisy" appears twice

## Fix History

### Attempt 2 fixes
- **Fix A: STEP 4.26 narrator threshold** — INEFFECTIVE (wrong layer)
- **Fix B: STEP 5.11 promotion** — INEFFECTIVE (code not firing)
- **Fix C: Relationship label override guard** — PARTIALLY EFFECTIVE

### Attempt 3 fixes
- **Fix D: Narrator layered defense (narrator.py + characters.py)** — EFFECTIVE ✓ (but regressed in attempt 4)
- **Fix E: "colleague" forbidden in profiler prompt** — INEFFECTIVE (LLM ignores forbidden list)
- **Fix F: STEP 5.11 diagnostic logging** — ADDED but promotion still didn't fire

### Attempt 4 fixes
- **Fix G: Role safety net in analyzer.py** — PARTIALLY EFFECTIVE (Gatsby promoted ✓, but may have caused narrator regression and role inflation for other characters)
- **Fix H: "colleague" filter in post-processing** — COMPLETELY INEFFECTIVE (198 "colleague" entries remain, nearly unchanged from 213)

### Attempt 5 fixes
- **Fix I: Relative mention guard in narrator.py `update_characters_with_narrator`** — Added guard: narrator candidate rejected if mention_count < 8% of max-mention character (when max > 20). Blocked characters clear narrator_info so downstream stages don't inherit wrong narrator. Root cause: Henry C. Gatz (13 mentions) was above the old ≤5 guard but below 8% of Gatsby's 268 = 21.4 threshold. Smoke test: Henry (13/268 = 4.9%) blocked, Nick (34/268 = 12.7%) passes.
- **Fix J: Step 6.6 narrator fallback minimum raised from 3 to 20 mentions** — The fallback that picks narrator as "fewest mentions in plot summary" now requires ≥20 mentions. This prevents low-mention background characters from being picked when primary detection fails. Henry (13) would be excluded from candidates.
- **Fix K: Colleague substring filter (both locations)** — Changed `startswith("colleague")` to `any("colleague" in v.lower())` at both filter locations (lines 2135 and 3782). Root cause: LLM outputs "business colleague", "former colleague", etc. which don't start with "colleague". Now uses substring containment for both "colleague" and "acquaintance" vague labels.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | **Partially effective** — Gatsby promoted but narrator regressed |
| 4 | "colleague" post-processing filter | `src/analyzer.py` (two locations) | **FAILED** — 198 "colleague" entries remain |

**Pattern detected:** Narrator detection has been fixed and broken across attempts 3-4. Fix G's safety net in analyzer.py may conflict with narrator detection from Fix D. Need to understand execution order and whether Fix G overwrites narrator assignments.

**Pattern detected:** "colleague" filtering has failed twice (prompt-level in attempt 3, code-level in attempt 4). Fix H code must be verified — it may have a syntax error, be in an unreachable code path, or relationships are set AFTER the filter runs.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- No chunking issues apparent

## Priority Fix Order for Attempt 5

**The two blocking categories are Character Extraction (5/10) and Profiles (3.5/10).**

1. **Fix the narrator REGRESSION** (Critical #1) — Verify Fix D is still intact. Understand why Henry C. Gatz became narrator. Add chapter-coverage guard: narrator must appear in >50% of chapters. This single fix should recover the ~1 point lost from attempt 3.

2. **Debug and fix the "colleague" filter** (Critical #2) — READ the actual code in analyzer.py to see if Fix H is syntactically correct and in the execution path. If the filter exists but doesn't fire, the relationships may be set in a different code path. Add a FINAL cleanup pass at the very end of `analyze()`, right before writing JSON, that strips all "colleague" relationship entries from every character.

3. **Add speech patterns to profile generation** (High #3) — Ensure the profiler prompt explicitly requests speech patterns and the response parser captures them. This is a moderate lift but impacts Profiles significantly.

4. **Fix role inflation** (High #5) — symbolic entities (is_symbolic=True) and characters with <50 mentions should NOT be promoted to "protagonist". Add guards to Fix G.

Items 1-3 together should bring Character Extraction to ~7 and Profiles to ~6-7. F6 clutter (High #6) needs to be addressed to push Characters above 8.

## Next Action
Run PROMPT_fix.md to address narrator regression (Critical #1) and colleague filter failure (Critical #2) as top priorities.
