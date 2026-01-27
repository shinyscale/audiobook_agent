# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.53
- **Competitive Mode:** single

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 7/10
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10
- **Overall: 7.65/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.53 | 0 | Initial evaluation |
| 2 | 7.65 | +0.12 | Geo location filtering FIXED, narrator duplicate FIXED |

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: "the old man" vs "De Lacey"**
   - Problem: "the old man" (main_cast_8, 34 mentions) and "De Lacey" (supporting_5, 8 mentions) listed as separate characters
   - Evidence: The blind old man in the cottage IS De Lacey - Felix and Agatha's father. The creature calls him "the old man" while narrating but he is explicitly named "De Lacey" in the text (e.g., Chapter 15: "I knocked. 'Who is there?' said the old man. 'Come in.' I entered. 'Pardon this intrusion,' said I; 'I am a traveller in want of a little rest...'" followed by De Lacey introducing himself)
   - ID patterns: `main_cast_8` (main cast) + `supporting_5` (supporting cast) - cross-pipeline merge needed
   - Location: Need cross-pipeline merge logic or better context-aware alias detection
   - Fix approach: Add post-processing merge logic that recognizes descriptive references (e.g., "the old man" in cottage context = De Lacey based on family relationships)

### HIGH

2. **Character profiles systemically empty**
   - Problem: ALL 32 characters have `physical_description: null` and empty `relationships: []`
   - Evidence: `jq` query shows 0/32 characters have populated physical_description or relationships fields
   - Location: Profile enrichment stage in `src/pipeline/character_extraction_v2/`
   - Fix: Debug why profile population isn't working - this was working in previous texts

3. **The creature's appearance is "unknown"**
   - Problem: Creature has `appearance.summary: "unknown"` and empty `distinguishing_features`
   - Evidence: Shelley provides vivid description in Chapter 5: "His yellow skin scarcely covered the work of muscles and arteries beneath; his hair was of a lustrous black, and flowing; his teeth of a pearly whiteness; but these luxuriances only formed a more horrid contrast with his watery eyes, that seemed almost of the same colour as the dun-white sockets in which they were set, his shrivelled complexion and straight black lips."
   - This is a subset of issue #2 but especially problematic for the protagonist/antagonist
   - Location: Profile extraction not capturing appearance details from creation scene

4. **Creature missing aliases**
   - Problem: "the creature" has only 5 mentions and no aliases
   - Evidence: The creature is referred to as "the monster", "the daemon", "the fiend", "the wretch" throughout the text - these should be captured as aliases
   - ID: `split_the_creature` (semantic split)
   - Location: Alias detection in main_cast or supporting pipeline
   - Fix: Improve alias detection for descriptive/epithetical references

### MEDIUM

5. **All pronunciation entries lack category**
   - Problem: 618 pronunciations all have `category: null`
   - Evidence: `jq '[.pronunciations[] | select(.category)] | length'` returns 0
   - Location: Pronunciation agent - category assignment
   - Fix: Populate category field (proper_noun, foreign_word, archaic, homograph, etc.)

6. **R.W. not merged with Robert Walton**
   - Problem: "R.W." (1 mention, f1b39c083608) exists separately from "Robert Walton"
   - Evidence: R.W. are Walton's initials used to sign letters
   - ID: Hash ID indicates F6 reconciliation
   - Fix: Improve initial detection to recognize initials as aliases

### LOW

7. **Structure titles mostly null**
   - Problem: Only Letters 2-4 have titles; Letter 1 and Chapters 1-24 have null titles
   - Evidence: `jq` shows 25/28 structure elements have null titles
   - Location: Structure detection - title extraction
   - Note: HTML handles this gracefully by displaying "Chapter 1", "Chapter 2", etc.
   - Fix: Improve title extraction or generate default titles in post-processing

## Fix Priority for Crossing 8.0 Threshold

Current score: 7.65. Need: 8.0. Gap: 0.35 points.

**Most impactful fixes:**
1. **Fix Character Profiles (#2)**: If profiles populate correctly → 6→8 (+0.30 weighted)
2. **Fix De Lacey split (#1)**: Reduces false splits → 7→8 (+0.25 weighted)

Combined expected impact: ~0.55 points → should cross 8.0 threshold

**Focus on issue #2 first** - if profile fields aren't populating at all, this is a systemic bug that affects all characters. Fixing this one issue could significantly boost the Character Profiles score.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | #2: Geographic locations as characters | src/pipeline/character_extraction_v2/supporting.py | **FIXED** ✓ |
| 1 | #3: Spurious "Narrator (Victor)" entry | src/analyzer.py | **FIXED** ✓ |
| 2 | #2: Character profiles - relationships field never populated | src/analyzer.py | **FIXED** ✓ (pending verification) |

## Verified Fixes from Attempt 1
- ✅ Geographic locations (Mont Blanc, Arve, Strasburgh, Mont Salêve) no longer appear as characters
- ✅ "Narrator (Victor)" spurious entry has been removed

## Fix Details for Attempt 2

### Issue #2: Relationships field never populated

**Root cause:**
- `_generate_character_profile()` did not extract or return relationships
- The function returned 6 values but relationships was never included
- The LLM prompt did not request relationships field
- The caller never assigned relationships to character objects

**Fix applied:**
1. Added "relationships" field to LLM prompt JSON response format (analyzer.py:2456)
2. Updated prompt instructions to extract family, friends, enemies, romantic connections (analyzer.py:2477)
3. Extended function signature to return 7 values including relationships (analyzer.py:2229)
4. Extract relationships from LLM response (analyzer.py:2669)
5. Clean and validate relationships dict (analyzer.py:2703)
6. Update caller to unpack and assign relationships (analyzer.py:1790, 1816)
7. Updated all error return statements to include 7th None value (analyzer.py:2813, 2814, 2830, 2844)

**Smoke test:** ✓ PASSED
- Function signature correct (returns 7-tuple)
- Code compiles without errors
- Prompt includes relationships field
- All 231 tests pass

**Expected impact:**
- relationships field should now populate for characters with sufficient context
- May improve Character Profiles score from 6/10 → 7-8/10

## What's Working Well
- 28/28 chapters correctly detected
- 3 narrators correctly identified (Walton, Victor, creature) - excellent for nested frame narrative
- Chapter summaries are accurate, detailed, and helpful for narrators
- HTML presentation is clean and functional
- Pronunciation IPA coverage is 96% (597/618)
- Homograph handling is good

## Notes
- Score improved from 7.53 → 7.65 (+0.12)
- The fixes from attempt 1 were verified working
- **Attempt 2 fix:** relationships field was never being populated (code bug, now fixed)
- Partial profile population (16/32 have appearance/personality) requires investigation in logs
- De Lacey/old man merge remains unaddressed (requires different fix approach)

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Pipeline Notes (Attempt 3)
- Analysis completed in 135m 28s (8134 seconds)
- Competitive consensus ENABLED (3 LLMs @ temps 0.5/0.7/0.9, 2/3 supermajority)
- Competitive stages: characters, structure, summaries
- 28 chapters detected (same as attempt 2)
- 33 characters extracted (attempt 2 had 32)
- 619 pronunciation flags (attempt 2 had 618)
- 18 character profiles generated for 18 eligible characters

### Warnings Observed:
- Structure: "TOC validation: 31 entries seems too many" - expected (meta-chapters in source)
- Structure: "Only 27 total boundaries found but TOC expects 31" - minor
- Structure: "1 errors found but refinement not yet implemented" - known limitation
- Character: Multiple "BLOCKED alias" messages - alias validation working correctly
- Character: "BLOCKED alias: 'De Lacey' and 'the old man'" - This is a FALSE NEGATIVE (they ARE the same person)
- Character: "SEMANTIC CONFLICT: 'the creature' vs 'the old man'" - correct conflict detection
- Profile: "No passages provided for William/Ernest/Margaret/etc." - minor characters with low mention counts
- Profile: "Failed to parse JSON response for Mr. Kirwin" - single profile generation error
- Profile: "Low confidence profile for Mr. Kirwin: 0.30" - flagged appropriately

## Next Action
**Phase:** awaiting_evaluation

Evaluate attempt 3 results to see if:
1. Competitive consensus (single mode) improved character extraction accuracy
2. Relationships field now populates for characters
3. Physical descriptions populate for main characters (especially the creature)
4. Overall score crosses 8.0 threshold
