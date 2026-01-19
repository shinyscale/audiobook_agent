# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 7
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
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 → 6 (+4 improvement)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 improvement)
- Presentation: 9 → 8 (-1 regression)
- **Overall: 6.75 → 6.85 (+0.10 slight improvement)**

## Attempt 7 Fix Assessment

### Fix: Increased context window for LLM cross-group resolution (150/120 → 400 chars)
**Status: DID NOT WORK**

The fix from attempt 7 increased the context window size in `_llm_cross_group_resolution()`:
1. Epithet context: 150 → 400 chars (line 2116)
2. Proper name context: 120 → 400 chars (line 2131)

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Evidence from analysis.json:**
- Character: "the Prince Prospero"
- Aliases: ["the mummer"]
- Only 1 character detected (should be 2)

**Why it failed:** Despite providing larger context windows (400 chars), the LLM is STILL deciding to merge these entities. Possible reasons:
1. The LLM prompt may not be clear enough about confrontation semantics
2. The merge decision is happening at an earlier stage before cross-group resolution
3. The LLM may be weighing other factors (both appear in masquerade context) over confrontation evidence
4. 400 chars may still not capture the full confrontation sentence

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
   - **SEVEN attempts have now failed to fix this issue**
   - Location: `src/pipeline/character_extraction/consensus.py`

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story should be its own character entry
   - Aliases that should be grouped together:
     - "the figure" / "the masked figure"
     - "the stranger"
     - "the intruder"
     - "the mummer"
     - "the Red Death" (personification)
   - Evidence: These ALL refer to the same supernatural entity that Prince Prospero confronts and dies fighting
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

### Summary of 7 Failed Attempts

| Attempt | Fix Applied | Result |
|---------|-------------|--------|
| 1 | Cross-group epithet resolution | No effect |
| 2 | Proper name with article classification | Caused regression - merge started |
| 3 | Added CRITICAL RULE #5 about confrontation in prompt | No effect |
| 4 | Implemented `_entities_in_confrontation()` function | No effect |
| 5 | Solo pattern matching for confrontation | No effect |
| 6 | (Evaluation only, no new fix) | No effect |
| 7 | Increased context window 150/120 → 400 chars | No effect |

### The Fundamental Problem

The merge decision is happening **despite** the confrontation detection code and prompt warnings. This suggests:

1. **The merge may happen BEFORE the cross-group resolution stage** - Epithets like "the mummer" may be classified and merged at an earlier stage
2. **The LLM is overriding explicit rules** - Even with prompt warnings about confrontation, the LLM decides to merge based on other similarities (both at masquerade, both in same scene)
3. **The confrontation detection code may not be executing** - Need to verify with explicit logging that the function is called AND that it returns True for these entities

### Recommended Next Approach: Hard Blocking Rule

After 7 failed attempts using LLM-based approaches, consider:

1. **Hard-coded rule: If entity A dies at the hands of entity B, they CANNOT be merged**
   - Check for patterns like "[A] fell prostrate in death" near "[B]" in confrontation context
   - This bypasses LLM judgment entirely

2. **Check WHERE the merge actually happens**
   - Add explicit logging at entry/exit of `_entities_in_confrontation()`
   - Add logging at the point where alias lists are created
   - Verify the confrontation check is called BEFORE the merge decision

3. **Examine the actual LLM response**
   - Log the raw LLM response when it decides to merge "the mummer" with "Prince Prospero"
   - Understand WHY the LLM thinks they're the same person
   - This may reveal a prompt issue or context issue

4. **Consider blocking merge for short stories with single proper name candidate**
   - If there's only one proper name character (Prince Prospero), be extra cautious about merging epithets that could be the antagonist

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
1. **Increased context window size** (consensus.py)
   - Changed epithet context: 150 → 400 chars (line 2116)
   - Changed proper name context: 120 → 400 chars (line 2131)
   - **Result: DID NOT WORK** - merge still happening
   - Score improved marginally: 6.70 → 6.85 (due to profile score re-evaluation)

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 7)
- Analysis completed successfully in ~7 minutes
- 1 character detected: "the Prince Prospero" (alias: "the mummer") ← STILL WRONG
- 1 character profile generated
- 73 pronunciation flags
- Character extraction time: 4m 40s (65.9% of total time)
- Total tokens: 32,098
- 18 LLM calls

## Next Action

Proceed to fix phase (awaiting_fix).

**Recommendation for Attempt 8:**
The LLM-based confrontation detection has failed 7 times. New approach needed:

1. **INVESTIGATE**: Add verbose logging to trace exactly WHERE the merge decision happens and WHY
2. **BYPASS LLM**: Implement hard-coded rules that detect death/killing relationships between entities
3. **EARLIER INTERVENTION**: Check if the merge happens at an earlier stage (not cross-group resolution)
4. **CHECK EXECUTION**: Verify `_entities_in_confrontation()` is actually being called by logging at entry/exit

The pattern "[X] fell prostrate in death" appearing near "[Y] confronted his pursuer" should be an absolute merge blocker, regardless of what the LLM thinks.
