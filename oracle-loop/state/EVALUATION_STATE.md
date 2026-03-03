# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 15
- **Phase:** fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 4/10
  - Alias Grouping: 6/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — Character Extraction 7/10, Character Profiles 6/10

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

## Issues (Priority Order for Attempt 15)

### CRITICAL
1. **"the masked figure" is a separate character from "the Red Death"** [Identity Resolution]
   - Problem: LLM Pass 1 extracted both as separate entities. Rule 0.5 prevents "figure" as alias for "death".
   - In the story, the masked figure IS the Red Death personified (revealed at the end).
   - In attempt 13 (score 7.98), only 2 chars extracted (Red Death standalone, no masked figure separate).
   - Fix approach: The within-main merge step (characters.py Step 3.5) or a post-extraction merge should detect that "the masked figure" and "the Red Death" are the same story entity.
   - Note: Previous attempt 9 tried "symbolic reveal merge" → REGRESSION (Red Death merged INTO masked figure, losing Red Death). The merge direction matters: masked figure must be MERGED INTO Red Death, not vice versa.
   - Impact: Identity Resolution +1-2 points

2. **No profile for the Red Death or the Ebony Clock** [Character Profiles]
   - Problem: Profiling pipeline runs independent character identification (from summaries). The summary's active_characters lists "the masked figure" not "the Red Death" or "the Ebony Clock", so only Prospero + masked figure are profiled.
   - Fix: Profiling pipeline should receive the Stage 4 character list (8 chars) as input, not re-identify independently. OR the summary_map should include Clock and Red Death in active_characters.
   - Impact: +1 on Profiles (adds Clock profile), +0.5-1 on character quality

### HIGH
3. **Red Death lacks valid text-based aliases** [Alias Grouping]
   - Problem: "the figure", "the intruder", "the stranger", "the mummer", "the masked figure" are all blocked by Rule 0.5 (core noun 'figure'/'intruder'/'stranger' ≠ 'death').
   - Current alias is "the figure resembling the Red Death" (LLM paraphrase, not direct text quote).
   - Impact: +1 on Alias Grouping if valid aliases can be preserved.

### MEDIUM
4. **Group character noise** [Completeness/Precision]
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
Fix attempt 15. Two root causes to address:
1. **[CRITICAL] Merge "the masked figure" INTO "the Red Death"** (Identity Resolution 4/10 → 8/10)
   - The two entities are the same: masked figure IS the Red Death personified.
   - Merge direction: masked figure → absorbed as alias of Red Death.
   - DO NOT repeat attempt 9's mistake (merged Red Death INTO masked figure, losing Red Death).
   - Approach: Post-extraction programmatic merge in characters.py or twostage_experiment.py.
   - Key signal: both are is_symbolic=True, both are antagonist role, "death" is core noun of Red Death.
2. **[CRITICAL] Fix profiling to use Stage 4 character list** (Character Profiles 6/10 → 8/10)
   - Profiling pipeline re-identifies chars from summaries, missing Red Death and Clock.
   - Fix: Pass the Stage 4 character list (from extraction) into the profiling pipeline as "required_characters".
   - This gives profiles for: Prospero, Red Death, Ebony Clock (all 3 main entities).
   - Expected impact: Character Profiles 6/10 → 8-9/10
