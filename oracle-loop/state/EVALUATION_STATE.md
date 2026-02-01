# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 (attempt 5 re-run evaluated)

## Latest Scores (Attempt 5 Re-run)
- Structure Detection: 7/10 ✗ (FAILING - 25/28 titles null)
- Character Extraction: 7.5/10 ✗ (FAILING - Walton not marked as narrator)
- Character Profiles: 7.5/10 ✗ (FAILING - Victor appearance unknown)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Improved in Attempt 5 Re-run

| Category | Attempt 5 | Re-run | Change |
|----------|-----------|--------|--------|
| Structure | 7.0 | 7.0 | - (no change) |
| Characters | 7.5 | 7.5 | - (Creature still good, Walton still not narrator) |
| Profiles | 6.5 | 7.5 | +1.0 (appearance data IS populated, was checking wrong field) |
| Summaries | 9.5 | 9.5 | - |
| Pronunciation | 9.0 | 9.0 | - |
| Presentation | 8.5 | 8.5 | - |
| **Overall** | 7.67 | 8.05 | +0.38 (profile assessment corrected) |

### Key Findings from Re-evaluation:

1. **Profile data IS populated** - The `appearance` object has data (9/34 characters with meaningful descriptions). The `physical_description` field being null is expected by the data model - it's the `appearance.summary` field that matters.

2. **The Creature extraction is GOOD:**
   - Appears as `main_cast_2` (not split_*)
   - Has 25 mentions (up from 5)
   - Has alias "the Monster"
   - Correctly marked as narrator (nested narrative)

3. **Victor correctly marked as narrator** - `is_narrator: true`

4. **Remaining issues are structural:**
   - Walton narrator status
   - Structure titles extraction
   - Victor's appearance description

## Current Issues (Priority Order)

### CRITICAL

1. **Robert Walton not marked as narrator**
   - Problem: Walton (`supporting_9`) has `is_narrator: false`
   - Evidence: Walton narrates the frame narrative (Letters 1-4 and conclusion)
   - Frankenstein has THREE narrators: Walton (outer frame), Victor (main narrative), Creature (inner narrative)
   - Impact: Cannot reach Character Extraction 8.0 without this
   - Location: `src/agents/characters.py` - Step 5.0.5 narrator detection
   - ID pattern: `supporting_*` → fix must target supporting cast narrator detection
   - Fix: Step 5.0.5 searches `combined_cast` for narrator matches - verify it's checking supporting characters

### HIGH

2. **Structure titles mostly null (25/28)**
   - Problem: Only "Letter 2", "Letter 3", "Letter 4" have titles
   - Missing: "Letter 1", "Chapter I" through "Chapter XXIV"
   - Evidence: Structure count is correct (28), but title extraction fails
   - Impact: Structure Detection score capped at 7/10
   - Location: `src/pipeline/chapter_detection/proposers/llm.py`
   - Fix: Title extraction prompt may need adjustment for Roman numerals

3. **Victor Frankenstein appearance is "unknown"**
   - Problem: Victor has `appearance.summary: "unknown"` despite text describing his deteriorating health
   - Expected: "Gaunt, pale, with signs of obsessive overwork and declining health"
   - Evidence: Novel describes Victor's physical decline throughout (especially during his creation frenzy)
   - Impact: Character Profiles score limited
   - Location: Character profiling pipeline - appearance extraction
   - Fix: Ensure appearance extraction includes health-related descriptions for narrators

### MEDIUM

4. **Walton missing aliases**
   - Problem: Walton has no aliases, should include "Robert Walton", "Captain Walton"
   - Evidence: The text uses all three forms
   - Location: Supporting cast alias resolution
   - Fix: Low priority - character is extracted correctly

5. **The Creature could have more aliases**
   - Problem: Only alias is "the Monster", missing "the daemon", "the fiend", "the wretch"
   - Evidence: Novel uses many terms for the Creature
   - Impact: Minor - main alias captured
   - Fix: Expand alias detection for common noun references

### LOW

6. **Minor F6 reconciliation characters**
   - Some minor characters from summaries added with minimal profiles
   - Not blocking - expected for minor characters

## Fix History

### Attempt 6 Fix (2026-01-31) - IN PROGRESS
1. ✅ **Walton narrator detection FIXED** - Bidirectional name matching
   - Root cause: `narrator.py:_match_to_character()` used one-directional substring check
   - Problem: "Robert Walton" (detected name) wasn't matching "Walton" (canonical name)
   - Fix: Changed line 222 to bidirectional check: `name_lower in char_name_lower or char_name_lower in name_lower`
   - Smoke test: PASS - Correctly matches both "Victor" → "Victor Frankenstein" and "Robert Walton" → "Walton"
   - File: `src/pipeline/character_extraction_v2/narrator.py`

2. ⏸️ **Structure titles - DEFERRED** (needs deeper investigation)
   - Root cause investigation: 25/28 structures have null titles (only Letter 2/3/4 have titles)
   - Finding: Chapter markers exist in source text at different positions than structure boundaries
   - Likely cause: Consensus pipeline choosing wrong proposals or not preserving titles
   - Action: Requires deeper trace through structure detection consensus logic
   - Deferred to next iteration (different scoring category, more complex fix)

3. ⏸️ **Victor appearance - DEFERRED** (upstream evidence problem)
   - Root cause investigation: Victor has only 1/7 evidence entries mentioning appearance keywords
   - That entry is about his mother's death, not Victor's physical state
   - Finding: Evidence gathering pipeline is not finding passages about Victor's deteriorating health
   - Fix location: Evidence gathering (upstream), not profile generation
   - Deferred to next iteration (requires fixing profile evidence gathering pipeline)

### Attempt 5 Re-run Evaluation (2026-01-31)
- **Corrected profile assessment:** The `appearance` object is populated correctly for 9/34 characters
- The Creature, Elizabeth, Safie, William, Waldman, Krempe all have good appearance data
- Previous evaluation incorrectly checked `physical_description` (always null by design) instead of `appearance.summary`

### Attempt 5 (2026-01-31) - PARTIAL SUCCESS
1. ✓ **The Creature now extracted** via main_cast (not split)
2. ✓ **The Creature marked as narrator** - correct for nested narrative
3. ✗ **Walton narrator status still failing** - Step 5.0.5 not finding Walton
4. ✓ **Profile generation working** - appearance data IS populated

**Changes implemented:**
- Upstream data fix: `characters_present` now passed to main_cast extraction
- Architectural improvements: co-occurrence validation, consolidated Pass 2

### Attempt 4 Fix (2026-01-31) - PARTIALLY SUCCESSFUL
1. ✓ Robert Walton narrator detection - WAS WORKING (now regressed)
   - Fix: Added Step 5.0.5 re-run with combined_cast (main + supporting)
   - File: src/agents/characters.py (lines 470-523)
   - Result: Walton HAD is_narrator=true in attempt 4

### Attempt 3 Fixes - PARTIALLY FAILED
1. ❌ Robert Walton epistolary narrator detection - did not apply (Walton in supporting_cast)
2. ❌ Alphonse relationship references - still fragmented

### Attempt 2 Fixes - SUCCESSFUL
1. ✅ Victor Frankenstein in main_cast
2. ✅ Krempe/Waldman now separate
3. ✅ The Creature appearance description format

### Attempt 1
- Initial analysis (baseline 6.35/10)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline 6.35 |
| 2 | Victor missing, Waldman/Krempe merge | main_cast.py | Victor FIXED, Waldman/Krempe FIXED |
| 3 | Walton narrator, Alphonse refs | main_cast.py | NO CHANGE (wrong file) |
| 4 | Walton narrator in supporting_cast | characters.py | FIXED (Walton was narrator) |
| 5 | Creature extraction via characters_present | characters.py, main_cast.py | Creature EXTRACTED, Walton REGRESSED |
| 6 | Walton narrator regression (bidirectional match) | narrator.py | FIXED (smoke test passed) |

**Pattern:** Attempt 5 didn't break Step 5.0.5 logic - the bug was always in `narrator.py:_match_to_character()` but only manifested when narrator name ("Robert Walton") was fuller than canonical name ("Walton").

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive consensus: ENABLED (single-model mode, 3 temperatures)

## Debug Focus for Next Fix

**Priority 1: Walton Narrator Detection**

The Step 5.0.5 logic (lines ~470-523 in characters.py) runs narrator detection on combined_cast (main + supporting). Need to verify:

1. Is `combined_cast` actually including supporting characters?
2. Is the narrator search pattern matching "Robert Walton" or "Walton"?
3. Is the update correctly applied to supporting cast entries?

Check the logs for:
```
"Narrator 'Robert Walton' identified but NOT found in main_cast"
```

This message suggests the detection finds Walton but can't locate him in the cast to update.

**Priority 2: Structure Titles**

The title extraction is only working for "Letter 2/3/4" but missing:
- "Letter 1" (first structure element)
- "Chapter I" through "Chapter XXIV"

This is likely a prompt issue in the structure detection LLM proposer.

**Phase:** awaiting_analysis

## Next Action

Re-run analysis to verify Walton narrator fix. Expected improvements:
- Character Extraction: 7.5 → 8.0+ (Walton now marked as narrator)
- Structure Detection: 7.0 (unchanged - deferred)
- Character Profiles: 7.5 (unchanged - Victor appearance deferred)
