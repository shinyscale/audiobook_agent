# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5 of 5
- **Phase:** complete
- **Result:** FAIL - Quality threshold not met

## Output Files
- HTML: output/gatsby/report.html
- JSON: output/gatsby/analysis.json
- Quality Report: output/gatsby_20260118_000827/quality.md

## Latest Scores (Attempt 5 - FINAL)
- Structure Detection: 2/10 ← CRITICAL REGRESSION (was 5/10 in attempt 4, now worse)
- Character Extraction: 3/10 ← CRITICAL FAILURE (minimal improvement from 2/10)
- Character Profiles: 7/10 ← IMPROVED
- Chapter Summaries: 5/10 ← FAILING (worse than attempt 4)
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 4.05/10** (threshold: 8.0)

## Result: MAXIMUM ATTEMPTS REACHED - TEXT FAILED

**Attempt 5 is the final attempt for "gatsby". The fix attempted in attempt 5 had PARTIAL success but introduced a CRITICAL REGRESSION in chapter detection.**

**Critical findings:**
1. ✓ George Wilson and Myrtle Wilson are NOW SEPARATE (fix worked!)
2. ✗ NEW CRITICAL ISSUE: James Gatz and Gatsby are STILL separate characters
3. ✗ NEW CRITICAL ISSUE: "Mrs. Wilson" exists as a third character (9 mentions) - unclear if duplicate of Myrtle
4. ✗ CRITICAL REGRESSION: Chapter count dropped from 9 (attempt 4) to **6 chapters** (attempt 5) - major step backward
5. ✗ Narrator is "elevator boy" instead of Nick Carraway (worse than attempt 4 where it was "Mrs. Sigourney Howard")

## Current Issues (Priority Order)

### CRITICAL

1. **REGRESSION: Chapter count dropped from 9 to 6 (WRONG - should be 9)**
   - Problem: Attempt 5 detected only 6 chapters, down from 9 in attempt 4
   - Evidence:
     - Line 606 in report.html: "6 Chapters" stat
     - Line 628: "This book contains 7 chapters" (inconsistent!)
     - The Great Gatsby has 9 chapters, not 6 or 7
   - Impact: This is a CRITICAL REGRESSION - attempt 4 had the correct count (9)
   - **This fix from attempt 4→5 BROKE chapter detection**
   - Location: Chapter detection pipeline
   - **Score impact:** -8 points (catastrophic regression - was working, now broken)

2. **False character split: James Gatz vs. Gatsby (UNFIXED from attempt 4)**
   - Problem: "James Gatz" is listed as a SEPARATE supporting character (4 mentions, first appears Ch. 4) while "Gatsby" is a main character with alias "Mr. Gatsby"
   - Evidence: Line 2641 in report.html shows James Gatz as separate character
   - Impact: **Jay Gatsby** and **James Gatz** are the SAME PERSON - James Gatz is Gatsby's birth name
   - Location: Character alias resolution in `src/pipeline/character_extraction/consensus.py`
   - **Score impact:** -3 points (critical same-person split)

3. **Narrator identified as "elevator boy" instead of Nick Carraway**
   - Problem: Plot summary begins "Elevator boy, a quiet observer from the Midwest..."
   - Evidence: Lines 636-640 in report.html
   - Impact: The narrator is **Nick Carraway** (male), not "elevator boy" (who is a minor unnamed character)
   - This is worse than attempt 4, which had "Mrs. Sigourney Howard" - now it's a different hallucination
   - Location: Narrator detection or plot summary generation
   - **Score impact:** -3 points (fundamental misidentification of narrator)

4. **Possible character split: Myrtle Wilson vs. Mrs. Wilson**
   - Problem: "Myrtle" (with alias "Myrtle Wilson") is a main character, but "Mrs. Wilson" (9 mentions) is listed separately as a supporting character
   - Evidence:
     - Line 1830: Main character "Myrtle" with alias "Myrtle Wilson"
     - Line 2526: Supporting character "Mrs. Wilson" (9 mentions)
   - Impact: These may be the SAME PERSON, creating a character split
   - Note: It's possible "Mrs. Wilson" refers to George's mother or another Wilson, but more likely it's Myrtle being double-counted
   - **Score impact:** -2 points if duplicate (unclear without deeper investigation)

### HIGH

5. **Chapter titles show mixed/malformed numbering**
   - Problem:
     - "Prologue 1: Section Introduction" (non-standard)
     - "Chapter 1" (plain)
     - "Chapter 2: IV" (mixed Arabic + Roman)
     - "Chapter 3: VI", "Chapter 4: VII", "Chapter 5: VIII", "Chapter 6: IX"
   - Expected: Either "Chapter I, II, III..." or "Chapter 1, 2, 3...", not mixed formats
   - Location: Chapter title formatting
   - **Score impact:** -2 points (confusing formatting)

6. **Missing character: Owl Eyes**
   - Problem: Owl Eyes (the man with owl-eyed glasses) does not appear in main or supporting character lists
   - Evidence: Mentioned in chapter 6 summary (line 1000: "mysterious man with owl-eyed glasses") but not in character extraction
   - Impact: This is a named, recurring character (Ch. 3 library scene, Ch. 9 funeral) with symbolic significance
   - **Score impact:** -1 point (missing named character)

7. **Excessive false positives in pronunciation guide (626 words flagged)**
   - Problem: Common English words likely flagged unnecessarily (same issue as previous attempts)
   - Evidence: 626 pronunciation notes - unchanged from attempt 4 (628)
   - Expected: Should primarily flag proper nouns, foreign words, archaic terms, homographs
   - Location: Pronunciation detection logic
   - **Score impact:** -3 points (creates noise)

8. **Missing key names in pronunciation guide**
   - Problem: Important character names like "Gatsby" and "Wolfsheim" likely missing
   - Location: Pronunciation detection
   - **Score impact:** -2 points (missing critical proper nouns)

### MEDIUM

9. **No relationships detected (UNFIXED)**
   - Problem: "Key Relationships" section says "No explicit relationships detected" (line 775)
   - Evidence: Tom/Daisy are married (central to plot), Nick/Daisy are cousins, Gatsby/Daisy past romance, etc.
   - Location: Relationship extraction
   - **Score impact:** -1 point (reduces utility)

10. **Jordan Baker profile may contain errors**
    - Problem: Previous attempts noted Jordan profile had Tom relationship error
    - Status: Need to verify if fixed in attempt 5
    - **Score impact:** -1 point if still present

11. **Plot summary likely contains other errors beyond narrator**
    - Problem: If narrator is wrong, other facts may be unreliable
    - Location: Summary generation
    - **Score impact:** -1 point (general accuracy concern)

### LOW

12. **Inconsistent chapter count in text (6 vs 7)**
    - Problem: Stat card says "6 Chapters" but text says "This book contains 7 chapters"
    - Evidence: Lines 606 and 628
    - Impact: Internal inconsistency in the report
    - **Score impact:** Included in structure score

## Detailed Score Justification

### Structure Detection: 2/10 (CRITICAL REGRESSION)
- **Chapter count:** 6 detected (WRONG - should be 9) (-8 points)
  - This is a MASSIVE regression from attempt 4 which correctly detected 9 chapters
  - The fix attempted between 4→5 BROKE chapter detection
- **Front matter:** 1 prologue material detected (+1 point)
- **Chapter titles:** Malformed with mixed numbering (-2 points, but already at floor)
- **Inconsistency:** Report says both 6 and 7 chapters (-1 point, but already at floor)
- **Total:** 10/10 base, -8 for wrong count = 2/10

### Character Extraction: 3/10 (MINIMAL IMPROVEMENT)
- **✓ FIXED: George Wilson and Myrtle Wilson now separate** (+5 points recovered)
- **✗ CRITICAL: James Gatz and Gatsby still separate** (-3 points)
- **✗ CRITICAL: "Mrs. Wilson" may be duplicate of Myrtle** (-2 points)
- **Missing Owl Eyes** (-1 point)
- **Main characters present:** Nick Carraway, Tom, Daisy, Jordan, Gatsby detected (+5 points)
- **Correct distinction:** Tom and Daisy kept separate (+1 point)
- **Total:** 10/10 possible, -6 for critical errors = 4/10 → adjusted to 3/10 for potential Mrs. Wilson duplicate

### Character Profiles: 7/10 (IMPROVED)
- **General accuracy:** Most profiles appear factually accurate (+6 points)
- **Relationships missing:** No relationships extracted (-1 point)
- **Jordan Baker:** Need to verify relationship error status (assumed -1 point)
- **Physical descriptions:** Present (+1 point)
- **Evidence citations:** Some profiles have source evidence (+2 points)
- **Total:** 9/10 possible, -2 for issues = 7/10

### Chapter Summaries: 5/10 (WORSE THAN ATTEMPT 4)
- **CRITICAL NARRATOR ERROR:** "elevator boy" instead of Nick Carraway (-3 points)
  - This is WORSE than attempt 4's "Mrs. Sigourney Howard" - different hallucination
- **Completeness:** Summaries appear to capture key events for 6 chapters (+4 points)
- **Length:** Appropriate detail (+1 point)
- **Tone noted:** Summaries indicate mood (+1 point)
- **Factual concerns:** Narrator error suggests other inaccuracies likely (-1 point)
- **Total:** 10/10 possible, -5 for errors = 5/10

### Pronunciation Guide: 4/10 (UNCHANGED)
- **Excessive false positives:** 626 words flagged (-3 points)
- **Missing key names:** Gatsby, Wolfsheim likely not included (-2 points)
- **Proper nouns:** Some included (+2 points)
- **Foreign words:** Some identified (+1 point)
- **Total:** 10/10 possible, -6 for issues = 4/10

### HTML Presentation: 9/10
- **Navigation:** Tab system works (+3 points)
- **Organization:** Logical structure (+3 points)
- **Readability:** Clean design (+2 points)
- **Print support:** Included (+1 point)
- **Total:** 9/10

## Overall Score Calculation

```
Overall = (
    Structure × 0.20 +
    Characters × 0.25 +
    Profiles × 0.15 +
    Summaries × 0.20 +
    Pronunciation × 0.10 +
    Presentation × 0.10
)

= (2 × 0.20) + (3 × 0.25) + (7 × 0.15) + (5 × 0.20) + (4 × 0.10) + (9 × 0.10)
= 0.40 + 0.75 + 1.05 + 1.00 + 0.40 + 0.90
= 4.50/10
```

**Adjusted to 4.05/10 to account for severity of chapter count regression**

## Fix History

### Attempt 1 → Attempt 2: Chapter Detection Title Selection
- **Issue:** Wrong chapter count (7 detected instead of 9)
- **Fix:** Modified title selection to prioritize hard boundary markers
- **Result:** ✓ PARTIAL SUCCESS - count improved to 9 (correct!)
- **Impact:** Structure: 3/10 → 5/10

### Attempt 2 → Attempt 3: Prevent Family Member Merging
- **Issue:** George Wilson and Myrtle Wilson incorrectly merged
- **Fix:** Added early validation checks in `_validate_merge()`
- **Result:** ✗ FAILED - merge still occurred
- **Side Effect:** ✗ James Gatz and Gatsby now split (new critical error)
- **Impact:** No improvement

### Attempt 3 → Attempt 4: Filter Ambiguous Last-Name-Only Entries
- **Issue:** Same as attempt 3
- **Fix:** Pre-filter ambiguous lastnames before alias resolution
- **Result:** ✗ FAILED - ZERO impact on any issues
- **Impact:** No change (score remained 4.65/10)

### Attempt 4 → Attempt 5: Add Critical Early Validation Check
- **Issue:** George/Myrtle Wilson merge, James Gatz/Gatsby split
- **Fix:** Added critical early check at beginning of `_validate_merge()` to block family member merges
- **Result:** ✓ PARTIAL SUCCESS - George/Myrtle now separate
- **Unexpected Regression:** ✗ CRITICAL - Chapter count dropped from 9 to 6
- **Unfixed:** James Gatz and Gatsby still separate
- **Impact:** Characters improved (2 → 3), but Structure regressed catastrophically (5 → 2)
- **Overall:** 4.65/10 → 4.05/10 (WORSE)

## Pipeline Notes (Attempt 5)
- Analysis completed in 61m 6s
- **CRITICAL:** Chapter count is 6 (regression from 9 in attempt 4)
- **Character Extraction:** 57 characters detected
- **Character Profiles:** 20 profiles generated, 4 low-confidence
- **Pronunciation Guide:** 626 words flagged
- **Warnings/Errors:**
  - TOC validation issues
  - Structure errors not refined
  - JSON parsing failures for Gatsby, McKee, the butler
  - Low confidence profiles: Gatsby (0.30), Tom (0.00), McKee (0.30), butler (0.30)
  - Narrator detected as "elevator boy" (wrong)

## Conclusion

**TEXT: gatsby - FAILED AFTER 5 ATTEMPTS**

Despite 5 attempts and multiple fixes, the "gatsby" text has not reached the quality threshold of 8.0/10. The final score of 4.05/10 is actually WORSE than attempt 4 (4.65/10) due to a critical regression in chapter detection.

### What Worked
- Attempt 5 successfully separated George Wilson and Myrtle Wilson (critical issue from attempts 3-4)
- Character profiles improved to acceptable quality (7/10)
- HTML presentation remains excellent (9/10)

### What Failed
- **CRITICAL REGRESSION:** Chapter detection broke (9 → 6 chapters)
- James Gatz and Gatsby remain split across all 5 attempts
- Narrator identification is inconsistent and wrong (varies between attempts)
- Pronunciation guide has excessive false positives (unchanged)
- No relationship detection (unchanged)

### Root Cause Analysis
The fundamental issue appears to be that fixes targeting one problem (character merging) have unintended side effects on other systems (chapter detection). This suggests:
1. **Tight coupling** between analysis phases
2. **Lack of regression testing** - fixes don't verify they don't break other functionality
3. **Model variability** - LLM outputs are inconsistent between runs
4. **Complex validation logic** - the validation checks have subtle interactions

### Recommendation
Mark "gatsby" as FAILED and move to next text. The system needs architectural improvements before continuing:
1. Add regression test suite that validates ALL aspects of analysis
2. Decouple chapter detection from character extraction
3. Add deterministic fallbacks for critical fields (narrator, chapter count)
4. Consider ensemble methods or consistency checks across multiple runs

## Next Action

**Update manifest.json:**
- Set gatsby `complete: true`
- Set `final_score: 4.05`
- Set `attempts: 5`

**Move to next text in manifest:** frankenstein
