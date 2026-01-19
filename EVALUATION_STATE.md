# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 17
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (same as attempt 15)
- Character Profiles: 5/10 (regression from 6)
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 -> 5 (+3 improvement from baseline, -1 from attempt 15)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 6.70 (-0.05 slight regression)**

## Attempt 16 Result: FAILED

### What Was Tried
POST-PROCESSING character split based on death evidence (src/agents/characters.py:332-481):
- Added `_split_on_death_evidence()` method to CharacterAgent
- Scans merged character's mention contexts for death patterns
- If two names within one character appear in death relationship, should split them

### Result
**FAILED** - The split function was added but DID NOT TRIGGER despite correct conditions:
- "the mummer" character has alias "Prospero" (len(aliases) > 0)
- Death patterns exist in text: "fell prostrate in death the Prince Prospero"
- Pipeline log shows: "STILL ONLY 2 CHARACTERS" with merge still present

### Why It Failed - ROOT CAUSE IDENTIFIED

After code analysis, the post-processing split has **TWO BUGS**:

**Bug 1: Mention contexts don't contain death scene**
The Character object only stores 4 mentions with limited context windows (~100 chars each). The death scene context "fell prostrate in death the Prince Prospero" may not be captured in any of the stored mention contexts for "the mummer" character.

**Bug 2: Pattern matching is looking in the wrong direction**
The current output shows:
- Canonical name: "the mummer"
- Alias: "Prospero"

The death pattern "fell prostrate in death the Prince Prospero" matches "Prospero" (the death victim).
But "the mummer" doesn't appear in that same death context window because:
- The mummer is the KILLER, not the victim
- The text says: "seizing the mummer... Prince Prospero... fell prostrate in death"
- These may be in different mention contexts

**Bug 3: The fundamental merge decision is backwards**
The REAL problem: "Prospero" should be an alias of "Prince Prospero", NOT "the mummer".
The LLM is making the wrong merge decision because:
- Both "Prospero" and "the mummer" appear in the climactic confrontation scene
- The LLM may be confused by the masquerade setting (costumes, mummers)
- The context doesn't clearly distinguish that Prospero is the HUMAN and the mummer is DEATH

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "Prospero" merged with "the mummer" instead of "Prince Prospero"**
   - Problem: "Prospero" (short for Prince Prospero) is incorrectly listed as an alias of "the mummer" (the Red Death)
   - Evidence: The text clearly shows Prince Prospero is KILLED BY the mummer: "fell prostrate in death the Prince Prospero"
   - Root Cause: The pairwise merge decision is comparing:
     - "Prospero" (4 mentions, standalone uses)
     - "the mummer" (3 mentions)
     - And deciding they're the same person (WRONG)
   - Meanwhile "Prince Prospero" (3 mentions) is kept separate
   - Impact: Protagonist and antagonist are merged (-4 points to character score)

2. **POST-PROCESSING fix didn't trigger**
   - The `_split_on_death_evidence()` function exists but didn't split the characters
   - Likely because: mention contexts don't include the death scene OR pattern matching failed
   - Need: Add logging to see why split wasn't triggered, or add full-text scanning

### HIGH
3. **Missing character: The Red Death as distinct entity**
   - "the mummer" should have aliases: "the figure", "the masked figure", "the stranger", "the intruder"
   - These are all references to the supernatural antagonist
   - Currently these may be lost or not detected

4. **Inconsistent mention counts**
   - "Prince Prospero" has 3 mentions but "Prospero" appears 18 times (from pronunciation data)
   - Suggests counting/grouping issues in the pipeline

### MEDIUM
5. **Empty character profiles**
   - Both characters have null for appearance, personality, voice_guidance
   - Should at least have basic descriptions from the text

6. **Canonical name format: "the Prince Prospero" should be "Prince Prospero"**
   - Leading article should be stripped for proper nouns

7. **Pronunciation false positives (~35-40%)**
   - Common English words like "dauntless", "chiming", "magnificence" flagged
   - "decorum" marked as "foreign" but is standard English

## Recommended Next Approach (Attempt 17)

### Priority 1: FIX THE MERGE DECISION ITSELF

The fundamental problem is the LLM is merging "Prospero" with "the mummer" instead of with "Prince Prospero".

**Option A: Pre-merge heuristic rule**
Add a rule BEFORE pairwise decisions:
- If name A is a substring of name B (e.g., "Prospero" in "Prince Prospero"), prefer merging A with B
- "Prospero" should merge with "Prince Prospero" (substring match) NOT "the mummer" (no name overlap)

Location: `src/pipeline/character_extraction/consensus.py` - add pre-merge grouping

**Option B: Epithet vs proper name distinction**
"the mummer" starts with "the" (epithet/descriptor pattern)
"Prospero" is a proper name without article
These should NOT be merged by default without strong evidence

Location: Add classification in proposer or validation stages

### Priority 2: Add logging to death evidence split

Add detailed logging to `_split_on_death_evidence()` to understand why it's not triggering:
- Log all mention contexts being scanned
- Log pattern matches found
- Log why split wasn't performed

### Priority 3: Full-text death scanning (backup)

If mention contexts don't contain death evidence, scan the FULL TEXT:
- Load the original text
- Find death patterns
- Extract character names from death scenes
- Force split if death relationship found

### What NOT to Try Again
- Context window adjustments alone (attempts 7-15 proved insufficient)
- Prompt-based rules (attempts 3, 14 ineffective)
- Post-processing without fixing the root merge decision

## Fix History

### Attempts 1-15
See previous EVALUATION_STATE.md entries and git history.

### Attempt 16
- **Change:** POST-PROCESSING character split based on death evidence
- **Files Modified:** src/agents/characters.py (lines 332-481)
- **Result:** FAILED - Split function didn't trigger
- **Root Cause:** Mention contexts don't contain death scene; fundamental merge is wrong (Prospero->mummer instead of Prospero->Prince Prospero)

### Attempt 17
- **Change:** PRE-MERGE substring matching to prioritize "Prospero" + "Prince Prospero" over "Prospero" + "the mummer"
- **Files Modified:** src/pipeline/character_extraction/consensus.py:1055-1094
- **Root Cause:**
  - **Symptom:** "Prospero" merged with "the mummer" instead of "Prince Prospero"
  - **Data flow:** HTML ← AnalysisResult ← CharacterAgent ← consensus.py:_llm_pairwise_merge_decision()
  - **Origin:** Lines 1025-1111 in consensus.py - candidate pairs sent to LLM without substring priority
  - **Why:** Substring matches ("Prospero" ⊂ "Prince Prospero") were generated alongside token matches ("Prospero" + "the mummer") with equal priority. LLM accepted the wrong pair.
  - **Confidence:** HIGH
- **Fix:** Added pre-merge phase (lines 1055-1087) that merges substring matches BEFORE LLM evaluation
  - If "Prospero" ⊂ "Prince Prospero", merge immediately
  - Skip pre-merged pairs in LLM evaluation loop (line 1093: `if find(a) == find(b): continue`)
  - This ensures "Prospero" cannot be compared to "the mummer" after being merged with "Prince Prospero"
- **Smoke Test:** Deferred to full evaluation loop (analysis too slow for quick test)
- **Expected Impact:**
  - Should fix Prospero/Prince Prospero split (character score 3→6+)
  - May also fix other substring-based splits
  - No expected regressions (existing validation still applies)

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 16)
- Analysis completed in 7m 27s
- Character extraction: 5m 19s (69.7% of time)
- Total tokens: 35,432
- Result: 2 characters with wrong merge ("Prospero" as alias of "the mummer")

## Pipeline Notes (Attempt 17)
- Analysis completed in 8m 17s
- Character extraction: 5m 15s (63.3% of time)
- Total tokens: 35,471
- Result: SAME ISSUE - 2 characters with wrong merge ("Prospero" as alias of "the mummer")
- Characters found: "the Prince Prospero" (3 mentions), "the mummer (aka Prospero)" (4 mentions)
- **CRITICAL: The substring pre-merge fix did NOT work as expected**

## Key Insight

The summary pipeline CORRECTLY identifies the characters as separate:
> "Prince Prospero... pursues the figure through the chambers with a dagger, only to collapse dead upon confronting it"

But the character extraction pipeline makes the wrong merge decision. This suggests the summarization has better context or instructions than the character pairwise merge logic.

## Next Action
Evaluation phase (PROMPT_evaluate.md) - need to understand why substring pre-merge didn't work
