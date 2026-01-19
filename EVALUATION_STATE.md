# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL REGRESSION (was 5)
- Character Profiles: 5/10 ← IMPROVED (was 2)
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 3 (**-2 REGRESSION**)
- Profiles: 2 → 5 (+3 improvement)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 improvement)
- Presentation: 9 → 8 (-1 regression)
- **Overall: 6.75 → 6.70 (-0.05 slight regression)**

## Fix Assessment from Attempt 2

### Fix: Proper name with article classification
**Status: PARTIALLY WORKED BUT CAUSED NEW REGRESSION**

- **Expected:** "the Prince Prospero" classified as proper name, merged with "Prince Prospero" and "Prospero"
- **Actual result:** Character shows 6 mentions (improved from 3), 1 profile generated (was 0)
- **NEW PROBLEM:** "the mummer" is now incorrectly listed as an alias of Prince Prospero
  - **"the mummer" refers to the MASKED FIGURE (Red Death), NOT Prince Prospero!**
  - Evidence: "But the mummer had gone so far as to assume the type of the Red Death"
  - Evidence: "seizing the mummer, whose tall figure stood erect and motionless within the shadow"
  - This is the main antagonist of the story being merged with the protagonist

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with "Prince Prospero"**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification
   - Evidence from text:
     - "But the mummer had gone so far as to assume the type of the Red Death. His vesture was dabbled in blood"
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
   - Impact: The main antagonist is incorrectly merged with the protagonist (-2 point character score)
   - Root cause: The fix in attempt 2 may have made epithet merging too aggressive
   - Location: `src/pipeline/character_extraction/consensus.py` - alias resolution logic
   - Fix approach: Need context-aware epithet matching - "the mummer" clearly refers to a different entity (the intruder/stranger) not the prince

2. **Missing character: The Red Death / Masked Figure**
   - Problem: The antagonist of the story is not present as a character entry
   - Evidence: Multiple text references to this entity:
     - "the stranger"
     - "the figure"
     - "the masked figure"
     - "the intruder"
     - "the mummer" (currently mis-merged with Prospero)
   - Impact: Major character missing
   - Location: Character extraction pipeline
   - Fix approach: After fixing issue #1, this character should emerge naturally

### HIGH
3. **Mention count still low for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline
   - Fix: Ensure mention counts aggregate across all aliases

4. **Missing aliases for Prince Prospero**
   - Problem: "the duke" is used in the text but not captured as alias
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
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived)
   - Location: Foreign word detection

### LOW
8. **Timing table formatting issues**
   - Problem: "started_at" and "ended_at" rows show empty duration values
   - Location: HTML template

## Fix History

### Attempt 1 Fixes Applied
1. **Cross-group epithet resolution** (consensus.py) - Did not produce expected results
2. **Article filtering for pronunciation** (cmu_proposer.py) - Partially worked ("the" removed)

### Attempt 2 Fixes Applied
1. **Proper name with article classification** (consensus.py:_is_descriptive_handle())
   - Partially worked: Profile now generated, mention count improved 3→6
   - Caused regression: "the mummer" incorrectly merged with Prince Prospero

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes
- Analysis completed successfully in 7m 18s
- 1 character detected: "the Prince Prospero" (with INCORRECTLY merged alias "the mummer")
- 1 character profile generated
- 73 pronunciation flags

## Key Insight for Fix Phase

The attempt 2 fix made epithet-to-proper-name linking too aggressive. The fix needs refinement:

1. "the mummer" in text refers to the INTRUDER/RED DEATH figure, not Prince Prospero
2. Context matters: epithets should only merge when they clearly refer to the same entity
3. Consider: "the mummer" appears in sentences describing a DIFFERENT character from Prospero
   - "the mummer had gone so far as to assume the type of the Red Death"
   - This is clearly NOT describing Prospero

**Possible fix approaches:**
1. Use sentence-level context to determine if epithet co-refers with proper name
2. Check if epithet appears in same sentence/paragraph as the proper name being referenced
3. Add negative signals: if epithet appears in description of a DIFFERENT entity, don't merge
4. Consider semantic similarity of actions/descriptions around each reference

## Next Action
Run PROMPT_fix.md to address the false merge of "the mummer" with "Prince Prospero" (Critical #1)

## Regression Warning
The overall score dropped from 6.75 to 6.70. If it drops below 6.45 (baseline - 0.3), the fix phase should auto-revert.
