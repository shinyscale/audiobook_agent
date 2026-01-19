# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 9
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (9 consecutive attempts failed)
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.85/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 → 6 (+4 improvement)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 improvement)
- Presentation: 9 → 8 (-1 regression)
- **Overall: 6.75 → 6.85 (+0.10 slight improvement)**

## Attempt 9 Fix Result: FAILED

### What Was Tried
1. **Increased LLM context windows:**
   - Epithet contexts: 400 → 800 chars
   - Proper name contexts: 400 → 600 chars

2. **Added explicit death rule to LLM prompt:**
   - CRITICAL RULE #6 in CROSS_GROUP_SYSTEM prompt
   - Examples: "fell prostrate in death", "killed by"

### Why It Failed
The merge STILL occurs despite all fixes. This confirms the merge is happening at a different pipeline stage than where fixes have been applied.

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
   - **NINE attempts have now failed to fix this issue**
   - Location: Unknown - not in cross-group resolution where all fixes have been applied

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
3. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

4. **Mention count discrepancy for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline

5. **Inaccurate death description in profile**
   - Problem: Profile states "He dies after being stabbed by the intruder"
   - Evidence: Prospero is NOT stabbed - he simply collapses dead after confronting the figure. The text says "fell prostrate in death the Prince Prospero" with no mention of stabbing
   - Location: Character profile generation

### MEDIUM
6. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

7. **Too many common words in pronunciation guide (65+ in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements" are flagged
   - Location: Pronunciation flagging threshold

8. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Why 9 Attempts Have Failed

### Summary of All Failed Attempts

| Attempt | Fix Applied | Result |
|---------|-------------|--------|
| 1 | Cross-group epithet resolution | No effect |
| 2 | Proper name with article classification | Caused regression - merge started |
| 3 | Added CRITICAL RULE #5 about confrontation in prompt | No effect |
| 4 | Implemented `_entities_in_confrontation()` function | No effect |
| 5 | Solo pattern matching for confrontation | No effect |
| 6 | (Evaluation only, no new fix) | No effect |
| 7 | Increased context window 150/120 → 400 chars | No effect |
| 8 | Hard-coded death relationship detection | No effect |
| 9 | Increased context windows to 600-800, added death rule #6 | No effect |

### The Fundamental Problem

After 9 attempts, we have tried:
- LLM prompt modifications (attempts 3, 5, 9)
- Structural pre-filters (attempts 4, 8)
- Context window increases (attempts 7, 9)
- Death relationship detection (attempt 8)

**None have worked.** The merge continues regardless of all fixes applied to the cross-group resolution stage.

### Critical Insight

The **chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves:
1. The underlying text analysis CAN distinguish these characters
2. The character extraction pipeline is making a WRONG DECISION somewhere
3. The decision point is NOT in cross-group resolution where all fixes have been applied

### Hypotheses for Next Attempt

1. **The merge may happen BEFORE cross-group resolution**: The epithet "the mummer" may be classified and merged at an earlier pipeline stage (e.g., initial entity grouping, NER, or single-group resolution)

2. **The cross-group resolution code may not be in the execution path**: Despite 9 attempts of modifications, the code may be conditionally skipped

3. **Need to trace the ACTUAL execution path**: Add comprehensive logging at EVERY decision point to identify exactly where the merge occurs

### Recommended Next Approach

**STOP modifying cross-group resolution code until we verify it's actually being called.**

1. **Add extensive debug logging** to trace the complete character extraction pipeline:
   - Log when initial entities are extracted
   - Log when entities are classified (epithet vs proper name)
   - Log when single-group resolution runs
   - Log when cross-group resolution runs
   - Log the EXACT point where "the mummer" gets linked to Prospero
   - Log the final character list before output

2. **Identify the EXACT line of code** where "the mummer" gets added to Prince Prospero's alias list

3. **Consider a fundamentally different approach**:
   - Post-processing step to DETECT incorrectly merged characters
   - Use chapter summary (which is correct) to validate character extraction
   - Add a "death relationship" post-filter that splits characters if one dies confronting the other

## Fix History

### Attempt 9 Fixes Applied
1. **Increased LLM context windows** (consensus.py lines 2205, 2220)
   - Root cause hypothesis: 100-char context windows too small to capture 150+ char death scene
   - Increased epithet contexts: 400 → 800 chars
   - Increased proper name contexts: 400 → 600 chars
   - **Result: DID NOT WORK**

2. **Added explicit death rule to LLM prompt** (consensus.py lines 112-115)
   - Added CRITICAL RULE #6 to CROSS_GROUP_SYSTEM prompt
   - Explicitly prohibits linking entities when one dies near the other
   - Provides examples: "fell prostrate in death", "killed by"
   - **Result: DID NOT WORK**

### Attempt 8 Fixes Applied
1. **Death relationship detection** (consensus.py)
   - Added `_entities_in_death_relationship()` function
   - **Result: DID NOT WORK** - context windows too small (hypothesis)

### Attempts 1-7 Fixes
See git history for full details.

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 9)
- Analysis completed in 7m 9s
- Total LLM tokens: 32,019
- Character count: 1 (still showing merge issue - "the Prince Prospero (aka the mummer)")
- Some LLM 500 errors occurred during identity/valence detection (EOF errors)
- Pipeline bottleneck: Character Extraction (67.4% of time, 4m55s)

## Key Observation

**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves the information is available - the character extraction pipeline is making a wrong decision at an unknown stage.

## Next Action

Run PROMPT_fix.md with focus on:
1. **MUST ADD debug logging** to trace exactly WHERE the merge decision is made
2. The fix should NOT modify existing cross-group resolution code until we know it's being executed
3. Consider implementing post-processing validation using chapter summary data
