# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_analysis
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

## Current Issues (Priority Order)

### CRITICAL

1. **Major characters misclassified as "minor"**
   - Problem: Jay Gatsby (267 mentions) and Daisy (179 mentions) have `role: "minor"`
   - Evidence: These are the protagonist and female lead - Gatsby is the title character, Daisy is central to the plot
   - Location: Role classification in V2 pipeline - likely `src/pipeline/character_extraction_v2/` role assignment logic
   - Character IDs: `supporting_9` (Gatsby), `supporting_1` (Daisy) - indicates they came from supporting cast extraction, not main cast
   - Fix: High-mention characters from supporting cast should be promoted or main cast detection improved

2. **Daisy missing surname and aliases**
   - Problem: Listed as "Daisy" with no aliases, but should be "Daisy Buchanan" with aliases ["Daisy", "Daisy Fay"]
   - Evidence: Chapter summaries correctly use "Daisy Buchanan" in `characters_present`, showing pipeline knows the full name
   - Evidence: Fitzgerald refers to her as "Daisy Buchanan" and historically as "Daisy Fay" (maiden name)
   - Location: F6 reconciliation mismatch between summary characters and extracted characters (analyzer.py:1220-1240)
   - Fix: When summary uses "Daisy Buchanan" but character list has "Daisy", merge/update the canonical name

### HIGH

3. **Character profiles missing physical_description and relationships**
   - Problem: 0/37 characters have populated `physical_description` or `relationships` fields
   - Evidence: Tom Buchanan's entry (the antagonist) has `"appearance": {"summary": "unknown"}` despite clear text descriptions
   - Text evidence: "a sturdy straw-haired man of thirty with a rather hard mouth and a supercilious manner. Two shining arrogant eyes..."
   - Location: Profile generation in `src/pipeline/character_profiles.py` or profile parsing failures noted in pipeline (30% confidence for Tom, Wolfsheim, Sloane)
   - Fix: Profile generation is producing data but parsing/population failing for key fields

4. **Owl-eyed man alias missing**
   - Problem: "the owl-eyed man" (1 mention) should be linked to "Owl Eyes" - the bespectacled man at Gatsby's library
   - Evidence: This is a named minor character who appears at parties (Ch. 3) and the funeral (Ch. 9)
   - Location: Alias resolution for descriptive nicknames
   - Fix: Improve handling of descriptive character references

### MEDIUM

5. **Chapter titles null for chapters 2-9**
   - Problem: Chapter 1 has title "I" but chapters 2-9 have `title: null`
   - Evidence: All chapters should have Roman numeral titles (I through IX)
   - Location: Structure detection title extraction
   - Fix: Ensure Roman numeral titles are captured for all chapters

6. **49 pronunciation entries missing IPA**
   - Problem: 49/555 words (9%) lack IPA transcription
   - Evidence: 506/555 have IPA - good coverage but incomplete
   - Location: Pronunciation generation
   - Impact: Minor - 91% coverage is acceptable but could be improved

### LOW

7. **Dr. T. J. Eckleburg listed as character**
   - Problem: "Doctor T. J. Eckleburg" (3 mentions) is listed - this is the billboard/eyes, not a character
   - Evidence: The "eyes of Doctor T. J. Eckleburg" is symbolic imagery, not a person
   - Location: Character extraction filtering for symbolic references
   - Impact: Low - doesn't affect narrator prep significantly

## Fix History

### Attempt 1 Fixes

**Fix: Enhanced main cast extraction prompt with mandatory inclusions**
- **Root cause:** Main cast extraction (main_cast.py) failed to extract Gatsby and Daisy despite being the title character and female lead. The LLM only extracted 9 of 10-15 requested characters and missed the two most important ones. They were picked up by fallback NER-based supporting cast extraction, which hardcodes role="minor".
- **Location:** `src/pipeline/character_extraction_v2/main_cast.py` lines 39-139
- **Changes:**
  1. Added "CRITICAL - MANDATORY INCLUSIONS" section emphasizing title characters, narrators, love interests, and spouses MUST be extracted
  2. Clarified that title characters MUST be extracted as main cast (use "supporting" as role, not as exclusion criterion)
  3. Added explicit Eckleburg example to "only sentient beings" rule to prevent billboard extraction
- **Addresses:**
  - Issue #1 (CRITICAL): Major characters misclassified as "minor" → should now extract Gatsby/Daisy with correct roles
  - Issue #2 (CRITICAL): Daisy missing surname/aliases → should now get full "Daisy Buchanan" with aliases from main cast
  - Issue #7 (LOW): Dr. T.J. Eckleburg listed as character → explicit example should prevent
- **Smoke test:** Manual verification - prompt changes correctly applied, no syntax errors
- **Confidence:** HIGH - prompt changes directly address LLM extraction failure

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Issues #1, #2, #7: Main cast extraction failures | `src/pipeline/character_extraction_v2/main_cast.py` | Awaiting re-analysis |

## Notes
Root cause analysis revealed:
1. **Issues #1 & #2 share same root cause:** Main cast extraction failed, causing Gatsby/Daisy to fall through to supporting cast (which hardcodes role="minor" and doesn't do full name/alias resolution)
2. **Issue #3 (profiles):** Partial failure - 13/37 have personality data, but 0/37 have relationships. Physical descriptions mostly "unknown" which may be acceptable.
3. **Data investigation showed:** Character IDs reveal pipeline sources - `supporting_*` indicates NER fallback was used instead of proper main cast extraction

The summaries and pronunciation are strong. Structure is good except for missing titles (MEDIUM priority).

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify fix effectiveness. Expect:
- Gatsby and Daisy in main_cast with proper roles (supporting/protagonist) and full names with aliases
- Eckleburg filtered out
- Character Extraction score should improve from 6/10 toward 8/10 threshold

If fix succeeds, may still need to address:
- Issue #3 (relationships): Systematic failure in relationship extraction (0/37 populated)
- Issue #4 (Owl-eyed man alias): Minor alias resolution
- Issue #5 (chapter titles): Structure detection issue
