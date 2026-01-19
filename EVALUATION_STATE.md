# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 13
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.85/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 -> 6 (+4 improvement)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 6.85 (+0.10 slight improvement)**

## Attempt 13 Analysis: ENHANCED DEATH DETECTION FAILED

### What Was Tried
Enhanced `_entities_in_death_relationship()` in `src/pipeline/character_extraction/consensus.py` to use multiple name variants and improved matching patterns.

### Result
**FAILED** - The merge STILL occurs with the production model (qwen3-next:80b).

### Key Finding from Debug Logs
`_entities_in_death_relationship()` is **NOT being called at all**.

This proves the merge is happening at a DIFFERENT level than cross-group resolution - likely at:
1. Pairwise alias resolution (`_llm_alias_resolution()` or `_heuristic_alias_resolution()`)
2. Or at the proposer level where "the mummer" is already associated with Prospero

### The Smoking Gun (Unchanged from Previous Attempts)
**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves the underlying LLM CAN distinguish these characters - the merge is happening in the character extraction consensus logic.

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with Prince Prospero**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification - THE MAIN ANTAGONIST
   - Evidence from text:
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
     - "fell prostrate in death the Prince Prospero" (Prospero DIES after confronting the mummer)
     - The mummer is "dressed as the Red Death itself, draped in grave-cloths"
     - When unmasked, the figure is "untenanted by any tangible form" (not a person at all)
   - Impact: The main antagonist is merged with the protagonist (-2 point character score minimum)
   - **THIRTEEN attempts have now failed to fix this issue**
   - **Status:** Cross-group resolution fixes don't work because the merge happens BEFORE that stage

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story should be its own character entry
   - Aliases that should be grouped together:
     - "the figure" / "the masked figure"
     - "the stranger"
     - "the intruder"
     - "the mummer"
     - "the Red Death" (personification)
   - Evidence: Chapter summary CORRECTLY identifies two characters but character extraction merges them
   - Impact: Major character missing from analysis

### HIGH
3. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
4. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

5. **Too many common words in pronunciation guide (65 in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements" are flagged
   - Location: Pronunciation flagging threshold

6. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Summary After 13 Attempts

### The Core Problem
The merge happens BEFORE cross-group resolution. Debug logging proves `_entities_in_death_relationship()` is never called, meaning "the mummer" and "Prince Prospero" are already in the same character group by the time cross-group resolution runs.

### Where the Merge Is Happening (Investigation Needed)
Possible locations:
1. **`_is_descriptive_handle()` classification** - "the mummer" may be classified as a proper name rather than an epithet
2. **`_llm_alias_resolution()` or `_heuristic_alias_resolution()`** - The LLM may be deciding "the mummer" = "Prince Prospero" at the pairwise merge level
3. **Initial extraction** - Proposers may already be tagging "the mummer" with Prospero

### What Has Been Tried (All Failed)
| Attempt | Fix Applied | Result |
|---------|-------------|--------|
| 1 | Cross-group epithet resolution | No effect |
| 2 | Proper name with article classification | Caused regression |
| 3 | CRITICAL RULE #5 about confrontation in prompt | No effect |
| 4 | `_entities_in_confrontation()` function | No effect |
| 5 | Solo pattern matching for confrontation | No effect |
| 6 | (Evaluation only) | No effect |
| 7 | Context window 150/120 -> 400 chars | No effect |
| 8 | Hard-coded death relationship detection | No effect |
| 9 | Context windows 600-800, death rule #6 | No effect |
| 10 | Death detection check ALL contexts | No effect |
| 11 | mention_context_chars 100 -> 200 | +0.15 score, merge still occurs |
| 12 | mention_context_chars 200 -> 250 | Works on small model, FAILS on production |
| 13 | Enhanced death relationship detection | Never called - merge happens earlier |

## Fix History

### Attempts 1-12
See previous EVALUATION_STATE.md entries and git history.

### Attempt 13
- **Change:** Enhanced `_entities_in_death_relationship()` with multiple name variants
- **Result:** Function is NEVER CALLED - merge happens before cross-group resolution
- **Conclusion:** Must investigate WHERE the merge actually happens (pairwise level, not cross-group)

## Recommended Next Approach (Attempt 14)

### Priority 1: Add Debug Logging to Find Merge Location
Add logging to these functions to trace where "the mummer" gets merged with "Prince Prospero":

1. **`_is_descriptive_handle()`** - Is "the mummer" classified as epithet or proper name?
2. **`_heuristic_alias_resolution()`** - Does heuristic logic merge them?
3. **`_llm_alias_resolution()`** - Does the LLM merge them at pairwise level?
4. **Initial extraction results** - Are they separate groups initially?

### Priority 2: Post-Processing Character Split
Since the summary pipeline correctly identifies both characters, add a post-processing step:
1. Extract character names from chapter summaries (already available in `characters_present`)
2. Compare against final character list
3. If summary identifies more characters than extraction, investigate potential incorrect merges
4. Use death scene detection to SPLIT characters that were incorrectly merged

### Priority 3: Classification Fix
If "the mummer" is being classified as a proper name:
- Make `_is_descriptive_handle()` more conservative about "the X" patterns
- "the mummer" should be classified as an epithet, not a proper name
- Epithets go through cross-group resolution (where death detection could work)

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Next Action
Run PROMPT_fix.md to:
1. First ADD DEBUG LOGGING to trace where the merge happens
2. Then apply targeted fix based on findings
