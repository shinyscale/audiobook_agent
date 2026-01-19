# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 11
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

## Attempt 11 Fix: FAILED

### What Was Tried
Increased `character_mention_context_chars` from 100 -> 200 in `src/agents/config.py` to allow death scenes to be captured within the context window.

### Why It Failed
The context window increase had **minimal effect**. The character count is still 1, and "the mummer" is still incorrectly merged with Prince Prospero. The score improved marginally (6.70 -> 6.85) but the core character merge issue persists.

**Critical Observation:** The death relationship detection logic added in attempts 1-10 was correct. The context window increase was correct. But **THE MERGE IS STILL HAPPENING** at an undetermined stage.

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
   - **ELEVEN attempts have now failed to fix this issue**
   - Location: **STILL UNKNOWN** - not in cross-group resolution, context window increase did not help

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

## Root Cause Analysis: Why 11 Attempts Have Failed

### Summary of All Failed Attempts

| Attempt | Fix Applied | Result |
|---------|-------------|--------|
| 1 | Cross-group epithet resolution | No effect |
| 2 | Proper name with article classification | Caused regression - merge started |
| 3 | Added CRITICAL RULE #5 about confrontation in prompt | No effect |
| 4 | Implemented `_entities_in_confrontation()` function | No effect |
| 5 | Solo pattern matching for confrontation | No effect |
| 6 | (Evaluation only, no new fix) | No effect |
| 7 | Increased context window 150/120 -> 400 chars | No effect |
| 8 | Hard-coded death relationship detection | No effect |
| 9 | Increased context windows to 600-800, added death rule #6 | No effect |
| 10 | Fixed death relationship detection (check ALL contexts) | No effect |
| 11 | Increased mention_context_chars 100 -> 200 | Minimal effect (+0.15 score) |

### The Fundamental Problem

After 11 attempts targeting:
- Cross-group resolution: 10 attempts, NO effect
- Context window (mention extraction): 1 attempt, MINIMAL effect

**CONCLUSION: The merge is NOT happening where we've been looking.**

### Critical Evidence

The **chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves:
1. The underlying text analysis CAN distinguish these characters
2. The merge decision is happening OUTSIDE of cross-group resolution
3. All 11 attempts have been fixing the WRONG code location

### Where Is the Merge Actually Happening?

We have eliminated:
- ✗ Cross-group resolution (10 attempts, no effect)
- ✗ Mention context window size (1 attempt, minimal effect)

Remaining possibilities:

1. **Initial NER entity grouping** - spaCy may be grouping "mummer" with "Prospero" at extraction time based on proximity/coreference
2. **Single-group resolution** - Before cross-group, entities within a single proposed group may be pre-merged
3. **Proposer-level consensus** - Multiple proposers may agree to merge before cross-group resolution runs
4. **Entity classification stage** - "the mummer" may be classified as an epithet for Prospero at entity classification time
5. **Character merging post-processor** - Final cleanup may re-merge characters

### Recommended Next Approach

**CRITICAL: STOP modifying cross-group resolution code - 11 attempts prove the bug is not there.**

1. **Add comprehensive tracing** at the PROPOSER level:
   - What entities does each proposer extract for "the mummer"?
   - What group does each proposer assign "the mummer" to?
   - Is "the mummer" being associated with Prospero BEFORE consensus runs?

2. **Examine the NER extraction stage** in `src/pipeline/character_extraction/`:
   - How does spaCy classify "the mummer"?
   - Is coreference resolution linking "the mummer" to "Prospero"?

3. **Add a DEBUG environment variable** to dump intermediate state:
   - Proposer outputs before consensus
   - Consensus input (what pairs are being considered)
   - Cross-group resolution input (what groups exist)

4. **Consider inverting the problem**:
   - Since the summary pipeline correctly identifies 2 characters, can we use the summary output to VALIDATE/CORRECT character extraction?
   - Add a post-processing step: "If the chapter summary mentions character X as distinct from character Y, they should NOT be merged"

## Fix History

### Attempt 11 Fixes Applied
1. **Increased mention context window** (src/agents/config.py line 72)
   - Changed `character_mention_context_chars` from 100 -> 200 characters
   - Rationale: Death scene spans 190 chars, needed wider context
   - Result: Score improved 6.70 -> 6.85 but merge still occurs
   - **Conclusion: Context window was NOT the bottleneck**

### Attempts 1-10 Fixes
See git history for full details. All targeted cross-group resolution in `consensus.py` - none succeeded.

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 11)
- Analysis completed in 7m 28s
- Total LLM tokens: 35,769
- Character count: 1 (STILL showing merge issue - "the Prince Prospero (aka Prospero, the mummer)")
- Pipeline bottleneck: Character Extraction (67.8% of time, 5m11s)

## Key Observation

**The chapter summary pipeline CORRECTLY identifies 2 characters:**
- "Prince Prospero"
- "The masked figure (Red Death)"

**But the character extraction pipeline merges them into 1.**

This proves the information IS available. The bug is in character extraction, NOT in text analysis capability.

## Next Action

Run PROMPT_fix.md with NEW APPROACH:

1. **DO NOT modify cross-group resolution code** - 11 attempts prove the bug is not there
2. **Add debug tracing at the PROPOSER level** to identify where "the mummer" gets associated with Prospero
3. **Examine NER extraction and entity classification stages**
4. **Consider using summary output to validate character extraction** (summary correctly distinguishes the characters)
