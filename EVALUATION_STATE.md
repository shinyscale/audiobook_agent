# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (unchanged from attempts 3, 4)
- Character Profiles: 5/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 3 (**-2 REGRESSION** from attempt 1, persisting since attempt 3)
- Profiles: 2 → 5 (+3 improvement)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 improvement)
- Presentation: 9 → 8 (-1 regression)
- **Overall: 6.75 → 6.70 (-0.05 slight regression, unchanged from attempt 4)**

## Attempt 4 Fix Assessment

### Fix: Structural confrontation detection pre-filter
**Status: DID NOT WORK**

The fix implemented `_entities_in_confrontation()` to:
1. Detect co-occurrences where epithet and proper name appear together
2. Look for confrontation verbs: pursued, seized, confronted, attacked, approached, retreating, etc.
3. Block merge if ≥50% of co-occurrences show confrontation patterns

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Why it failed:** The confrontation detection either:
1. Did not find sufficient co-occurrences (sampling issue)
2. Did not recognize the confrontation patterns in context
3. The threshold (50%) may be too high
4. The function may not be getting called or is being bypassed

**Evidence from analysis.json:**
- Character: "the Prince Prospero"
- Aliases: ["the mummer"]
- This proves the merge IS still happening despite the fix

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with "Prince Prospero"**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification
   - Evidence from text:
     - "But the mummer had gone so far as to assume the type of the Red Death. His vesture was dabbled in blood"
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
     - "the latter, having attained the extremity of the velvet apartment, turned suddenly and confronted his pursuer"
     - The mummer is "tall and gaunt" and "shrouded from head to foot in the habiliments of the grave"
     - Prince Prospero PURSUES and CONFRONTS the mummer - they are clearly separate entities that INTERACT
   - Impact: The main antagonist is merged with the protagonist (-2 point character score minimum)
   - **Five attempts have failed to fix this issue**
   - Location: `src/pipeline/character_extraction/consensus.py`

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story should be its own character entry
   - Aliases that should be grouped:
     - "the figure" / "the masked figure"
     - "the stranger"
     - "the intruder"
     - "the mummer"
     - "the Red Death" (personification)
   - Evidence: Multiple text references describe this entity as separate from all other characters
   - Impact: Major character missing from analysis
   - Note: Will emerge naturally once issue #1 is fixed

### HIGH
3. **Mention count too low for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline

4. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
5. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

6. **Too many common words in pronunciation guide (65+ in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence" are flagged
   - Location: Pronunciation flagging threshold

7. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Fix History

### Attempt 1 Fixes Applied
1. Cross-group epithet resolution (consensus.py) - Did not produce expected results
2. Article filtering for pronunciation (cmu_proposer.py) - Partially worked

### Attempt 2 Fixes Applied
1. Proper name with article classification (consensus.py:_is_descriptive_handle())
   - Partially worked: Profile now generated, mention count improved 3→6
   - Caused regression: "the mummer" incorrectly merged with Prince Prospero

### Attempt 3 Fixes Applied
1. Enhanced cross-group resolution with conflict detection (consensus.py)
   - Added CRITICAL RULE #5 about conflict/opposition/confrontation
   - Increased epithet context from 3x100 to 4x150 chars
   - Added context snippets for proper names (3x120 chars)
   - **Result: DID NOT WORK** - merge still happening

### Attempt 4 Fixes Applied
1. Structural confrontation detection pre-filter (consensus.py)
   - Implemented `_entities_in_confrontation()` function (lines 1954-2047)
   - Pre-filter check added in `_llm_cross_group_resolution()` (lines 2119-2125)
   - **Result: DID NOT WORK** - merge still happening

## Root Cause Analysis

**The problem persists because the merge is likely NOT happening in `_llm_cross_group_resolution()`.**

Possible alternative merge locations:
1. **`_llm_pairwise_merge()`** - Direct pairwise merge decisions
2. **`_merge_groups()`** - Group merging logic
3. **NER initial extraction** - Entities may be grouped too early in the pipeline
4. **Proposer consensus** - Before the consensus phase

**Debug recommendation for attempt 6:**
1. Add logging to trace WHERE exactly "the mummer" gets associated with "Prince Prospero"
2. Check if the merge happens BEFORE `_llm_cross_group_resolution()` is even called
3. The confrontation detection code may be correct but the merge happens elsewhere

## Key Insights

**Pattern of failure:** All four fix attempts have targeted `_llm_cross_group_resolution()` and its supporting functions. If the merge is still happening, either:
1. The code path is never reached for this specific case
2. The merge happens in a completely different function
3. There's an early-stage grouping that pre-merges these entities

**New diagnostic approach needed:**
Instead of adding more logic to the same function, we need to:
1. Add comprehensive logging to trace the EXACT point where "the mummer" becomes an alias of "Prince Prospero"
2. This may be in NER extraction, initial grouping, or a different merge pathway

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 5)
- Analysis completed successfully in 7m 20s
- 1 character detected: "the Prince Prospero" (alias: "the mummer") ← WRONG
- 1 character profile generated
- 73 pronunciation flags
- Character extraction time: 4m 55s (65.3% of total time)
- Total tokens: 33,923
- 19 LLM calls

## Next Action
Run PROMPT_fix.md with a NEW APPROACH:
1. First ADD DIAGNOSTIC LOGGING to trace exactly where "the mummer" becomes associated with "Prince Prospero"
2. Run analysis again with logging enabled
3. Use the logs to identify the ACTUAL location of the problematic merge
4. Then apply a targeted fix at the correct location

The previous four attempts have all targeted the wrong code path. We need to find where the merge actually happens before we can fix it.
