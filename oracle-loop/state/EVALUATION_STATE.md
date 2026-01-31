# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Last modified: 2026-01-30 19:14:52 (verified AFTER fix commit)

## Pipeline Notes
- Competitive consensus enabled (single model, 3 temperatures)
- Competitive stages: characters, structure, summaries (via --competitive-all)
- Model: qwen3-next:80b-a3b-instruct-q8_0
- Analysis completed successfully with Wolfsheim fuzzy merge fix applied
- Output files regenerated and verified with correct timestamps

## Latest Scores (Attempt 4 - FRESH EVALUATION)

- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Detailed Score Justification

### Structure Detection: 10/10 ✓
- 9 chapters detected (I through IX) - matches expected count exactly
- All chapter boundaries correct
- Roman numeral titles handled properly
- No merged or split chapters

### Character Extraction: 8/10 ✓ (IMPROVED from 7/10)
**Major improvement:** Wolfsheim fix WORKED!
- main_cast_7 "Meyer Wolfsheim" now has aliases: `["Meyer Wolfshiem", "Wolfshiem"]`
- Both spelling variants successfully merged

**All major characters present:**
- Nick Carraway (narrator ✓), James Gatz/Jay Gatsby (271 mentions), Daisy Buchanan, Tom Buchanan
- Jordan Baker, Myrtle Wilson, George Wilson, Meyer Wolfsheim
- Henry C. Gatz (now with full name and aliases - improved from just "Gatz")

**Alias handling improved:**
- James Gatz correctly has aliases: `["Jay Gatsby", "Gatsby", "the host", "Gatsby of West Egg"]`
- Henry C. Gatz has aliases: `["Mr. Gatz", "Gatsby's father", "Gatz"]`

**Remaining minor issues (not blocking):**
- "Town Tattle" (supporting_9) is a publication, not a character - false positive but minor
- "Doctor T. J. Eckleburg" (main_cast_9) extracted as character - ACCEPTABLE per rubric (symbolic presence with narrative significance)
- "The man with owl-eyed glasses" could use "Owl Eyes" nickname but text may not use that term

### Character Profiles: 7.5/10 ✗ (FAILING)

**Major gap: Physical appearance data sparse**
- Only 6/38 characters have non-"unknown" appearance data
- Characters with appearance: Tom Buchanan, Henry C. Gatz, Catherine, Mr. McKee, Dan Cody, Miss Baedeker
- Missing appearances for MAJOR characters: Nick, Gatsby, Daisy, Jordan

**What's working well:**
- 28/38 characters have relationship data
- Personality profiles present (e.g., Nick: "observant, reserved, diplomatic")
- Voice guidance present with example quotes
- Temperament data present

**Why this is 7.5 instead of 8:**
- Appearance is a key component of character profiles for narrators
- Major characters like Gatsby and Daisy have "unknown" appearance despite having textual descriptions
- The text describes Gatsby ("an elegant young rough-neck") and Daisy ("a face... bright eyes and a bright passionate mouth")

### Chapter Summaries: 9.5/10 ✓
- All 9 chapters have summaries
- Verified sample summaries are accurate:
  - Chapter I: Nick's father's advice, moving to West Egg ✓
  - Chapter II: Valley of Ashes, Doctor T. J. Eckleburg reference ✓
  - Chapter III: Gatsby's lavish party ✓
- Key events captured with appropriate detail
- Narrator-useful tone information present

### Pronunciation Guide: 9/10 ✓ (IMPROVED from 8.5)
- 405 entries with 386 having IPA (95% coverage)
- Wolfsheim/Wolfshiem correctly handled with IPA `/ˈwʊlfʃiːm/`
- Detailed notes provided (e.g., "Pronounce 'Wolf' as in the animal")
- Foreign terms and unusual names properly flagged
- Context examples included for each entry

### HTML Presentation: 9/10 ✓
- Clean tabbed navigation (Chapters, Characters, Pronunciation)
- Character profiles well-organized with expandable evidence sections
- Confidence badges displayed
- Relationships shown as tags
- Voice guidance section formatted with example quotes

## Current Issues (Priority Order)

### HIGH

1. **Physical appearance data missing for major characters**
   - Problem: 32/38 characters have `appearance.summary: "unknown"` including Gatsby, Nick, Daisy, Jordan
   - Evidence: The text contains physical descriptions (e.g., Tom is described as "a sturdy straw-haired man of thirty")
   - Location: `src/pipeline/character_profiling/` - appearance extraction
   - ID patterns: Affects main_cast_* characters
   - Fix: Improve appearance extraction prompts to find physical descriptions from text evidence

### MEDIUM

2. **False positive: "Town Tattle" extracted as character**
   - Problem: Publication listed as character (supporting_9, 3 mentions)
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Prompt clarification to exclude publications/media titles

3. **Canonical name ordering for Gatsby**
   - Problem: supporting_11 uses "James Gatz" as canonical name with "Jay Gatsby" as alias
   - Impact: Minor - narrators more likely to recognize "Jay Gatsby" as primary name
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or cross-pipeline merge logic
   - Note: Functionally correct (aliases work), but "Jay Gatsby" would be more narrator-friendly

## Fix History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed |
| 2 | Main cast extraction failure | src/pipeline/character_extraction_v2/main_cast.py | Diagnostic logging |
| 3 | JSON format for qwen3-next | src/pipeline/character_extraction_v2/main_cast.py | Wrapped object prompts - MAJOR IMPROVEMENT (+1.15) |
| 4 | Wolfsheim/Wolfshiem spelling variants | src/agents/characters.py:2419-2445 | **VERIFIED FIXED** - both variants now merged |
| 5 | Missing physical appearance data | src/analyzer.py:2608-2645 | Improved mention sampling: first 3 mentions (was 1), 800-char context (was 400), 12 samples (was 10) |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |
| 2 | 7.35 | 0.00 | First scoreable run - character fragmentation + missing profiles |
| 3 | 8.5 | +1.15 | Character consolidation fixed, 2 categories still below 8.0 |
| 4 | 8.6 | +1.25 | Character Extraction now passes (8/10), only Profiles failing |

## Configuration Notes

Model: qwen3-next:80b-a3b-instruct-q8_0 (user-specified, DO NOT CHANGE)
Competitive Mode: single
Output files: Verified fresh - last modified 2026-01-30 19:14:52

## Next Action

Re-run analysis to verify fix for Character Profiles appearance extraction.

**Fix Applied (Attempt 5):**
- **Root cause:** Profile generator sampled only 1 early mention + 9 distributed mentions. Physical descriptions often appear at first in-person meeting (not first name mention), so they were frequently missed.
- **Change:** Now samples first **3 mentions** (captures introduction scenes), uses **800-char context windows** (was 400), and samples **12 total** (was 10).
- **Smoke test:** ✅ PASSED - Verified first 3 mentions included, larger context windows working.
- **Expected impact:** Profiles should increase from 7.5 → 8.0+ as physical descriptions from character introduction scenes are now captured.
