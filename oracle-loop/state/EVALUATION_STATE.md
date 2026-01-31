# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 16:07 (attempt 5 analysis complete)

## Latest Scores (Attempt 5)
- Structure Detection: 7/10 ✗ (FAILING - 25/28 titles null, Letter 1 missing)
- Character Extraction: 7.5/10 ✗ (FAILING - Creature extracted but undercounted, Walton narrator REGRESSED)
- Character Profiles: 6.5/10 ✗ (FAILING - ALL physical_description null, relationships good)
- Chapter Summaries: 9.5/10 ✓ (excellent quality, factually accurate)
- Pronunciation Guide: 9/10 ✓ (436/457 have IPA, good coverage)
- HTML Presentation: 8.5/10 ✓ (navigation works, character list complete)
- **Overall: 7.67/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Improved in Attempt 5

| Category | Attempt 4 | Attempt 5 | Change |
|----------|-----------|-----------|--------|
| Structure | 7.0 | 7.0 | - (unchanged) |
| Characters | 7.0 | 7.5 | +0.5 (Creature now extracted!) |
| Profiles | 7.5 | 6.5 | -1.0 (REGRESSION - all descriptions now null) |
| Summaries | 9.5 | 9.5 | - |
| Pronunciation | 9.0 | 9.0 | - |
| Presentation | 8.5 | 8.5 | - |
| **Overall** | 7.88 | 7.67 | -0.21 (profile regression) |

### Key Progress:
1. ✅ **The Creature IS NOW EXTRACTED** - Appears via `split_the_creature` ID
2. ✅ **The Creature marked as narrator** - `is_narrator: true` (correct for nested narrative)
3. ✅ **Victor Frankenstein confirmed in main_cast** with 55 mentions

### Key Regressions:
1. ❌ **Robert Walton no longer marked as narrator** - Was fixed in attempt 4, now `is_narrator: false`
2. ❌ **ALL physical_description fields are null** - Profile generation appears broken

## Current Issues (Priority Order)

### CRITICAL

1. **Robert Walton narrator status REGRESSED**
   - Problem: Walton (`supporting_4`) now has `is_narrator: false`
   - Attempt 4 status: Was `is_narrator: true` after Step 5.0.5 fix
   - Evidence: Walton narrates the frame narrative (Letters 1-4 and conclusion)
   - Impact: Character Extraction cannot reach 8.0 without correct narrator identification
   - Location: The Step 5.0.5 re-run logic in `src/agents/characters.py` (lines 470-523) may not be executing
   - Fix: Verify Step 5.0.5 is running and finding Walton in combined_cast

2. **ALL physical_description fields are null**
   - Problem: 0/27 characters have `physical_description` populated
   - Evidence: `jq '.characters | map(.physical_description) | unique'` returns `[null]`
   - Critical examples:
     - The Creature has one of literature's most detailed descriptions (yellow skin, watery eyes, black lips, 8ft tall)
     - Victor's deteriorating health is described throughout the novel
   - Impact: Character Profiles score dropped from 7.5 → 6.5, cannot reach 8.0
   - Location: Character profiling pipeline - likely `src/pipeline/character_profiling/`
   - Fix: Investigate why appearance extraction is returning null for ALL characters

### HIGH

3. **The Creature only has 5 mentions, should have 40+**
   - Problem: `split_the_creature` has `mention_count: 5` with no aliases
   - Evidence: The Creature is referred to as "the creature", "the monster", "the daemon", "the fiend", "the wretch" throughout
   - Expected aliases: `["the monster", "the daemon", "the fiend", "the wretch", "my creature"]`
   - ID pattern: `split_*` - created by semantic conflict split from Step 3.8
   - Location: Semantic split logic may not be grounding mentions properly
   - Impact: The Creature is the deuteragonist - undercounted by 90%
   - Fix: After semantic split, run grounding for the split-off character

4. **Alphonse Frankenstein fragmented into two entries**
   - Problem: Two separate F6 reconciliation entries:
     - "Alphonse Frankenstein" (cf652e4d2e68, 1 mention)
     - "The narrator's father" (4542ed769e00, 1 mention)
   - Evidence: Same person - Victor's father is Alphonse Frankenstein
   - ID patterns: Both 12-char hashes → F6 reconciliation (analyzer.py:1220-1240)
   - Location: F6 reconciliation should merge relationship-based references with named characters
   - Impact: Minor but affects character completeness

### MEDIUM

5. **Structure titles still mostly null**
   - Problem: Only 3/28 structure elements have titles (Letters 2-4)
   - Missing: Letter 1, Chapter I through Chapter XXIV
   - Evidence: First 4 entries have titles `[null, "Letter 2", "Letter 3", "Letter 4"]`
   - Impact: Navigation and chapter reference usability reduced
   - Location: Structure detection pipeline (`src/pipeline/chapter_detection/proposers/llm.py`)
   - Fix: Title extraction needs to capture "Letter 1" and "Chapter I" through "Chapter XXIV"

6. **Generic group still extracted as character**
   - Problem: "the court officials" (d7065e27fa05, 1 mention) in character list
   - Evidence: This is a generic reference, not a named character
   - ID pattern: F6 reconciliation hash ID
   - Location: F6 reconciliation or summary character list
   - Fix: Filter generic group references from character reconciliation

### LOW

7. **Walton missing "Robert Walton" alias**
   - Problem: Walton (supporting_4) has no aliases, should have "Robert Walton", "Captain Walton"
   - Impact: Minor - character is extracted
   - Fix: Alias resolution for supporting cast

## Fix History

### Attempt 5 (2026-01-31) - PARTIAL SUCCESS
1. ✓ **The Creature now extracted** via semantic split (`split_the_creature`)
2. ✓ **The Creature marked as narrator** - correct for nested narrative
3. ✗ **Walton narrator status REGRESSED** - Step 5.0.5 not working as expected
4. ✗ **Profile generation BROKEN** - all physical_description null

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
| 4 | Walton narrator in supporting_cast | characters.py | FIXED (Walton now narrator) |
| 5 | Creature extraction via characters_present | characters.py, main_cast.py | Creature EXTRACTED, Walton REGRESSED, Profiles BROKEN |

**Pattern:** Attempt 5 changes to characters.py appear to have broken profile generation and regressed Walton narrator detection. The changes may have unintended side effects.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive consensus: ENABLED (single-model mode, 3 temperatures)
- Total LLM calls: 620
- Total tokens: 636,570
- Processing time: 152m 13s

## Next Action

**Phase:** awaiting_analysis

**External Changes Detected:**
The following files have been modified outside the oracle loop:
- `src/agents/characters.py`
- `src/models.py`
- `src/pipeline/character_extraction_v2/main_cast.py`
- `tests/test_character_extraction_v2.py`

**Action Required:** Re-run analysis to test external changes before applying additional fixes.

**Reason:** External changes may have already addressed some or all of the issues identified in attempt 5. Must verify current behavior before making additional modifications.

---

## Issues to Re-Check After Analysis

**Priority 1 (CRITICAL):** Walton narrator regression
- Investigate why Step 5.0.5 is no longer detecting Walton as narrator
- The logic from attempt 4 was working - something in attempt 5/6 changes broke it

**Priority 2 (CRITICAL):** physical_description null for all characters
- Profile generation is completely broken
- This is a major regression from attempt 4 (which had some profiles)
- Investigate character profiling pipeline

**Priority 3 (HIGH):** The Creature's mention count and aliases
- After semantic split, run grounding to find all mentions
- Add alias detection for common noun references (daemon, fiend, wretch)
