# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 12
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

## Attempt 12 Analysis: CONTEXT WINDOW FIX FAILED

### What Was Tried
Increased `character_mention_context_chars` from 200 -> 250 in `src/agents/config.py`.

### Result
**FAILED** - The merge STILL occurs with the production model (qwen3-next:80b).

### Key Finding
The smoke test with qwen3:4b-instruct showed the fix working (3 characters extracted), but the full analysis with qwen3-next:80b shows the merge still happening (1 character extracted with "the mummer" as an alias).

**This is critical information:** The fix is MODEL-DEPENDENT.

### Why the Fix Worked on Small Model but Failed on Large Model
Possible reasons:
1. **Different consensus behavior**: The 80b model may have stronger consensus logic that overrides the death detection
2. **Different tokenization**: The 80b model may process context differently
3. **Different prompt interpretation**: The 80b model may interpret the "same person" heuristic differently
4. **Merge happening earlier**: The 80b model may be merging at the proposer level, not cross-group resolution

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
   - **TWELVE attempts have now failed to fix this issue**
   - **Status:** Context window fixes (attempts 11-12) work on small models but NOT on production model

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

### HIGH
3. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
4. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

5. **Too many common words in pronunciation guide (65+ in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence", "casements" are flagged
   - Location: Pronunciation flagging threshold

6. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

## Root Cause Analysis: Summary After 12 Attempts

### The Smoking Gun Evidence
**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves:
1. The underlying text analysis CAN distinguish these characters
2. The LLM models UNDERSTAND they are different entities
3. The merge is happening in the character extraction consensus/resolution logic, not in understanding

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

### Key Insight from Attempt 12
The context window fix DOES work - but only on smaller models. The production model (qwen3-next:80b) still merges the characters. This suggests:

1. **The fix targets the right mechanism** (death scene context)
2. **But the production model has a stronger merge bias** that overrides the death detection

### Recommended Next Approach

**STOP trying to fix cross-group resolution or context windows. After 12 attempts, we know:**
1. Cross-group resolution fixes don't work (10 attempts)
2. Context window fixes are model-dependent (2 attempts)

**NEW APPROACH NEEDED:**

#### Option A: Use Summary Output to Validate Characters
Since the summary pipeline correctly identifies 2 characters, we could:
1. Extract character names from the chapter summary
2. Use these to VALIDATE/CORRECT the character extraction output
3. If summary says "Prince Prospero" and "The masked figure (Red Death)" are separate, split them

#### Option B: Add Post-Processing Character Split Rule
Add a rule in the final character output stage:
- If a character has an alias that appears in a "death scene" where the canonical name dies, split them
- Pattern: "fell prostrate in death [character A]... seizing [character B]" -> split A and B

#### Option C: Model-Specific Configuration
Since the fix works on smaller models:
- Use a smaller model specifically for character extraction on short texts
- Or add model-specific thresholds for merge decisions

#### Option D: Proposer-Level Investigation
The merge may be happening at the PROPOSER level, not consensus:
1. Add debug logging to see what each proposer extracts
2. Check if "the mummer" is being associated with Prospero by individual proposers
3. If so, fix at the proposer prompt level, not consensus

## Fix History

### Attempts 1-10
See git history. All targeted cross-group resolution in `consensus.py`. None worked.

### Attempt 11
- **Change:** `character_mention_context_chars` 100 -> 200
- **Result:** Score +0.15, merge still occurs

### Attempt 12
- **Change:** `character_mention_context_chars` 200 -> 250
- **Result:** Works on qwen3:4b-instruct, FAILS on qwen3-next:80b
- **Conclusion:** Fix is model-dependent, production model has stronger merge bias

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 12)
- Analysis completed in 7m 26s
- Total LLM tokens: 39,946
- Character count: 1 (STILL showing merge issue)
- Model used for Character Extraction: qwen3-next:80b-a3b-instruct-q8_0

## Next Action

**Implement Option A or B:** Use the summary output to validate/correct character extraction.

The summary pipeline KNOWS these are different characters. We need to leverage that knowledge to fix the character extraction output.

Specifically:
1. After character extraction completes, parse the chapter summary for character mentions
2. If the summary lists characters as separate but character extraction merged them, split them
3. This is a post-processing correction, not a fix to the extraction logic itself

This approach has the highest chance of success because:
- It uses information we KNOW is correct (summary output)
- It's a targeted fix for this specific failure mode
- It doesn't require understanding why the merge is happening
