# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 22:40 (attempt 6 complete)

## Latest Scores (Attempt 6)
- Structure Detection: 7/10 ✗ (FAILING - 25/28 titles still null)
- Character Extraction: 5/10 ✗ (FAILING - CRITICAL REGRESSION)
- Character Profiles: 7.5/10 ✗ (FAILING - Victor appearance unknown)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold, with CRITICAL REGRESSION)

## ⚠️ CRITICAL REGRESSION IN ATTEMPT 6

**Character Extraction dropped from 7.5/10 to 5/10** - This is a critical failure:

1. **"the Creature" incorrectly merged into "the magistrate" as an alias**
   - `main_cast_20` ("the magistrate") now has alias `["the Creature"]`
   - This is COMPLETELY WRONG - the Creature is the novel's antagonist/monster
   - The magistrate is a minor government official who appears only in chapters 21-22

2. **The Creature/Monster extraction is fragmented and reduced**
   - Attempt 5: "the Creature" (main_cast_2) with 25 mentions, is_narrator=true
   - Attempt 6: "the Monster" (843d532715f2, F6 hash ID) with only 7 mentions
   - The Creature has been effectively erased from the main character list

3. **"the magistrate" incorrectly marked as narrator**
   - `is_narrator: true` for the magistrate is WRONG
   - The magistrate is not a narrator - he's a minor official
   - This likely happened because the Creature (actual narrator) was merged into him

4. **Walton STILL not marked as narrator** (the fix we applied didn't work)
   - `supporting_8` ("Walton") has `is_narrator: false`
   - Walton narrates the frame narrative (Letters 1-4 and conclusion)

## Score Comparison: Attempt 5 vs Attempt 6

| Category | Attempt 5 | Attempt 6 | Change |
|----------|-----------|-----------|--------|
| Structure | 7.0 | 7.0 | - (no change) |
| Characters | 7.5 | **5.0** | **-2.5 REGRESSION** |
| Profiles | 7.5 | 7.5 | - |
| Summaries | 9.5 | 9.5 | - |
| Pronunciation | 9.0 | 9.0 | - |
| Presentation | 8.5 | 8.5 | - |
| **Overall** | 8.05 | **7.23** | **-0.82 REGRESSION** |

## Current Issues (Priority Order)

### CRITICAL

1. **The Creature incorrectly merged into "the magistrate"**
   - Problem: `main_cast_20` ("the magistrate") has alias `["the Creature"]`
   - Evidence: The Creature is Victor's creation, the novel's antagonist. The magistrate is a minor judicial official.
   - Impact: Character Extraction score dropped from 7.5 to 5.0
   - ID pattern: `main_cast_*` → The merge happened in main_cast extraction/alias resolution
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - alias resolution logic
   - Root cause: Possibly the consolidated Pass 2 alias resolution incorrectly merged "the Creature" → "the magistrate"
   - Fix: The Creature must be its own character, not an alias of the magistrate

2. **"the magistrate" incorrectly marked as narrator**
   - Problem: `is_narrator: true` for main_cast_20
   - Evidence: The magistrate appears only in chapters 21-22 as a judicial authority, never narrates
   - Impact: Contaminates narrator detection results
   - Location: `src/pipeline/character_extraction_v2/narrator.py`
   - Root cause: Because "the Creature" was merged as alias, narrator detection matched wrong character
   - Fix: Will be fixed when Creature merge is undone

3. **Walton still not marked as narrator**
   - Problem: `supporting_8` ("Walton") has `is_narrator: false`
   - Evidence: Walton narrates Letters 1-4 and the conclusion (frame narrative)
   - The bidirectional fix in `narrator.py:_match_to_character()` may not have been triggered
   - Location: `src/pipeline/character_extraction_v2/narrator.py`
   - **Smoke test passed but production failed** - need to investigate why
   - Fix: Debug why narrator detection isn't finding Walton in production runs

### HIGH

4. **Structure titles mostly null (25/28)**
   - Problem: Only "Letter 2", "Letter 3", "Letter 4" have titles
   - Missing: "Letter 1", "Chapter I" through "Chapter XXIV"
   - Evidence: Structure count is correct (28), but title extraction fails
   - Impact: Structure Detection score capped at 7/10
   - Location: `src/pipeline/chapter_detection/proposers/llm.py`
   - Fix: Title extraction prompt may need adjustment for Roman numerals

5. **Victor Frankenstein appearance is "unknown"**
   - Problem: Victor has `appearance.summary: "unknown"` despite text describing his deteriorating health
   - Expected: "Gaunt, pale, with signs of obsessive overwork and declining health"
   - Evidence: Novel describes Victor's physical decline throughout (especially during creation)
   - Impact: Character Profiles score limited
   - Location: Character profiling pipeline - appearance extraction
   - Fix: Ensure appearance extraction includes health-related descriptions for narrators

### MEDIUM

6. **The Monster is fragmented (F6 reconciliation artifact)**
   - Problem: `843d532715f2` ("the Monster") has only 7 mentions, is_narrator: false
   - Should be merged with a proper Creature character entry
   - ID pattern: 12-char hash → came from F6 summary reconciliation
   - Fix: Secondary to Critical #1 - fixing Creature extraction will resolve this

7. **Walton missing aliases**
   - Problem: Walton has no aliases, should include "Robert Walton", "Captain Walton"
   - Evidence: The text uses all three forms
   - Location: Supporting cast alias resolution

### LOW

8. **Defensive step activations remain low**
   - `total_activations: 3` - reasonable
   - Not blocking progress

## Fix History

### Attempt 6 (2026-01-31) - REGRESSION
- Applied: Bidirectional narrator name matching in `narrator.py:_match_to_character()`
- Result: **REGRESSION** - Creature merged into magistrate, narrator detection broken
- Theory: The fix may have enabled incorrect matching OR another change caused the Creature→magistrate merge

### Attempt 5 Re-run Evaluation (2026-01-31)
- **Corrected profile assessment:** The `appearance` object is populated correctly for 9/34 characters
- The Creature, Elizabeth, Safie, William, Waldman, Krempe all have good appearance data
- Previous evaluation incorrectly checked `physical_description` instead of `appearance.summary`

### Attempt 5 (2026-01-31) - PARTIAL SUCCESS
1. ✓ **The Creature now extracted** via main_cast (not split)
2. ✓ **The Creature marked as narrator** - correct for nested narrative
3. ✗ **Walton narrator status still failing** - Step 5.0.5 not finding Walton
4. ✓ **Profile generation working** - appearance data IS populated

### Earlier Attempts
See previous EVALUATION_STATE.md versions for full history.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline 6.35 |
| 2 | Victor missing, Waldman/Krempe merge | main_cast.py | Victor FIXED, Waldman/Krempe FIXED |
| 3 | Walton narrator, Alphonse refs | main_cast.py | NO CHANGE (wrong file) |
| 4 | Walton narrator in supporting_cast | characters.py | FIXED (Walton was narrator) |
| 5 | Creature extraction via characters_present | characters.py, main_cast.py | Creature EXTRACTED, Walton REGRESSED |
| 6 | Walton narrator (bidirectional match) | narrator.py | **REGRESSION** - Creature→magistrate merge |

**Pattern:** Attempt 6 caused a severe regression. Need to revert and investigate.

## Debug Focus for Fix Phase

**IMMEDIATE ACTION: REVERT ATTEMPT 6 CHANGES**

Since attempt 6 score (7.23) is significantly below attempt 5 (8.05), the fix phase should:
1. `git revert` the attempt 6 fix commit(s)
2. Re-analyze to restore attempt 5 state
3. Then investigate why the bidirectional match caused the Creature→magistrate merge

**Root Cause Investigation Needed:**

The bidirectional name matching fix (`name_lower in char_name_lower or char_name_lower in name_lower`) may have:
1. Incorrectly matched "Creature" to "magistrate" (how? they don't share substrings)
2. OR: There was ANOTHER change in attempt 6 that caused the merge
3. OR: The analysis run used different code/config than expected

Check:
- What exactly was committed in `c9dfb6c` (Bidirectional narrator fix)?
- Was there any other change in the pipeline between attempt 5 and 6?
- What does the consensus log show for the Creature/magistrate merge decision?

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive consensus: ENABLED (single-model mode, 3 temperatures)

## Next Action
The fix phase MUST revert attempt 6 changes due to critical regression. Score dropped from 8.05 to 7.23 (-0.82), exceeding the 0.3 regression threshold.
