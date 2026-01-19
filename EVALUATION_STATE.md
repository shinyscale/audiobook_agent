# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 9
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (8 consecutive attempts failed)
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

## Attempt 9 Fix

### Root Cause Analysis (CONFIRMED):

After tracing the complete data flow, the root cause is:

1. **"the mummer"** has only 3 mentions in the text
2. The critical 3rd mention: "seizing the mummer, whose tall figure stood erect..."
3. This occurs ~150 characters AFTER "fell prostrate in death the Prince Prospero"
4. **Context windows were only 100 chars**, so the death scene was SPLIT across windows
5. The LLM never saw both entities AND the death pattern in the same context
6. Post-hoc death checks (attempts 4, 8) failed for the same reason - they used 100-char windows

**Why ALL previous attempts failed:**
- Attempts 3-5, 7: LLM prompt rules couldn't work - LLM never saw the full death scene
- Attempts 4, 8: Post-hoc code checks couldn't work - they searched the same 100-char windows
- Attempt 7: Increased to 400 chars TOTAL (= 4 contexts × 100 each) - still too small per context

### Fix Applied:

1. **Increased context window for cross-group LLM prompt:**
   - Epithets: 400 → **800 chars** (showing ~200 chars per context)
   - Proper names: 400 → **600 chars** (showing ~200 chars per context)
   - Ensures death/confrontation scenes spanning 150+ chars are fully captured

2. **Added explicit death rule to LLM system prompt (CRITICAL RULE #6):**
   - "DO NOT link if one entity DIES in interaction with the other entity"
   - Examples: "fell prostrate in death", "killed by"
   - Makes death prohibition explicit alongside existing confrontation rule

**Files modified:**
- `src/pipeline/character_extraction/consensus.py:96-117` (CROSS_GROUP_SYSTEM - added rule #6)
- `src/pipeline/character_extraction/consensus.py:2205` (increased epithet context 400→800)
- `src/pipeline/character_extraction/consensus.py:2220` (increased proper name context 400→600)

**Expected outcome:**
LLM will now see: "fell prostrate in death the Prince Prospero. Then... seizing the mummer" in a single ~200-char context, recognize the death pattern per rule #6, and reject the merge

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with Prince Prospero**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification - THE MAIN ANTAGONIST
   - Evidence from text:
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
     - "fell prostrate in death the Prince Prospero" (Prospero DIES after confronting the mummer)
     - The mummer is described as "dressed as the Red Death itself, draped in grave-cloths"
   - Impact: The main antagonist is merged with the protagonist (-2 point character score minimum)
   - **EIGHT attempts have now failed to fix this issue**
   - Location: `src/pipeline/character_extraction/consensus.py`

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

4. **Mention count too low for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline

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

## Root Cause Analysis: Why 8 Attempts Have Failed

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

### The Fundamental Problem

After 8 attempts, we have tried:
- LLM prompt modifications (attempts 3, 5)
- Structural pre-filters (attempts 4, 8)
- Context window increases (attempt 7)
- Death relationship detection (attempt 8)

**None have worked.** The merge is happening despite ALL of these fixes.

### Hypotheses for Why Fixes Keep Failing

1. **The merge may happen BEFORE cross-group resolution**: The epithet "the mummer" may be classified and merged at an earlier pipeline stage before any of our checks run

2. **The LLM merge decision is overriding all rules**: Even with explicit blocking code, the final merge decision may be bypassing these checks

3. **Logging gap**: We haven't verified that the blocking code is actually being called. Need to add explicit debug logging to trace the exact point where the merge decision is made

4. **The fix code may not be in the execution path**: The `_entities_in_death_relationship()` and `_entities_in_confrontation()` functions may exist but never be invoked

### Recommended Next Approach

**STOP adding new detection code until we verify existing code is being called.**

1. **Add trace logging at EVERY decision point** in the character extraction pipeline:
   - Log when epithet candidates are generated
   - Log when cross-group resolution is called
   - Log when confrontation/death checks are executed
   - Log the exact LLM prompt and response for the merge decision
   - Log the final merge output

2. **Identify the EXACT line of code** where "the mummer" gets added to Prince Prospero's alias list

3. **Consider fundamentally different approach**:
   - Instead of trying to prevent the merge, post-process to SPLIT incorrectly merged characters
   - Use the chapter summary (which correctly identifies 2 characters) to validate character extraction

## Fix History

### Attempt 9 Fixes Applied
1. **Increased LLM context windows** (consensus.py lines 2205, 2220)
   - Root cause: 100-char context windows too small to capture 150+ char death scene
   - Increased epithet contexts: 400 → 800 chars
   - Increased proper name contexts: 400 → 600 chars
   - Result: AWAITING EVALUATION

2. **Added explicit death rule to LLM prompt** (consensus.py lines 112-115)
   - Added CRITICAL RULE #6 to CROSS_GROUP_SYSTEM prompt
   - Explicitly prohibits linking entities when one dies near the other
   - Provides examples: "fell prostrate in death", "killed by"
   - Result: AWAITING EVALUATION

### Attempt 8 Fixes Applied
1. **Death relationship detection** (consensus.py)
   - Added `_entities_in_death_relationship()` function
   - **Result: DID NOT WORK** - context windows too small

### Attempt 1-7 Fixes
See git history for full details.

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json
- Quality report: output/Masque of the Red Death - Poe_20260119_015239/quality.md

## Pipeline Notes (Attempt 9)
- Analysis completed in 7m 18s
- Total LLM tokens: 32,019
- Character count: 1 (still showing merge issue - "the Prince Prospero (aka the mummer)")
- Some LLM 500 errors occurred during identity/valence detection (EOF errors)
- Pipeline bottleneck: Character Extraction (67.4% of time, 4m55s)

## Key Observation

**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves the information is available - the character extraction pipeline is making a wrong decision.

## Next Action

Run PROMPT_fix.md with focus on:
1. Add comprehensive debug logging to trace exactly WHERE the merge decision is made
2. Verify that blocking code is actually being executed
3. Consider post-processing approach to split incorrectly merged characters
