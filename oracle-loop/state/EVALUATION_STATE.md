# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.95 | 0.00 | Initial - Characters & Profiles failing |
| 2 | 6.95 | 0.00 | Fix did NOT work - Gatsby/Daisy still from supporting_cast |

## Current Issues (Priority Order)

### CRITICAL

1. **Main cast extraction prompt fix did NOT work - Gatsby and Daisy still extracted by supporting cast**
   - Problem: Jay Gatsby (267 mentions) has ID `supporting_9` and Daisy (179 mentions) has ID `supporting_1`
   - Evidence: The main_cast pipeline extracted 10 characters but NOT Gatsby or Daisy:
     - Nick Carraway, Tom Buchanan, Myrtle Wilson, George Wilson, Jordan Baker, Meyer Wolfsheim, Henry C. Gatz, Doctor T. J. Eckleburg, Catherine, Mr. Sloane
   - Root cause: The LLM is STILL not following the prompt instructions. The prompt fix added "MANDATORY INCLUSIONS" but the LLM ignored it. This suggests:
     a) The prompt changes may not have been included in the actual LLM call, OR
     b) The LLM model being used doesn't follow complex instructions well, OR
     c) There's a hardcoded list or other logic overriding the prompt
   - Location: Need to verify `src/pipeline/character_extraction_v2/main_cast.py` is actually being called AND verify the prompt is reaching the LLM
   - Fix: Either add explicit logic to ALWAYS include title characters (programmatic, not prompt-based), or investigate why prompt isn't being followed

2. **Daisy missing surname and ALL aliases**
   - Problem: Listed as "Daisy" with no aliases `[]`, but should be "Daisy Buchanan" with aliases ["Daisy", "Daisy Fay"]
   - Evidence: Chapter summaries correctly use "Daisy Buchanan" in `characters_present` for every chapter she appears
   - Location: F6 reconciliation should be merging these OR the character should have full name from extraction
   - Fix: Either main_cast must extract full name, OR F6 reconciliation must update canonical_name when summary uses full name

3. **Gatsby and Daisy have role="minor" despite being protagonist/love interest**
   - Problem: Title character Jay Gatsby has `role: "minor"`, female lead Daisy has `role: "minor"`
   - Evidence: The supporting cast pipeline hardcodes `role: "minor"` - this is working as designed, but the design is wrong when main cast fails
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - role assignment
   - Fix: Either fix main_cast extraction (root cause), OR add post-processing to promote high-mention characters from supporting_cast

### HIGH

4. **Character profiles completely empty for physical_description and relationships**
   - Problem: 0/32 characters have populated `physical_description` or `relationships` fields
   - Evidence: All characters have `"physical_description": null` and `"relationships": {}` in JSON
   - But: Personality data IS populated (13/32 have personality traits)
   - Text evidence for Tom Buchanan: "a sturdy straw-haired man of thirty with a rather hard mouth and a supercilious manner. Two shining arrogant eyes..."
   - Location: `src/pipeline/character_profiles.py` - profile generation or JSON population
   - Fix: Profile pipeline is generating personality but NOT physical_description/relationships - check if these fields are being extracted but not saved

5. **Doctor T. J. Eckleburg still extracted as a character despite explicit prompt exclusion**
   - Problem: Main cast includes "Doctor T. J. Eckleburg" (ID `main_cast_8`) with role "supporting"
   - Evidence: The fix explicitly added Eckleburg as an example of "only sentient beings" but LLM still extracted it
   - This confirms: The LLM is NOT following the updated prompt instructions
   - Location: Same root cause as issue #1 - prompt not being respected
   - Fix: Add explicit post-processing filter for known non-character references (billboard, painting, etc.)

### MEDIUM

6. **Chapter titles null for chapters 2-9**
   - Problem: Chapter 1 has title "I" but chapters 2-9 have `title: null`
   - Evidence: All chapters should have Roman numeral titles (I through IX)
   - Location: Structure detection title extraction
   - Fix: Ensure Roman numeral titles are captured for all chapters

7. **49 pronunciation entries missing IPA (9%)**
   - Problem: 506/555 have IPA - 91% coverage
   - Evidence: 49 words lack phonetic transcription
   - Impact: Minor - 91% is acceptable but could be improved

### LOW

8. **Owl-eyed man alias not linked**
   - Problem: "the owl-eyed man" should be linked to "Owl Eyes"
   - Evidence: Same character, descriptive reference
   - Impact: Very low - minor character

## Fix History

### Attempt 1 Fixes

**Fix: Enhanced main cast extraction prompt with mandatory inclusions** - FAILED
- **Changes made:** Added "CRITICAL - MANDATORY INCLUSIONS" section to main_cast.py prompt
- **Expected result:** Gatsby and Daisy extracted by main_cast with correct roles
- **Actual result:** Neither change took effect - Gatsby/Daisy still from supporting_cast, Eckleburg still extracted
- **Conclusion:** Prompt-based fixes are not working. Need programmatic solution.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Issues #1, #2, #7: Main cast extraction failures | `src/pipeline/character_extraction_v2/main_cast.py` | **No change** - LLM ignored prompt |

**Pattern Detected:** Prompt-only fixes are not effective. The LLM is not following enhanced instructions. Next fix MUST use programmatic/code-based approach rather than prompt engineering.

## Root Cause Analysis

The fundamental issue is that **main_cast extraction is unreliable** - it extracts 10 characters but misses the two most important ones (Gatsby, Daisy). The LLM does not reliably follow prompt instructions about mandatory inclusions.

**Solution Direction:** Instead of relying on LLM to follow instructions, add POST-PROCESSING logic:
1. After main_cast extraction, check if title character (from book title) is missing → force-add from NER/supporting
2. After supporting_cast extraction, promote any character with >50 mentions to "supporting" role minimum
3. Add explicit filter for non-sentient references (billboards, paintings, objects)
4. F6 reconciliation should UPDATE canonical_name when summary uses a fuller name

## Pipeline Execution Notes (Attempt 2)

**Analysis completed:** 2026-01-27 14:53
**Duration:** 76m 20s

**Character Pipeline Results:**
- 10 characters from main_cast (but missing Gatsby and Daisy)
- 12 characters from supporting_cast (includes Gatsby and Daisy with wrong roles)
- 10 characters from F6 reconciliation (hash IDs)

## Next Action
**Phase:** awaiting_fix

Fix phase must use PROGRAMMATIC solutions, not prompt engineering:
1. Add post-extraction promotion logic for high-mention supporting characters
2. Add post-extraction filter for non-character objects (Eckleburg billboard)
3. Investigate why physical_description and relationships are null in profiles
