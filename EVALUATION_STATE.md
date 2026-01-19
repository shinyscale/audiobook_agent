# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 15
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

## Attempt 15 Result: FAILED

### What Was Tried
Increased `max_chars` in pairwise context formatting (consensus.py:991-994):
- Ambiguous names: 200 → 300 chars
- Non-ambiguous: 160 → 250 chars

### Result
**FAILED** - Smoke test showed 2 separate characters, but full analysis still merged them:
- Smoke test (12m 3s): 2 characters detected separately
- Full analysis (7m 45s): 1 character with "the mummer" as alias of "Prince Prospero"

### Why It Failed
The context window increase was not sufficient. The merge is happening at a level that context alone cannot fix. Possible reasons:
1. The LLM is still deciding these are the same character despite having the death scene context
2. The pairwise decision is influenced by other factors (scene proximity, masquerade setting)
3. The merge may be happening earlier in the pipeline (initial extraction or heuristics)

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
   - **FIFTEEN attempts have now failed to fix this issue**
   - **Status:** Context windows, prompt rules, death detection functions - NONE have worked

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
   - Problem: Text uses "the duke" to refer to Prospero: "The tastes of the duke were peculiar"
   - Location: Alias detection

### MEDIUM
4. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

5. **Too many common words in pronunciation guide (35-40% false positives)**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements", "buffoons", "glaringly" are flagged
   - Count: ~25-30 of 73 entries are false positives
   - Location: Pronunciation flagging threshold or common word filter

6. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Summary After 15 Attempts

### The Core Problem
The LLM decides "the mummer" = "Prince Prospero" despite all fixes. 15 different approaches have been tried at various pipeline stages, and NONE have worked.

### Key Observation
The chapter summary pipeline CORRECTLY identifies them as separate:
> "Prince Prospero... pursues the figure through the chambers with a dagger, only to collapse dead upon confronting it in the black room"

But the character extraction pipeline merges them. This suggests:
1. The summary agent has different/better context
2. The character extraction pairwise decision is the bottleneck
3. The merge decision is made with incomplete reasoning

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
| 14 | Death/confrontation rules in pairwise prompt | No effect |
| 15 | Pairwise context max_chars 160/200 -> 250/300 | Smoke test passed, full analysis failed |

## Recommended Next Approach (Attempt 16)

### Priority 1: POST-PROCESSING SPLIT Based on Death Evidence
Since every pre-merge approach has failed, implement a POST-PROCESSING step:

1. After character extraction completes, scan the merged character's evidence/contexts
2. Look for patterns indicating A kills B or A dies confronting B:
   - "fell prostrate in death the [NAME]"
   - "collapsed dead"
   - "pursued... then died"
3. If two names within a single character entry appear in a death relationship:
   - SPLIT them into separate characters
   - Move relevant contexts to each

This is a REMEDIATION approach that works AFTER the LLM has made its (wrong) decision.

### Priority 2: Compare Character List Against Summary
The summary correctly identifies "Prince Prospero" and "the masked figure (Red Death)" as separate. Use this:

1. Parse `characters_present` from chapter summaries
2. If summaries identify entities not in the final character list, flag potential false merges
3. If a character in summaries is listed as an alias in extraction, investigate splitting

### Priority 3: Force Split for Supernatural Entities
Add a rule: if an entity is described as "untenanted by any tangible form" or similar supernatural descriptors, it CANNOT be an alias of a human character.

### What NOT to Try Again
- Context window adjustments (attempts 7-15 proved these don't help significantly)
- Prompt-based rules alone (attempts 3, 14 proved these don't help)
- Death detection functions that rely on LLM decision (attempts 4-5, 8-10, 13)
- Pre-merge heuristics (the LLM overrides them)

## Fix History

### Attempts 1-14
See previous EVALUATION_STATE.md entries and git history.

### Attempt 15
- **Change:** Increased pairwise context max_chars from 160/200 to 250/300 (consensus.py:991-994)
- **Root Cause Hypothesis:** Death scene evidence (~221 chars) was being truncated before reaching LLM
- **Smoke Test:** PASS - 2 separate characters detected ("Prince Prospero" and "the mummer")
- **Full Analysis:** FAIL - Characters still merged
- **Files Modified:** src/pipeline/character_extraction/consensus.py
- **Conclusion:** Context window increase alone is not sufficient; smoke test vs full analysis discrepancy suggests model behavior variance or other pipeline factors

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json
- Directory: output/Masque of the Red Death - Poe_20260119_044538

## Pipeline Notes (Attempt 15)
- Analysis completed successfully in 7m 45s
- Total tokens: 40,243
- Character extraction bottleneck: 66% of time (5m 7s)
- Result: Still only 1 character detected with "the mummer" listed as an alias of "Prince Prospero"

## Next Action
Run PROMPT_fix.md to implement post-processing character split based on death evidence
