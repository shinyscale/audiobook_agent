# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 15
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores (Attempt 15)
- Structure Detection: 9/10 ✓
- Character Extraction: ? (awaiting evaluation)
- Character Profiles: ? (awaiting evaluation)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: ?/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** AWAITING EVALUATION

## Attempt 15 Pipeline Output (Run Notes)

### Characters Found (7 after merge)
```
Prince Prospero (aka Prospero, the prince)  [protagonist]
the Red Death (aka the masked figure)  [antagonist]  is_symbolic=True  ← MERGED ✓
the narrator  [supporting]  ← NEW FALSE POSITIVE
the thousand friends  [supporting]  is_symbolic=True
the courtiers  [supporting]
the musicians  [minor]
the waltzers  [minor]
MISSING: the giant ebony clock  ← REGRESSION vs attempt 14
```

### Fix Verification
- **Fix 1 (identity reveal merge)**: ✓ WORKED — "the masked figure" merged INTO "the Red Death" (correct direction)
- **Fix 2 (profiling injection)**: ✓ WORKED — Red Death now has a profile (was missing in attempt 14)

### Profiling (2 profiles generated)
1. **Prince Prospero** — "bold and robust man", personality: cruel/calculating/hedonistic, voice: authoritative→hysterical rage, 3 relationships ✓
2. **the Red Death** — "tall gaunt figure dressed in habiliments of grave, mask resembling stiffened corpse", personality: unstoppable malevolent force, voice: silent presence, 2 relationships ✓  ← MAJOR IMPROVEMENT vs attempt 14

### Model/Config Notes
- Same as attempt 14 — qwen3.5:122b-a10b with think=False for all stages

## Issues (Priority Order for Attempt 16 if needed)

### CRITICAL (if attempt 15 fails)
1. **Giant Ebony Clock missing** [Completeness]
   - key_events DID mention "a giant ebony clock" in attempt 15, but LLM Pass 1 didn't extract it (non-determinism)
   - In attempt 14, Clock WAS extracted; in attempt 15 it was NOT — same key_events injection
   - Fix approach: More reliable Clock detection — e.g., parse key_events for named entities and add them as "candidate characters" to summary active_characters (forcing them into Pass 1's view)

### HIGH
2. **"the narrator" false positive** [Completeness/Precision]
   - "the narrator" was extracted by LLM Pass 1 in attempt 15, not in attempt 14 (non-determinism)
   - Masque of Red Death is 3rd person — no named narrator
   - Fix: Filter narrator characters from main_cast in twostage_experiment.py post-extraction

## Attempt 14 vs Attempt 15 Comparison

| Metric | Attempt 14 | Attempt 15 | Change |
|--------|-----------|-----------|--------|
| Total characters | 8 | 7 | -1 (masked figure merged) |
| Ebony Clock present | Yes ✓ | No ✗ | REGRESSION |
| Clock alias "the clock" | Yes ✓ | N/A | REGRESSION |
| Red Death standalone | Yes | Yes | Same |
| "masked figure" separate | Yes ✗ | No ✓ (now alias) | IMPROVED |
| Profiles count | 2 | 2 | Same |
| Profile 1 character | Prospero ✓ | Prospero ✓ | Same |
| Profile 2 character | masked figure ✗ | Red Death ✓ | IMPROVED |
| Red Death profile | Missing | Present ✓ | IMPROVED |
| Narrator FP | No | Yes ✗ | REGRESSION |

## Attempt 14 Pipeline Output (Run Notes)

### Characters Found (8 total)
```
Prince Prospero (aka the Prince, Prospero)  [protagonist]
the Red Death (aka the figure resembling the Red Death)  [antagonist]  is_symbolic=True
the masked figure  [antagonist]  is_symbolic=True
the courtiers  [supporting]
the thousand friends  [supporting]  is_symbolic=True
the musicians  [minor]
the waltzers  [minor]
the giant ebony clock (aka the clock)  [supporting]  is_symbolic=True
```

### Fix Verification
- **Fix 1 (short-form alias)**: ✓ WORKED — "the giant ebony clock" has alias "the clock"
- **Fix 2 (collective noun block)**: ✓ WORKED — no "the crowd" alias anywhere in output
- **AmbiguousName bug fix**: ✓ WORKED — profiling no longer crashes

### Profiling (2 profiles generated)
1. **Prince Prospero** — appearance: "bold and robust man", personality: selfish/arrogant/cruel, 3 relationships ✓
2. **the masked figure** — appearance: "tall, gaunt figure... grave clothes... mask resembling stiffened corpse" ✓

### Model/Config Notes
- Quality model: qwen3.5:122b-a10b with think=False (think=True + format=json produces empty content)
- Summarization: think=False — works fine (51s)
- Character extraction: think=False — two-pass works now that key_events are in summary_strings
- key_events include "giant ebony clock" references → Clock extracted in Pass 1 ✓
- Profiling: think=False — 2 profiles from profiling pipeline's own character identification (independent of Stage 4)

## Issues (Priority Order — Attempt 15 resolved, carry-forward issues)

### [RESOLVED in attempt 15]
- ~~"the masked figure" is a separate character from "the Red Death"~~ — FIXED: post-extraction merge
- ~~No profile for the Red Death~~ — FIXED: profiling injection

### CRITICAL (if attempt 15 fails evaluation)
1. **Giant Ebony Clock missing** [Completeness]
   - key_events DID mention "a giant ebony clock" but LLM Pass 1 didn't extract it in attempt 15
   - Non-deterministic: was extracted in attempt 14 (same key_events approach)
   - Fix: Parse key_events for noun-phrase "objects" and add as candidate chars to active_characters

2. **"the narrator" false positive** [Precision]
   - "the narrator" extracted in attempt 15 but not attempt 14 — non-deterministic
   - Post-extraction filter: remove characters named "narrator" or "the narrator" from main_cast

### MEDIUM
3. **Group character noise** [Completeness/Precision]
   - "the courtiers", "the thousand friends", "the musicians", "the waltzers" are valid text entities but shouldn't be main cast.
   - The existing Rule 0.6 blocks these as ALIASES, but they're canonical names here.
   - These are extracted by Pass 1 because key_events mentions them explicitly.
   - Impact: Minor score penalty for false positives, but evaluator likely lenient on textual group characters.

5. **Prospero's description incomplete** [Profiles]
   - Missing "happy and dauntless and sagacious" from text. Current has "bold and robust" only.
   - Impact: ~0.25 points.

## Previous Attempt 13 vs Attempt 14 Comparison

| Metric | Attempt 13 | Attempt 14 | Change |
|--------|-----------|-----------|--------|
| Total characters | 2 | 8 | More (FPs added) |
| Ebony Clock present | No | Yes ✓ | IMPROVED |
| Clock alias "the clock" | N/A | Yes ✓ | IMPROVED |
| Red Death standalone | Yes | Yes | Same |
| "the crowd" false alias | Yes | No | IMPROVED |
| "the masked figure" separate | No | Yes | REGRESSION |
| Profiles count | 2 | 2 | Same |
| Profile quality (Prospero) | Thin | Good | IMPROVED |
| Profile quality (Red Death) | Excellent | Missing (masked fig used) | REGRESSION |

## Fix History

### Attempt 15 (Score: awaiting evaluation)
1. **Post-extraction identity reveal merge** in twostage_experiment.py:
   - Result: ✓ WORKED — "the masked figure" merged INTO "the Red Death" (correct direction)
2. **Profiling injection (inject_characters_for_profiling)** in twostage_experiment.py:
   - Result: ✓ WORKED — Red Death now profiled with excellent quality
- Side effect: ✗ Ebony Clock not extracted this run (LLM non-determinism)
- Side effect: ✗ "the narrator" extracted as false positive (LLM non-determinism)

### Attempt 14 (Score: 7.95/10 — FAIL)
1. **Short-form alias for is_symbolic** in main_cast.py:
   - Result: ✓ WORKED — Clock extracted with alias "the clock"
2. **Collective noun block (Rule 0.6b)** in main_cast.py:
   - Result: ✓ WORKED — no "the crowd" false alias
3. **AmbiguousName bug fix** in summary_evidence.py:
   - Result: ✓ WORKED — profiling no longer crashes
4. **think=False for qwen3.5 models** in twostage_experiment.py:
   - Result: ✓ WORKED — summarization and extraction both complete
5. **key_events in summary_strings** in twostage_experiment.py:
   - Result: ✓ WORKED — Pass 1 sees "giant ebony clock" in key_events → extracts it
- Score delta: 7.98→7.95 (slight regression despite Clock improvement — masked figure identity split hurt Identity Resolution 4/10)

### Attempt 13 (Score: 7.98/10 — improvement from 7.0)
1. **Artifact core noun `is_symbolic` detection** in main_cast.py:
   - Result: ✓ PARTIALLY WORKED — Red Death now standalone (unmerged from Clock)
   - Side effect: ✗ Ebony Clock disappeared (filtering removed it after alias cleanup)
   - New issue: Red Death had wrong alias "the crowd"

### Attempt 12 (Score: 7.0/10 — marginal improvement from 6.95)
1. **REVERT min_grounding_mentions to 1** in characters.py: ✗ DID NOT FIX
2. **POV guard for narrator assignment** in narrator.py: ✓ WORKED

### Attempt 11 (Score: 6.95/10 — REGRESSION from 7.68)
1. F6 plural group noun filter in analyzer.py: ✓ WORKED
2. min_grounding_mentions = 2 in characters.py: ✗ OVER-FILTERED
3. Narrator min-mention guard in narrator.py: ✓ Works for 1-mention case
4. "stra" suffix in main_cast.py and characters.py: ✓ WORKED

### Attempt 10 (Score: 7.68/10)
1. REVERTED symbolic reveal merge: ✓ Red Death restored
2. KEPT plural suffix filter: ✓

### Attempt 9 (Score: 7.35/10 — REGRESSION)
1. Plural group noun filter: ✓ WORKED
2. Symbolic descriptor reveal merge: ✗ REGRESSION — REVERTED

### Attempt 8 (Score: 8.35/10 — BEST)
### Attempt 7 (Score: 8.35/10)
### Attempt 6 (Score: 8.35/10 — tied BEST)

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13)
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← BEST
- Attempt 7: 8.35/10 (+0.00)
- Attempt 8: 8.35/10 (+0.00)
- Attempt 9: 7.35/10 (-1.00) ← REGRESSION
- Attempt 10: 7.68/10 (+0.33)
- Attempt 11: 6.95/10 (-0.73) ← REGRESSION
- Attempt 12: 7.0/10 (+0.05)
- Attempt 13: 7.98/10 (+0.98) ← Red Death unmerged, but Clock missing
- Attempt 14: 7.95/10 (-0.03) ← Clock present, but masked figure identity split hurt Identity Resolution
- Attempt 15: ?/10 (awaiting evaluation — masked figure merged into Red Death, Red Death profiled)

## Configuration Audit
- Models: qwen3.5:122b-a10b with think=False for characters/summaries/profiling, qwen3.5:35b-a3b with think=False for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **qwen3.5 models require think=False to avoid empty content responses** — with think=None (default), model generates thinking-only responses; with think=True + format=json, same issue. think=False is required.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 15 | Post-extraction identity reveal merge (masked figure → Red Death) | twostage_experiment.py | ✓ WORKED |
| 15 | Inject Stage 4 characters into summary active_characters for profiling | twostage_experiment.py | ✓ WORKED — Red Death profiled |
| 14 | Short-form alias for is_symbolic objects | main_cast.py | ✓ Clock extracted with "the clock" |
| 14 | Collective noun block (Rule 0.6b) | main_cast.py | ✓ No "the crowd" false alias |
| 14 | AmbiguousName not iterable bug | summary_evidence.py | ✓ Profiling no longer crashes |
| 14 | think=False for qwen3.5 + key_events in summary_strings | twostage_experiment.py | ✓ Full pipeline runs |
| 13 | Artifact core noun `is_symbolic` detection | main_cast.py | ✓ Partially (Red Death unmerged) / ✗ Clock missing |
| 12 | Revert min_grounding_mentions from 2 to 1 | characters.py | ✗ DID NOT FIX |
| 12 | POV guard: narrator only for 1st-person/epistolary | narrator.py | ✓ WORKED |
| 11 | F6 plural group noun filter | analyzer.py | ✓ Worked |
| 11 | min_grounding_mentions = 2 | characters.py | ✗ OVER-FILTERED |
| 11 | Narrator min-mention guard | narrator.py | ✓ Works for 1-mention |
| 11 | "stra" suffix for collective nouns | main_cast.py, characters.py | ✓ Worked |
| 10 | Revert symbolic merge | main_cast.py | ✓ Red Death restored |
| 9 | Group aliases: plural suffix filter | characters.py | ✓ WORKED |
| 9 | Symbolic descriptor reveal merge | main_cast.py | ✗ REGRESSION — REVERTED |
| 8 | Rule 2 prompt clarification | main_cast.py | No change |
| 7 | Rule 0.7 in verify_aliases | main_cast.py | Partial |
| 7 | Rule 3 exception | main_cast.py | No change |
| 6 | Revert characters.py regression | characters.py | Fixed ✓ |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ |
| 5 | Wrong group aliases on Red Death | characters.py | REGRESSION |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

## Next Action
Evaluate attempt 15. Expected improvements vs attempt 14:
1. **Identity Resolution**: 4/10 → 9/10 (masked figure correctly merged as alias of Red Death)
2. **Character Profiles**: 6/10 → 8/10 (Red Death now profiled with excellent quality)
3. **Completeness**: 8/10 → 7-8/10 (Clock missing this run — non-deterministic LLM)
4. **Expected overall**: ~8.3-8.5/10 → borderline PASS

If attempt 15 FAILS (Clock absence drops character extraction to 7.5/10):
- Fix A: Filter narrator FP in twostage_experiment.py (quick win, +0.25)
- Fix B: More reliable Clock detection — inject important noun-phrase entities from key_events into candidate characters
