# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 6
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (unchanged from attempts 3, 4)
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
- **Overall: 6.75 → 6.70 (-0.05 slight regression, unchanged from attempt 4)**

## Attempt 4 Fix Assessment

### Fix: Structural confrontation detection pre-filter
**Status: DID NOT WORK**

The fix implemented `_entities_in_confrontation()` to:
1. Detect co-occurrences where epithet and proper name appear together
2. Look for confrontation verbs: pursued, seized, confronted, attacked, approached, retreating, etc.
3. Block merge if ≥50% of co-occurrences show confrontation patterns

**Result:** "the mummer" is STILL incorrectly merged with "Prince Prospero"

**Why it failed:** The confrontation detection either:
1. Did not find sufficient co-occurrences (sampling issue)
2. Did not recognize the confrontation patterns in context
3. The threshold (50%) may be too high
4. The function may not be getting called or is being bypassed

**Evidence from analysis.json:**
- Character: "the Prince Prospero"
- Aliases: ["the mummer"]
- This proves the merge IS still happening despite the fix

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "the mummer" merged with "Prince Prospero"**
   - Problem: "the mummer" is listed as an alias of Prince Prospero, but it refers to the Red Death personification
   - Evidence from text:
     - "But the mummer had gone so far as to assume the type of the Red Death. His vesture was dabbled in blood"
     - "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock"
     - "the latter, having attained the extremity of the velvet apartment, turned suddenly and confronted his pursuer"
     - The mummer is "tall and gaunt" and "shrouded from head to foot in the habiliments of the grave"
     - Prince Prospero PURSUES and CONFRONTS the mummer - they are clearly separate entities that INTERACT
   - Impact: The main antagonist is merged with the protagonist (-2 point character score minimum)
   - **Five attempts have failed to fix this issue**
   - Location: `src/pipeline/character_extraction/consensus.py`

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
   - Note: Will emerge naturally once issue #1 is fixed

### HIGH
3. **Mention count too low for Prince Prospero**
   - Problem: Character shows 6 mentions, but pronunciation shows 18 "Prospero" + 9 "Prince" occurrences
   - Evidence: Clear discrepancy between pronunciation counting and character counting
   - Location: Mention count aggregation in character pipeline

4. **Missing alias: "the duke" for Prince Prospero**
   - Problem: Text uses "the duke" to refer to Prospero: "as might have been expected from the duke's love of the bizarre"
   - Location: Alias detection

### MEDIUM
5. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Location: Character name normalization

6. **Too many common words in pronunciation guide (65+ in "Other")**
   - Problem: Common words like "dauntless", "chiming", "magnificence" are flagged
   - Location: Pronunciation flagging threshold

7. **Foreign word false positive: "decorum"**
   - Problem: "decorum" flagged as foreign word - it's standard English (Latin-derived but fully assimilated)
   - Location: Foreign word detection

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
   - Root cause: Context windows (120-150 chars) too small for Poe's long sentences
   - Added indirect reference patterns ("his pursuer", "the retreating figure")
   - NEW: Count confrontation patterns in each entity's contexts independently
   - NEW: Block merge if BOTH entities show >=2 confrontation patterns (solo logic)
   - This works even when names don't co-occur in the same small context window
   - Modified: `_entities_in_confrontation()` (lines 1959-2089)
   - Added comprehensive diagnostic logging throughout `build_consensus()`
   - **Result: PENDING** - awaiting re-analysis

## Root Cause Analysis (RESOLVED in Attempt 5)

**The merge WAS happening in `_llm_cross_group_resolution()` - but the confrontation detection wasn't working.**

### Why Previous Attempts Failed
All four previous attempts correctly identified the merge location (`_llm_cross_group_resolution()`) and added confrontation detection (`_entities_in_confrontation()`). However, the detection logic had a fatal flaw:

**The Flaw:** It required BOTH names to appear in the same context snippet (co-occurrence check).

**Why This Failed:**
1. Context windows are small: 150 chars for epithets, 120 chars for proper names
2. Poe's confrontation scene is a single 500+ character sentence
3. With small windows, "seizing the mummer" and "Prince Prospero" appear in DIFFERENT snippets
4. The co-occurrence threshold (`total_cooccurrence >= 2`) was never met
5. Therefore, the confrontation was never detected despite being present in the text

### Attempt 5 Solution
Instead of requiring co-occurrence, the new logic:
1. Counts confrontation patterns in EACH entity's contexts separately
2. Blocks merge if BOTH entities show confrontation patterns (>=2 each)
3. This works because:
   - "the mummer" contexts will contain "seizing", "retreating", "confronted his pursuer"
   - "Prince Prospero" contexts will contain "pursued", "rushed", "bore aloft a drawn dagger"
   - Both showing confrontation patterns = they are separate interacting entities

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json
- Quality Report: output/Masque of the Red Death - Poe_20260119_010013/quality.md
- Per-run directory: output/Masque of the Red Death - Poe_20260119_010013

## Pipeline Notes (Attempt 6)
- Analysis completed successfully in 7m 23s
- 1 character detected: "the Prince Prospero" (alias: "the mummer") ← STILL WRONG
- 1 character profile generated
- 73 pronunciation flags
- Character extraction time: 4m 56s (66.6% of total time)
- Total tokens: 33,419
- 19 LLM calls
- Warning: LLM identity detection failed at end (EOF error - likely model unload issue)

## Attempt 5 Root Cause Analysis (COMPLETED)

### Diagnostic Investigation
1. ✅ Added comprehensive logging to `consensus.py` to trace the merge decision
2. ✅ Read the source text to understand the confrontation context
3. ✅ Analyzed the `_entities_in_confrontation()` function logic

### Root Cause Identified
**Location:** `src/pipeline/character_extraction/consensus.py:_entities_in_confrontation()`

**The Problem:**
The confrontation detection function was looking for co-occurrences where BOTH "the mummer" and "Prince Prospero" appear in the same context snippet. However:

1. **Context windows are too small:** Epithet contexts are 150 chars, proper name contexts are 120 chars
2. **Poe's sentences are very long:** The critical confrontation scene is a single 500+ character sentence
3. **Names appear in separate fragments:** With small context windows, "seizing the mummer" and "Prince Prospero" get extracted into different snippets
4. **Co-occurrence threshold not met:** The function requires `total_cooccurrence >= 2`, but with fragmented contexts, this threshold isn't reached

**Evidence from text (line 30):**
The entire confrontation is ONE LONG SENTENCE containing:
- "Prince Prospero... rushed... bore aloft a drawn dagger"
- "the retreating figure... turned suddenly and confronted his pursuer"
- "fell prostrate in death the Prince Prospero"
- "seizing the mummer, whose tall figure stood erect"

This proves they are separate entities, but a 150-char window only captures fragments like:
- "seizing the mummer, whose tall figure stood erect and motionless within the shadow of the ebony clock" (no mention of Prospero)

### The Fix (Attempt 5)
**Modified:** `src/pipeline/character_extraction/consensus.py:_entities_in_confrontation()`

**Changes:**
1. **Added indirect reference patterns:**
   - `his/her/their (pursuer|opponent|attacker|assailant)`
   - `the (retreating|advancing|approaching) (figure|form|person|intruder|stranger)`

2. **NEW LOGIC:** Solo confrontation pattern detection
   - Count confrontation patterns in epithet contexts independently
   - Count confrontation patterns in proper name contexts independently
   - Block merge if BOTH entities show >= 2 confrontation patterns in their own contexts
   - This works even when long sentences prevent co-occurrence in small context windows

3. **Added diagnostic logging** to track:
   - Classification of names as epithet vs proper name
   - LLM cross-group recommendations
   - Confrontation detection results (co-occurrence, solo patterns)

**Rationale:**
If "the mummer" contexts mention "seizing", "retreating", "confronted", AND "Prince Prospero" contexts mention "pursued", "approached", "rushed", they are clearly separate entities engaged in interaction, even if those words don't appear in the same 150-char snippet.

## Next Action
Run PROMPT_analyze.md to re-run analysis with the enhanced confrontation detection and verify the fix works.
