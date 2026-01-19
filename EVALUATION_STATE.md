# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 19
- **Phase:** awaiting_analysis
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 3/10 ← CRITICAL FAILURE (unchanged from attempts 16-17)
- Character Profiles: 5/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 3 (**-2 REGRESSION** from attempt 1)
- Profiles: 2 -> 5 (+3 improvement from baseline)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 6.70 (-0.05 slight regression)**

## Attempt 18 Result: FAILED

### What Was Tried
Allow substring matches to bypass ambiguous last name validation check in `_validate_merge()` (src/pipeline/character_extraction/consensus.py:1684-1700).

### Result
**FAILED** - The Prospero/mummer mismerge PERSISTS. The substring fix did NOT work.

### Root Cause Analysis (Attempt 18)

The fix added substring detection to the ambiguous last name validation check. However, the issue still occurs. This means one of the following:

1. **The pre-merge phase isn't being reached** - The names list may not include both "Prospero" and "the Prince Prospero" at the time the pre-merge loop runs

2. **A different validation check is rejecting the merge** - There may be another validation rule in `_validate_merge()` that rejects the Prospero/Prince Prospero pair BEFORE or AFTER the last name check

3. **The LLM is still deciding the merge** - Despite the pre-merge attempt, the actual pairing may still go to the LLM which incorrectly pairs Prospero with the mummer

4. **Execution order issue** - The "Prospero" + "the mummer" merge may be happening through a different code path that bypasses the pre-merge phase entirely

### Evidence from Output
```json
{
  "canonical_name": "the mummer",
  "aliases": ["Prospero"]
}
```

This shows "Prospero" was merged with "the mummer" - the SAME incorrect result as before.

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: "Prospero" merged with "the mummer" instead of "Prince Prospero"**
   - Problem: "Prospero" (short for Prince Prospero) is incorrectly listed as an alias of "the mummer" (the Red Death)
   - Evidence: The text clearly shows Prince Prospero is KILLED BY the mummer: "fell prostrate in death the Prince Prospero"
   - Root Cause: **UNKNOWN** - Two attempts at pre-merge substring matching have failed
   - **18 ATTEMPTS AND COUNTING** - This is a persistent, blocking issue

### HIGH
2. **Only 2 characters detected for a story with a named protagonist and supernatural antagonist**
   - Prince Prospero (protagonist) should be clearly identified with proper aliases
   - The Red Death/mummer (antagonist) should be clearly identified
   - These MUST be SEPARATE characters

3. **"the Prince Prospero" has ZERO aliases**
   - Should have: "Prospero", "the prince"
   - This is a canonical name issue - the text uses "Prospero" 18 times, "Prince Prospero" 3 times

### MEDIUM
4. **Empty character profiles**
   - Both characters have null for appearance, personality, voice_guidance
   - Should have basic descriptions from the text

5. **Canonical name format: "the Prince Prospero" should be "Prince Prospero"**
   - Leading article "the" should be stripped for proper nouns

6. **Pronunciation false positives (~35-40%)**
   - Common English words flagged: "dauntless", "chiming", "magnificence"

## Recommended Next Approach (Attempt 19)

### CRITICAL: Different Strategy Needed

The pre-merge substring approach has FAILED TWICE (attempts 17-18). Need a fundamentally different approach.

### Option A: Debug the actual merge decision flow
Add extensive logging to understand EXACTLY where and how "Prospero" is being merged with "the mummer":
1. Log all candidate pairs generated
2. Log which pairs pass validation
3. Log which pairs go to LLM
4. Log LLM decisions
5. Log final merge results

### Option B: Post-process to fix the mismerge
Instead of preventing the wrong merge, detect and fix it after the fact:
1. After consensus completes, check for character pairs where:
   - One name contains "the" + another character's base name
   - E.g., "the mummer" has alias "Prospero" but "the Prince Prospero" exists
2. Move "Prospero" from mummer's aliases to Prince Prospero's aliases

### Option C: Name normalization before consensus
Before running consensus, normalize names:
1. "Prospero" -> link to "Prince Prospero" explicitly
2. Create a canonical name mapping before the merge process

### Recommendation: Option B
Post-processing is lower risk and directly addresses the symptom. The pre-merge approach keeps failing, likely due to execution order or code path issues that are hard to debug.

## What NOT to Try Again
- Pre-merge substring matching (attempts 17-18) - FAILED TWICE
- Substring validation bypass (attempt 18) - FAILED
- Prompt-based rules (attempts 3, 14 ineffective)
- Post-processing splits without proper context (attempts 15-16)
- Context window adjustments (attempts 7-15 proved insufficient)

## Fix History

### Attempts 1-16
See git history and previous EVALUATION_STATE.md entries.

### Attempt 17
- **Change:** PRE-MERGE substring matching before LLM evaluation
- **Files Modified:** src/pipeline/character_extraction/consensus.py (lines 1055-1094)
- **Result:** FAILED - Substring check wasn't triggering

### Attempt 18
- **Change:** Allow substring matches to bypass ambiguous last name validation
- **Files Modified:** src/pipeline/character_extraction/consensus.py (lines 1684-1700)
- **Result:** FAILED - Same incorrect merge persists
- **Full Test Suite:** PASSED (444 tests)
- **Conclusion:** The fix logic is in place but isn't being used in the actual merge flow

### Attempt 19
- **Change:** POST-PROCESSING cross-character alias fix - detect and move misplaced aliases AFTER consensus
- **Files Modified:** src/agents/characters.py (added `_fix_misplaced_aliases()` method at line 487-575, called at line 145)
- **Root Cause:**
  - **Symptom:** "Prospero" listed as alias of "the mummer" (line 52-54 in analysis.json)
  - **Data flow:** analysis.json ← AnalysisResult ← CharacterAgent.run() ← consensus.py
  - **Originates in:** LLM merge decision in consensus phase incorrectly pairs "Prospero" with "the mummer" instead of "Prince Prospero"
  - **Confidence:** HIGH
- **Approach:** Instead of preventing the wrong merge (attempts 17-18 failed), detect and fix it AFTER consensus:
  1. For each character with aliases
  2. Check if any alias is a substring or word match of another character's canonical name
  3. Move the alias to the better-matching character
  4. Example: "Prospero" is substring of "the Prince Prospero", so move it from "the mummer"
- **Smoke Test:** PASS - Test script verified:
  - ✓ "Prospero" moved from "the mummer" to "the Prince Prospero"
  - ✓ Metadata tracked the move (post_processing_alias_moves: 1)
- **Full Test Suite:** PASSED (444 tests, 11 skipped, 1 warning)
- **Next:** Re-run analysis to verify fix works on actual masque_of_red_death text

## Evaluation Details

### 2.1 Structure Detection (Weight: 20%)

**Score: 10/10**

"The Masque of the Red Death" is a short story. Correctly identified as a single chapter.

### 2.2 Character Extraction (Weight: 25%)

**Score: 3/10** - CRITICAL FAILURE

**Output:**
1. "the Prince Prospero" - 3 mentions, NO aliases
2. "the mummer" - 4 mentions, aliases: ["Prospero"]

**Expected for "The Masque of the Red Death":**
- Prince Prospero (protagonist) - aliases: "Prospero", "the prince"
- The Red Death / The Mummer (antagonist) - aliases: "the figure", "the masked figure", "the stranger", "the intruder"

**Critical Error:** "Prospero" merged with "the mummer" instead of "Prince Prospero". These are ANTAGONIST and PROTAGONIST - fundamentally different characters!

### 2.3 Character Profiles (Weight: 15%)

**Score: 5/10**

- Both characters have null appearance, personality, voice_guidance
- No useful profile information for narration
- The summary contains character details not extracted to profiles

### 2.4 Chapter Summaries (Weight: 20%)

**Score: 9/10**

Excellent summary capturing:
- The Red Death plague setting
- Prince Prospero's retreat with courtiers
- The seven colored rooms
- The ebony clock's hourly effect
- The mysterious figure's midnight appearance
- Prospero's pursuit and confrontation
- The revelation of the empty costume
- The final deaths

### 2.5 Pronunciation Guide (Weight: 10%)

**Score: 6/10**

**Good catches:**
- "Prospero" (Italian name)
- "improvisatori" (Italian term)
- "candelabrum" (Latin)
- "Hernani" (literary reference)
- "arabesque" (French)
- "habiliments", "cerements" (archaic English)

**False positives (~35-40%):**
- "dauntless" - common English
- "chiming" - common English
- "magnificence" - common English
- "evolutions" - common English
- "girdled", "massy" - less common but standard English

**Homographs correctly identified:**
- "live" (verb vs adjective)
- "close" (near vs shut)
- "produce" (noun vs verb)
- "deliberate" (adjective vs verb)

### 2.6 HTML Presentation (Weight: 10%)

**Score: 8/10**

- Navigation works
- Tab-based interface functional
- Character profiles section present
- Pronunciation guide organized well
- Print styles included
- Shows "0 Main Characters" which is technically correct (both are "Supporting")

## Overall Score Calculation

```
Overall = (
    10 × 0.20 +   # Structure: 2.00
    3 × 0.25 +    # Characters: 0.75
    5 × 0.15 +    # Profiles: 0.75
    9 × 0.20 +    # Summaries: 1.80
    6 × 0.10 +    # Pronunciation: 0.60
    8 × 0.10      # Presentation: 0.80
) = 6.70/10
```

**Overall: 6.70/10** (threshold: 8.0) - **FAIL**

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Next Action
Run PROMPT_fix.md with Option B: Post-process to detect and fix the Prospero/mummer mismerge after consensus completes
