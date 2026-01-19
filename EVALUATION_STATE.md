# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL (unchanged from attempt 3)
- Character Profiles: 5/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 3 (**-2 REGRESSION**, unchanged from attempt 3)
- Profiles: 2 → 5 (+3 improvement)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 improvement)
- Presentation: 9 → 8 (-1 regression)
- **Overall: 6.75 → 6.70 (-0.05 slight regression)**

## Attempt 3 Fix Assessment

### Fix: Enhanced cross-group resolution with conflict detection
**Status: DID NOT WORK**

The fix added:
1. CRITICAL RULE #5 about conflict/opposition/confrontation
2. Increased epithet context from 3x100 to 4x150 chars
3. Added context snippets for proper names (3x120 chars)
4. Enhanced prompt warnings about separate entities in conflict

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Root cause analysis:**
- The LLM is still making the wrong decision despite enhanced prompts
- The context provided may still not be sufficient OR
- The LLM model (qwen3-next:80b) is not following the conflict detection instructions
- Note from logs: "LLM identity detection failed (server error 500)" and "Moral valence classification failed (server error 500)" - these errors may have affected quality

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with "Prince Prospero"**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification
   - Evidence from text:
     - "But the mummer had gone so far as to assume the type of the Red Death. His vesture was dabbled in blood"
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
     - The mummer is "tall and gaunt" and "shrouded from head to foot in the habiliments of the grave"
     - Prince Prospero PURSUES and CONFRONTS the mummer - they are clearly separate entities
   - Impact: The main antagonist is merged with the protagonist (-2 point character score)
   - **Previous fix attempt:** Enhanced conflict detection prompts - DID NOT WORK
   - Root cause hypothesis: The LLM pairwise merge decision is still approving this incorrect merge despite prompt enhancements
   - Location: `src/pipeline/character_extraction/consensus.py` - `_llm_cross_group_resolution()` or `_llm_pairwise_merge()`

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
   - Note: Will likely emerge naturally once issue #1 is fixed

### HIGH
3. **Mention count too low for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline
   - Fix: Ensure mention counts aggregate across all aliases

4. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero but this isn't captured
   - Evidence: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
5. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

6. **Too many common words in pronunciation guide (65 in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence" are flagged
   - Location: Pronunciation flagging threshold

7. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but assimilated)
   - Location: Foreign word detection

### LOW
8. **Timing table formatting**
   - Problem: "started_at" and "ended_at" rows in timing may show formatting issues
   - Location: HTML template

## Fix History

### Attempt 1 Fixes Applied
1. **Cross-group epithet resolution** (consensus.py) - Did not produce expected results
2. **Article filtering for pronunciation** (cmu_proposer.py) - Partially worked

### Attempt 2 Fixes Applied
1. **Proper name with article classification** (consensus.py:_is_descriptive_handle())
   - Partially worked: Profile now generated, mention count improved 3→6
   - Caused regression: "the mummer" incorrectly merged with Prince Prospero

### Attempt 3 Fixes Applied
1. **Enhanced cross-group resolution with conflict detection** (consensus.py)
   - Added CRITICAL RULE #5 about conflict/opposition/confrontation
   - Increased epithet context from 3x100 to 4x150 chars
   - Added context snippets for proper names (3x120 chars)
   - **Result: DID NOT WORK** - merge still happening

## Key Insight for Fix Phase

**The prompt-based approach is not working.** Three attempts have tried to fix this via LLM prompt improvements:
1. Attempt 1: Cross-group epithet resolution
2. Attempt 2: Proper name with article classification (caused the regression)
3. Attempt 3: Enhanced conflict detection prompts (did not work)

**New approach needed:** Instead of relying on LLM judgment, implement a **structural/heuristic check**:

1. **Pre-filter approach:** Before sending epithet-to-proper-name pairs to LLM, check if the epithet appears in sentences that describe CONFRONTATION with the proper name:
   - Look for verbs like: "pursued", "confronted", "seized", "approached", "retreating from"
   - If the epithet is the OBJECT of such verbs where the proper name is the SUBJECT, they are likely different entities

2. **Example for this text:**
   - "Prince Prospero... rushed hurriedly through the six chambers" + "the retreating figure"
   - "seizing the mummer" (revellers seize the mummer)
   - "Prince Prospero... had approached... to within three or four feet of the retreating figure"
   - These patterns show the mummer/figure is being ACTED UPON separately from Prospero

3. **Implementation location:** `src/pipeline/character_extraction/consensus.py` in `_candidate_pairs_for_merge()` or early in `_llm_cross_group_resolution()`

4. **Pseudo-code:**
   ```python
   def _entities_in_confrontation(entity1: str, entity2: str, text: str) -> bool:
       """Check if two entities appear in confrontational relationship."""
       confrontation_verbs = ['pursued', 'confronted', 'seized', 'attacked',
                             'approached', 'retreating', 'chased', 'fled']
       # Find sentences containing both entities
       # Check if one entity is agent and other is patient of confrontation verb
       # Return True if they appear to be opposing entities
   ```

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 4)
- Analysis completed successfully in ~7m
- 1 character detected: "the Prince Prospero" (alias: "the mummer")
- 1 character profile generated
- 73 pronunciation flags
- Character extraction time: 4m 28s (62.5% of total time)
- Note: LLM identity detection failed (server error 500)
- Note: Moral valence classification failed (server error 500)

## Regression Warning
The overall score remains at 6.70 (no change from attempt 3). The attempt 3 fix did not work. A new approach is needed.

## Next Action
Run PROMPT_fix.md with new approach: Implement structural/heuristic confrontation detection to pre-filter epithet-proper name pairs BEFORE LLM evaluation. Do not rely solely on LLM prompt instructions.
