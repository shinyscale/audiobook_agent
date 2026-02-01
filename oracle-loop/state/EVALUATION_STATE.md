# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.5

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score Breakdown

### Structure Detection: 8/10 ✓
- **Correct:** 3 parts detected matching the story's I, II, III structure
- **Correct:** All confidence levels are "high"
- **Minor issue:** Part I and II titles are `null`, only Part III has title "III"
- The story uses Roman numerals (I, II, III) - first two weren't captured but boundaries are correct

### Character Extraction: 5/10 ✗
- **CRITICAL:** "the old man" (26 mentions) extracted as SEPARATE character from "Mr. White" (10 mentions)
- **CRITICAL:** "the old woman" incorrectly listed as alias of "the old man" instead of being Mrs. White
- These are epithets used in Part III to refer to Mr. and Mrs. White in their grief
- System even detected `"Mr. White": "self"` in relationships but didn't merge
- Morris missing "Sergeant-Major" title in aliases (appears in chapter summaries as "Sergeant-Major Morris")
- Symbolic object "the monkey's paw" correctly extracted (acceptable per rubric)

### Character Profiles: 7/10 ✗
- **No physical_description for any character** (0/6 have this field populated)
- Relationships are generally correct where present
- Evidence collection is good
- Voice guidance is useful
- "the old man" profile has rich detail but belongs merged into Mr. White

### Chapter Summaries: 9/10 ✓
- All 3 summaries are accurate and capture key events
- Part I: Correctly describes Morris's arrival, the paw's history, the first wish
- Part II: Correctly describes Herbert's death, the two hundred pounds compensation
- Part III: Correctly describes the second wish, the knocking, the third wish
- Good length and detail for narrator preparation

### Pronunciation Guide: 9/10 ✓
- 34/37 entries have IPA transcriptions
- Good coverage: "fakir", "fakirs", "rubicund", "condoling", "Meggins"
- Minor: Some common words flagged (e.g., "to-night" - archaic spelling)
- No major false positives

### HTML Presentation: 9/10 ✓
- Clean navigation with tabbed interface
- Proper styling with dark theme
- Print-friendly CSS
- Mobile responsive
- Good organization of character profiles

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: "the old man" vs "Mr. White"**
   - Problem: "the old man" (26 mentions) and "Mr. White" (10 mentions) are separate entries
   - Evidence: In Part III, W.W. Jacobs uses "the old man" and "the old woman" as epithets for Mr. and Mrs. White. The system's own relationship data shows `"Mr. White": "self"` under "the old man", proving it recognized the identity.
   - Location: Character extraction V2 - likely in `src/pipeline/character_extraction_v2/main_cast.py` or post-processing merge logic
   - Fix: Need to recognize epithet patterns (definite article + descriptor = possible alias). The "self" relationship is a strong signal that should trigger a merge.
   - ID patterns: `main_cast_1` (Mr. White), `main_cast_5` (the old man) - both from main cast pipeline

2. **False character merge: "the old woman" aliased to "the old man"**
   - Problem: "the old woman" is listed as an alias of "the old man"
   - Evidence: "the old woman" refers to Mrs. White, not Mr. White. They are different people (husband and wife).
   - Location: Same as above - alias resolution is grouping same-structure epithets incorrectly
   - Fix: When merging epithets, check gender markers (old man/old woman = different genders = different people)

### HIGH

3. **Morris missing full title**
   - Problem: Character entry is just "Morris" but text uses "Sergeant-Major Morris"
   - Evidence: Chapter summary says "Sergeant-Major Morris" shows up. Full title appears in character_present lists.
   - Location: Alias resolution in `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: Add "Sergeant-Major Morris" as alias or make it canonical name

### MEDIUM

4. **Physical descriptions empty for all characters**
   - Problem: `physical_description` is `null` for all 6 characters
   - Evidence: The text DOES have physical descriptions (e.g., "thin grey beard" is captured in evidence for "the old man")
   - Location: `src/pipeline/character_profiling/` - the `physical_description` field isn't being populated even though evidence exists
   - Fix: Extract physical description from evidence statements that mention appearance

5. **Structure titles incomplete**
   - Problem: Parts I and II have `null` titles, only Part III captured "III"
   - Evidence: The story structure is "I", "II", "III" - all should be captured
   - Location: `src/pipeline/chapter_detection/`
   - Fix: Ensure Roman numeral detection works for all parts, not just the last one

## Fix Guidance for Character Split Issue

The epithet merge issue is the most impactful. Key observations:

1. **Strong signal exists:** The relationship `"Mr. White": "self"` under "the old man" is a clear indicator they're the same person
2. **Gender should block merges:** "old man" and "old woman" should NEVER be aliases (gender mismatch)
3. **Pattern to recognize:** Definite article + age/descriptor (the old man, the young woman, the fat man) often refers to an already-named character in the same scene/chapter

Suggested fix approach:
- In post-processing merge logic, when a character has a "self" relationship to another character, automatically merge them
- Add gender-aware validation to prevent aliasing "old man" to "old woman"
- This is a generic fix (relationship-based merge) that should work for any book

## Fix History
(First attempt - no prior fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline evaluation) | N/A | Baseline established |

## Next Action
Run PROMPT_fix.md to address the critical character split issues (the old man/Mr. White merge)
