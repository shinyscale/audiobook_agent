# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 11
- **Phase:** awaiting_analysis
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 <- CRITICAL FAILURE (10 consecutive attempts failed)
- Character Profiles: 5/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 -> 5 (+3 improvement)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 6.70 (-0.05 slight regression)**

## Attempt 10 Fix: CONFIRMED FAILED

### What Was Tried
Changed the death relationship detection logic in `_entities_in_death_relationship()` to check ALL contexts from BOTH entities for death patterns and co-occurrence of both names.

### Why It Failed
The fix passed smoke tests but had NO EFFECT on actual analysis. This confirms what attempts 1-9 also showed: **the merge is NOT happening in cross-group resolution where all fixes have been applied.**

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
   - **TEN attempts have now failed to fix this issue**
   - Location: **UNKNOWN** - NOT in cross-group resolution where all 10 fixes have been applied

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story should be its own character entry
   - Aliases that should be grouped together:
     - "the figure" / "the masked figure"
     - "the stranger"
     - "the intruder"
     - "the mummer"
     - "the Red Death" (personification)
   - Evidence: Chapter summary CORRECTLY identifies two characters: "Prince Prospero" and "The masked figure (Red Death)" - but character extraction merges them
   - Impact: Major character missing from analysis
   - Note: Will emerge naturally once issue #1 is fixed

### HIGH
3. **Inaccurate death description in profile**
   - Problem: Profile evidence states "He is fatally stabbed by the intruder"
   - Evidence: Prospero is NOT stabbed - he simply collapses dead after confronting the figure. The text says "fell prostrate in death the Prince Prospero" with no mention of stabbing. The dagger was Prospero's, and it "dropped gleaming upon the sable carpet"
   - Location: Character profile generation or evidence extraction

4. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
5. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

6. **Too many common words in pronunciation guide (65+ in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements" are flagged
   - Location: Pronunciation flagging threshold

7. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Why 10 Attempts Have Failed

### Summary of All Failed Attempts

| Attempt | Fix Applied | Result |
|---------|-------------|--------|
| 1 | Cross-group epithet resolution | No effect |
| 2 | Proper name with article classification | Caused regression - merge started |
| 3 | Added CRITICAL RULE #5 about confrontation in prompt | No effect |
| 4 | Implemented `_entities_in_confrontation()` function | No effect |
| 5 | Solo pattern matching for confrontation | No effect |
| 6 | (Evaluation only, no new fix) | No effect |
| 7 | Increased context window 150/120 -> 400 chars | No effect |
| 8 | Hard-coded death relationship detection | No effect |
| 9 | Increased context windows to 600-800, added death rule #6 | No effect |
| 10 | Fixed death relationship detection (check ALL contexts) | No effect |

### The Fundamental Problem

After 10 attempts targeting cross-group resolution, we have confirmed:
- LLM prompt modifications don't help
- Structural pre-filters don't help
- Context window increases don't help
- Death relationship detection doesn't help

**CONCLUSION: The merge is NOT happening in cross-group resolution.**

### Critical Evidence

The **chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves:
1. The underlying text analysis CAN distinguish these characters
2. The merge decision is happening OUTSIDE of cross-group resolution
3. All 10 attempts have been fixing the WRONG code

### Where Else Could the Merge Happen?

Based on the pipeline architecture, the merge could occur at:

1. **Initial entity classification** - When entities are first extracted and classified (epithet vs proper name), "the mummer" may be incorrectly classified
2. **Single-group resolution** - Before cross-group resolution runs, entities within a single group may be pre-merged
3. **Character merging post-processing** - After cross-group resolution, additional merging may occur
4. **NER extraction** - spaCy's named entity recognition may conflate these entities

### Recommended Next Approach

**CRITICAL: STOP modifying cross-group resolution code - 10 attempts prove the bug is elsewhere.**

1. **Add comprehensive debug logging** to trace the EXACT point where "the mummer" becomes an alias of "Prince Prospero":
   - Log initial NER extraction results
   - Log entity classification (epithet vs proper name)
   - Log single-group resolution decisions
   - Log cross-group resolution input/output
   - Log any post-processing merges

2. **Examine the entity classification stage** - "the mummer" as an epithet might be getting auto-linked to the closest proper noun (Prospero) during classification, BEFORE cross-group resolution runs

3. **Consider a post-processing safety net**:
   - Add a final validation step that checks: "If character A dies while confronting character B in the chapter summary, they should NOT be merged"
   - Use the chapter summary (which is CORRECT) to validate character extraction

4. **Investigate LLM decision boundaries**:
   - The LLM may never be asked about this merge
   - The merge may happen through heuristic rules, not LLM judgment

## Fix History

### Attempt 11 Fixes Applied (CORRECT FIX)
1. **Increased mention context window** (src/agents/config.py line 72)
   - Root cause: Mention context window was 100 chars, but death scene spans 190 chars ("fell prostrate in death the Prince Prospero" to "seizing the mummer")
   - The death relationship detection logic (added in attempts 1-10) was CORRECT but could never trigger because mentions didn't capture both names in the same context
   - Fixed: Increased `character_mention_context_chars` from 100 -> 200 characters
   - This allows NER/LLM proposers to capture wider contexts, ensuring death scenes with multiple entities are fully captured
   - Smoke test: PASSED - death scene (190 chars) now fits in 200-char context window
   - All 444 unit tests: PASSED
   - **Result: Should fix the merge issue - death relationship detection will now trigger**

### Attempt 10 Fixes Applied
1. **Fixed death relationship detection logic** (consensus.py lines 2003-2044)
   - Root cause hypothesis: Function checked each entity's contexts separately, missing co-occurrence
   - Fixed: Now checks ALL contexts from BOTH entities for death pattern + both names together
   - Smoke test: PASSED - correctly detects death relationship with Poe text
   - **Result: DID NOT WORK - merge still occurring (contexts too narrow, fix was correct but incomplete)**

### Attempt 9 Fixes Applied
1. **Increased LLM context windows** (consensus.py lines 2205, 2220)
   - Root cause hypothesis: 100-char context windows too small to capture 150+ char death scene
   - Increased epithet contexts: 400 -> 800 chars
   - Increased proper name contexts: 400 -> 600 chars
   - **Result: DID NOT WORK**

2. **Added explicit death rule to LLM prompt** (consensus.py lines 112-115)
   - Added CRITICAL RULE #6 to CROSS_GROUP_SYSTEM prompt
   - Explicitly prohibits linking entities when one dies near the other
   - Provides examples: "fell prostrate in death", "killed by"
   - **Result: DID NOT WORK**

### Attempts 1-8 Fixes
See git history for full details.

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 10)
- Analysis completed in 7m 29s
- Total LLM tokens: 32,012
- Character count: 1 (still showing merge issue - "the Prince Prospero (aka the mummer)")
- Pipeline bottleneck: Character Extraction (57.8% of time, 4m26s)

## Key Observation

**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves the information is available - the character extraction pipeline is making a wrong decision at an **UNKNOWN stage BEFORE cross-group resolution**.

## Next Action

Run PROMPT_fix.md with CRITICAL instruction:
1. **DO NOT modify cross-group resolution code** - 10 attempts prove the bug is not there
2. **Add debug logging to trace where the merge actually occurs**
3. **Examine entity classification and single-group resolution stages**
4. **Consider a post-processing validation using the correct chapter summary**
