# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 21
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.75

## Output Files
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 7/10
- Character Profiles: 6/10 ← IMPROVED from 5/10 (attempt 19)
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.85/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 7 (+2 improvement from baseline)
- Profiles: 2 -> 6 (+4 improvement from baseline)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 7.85 (+1.10 improvement)**

## Gap to Threshold
Current: 7.85 | Threshold: 8.0 | Gap: **0.15 points**

## Attempt 20 Result: PARTIAL SUCCESS ✓

### What Was Tried
Adaptive MIN_MENTIONS_FOR_PROFILE threshold for short texts (threshold of 2 for texts < 5000 words).

### Result
**PARTIAL SUCCESS** - Profile generation stage now runs:
- Duration: 26.65s (was 0.0s)
- LLM calls: 3 (was 0)
- Items processed: 2 (was 0)
- Confidence: 2 high (was 0)

**BUT**: The generated profiles are stored in the `descriptions` array, NOT in the structured `appearance`, `personality`, `voice_guidance` fields which remain null.

### Score Impact
- Character Profiles: 5/10 → 6/10 (+1 point)
- Overall: 7.70 → 7.85 (+0.15 point)

## Current Issues (Priority Order)

### HIGH
1. **Structured profile fields are empty (6/10)**
   - Problem: `appearance`, `personality`, `voice_guidance` are all null for both characters
   - The profile LLM is generating good content, but it's stored in `descriptions` array only
   - Impact: +0.15 points available if raised to 7/10 (would pass threshold)
   - Evidence: The descriptions text contains personality info like "noble figure", "bold and aggressive"
   - Root cause: `_generate_character_profile()` populates `descriptions` but not structured fields
   - Location: `src/analyzer.py` around line 1050-1100 (profile generation and population)
   - Fix: Extract structured data from LLM response OR modify LLM prompt to return structured fields

### MEDIUM
2. **Canonical name format: "the Prince Prospero" should be "Prince Prospero"**
   - Problem: Leading article "the" shouldn't be part of a proper name
   - Impact: Minor usability issue
   - Location: Name normalization in character extraction
   - Fix: Strip leading "the" from proper noun canonical names

3. **Missing alias "the prince" for Prospero**
   - Problem: Text uses "the prince" 6 times to refer to Prospero
   - Impact: Minor completeness issue
   - Location: Alias detection in character extraction

4. **Pronunciation false positives (~35-40%)**
   - Problem: Common English words flagged: "dauntless", "chiming", "magnificence", "buffoons", etc.
   - Impact: +0.10 points available if reduced
   - 73 entries for a 2500-word text is excessive
   - Location: `src/agents/pronunciation.py` or pronunciation pipeline
   - Fix: Add frequency-based filtering to exclude common words

### LOW
5. **Mention count doesn't include aliases**
   - Problem: "the Prince Prospero" shows 3 mentions, but "Prospero" appears 18 times
   - The combined count should be ~21
   - Location: Mention counting logic

## Recommended Next Fix (Attempt 21)

### Priority: Populate Structured Profile Fields (quickest path to 8.0)

The profile generation is now running and producing good content in `descriptions`. The issue is that `appearance`, `personality`, and `voice_guidance` remain null.

**Investigation needed:**
1. Check how `_generate_character_profile()` handles the LLM response
2. The LLM may be returning unstructured text that goes to `descriptions`
3. Need to either:
   a. Modify LLM prompt to return structured JSON with appearance/personality/voice_guidance
   b. Post-process the descriptions text to extract structured fields
   c. Modify the code that populates Character model to also set structured fields

**Expected Impact:** +0.15+ points on Profiles (6→7), reaching 8.0 threshold

## What NOT to Try Again
- Pre-merge substring matching (attempts 17-18) - FAILED
- Prompt-based rules (attempts 3, 14) - ineffective alone
- Context window adjustments (attempts 7-15) - insufficient

## Fix History

### Attempts 1-18
See git history and previous EVALUATION_STATE.md entries.

### Attempt 19 - SUCCESS ✓
- **Change:** POST-PROCESSING cross-character alias fix
- **Files Modified:** `src/agents/characters.py` (added `_fix_misplaced_aliases()` method)
- **Result:** SUCCESS - Prospero alias correctly moved to Prince Prospero
- **Score Impact:** +1.0 overall (6.70 → 7.70)
- **Status:** Fix is working

### Attempt 20 - PARTIAL SUCCESS
- **Change:** Adaptive MIN_MENTIONS_FOR_PROFILE threshold for short texts
- **Files Modified:** `src/analyzer.py` lines 1013-1025
- **Result:** PARTIAL - Profile stage runs (26.65s, 3 LLM calls, 2 items)
- **BUT:** Structured fields (appearance/personality/voice_guidance) still null
- **Score Impact:** +0.15 overall (7.70 → 7.85)
- **Status:** Profile generation works, but output format needs adjustment

### Attempt 21 - ANALYSIS COMPLETE
- **Change:** Populate structured profile fields (appearance, personality, voice_guidance)
- **Files Modified:** `src/analyzer.py` lines 1630-1806
- **Root Cause:** `_generate_character_profile()` was returning profile text which was stored in legacy `descriptions` field, but never populating the structured fields added in F8
- **Fix Details:**
  1. Modified LLM prompt to request structured JSON with appearance/personality/voice_guidance fields
  2. Updated return signature to include structured fields (now returns 6-tuple instead of 3-tuple)
  3. Updated calling code (line 1113) to unpack and store structured fields on character object
  4. Added fallback: if LLM doesn't return structured fields, use secondary LLM call to structure the profile text
- **Smoke Test:** Code runs without errors, all 444 unit tests pass
- **Pipeline Run:** Completed in 8m 37s
  - Character Profiles: 39.4s, 5 LLM calls, 2 items, 2 high confidence
  - Total: 28 LLM calls, 43,037 tokens
- **Status:** Ready for evaluation

## Next Action
**Phase:** awaiting_evaluation
Evaluate the analysis output to verify structured profile fields are now populated correctly.

Expected score improvement: 6/10 → 7/10 on Character Profiles (+0.15 overall → 8.0 total)
