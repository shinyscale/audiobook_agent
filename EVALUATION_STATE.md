# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 8
- **Phase:** awaiting_fix
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

## Attempt 8 Fix Assessment

### Fix: Hard-coded death relationship detection
**Status: DID NOT WORK**

The fix from attempt 8 added `_entities_in_death_relationship()` function to detect when one entity dies at the hands of another. This was meant to block the merge of "the mummer" with "Prince Prospero" based on the text:
- "fell prostrate in death the Prince Prospero" (Prospero dies)
- "seizing the mummer" (after Prospero confronts the mummer)

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Evidence from analysis.json:**
- Character: "the Prince Prospero"
- Aliases: ["the mummer"]
- Only 1 character detected (should be 2)

**Why it failed:** Possible reasons:
1. The death relationship function may not be getting called
2. The merge may be happening at an earlier pipeline stage
3. The function's pattern matching may not be capturing the actual text patterns
4. The merge decision may be bypassing the death relationship check

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

### Attempt 8 Fixes Applied
1. **Death relationship detection** (consensus.py)
   - Root cause: `src/pipeline/character_extraction/consensus.py:_llm_cross_group_resolution()`
   - Added `_entities_in_death_relationship()` function
   - Detects patterns like "fell prostrate in death" + entity name co-occurrence
   - **Result: DID NOT WORK** - merge still happening

### Attempt 1-7 Fixes
See previous evaluation state for full history.

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

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
