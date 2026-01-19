# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 7
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE
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
- **Overall: 6.75 → 6.70 (-0.05 slight regression, unchanged from attempts 4, 5)**

## Attempt 6 Fix Assessment

### Fix: Enhanced confrontation detection with solo pattern matching
**Status: DID NOT WORK**

The fix from attempt 5 implemented solo confrontation pattern detection to:
1. Count confrontation patterns in each entity's contexts independently
2. Block merge if BOTH entities show >= 2 confrontation patterns
3. Work even when names don't co-occur in the same small context window

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Evidence from analysis.json:**
- Character: "the Prince Prospero"
- Aliases: ["the mummer"]
- Only 1 character detected (should be 2)

**Why it failed:** The confrontation detection code exists but is either:
1. Not being invoked at the right stage of the pipeline
2. Being bypassed by an earlier decision in the merge logic
3. Not extracting enough context to detect the confrontation patterns
4. The threshold may still be too high or the patterns too narrow

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with Prince Prospero**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification - THE MAIN ANTAGONIST
   - Evidence from text (line 30 of source):
     - "He bore aloft a drawn dagger, and had approached, in rapid impetuosity, to within three or four feet of the retreating figure"
     - "the latter, having attained the extremity of the velvet apartment, turned suddenly and confronted his pursuer"
     - "seizing the mummer, whose tall figure stood erect and motionless"
     - "fell prostrate in death the Prince Prospero" (Prospero DIES after confronting the mummer)
   - Impact: The main antagonist is merged with the protagonist (-2 point character score minimum)
   - **SIX attempts have now failed to fix this issue**
   - Location: `src/pipeline/character_extraction/consensus.py`

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story should be its own character entry
   - Aliases that should be grouped together:
     - "the figure" / "the masked figure"
     - "the stranger"
     - "the intruder"
     - "the mummer"
     - "the Red Death" (personification)
   - Evidence: These ALL refer to the same supernatural entity that Prince Prospero confronts
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

## Root Cause Analysis: Why Confrontation Detection Keeps Failing

### Investigation Needed
After 6 failed attempts, the confrontation detection approach needs fundamental reassessment:

1. **Verify function is being called:** Add explicit logging at entry/exit of `_entities_in_confrontation()` to confirm it executes
2. **Check where the merge actually happens:** The merge may be happening BEFORE the cross-group resolution stage where confrontation detection runs
3. **Examine the LLM prompt:** The LLM may be overriding the confrontation detection with its own judgment
4. **Consider blocking at an earlier stage:** If epithets like "the mummer" are being classified as proper names early on, they may never reach the cross-group stage

### Potential Alternative Approaches
1. **Hard rule for this pattern:** If epithet and proper name appear in a "confrontation" context (verbs like pursued, confronted, seized), NEVER merge them regardless of LLM recommendation
2. **Add confrontation check BEFORE LLM call:** Don't even ask the LLM if confrontation is detected
3. **Block merge for short stories with single characters:** If there's only one main character candidate, be extra cautious about merging epithets
4. **Character role detection:** If one name appears as "pursuer" and another as "pursued/retreating", they cannot be the same person

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

### Attempt 5 Fixes Applied
1. Enhanced confrontation detection with solo pattern matching (consensus.py)
   - Root cause identified: Context windows (120-150 chars) too small for Poe's long sentences
   - Added indirect reference patterns ("his pursuer", "the retreating figure")
   - NEW: Count confrontation patterns in each entity's contexts independently
   - NEW: Block merge if BOTH entities show >= 2 confrontation patterns
   - Added comprehensive diagnostic logging
   - **Result: DID NOT WORK** - merge still happening

### Attempt 6 Assessment
- Analysis completed successfully
- Same result as attempts 3, 4, 5: "the mummer" still merged with Prince Prospero
- Score unchanged at 6.70/10
- The fix from attempt 5 had no observable effect

### Attempt 7 Fixes Applied
1. **Root cause analysis completed** (Phase 1 mandatory step)
   - Root cause: Context window too small for LLM cross-group resolution
   - Evidence: Poe's confrontation scene is ~500 chars, but context was limited to 150 chars (epithets) and 120 chars (proper names)
   - Location: `src/pipeline/character_extraction/consensus.py:_llm_cross_group_resolution()` lines 2116, 2131
   - The LLM prompt warns against merging entities in confrontation, but couldn't apply the rule without seeing the full sentence
   - Confrontation detection code exists (line 2168) but runs AFTER LLM decision - by then it's too late
2. **Fix applied: Increased context window size**
   - Changed epithet context: 150 → 400 chars (line 2116)
   - Changed proper name context: 120 → 400 chars (line 2131)
   - This allows the LLM to see Poe's full confrontation sentence
   - Smoke test: Running in background (full pipeline takes ~7min)
3. **Modified files:**
   - `src/pipeline/character_extraction/consensus.py`

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 7)
- Analysis completed successfully in 7m 5s
- 1 character detected: "the Prince Prospero" (alias: "the mummer") ← STILL WRONG
- 1 character profile generated
- 73 pronunciation flags
- Character extraction time: 4m 40s (65.9% of total time)
- Total tokens: 32,098
- 18 LLM calls
- Some LLM 500 errors during identity detection and moral valence classification (non-fatal)

## Next Action

Proceed to evaluation phase (awaiting_evaluation).

**Attempt 7 Assessment:**
- Fix from attempt 7 (increased context window 150/120 → 400 chars) DID NOT WORK
- "the mummer" is still merged with Prince Prospero
- This is the SEVENTH consecutive failed attempt to fix this issue
- The context window increase had no observable effect on the merge decision
