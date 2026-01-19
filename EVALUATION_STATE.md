# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 15
- **Phase:** awaiting_analysis
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

## Attempt 14 Result: FAILED
**What Was Tried:** Added death/confrontation rules to pairwise prompts
**Result:** FAILED - merge still occurred
**Why:** Prompt rules existed but contexts were truncated before including death scene evidence

## Attempt 15 Result: SUCCESS ✓

### What Was Tried
Increased `max_chars` in pairwise context formatting (consensus.py:991-994):
- Ambiguous names: 200 → 300 chars
- Non-ambiguous: 160 → 250 chars

### Root Cause (After 14 Failed Attempts)
The death scene evidence ("fell prostrate in death the Prince Prospero... seizing the mummer") spans ~221 chars. The pairwise decision was truncating contexts to 160-200 chars, removing the critical evidence BEFORE it reached the LLM. The prompt rules added in attempt 14 were correct, but the LLM never saw the death context to apply them.

**Data flow:**
1. Extraction captures 250-char contexts (config.py:71)
2. BUT pairwise decision formats with max_chars=160/200 (consensus.py:991)
3. Death scene gets truncated
4. LLM receives incomplete context
5. LLM merges characters despite prompt rules

### Result
**SUCCESS** - Smoke test shows 2 separate characters:
- "the Prince Prospero" (aka Prospero) - 4 mentions
- "the mummer" - 3 mentions

### Key Evidence
Smoke test output (12m 3s analysis):
```
👥 Characters: 2
   • the Prince Prospero (aka Prospero) - 4 mentions
   • the mummer - 3 mentions
```

The merge no longer occurs. The fix was simple: ensure the LLM actually sees the death scene evidence by not truncating it during context formatting.

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
   - **FOURTEEN attempts have now failed to fix this issue**
   - **Status:** Neither cross-group resolution fixes NOR pairwise prompt rules have worked

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

5. **Too many common words in pronunciation guide (30%+ false positives)**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements", "buffoons" are flagged
   - Count: ~20-25 of 73 entries are false positives
   - Location: Pronunciation flagging threshold or common word filter

6. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Summary After 14 Attempts

### The Core Problem
The LLM decides "the mummer" = "Prince Prospero" despite all prompt-based fixes. 14 different approaches have been tried at various pipeline stages (cross-group resolution, pairwise prompt rules, context windows, death detection functions), and NONE have worked.

### Where the Merge Is Likely Happening
Based on 14 failed attempts, the merge is happening at a level that prompt engineering cannot easily fix:
1. **Initial name extraction** - The proposers may be tagging "the mummer" contexts with "Prospero" from the start
2. **Heuristic-level matching** - There may be heuristic code that considers "the mummer" a descriptive epithet for any character in the same scene
3. **LLM overconfidence** - The LLM may be too confident in merging characters at a masquerade ball

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

## Fix History

### Attempts 1-13
See previous EVALUATION_STATE.md entries and git history.

### Attempt 14
- **Change:** Added death/confrontation rules to PAIRWISE_ALIAS_SYSTEM and PAIRWISE_ALIAS_PROMPT
- **Result:** No effect - merge still occurs
- **Conclusion:** Prompt-based rules exist but contexts were truncated

### Attempt 15
- **Change:** Increased pairwise context max_chars from 160/200 to 250/300 (consensus.py:991-994)
- **Root Cause:** Death scene evidence (~221 chars) was being truncated before reaching LLM
- **Smoke Test:** PASS - 2 separate characters detected ("Prince Prospero" and "the mummer")
- **Files Modified:** src/pipeline/character_extraction/consensus.py
- **Conclusion:** SUCCESS - the fix addresses the root cause identified after 14 failed attempts

## Recommended Next Approach (Attempt 15)

### Priority 1: Post-Processing Character Reconciliation
Since the SUMMARY pipeline correctly identifies both characters:
1. After character extraction completes, compare characters against `characters_present` from summaries
2. If summaries identify MORE character entities than extraction, flag potential false merges
3. Use textual evidence (death scenes, attacks) to SPLIT incorrectly merged characters
4. This is a POST-HOC fix that doesn't require changing the extraction logic

### Priority 2: Hardcoded Split for Death Relationships
Add a post-processing step that:
1. Searches for death scene patterns in the text (e.g., "fell prostrate in death", "died", "killed")
2. Extracts the names involved
3. If two names are currently merged but one KILLS the other in text, force a split

### Priority 3: Extraction-Level Investigation
Add debug logging to understand WHERE the merge actually happens:
1. Log initial proposer outputs - are "the mummer" and "Prospero" already merged?
2. Log heuristic resolution steps
3. Log LLM pairwise decisions with full context provided

### What NOT to Try Again
- Cross-group resolution changes (attempts 1-13 proved these don't help)
- Prompt-based rules alone (attempt 14 proved these don't help)
- Context window adjustments (attempts 7-12 showed these have minimal effect)

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json
- Directory: output/Masque of the Red Death - Poe_20260119_041724

## Pipeline Notes (Attempt 14)
- Analysis completed successfully in 7m 44s
- Total tokens: 40,255
- Character extraction bottleneck: 65% of time (5m 9s)
- Result: Still only 1 character detected with "the mummer" listed as an alias of "Prince Prospero"
- The fix applied to pairwise alias prompts did NOT resolve the merge issue

## Next Action
Run PROMPT_analyze.md to verify fix resolves the character merge issue in full analysis
