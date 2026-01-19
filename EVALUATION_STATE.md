# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 20
- **Phase:** awaiting_analysis
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 7/10 ← IMPROVED from 3/10 (attempt 18)
- Character Profiles: 5/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.70/10** (threshold: 8.0)

## Score Delta from Baseline (Attempt 1)
- Structure: 10 -> 10 (unchanged)
- Characters: 5 -> 7 (**+2 improvement** from baseline!)
- Profiles: 2 -> 5 (+3 improvement from baseline)
- Summaries: 9 -> 9 (unchanged)
- Pronunciation: 5 -> 6 (+1 improvement)
- Presentation: 9 -> 8 (-1 regression)
- **Overall: 6.75 -> 7.70 (+0.95 improvement)**

## Attempt 19 Result: SIGNIFICANT IMPROVEMENT ✓

### What Was Tried
Post-processing fix to detect and move misplaced character aliases AFTER consensus completes.

### Result
**SUCCESS** - The Prospero/mummer mismerge is FIXED!
- "the Prince Prospero" now correctly has alias: ["Prospero"]
- "the mummer" now correctly has no aliases (empty list)

The post-processing approach worked where pre-merge approaches (attempts 17-18) failed.

### Score Impact
- Character Extraction: 3/10 → 7/10 (+4 points)
- Overall: 6.70 → 7.70 (+1.0 point)

## Gap to Threshold
Current: 7.70 | Threshold: 8.0 | Gap: **0.30 points**

## Current Issues (Priority Order)

### HIGH
1. **Character Profiles are empty (5/10)**
   - Problem: Both characters have null for appearance, personality, voice_guidance
   - Impact: +0.30 points available if raised to 7/10 (would meet threshold exactly)
   - Evidence from text for Prince Prospero:
     - Personality: "happy and dauntless and sagacious", "bold and fiery"
     - Taste: "eccentric yet august taste"
   - Evidence for the mummer:
     - Appearance: "tall and gaunt, shrouded from head to foot in the habiliments of the grave"
     - Mask: "made so nearly to resemble the countenance of a stiffened corpse"
     - Vesture: "dabbled in blood"
   - Location: `src/agents/characters.py` or profile extraction pipeline
   - Fix: Ensure profile extraction runs and populates these fields

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
   - Problem: Common English words flagged: "dauntless", "chiming", "magnificence", "embellishments", "buffoons"
   - Impact: +0.20 points available if reduced
   - Location: `src/agents/pronunciation.py` or pronunciation pipeline
   - Fix: Add frequency-based filtering to exclude common words

5. **"away" incorrectly flagged as foreign**
   - Problem: Standard English word "away" flagged with note about German "weg"
   - Location: Foreign word detection logic
   - Fix: Improve foreign word detection to not flag common English words

### LOW
6. **Mention count doesn't include aliases**
   - Problem: "the Prince Prospero" shows 3 mentions, but "Prospero" appears 18 times
   - The combined count should be ~21
   - Location: Mention counting logic

7. **Minor summary inaccuracy**
   - Problem: Summary says prince confronts figure "in the blue chamber"
   - Reality: Pursuit starts in blue chamber, Prospero dies in black apartment
   - Impact: Minimal

## Recommended Next Fix (Attempt 20)

### Priority: Character Profiles (quickest path to 8.0)

Raising profiles from 5/10 to 7/10 would add 0.30 points → 8.00 (PASS)

**Investigation needed:**
1. Check why `Character Profiles` stage shows 0.0s duration and 0 LLM calls
2. The profiling data shows the stage ran but did nothing:
   ```json
   "Character Profiles": {
     "duration_seconds": 0.0,
     "llm_calls": 0,
     "items_processed": 0
   }
   ```
3. This suggests profile extraction is being skipped or erroring silently

**Likely fix locations:**
- `src/agents/characters.py` - check if profile population is called
- `src/pipeline/character_extraction/` - check profile extraction logic
- Check if there's a minimum character count threshold preventing profile extraction

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
- **Status:** Fix is working, but not yet at threshold

### Attempt 20 - Adaptive Profile Threshold
- **Change:** Adaptive MIN_MENTIONS_FOR_PROFILE threshold for short texts
- **Files Modified:** `src/analyzer.py` lines 1013-1025
- **Root Cause:**
  - Symptom: Character Profiles empty (appearance/personality/voice_guidance = null)
  - Data flow: Profiles generated by `_generate_character_profile()` → stored in pipeline Character.description
  - Issue location: Line 1036-1039 filters characters by mention count >= 5
  - Problem: Masque characters have only 3 and 4 mentions (short story with 2449 words)
  - Profiles were NEVER GENERATED (0.0s duration, 0 LLM calls) because no characters met threshold
- **Smoke Test:** PASS - Logic change verified, adaptive threshold (2 for texts < 5000 words)
- **Expected Impact:** +0.30 points (Character Profiles 5→7), reaching exactly 8.0 threshold

## Next Action
**Phase:** awaiting_analysis
Re-run analysis to verify profiles are now generated for short story characters.
