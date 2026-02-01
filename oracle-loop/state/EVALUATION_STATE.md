# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.90

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE SPLIT: "the old man" should be alias of Mr. White**
   - Problem: "the old man" (id=main_cast_5, 26 mentions) is extracted as a separate character from "Mr. White" (id=main_cast_0, 10 mentions)
   - Evidence: In "The Monkey's Paw", "the old man" is clearly Mr. White referred to by a common descriptor. Part 3 exclusively uses "the old man" and "the old woman" to refer to the elderly couple.
   - ID Pattern: Both have `main_cast_*` IDs → Fix in main cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - alias resolution or merge logic
   - Fix: The consolidated alias prompt (Pass 2) should recognize that named characters like "Mr. White" can have descriptive aliases like "the old man". Need to improve pattern matching for definite-article descriptors ("the old man", "the old woman", "the stranger", etc.)

2. **FALSE MERGE: "the old woman" incorrectly aliased to "the old man"**
   - Problem: "the old woman" is listed as an alias of "the old man" character entry
   - Evidence: "the old woman" clearly refers to Mrs. White (the wife), not an alias for "the old man" (Mr. White, the husband). They are husband and wife - opposite genders, different people.
   - ID Pattern: `main_cast_5` contains this incorrect alias
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - CONSOLIDATED_ALIAS_PROMPT or `_process_consolidated_pass2()`
   - Fix: The alias resolution prompt should include explicit guidance that gendered descriptors ("old man" vs "old woman", "he" vs "she") indicate DIFFERENT characters, not aliases.

### HIGH

3. **Missing aliases for Mr. White and Mrs. White**
   - Problem: Mr. White has no aliases (should include "the old man"); Mrs. White has no aliases (should include "the old woman")
   - Evidence: Part 3 of the story uses exclusively descriptive references for the couple
   - Location: Same as issues #1 and #2 - `main_cast.py` alias resolution
   - Fix: After fixing the split/merge issues, ensure the descriptors are properly assigned as aliases to the named characters

4. **Zero physical descriptions for all characters**
   - Problem: All 7 characters have `physical_description: null`
   - Evidence: The text has some physical details (e.g., Morris is described, Herbert's appearance after the accident is implied)
   - Location: `src/pipeline/character_profiling/` - evidence gathering or profile generation
   - Fix: May need to improve passage gathering for short stories where physical descriptions are sparse

### MEDIUM

5. **Morris missing full title**
   - Problem: Listed as "Morris" but should be "Sergeant-Major Morris"
   - Evidence: He's consistently referred to with his military title in the text
   - Location: `main_cast.py` or supporting cast extraction
   - Fix: Preserve full titles when extracting character names

6. **"the talisman" vs "the monkey's paw"**
   - Problem: Object is listed as "the talisman" but the iconic name is "the monkey's paw"
   - Evidence: The title of the story and most references use "the monkey's paw"
   - Location: Main cast extraction - canonical name selection
   - Fix: Prefer story-title terms when selecting canonical names for symbolic objects

## Root Cause Analysis

The core issue is that Part 3 of "The Monkey's Paw" shifts narrative style - it uses descriptive epithets ("the old man", "the old woman") instead of proper names. The chapter summary correctly identifies these as characters_present, but the character extraction pipeline:

1. Creates "the old man" as a separate main_cast entry (main_cast_5)
2. Then incorrectly merges "the old woman" as an alias (probably because they appear together)
3. Fails to recognize that "the old man" = "Mr. White" and "the old woman" = "Mrs. White"

**Fix Priority:**
1. First: Prevent gendered descriptor merge ("old man" ≠ "old woman")
2. Second: Merge descriptive epithets with named characters ("the old man" → Mr. White alias)

## Fix History

- Attempt 1 (score 7.90): Initial analysis. Same character fragmentation issues.
- Attempt 2 (score 7.65): Regression. Same issues persisted, possibly worse due to other changes.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline - fragmentation present |
| 2 | Unknown | Unknown | Regression (7.65 < 7.90) |
| 3 | Pending | - | - |

**Pattern Alert:** Character extraction fragmentation has persisted across 2 attempts. Fix phase should focus on:
1. `src/pipeline/character_extraction_v2/main_cast.py` - CONSOLIDATED_ALIAS_PROMPT needs explicit guidance on gendered descriptors
2. Co-occurrence validation should block "old man" + "old woman" merge (they appear in same sentences, different roles)

## Next Action

Run PROMPT_fix.md to address character fragmentation:
1. Add explicit guidance to CONSOLIDATED_ALIAS_PROMPT that gendered descriptors are DIFFERENT characters
2. Improve co-occurrence validation to detect same-sentence but different-role appearances
3. Add heuristic to merge definite-article descriptors ("the old man") with nearby named characters of matching attributes
