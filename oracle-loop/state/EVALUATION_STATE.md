# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.53
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 7/10
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10
- **Overall: 7.53/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.53 | 0 | Initial evaluation |

## Current Issues (Priority Order)

### CRITICAL

1. **Character false split: "the old man" vs "De Lacey"**
   - Problem: "the old man" (split_the_old_man, 29 mentions) and "De Lacey" (supporting_5, 8 mentions) are listed as separate characters
   - Evidence: These refer to the same person - the blind old man in the cottage IS De Lacey, Felix and Agatha's father. The creature calls him "the old man" while narrating but he is explicitly named De Lacey in the text
   - ID patterns: `split_the_old_man` (semantic split) + `supporting_5` (supporting cast)
   - Location: Cross-pipeline merge issue - need to merge characters from different extraction stages
   - Fix: Add merge logic to recognize "the old man" refers to De Lacey based on context (same cottage, father of Felix/Agatha)

### HIGH

2. **Geographic locations incorrectly classified as characters**
   - Problem: Mont Blanc, Mont Salêve, Arve (river), Strasburgh (Strasbourg) are listed as characters
   - Evidence: These are places, not people. Mont Blanc is a mountain, Arve is a river, Strasburgh is a city
   - IDs: supporting_11, supporting_13, supporting_14, supporting_15 (all from supporting cast pipeline)
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - location filtering
   - Fix: Improve entity classification to filter out geographical entities (LOCATION/GPE in NER)

3. **Spurious "Narrator (Victor)" character entry**
   - Problem: "Narrator (Victor)" (184ba9994299, 1 mention) exists as separate character alongside "Victor Frankenstein"
   - Evidence: This is a duplicate/artifact - Victor Frankenstein is already correctly identified as a narrator
   - ID: Hash ID indicates F6 reconciliation
   - Location: F6 summary reconciliation in `src/analyzer.py:1220-1240`
   - Fix: Improve reconciliation to not create separate entries for narrator references

4. **Creature's appearance is "Unknown" despite detailed description in text**
   - Problem: The creature has `appearance.summary: "Unknown"` and empty `distinguishing_features`
   - Evidence: Shelley provides vivid description in Chapter 5: "yellow skin," "lustrous black hair," "watery eyes," "shrivelled complexion," 8 feet tall
   - Location: `src/pipeline/character_extraction_v2/` profile enrichment
   - Fix: Improve profile extraction to capture appearance details from creation scene

5. **Letter 1 missing title in structure**
   - Problem: First structure element has `title: null` but contains Letter 1 content
   - Evidence: Summary describes "Robert Walton writing a letter to his sister Margaret from St. Petersburg" - this is Letter 1
   - Location: Structure detection - title extraction
   - Fix: Improve title detection for first letter (may lack "Letter 1" header in source)

### MEDIUM

6. **All pronunciation entries lack category classification**
   - Problem: 621 pronunciations all have `category: null`
   - Evidence: `jq` query shows all 621 entries have null category
   - Location: Pronunciation agent - category assignment
   - Fix: Populate category field (proper_noun, foreign_word, archaic, etc.)

7. **Missing aliases for some supporting characters**
   - Problem: Ernest has no aliases (should include "Ernest Frankenstein"), Margaret has no aliases (should be "Margaret Saville")
   - Evidence: These are Victor's family members with full names in text
   - Location: Alias resolution in supporting cast pipeline
   - Fix: Improve alias detection for supporting characters

### LOW

8. **Some chapters have null titles when they should have chapter numbers**
   - Problem: 25 structure elements have null titles but should show "Chapter 1", "Chapter 2", etc.
   - Evidence: HTML renders them correctly but JSON data is incomplete
   - Location: Structure detection post-processing
   - Fix: Ensure chapter numbers are captured even when no explicit title

## Fix Priority for Crossing 8.0 Threshold

To reach 8.0, focus on:
1. **Character Extraction (7→8)**: Fix issues #1 (De Lacey split), #2 (geo locations), #3 (narrator duplicate) = +1 point
2. **Character Profiles (7→7.5)**: Fix issue #4 (creature appearance) = +0.5 points
3. **Pronunciation (7→7.5)**: Fix issue #6 (categories) = +0.5 points

Estimated impact: 7.53 → 8.0+ (crossing threshold)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Notes
- Pipeline completed successfully in 118m 20s
- 28 chapters detected (correct for 4 letters + 24 chapters)
- 3 narrators correctly identified (Walton, Victor, creature) - excellent for nested narrative
- Summaries are high quality and accurate
- HTML presentation is clean and functional
- Main character issues are merge/split problems, not missing characters

## Next Action
Run PROMPT_fix.md to address character extraction issues (Critical #1, High #2, #3)
