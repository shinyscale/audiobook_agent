# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 4 of 5
- **Phase:** awaiting_analysis

## Output Files
- HTML: output/gatsby/report.html
- JSON: output/gatsby/analysis.json
- Quality Report: output/gatsby_20260117_212312/quality.md

## Latest Scores
- Structure Detection: 5/10 ← FAILING
- Character Extraction: 2/10 ← CRITICAL FAILURE (no improvement from attempt 2)
- Character Profiles: 6/10 ← FAILING
- Chapter Summaries: 6/10 ← FAILING
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 4.65/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL

1. **False character merge: George Wilson + Myrtle Wilson (ATTEMPT 3 FIX FAILED)**
   - Problem: "Wilson" character STILL has aliases: "George B. Wilson, George Wilson, **Myrtle, Myrtle Wilson**, George, Mrs. Wilson"
   - Evidence: George Wilson and Myrtle Wilson are **HUSBAND AND WIFE** - two completely different people who should be separate characters
   - **ATTEMPTED FIX IN ATTEMPT 3:** Added early validation checks in `_validate_merge()` (lines 1522-1568 in `src/pipeline/character_extraction/consensus.py`) to reject merges when:
     - Both names have first+last components with same last name but different first names
     - One name is a single word matching a last name with multiple different people sharing that last name
   - **FIX DID NOT WORK:** The merge is still happening, indicating the validation logic is either not being reached, or the merge is happening elsewhere in the pipeline
   - **Next diagnostic step:** Need to add debug logging to understand:
     - Is `_validate_merge()` being called for "Wilson" + "Myrtle Wilson"?
     - If yes, why is the validation check not triggering?
     - If no, where else are these characters being merged?
   - Location: Character alias resolution in `src/pipeline/character_extraction/consensus.py` or potentially in an earlier stage
   - **Score impact:** -5 points (catastrophic main character error - Myrtle is a major character)

2. **Narrator identified as "Mrs. Sigourney Howard" instead of Nick Carraway**
   - Problem: Plot summary begins "Mrs. Sigourney Howard, recounting her experiences from the summer of 1922..."
   - Evidence: The narrator is **Nick Carraway** (male), not "Mrs. Sigourney Howard" (who doesn't exist in the novel)
   - This is a hallucination - the system invented a non-existent character as the narrator
   - Location: Plot summary generation in `src/agents/summary_agent.py`
   - Fix: Either extract narrator identity from character metadata (Nick Carraway is tagged as narrator) or verify narrator name against character list before generating plot summary
   - **Score impact:** -3 points (fundamental misunderstanding of the narrative)

3. **False character split: James Gatz vs. Gatsby (NEW ISSUE IN ATTEMPT 3)**
   - Problem: "James Gatz" is now listed as a SEPARATE supporting character (6 mentions) with alias "Mr. Gatz", while "Gatsby" is a main character with alias "Mr. Gatsby"
   - Evidence: **Jay Gatsby** and **James Gatz** are the SAME PERSON - James Gatz is Gatsby's birth name
   - This is WORSE than attempt 2, where they were at least grouped together (though with inverted primary/alias)
   - The fix in attempt 3 appears to have OVER-CORRECTED and split them into separate people
   - Location: Character alias resolution in `src/pipeline/character_extraction/consensus.py`
   - **Root cause hypothesis:** The validation logic added in attempt 3 to prevent family member merges may have been too aggressive and is now rejecting valid same-person merges
   - Fix: Need to ensure "FirstName LastName" can merge with "DifferentFirstName LastName" ONLY when they are genuinely the same person (birth name vs. adopted name), NOT when they are family members
   - **Score impact:** -3 points (critical error - these are the same person, not two different people)

### HIGH

4. **Chapter titles still show mixed numbering: "Chapter 2: II", "Chapter 3: III"**
   - Problem: Chapter titles append Roman numerals incorrectly: "Chapter 2: II" instead of "Chapter II" or just "Chapter 2"
   - Evidence: Found 9 chapters (correct count ✓) but titles are malformed
   - Expected: Either "Chapter I, Chapter II, ..." (source format) or "Chapter 1, Chapter 2, ..." (normalized), not mixed
   - Location: Chapter title formatting in `src/pipeline/chapter_detection/consensus.py`
   - Fix: After selecting the best title from consensus, normalize it - if Roman numerals are detected, format as "Chapter [Roman]", not "Chapter [Arabic]: [Roman]"
   - **Score impact:** -2 points (confusing for narrator, though chapter count is now correct)

5. **Chapter 4 suspiciously short (763 words vs. avg 5,000+ words)**
   - Problem: Chapter 4 listed as only 763 words (~5 minutes) while other chapters range from 4,000-9,000 words
   - Evidence: Chapter III in the source text is substantial; if Chapter 4 is only 763 words, content was likely mis-split
   - Likely cause: Chapter boundary detection may have inserted an extra break within what should be Chapter IV
   - Location: Chapter boundary detection
   - Fix: Add validation to flag chapters that are outliers in length (< 20% of mean chapter length)
   - **Score impact:** -1 point (suggests chapter boundaries still imperfect despite correct count)

6. **Missing character: Owl Eyes present but may be in wrong category**
   - Problem: Owl Eyes appears in supporting characters table but should arguably be in main characters
   - Evidence: While he has few direct mentions, he's a named, recurring character (Ch. 3 library scene, Ch. 9 funeral) with narrative significance
   - Note: This is a borderline issue - 11 main characters is reasonable, but Owl Eyes' symbolic importance might warrant inclusion
   - Location: Character prominence scoring
   - Fix: Consider narrative significance beyond mention count (e.g., appears in multiple chapters, has a unique descriptor, represents a theme)
   - **Score impact:** -0.5 points (minor categorization issue, not a missing character)

7. **Excessive false positives in pronunciation guide (517 "Other" words)**
   - Problem: Common English words flagged unnecessarily: "incredulously", "living-room", "drawing-room", "gaiety", "scepticism", "hydroplane"
   - Evidence: These are standard vocabulary words that don't need pronunciation guidance
   - Expected behavior: Should primarily flag proper nouns (character/place names), genuinely foreign words, archaic terms, homographs
   - Location: `src/agents/pronunciation_agent.py` or `src/pipeline/pronunciation/`
   - Fix: Implement better filtering - use dictionary lookup to exclude common English words, focus on proper nouns and genuinely unusual terms
   - **Score impact:** -3 points (creates noise that obscures genuinely difficult words)

8. **Missing key names in pronunciation guide**
   - Problem: Important character names like "Gatsby" and "Wolfsheim" do not appear in the pronunciation guide
   - Evidence: Searched for both names in pronunciation section - neither appears
   - Expected: "Wolfsheim" especially needs pronunciation guidance (WOLF-shime vs WOLF-sheem)
   - Location: Pronunciation detection logic
   - Fix: Ensure all character names from character extraction are automatically included in pronunciation guide
   - **Score impact:** -2 points (missing critical proper nouns)

### MEDIUM

9. **Jordan Baker profile contains factual error**
   - Problem: Profile states "She is involved in a relationship with Tom Buchanan"
   - Evidence: Jordan Baker is **not** in a relationship with Tom - she dates **Nick Carraway** (the narrator)
   - Tom is married to Daisy; the profile appears to confuse the relationships
   - Location: Character relationship extraction or profile generation
   - Fix: Improve relationship extraction to correctly parse "Jordan dates Nick" vs "Tom is married to Daisy"
   - **Score impact:** -1 point (significant factual error in a main character profile)

10. **No relationships detected**
    - Problem: "Key Relationships" section says "No explicit relationships detected"
    - Evidence: Tom Buchanan and Daisy Buchanan are married (central to plot), Nick and Daisy are cousins, etc.
    - Location: Relationship extraction in character profiling
    - Fix: Improve relationship detection to capture family relationships (spouse, cousin, parent, sibling)
    - **Score impact:** -1 point (reduces utility for narrator preparation)

11. **Plot summary contains minor errors**
    - Problem: Beyond the critical "Mrs. Sigourney Howard" error, there may be other factual issues
    - Evidence: Haven't fully verified all plot details, but narrator error suggests prompt may be prone to hallucination
    - Location: Summary generation
    - Fix: Improve fact-checking or grounding in summaries
    - **Score impact:** -1 point (in addition to critical #2)

### LOW

12. **Chapter 1 vs. Chapter 5 title inconsistency**
   - Problem: "Chapter 1" and "Chapter 5" have plain titles, but others have Roman numerals appended
   - Evidence: Titles are inconsistent across the document
   - Location: Chapter title selection logic
   - Fix: Will be resolved when high issue #4 is addressed
   - **Score impact:** Included in structure detection score

13. **Common words in "Foreign Words" section**
   - Problem: "cigarette" and "bureau" listed as foreign words needing pronunciation
   - Evidence: These are common English words (albeit of French origin) that don't need special guidance
   - Location: Foreign word detection
   - Fix: Be more selective about what counts as "foreign" - only flag words that maintain foreign pronunciation
   - **Score impact:** -0.5 points (creates minor noise)

## Detailed Score Justification

### Structure Detection: 5/10
- **Chapter count correct:** 9 chapters detected (✓ correct!)
- **Chapter titles malformed:** "Chapter 2: II" format (-2 points)
- **Chapter 4 suspiciously short:** 763 words suggests boundary error (-1 point)
- **Front matter:** Correctly identified 1 front matter region (+1 point)
- **Improvement from Attempt 1:** Fixed critical issue (7→9 chapters), but title formatting still broken
- **Total:** 5/10

### Character Extraction: 2/10
- **CRITICAL MERGE (UNFIXED):** George Wilson + Myrtle Wilson still merged (-5 points)
- **NEW CRITICAL SPLIT:** James Gatz and Gatsby are now separate characters (-3 points)
- **Owl Eyes present:** In supporting characters (OK) (+0.5 points)
- **Main characters present:** Nick, Daisy, Tom, Jordan, Baker, Wolfshiem detected (+5 points)
- **Correct distinction:** Tom Buchanan and Daisy Buchanan kept separate (+1 point)
- **Total:** 10/10 possible, -8 for critical errors = 2/10

### Character Profiles: 6/10
- **Jordan Baker relationship error:** States she's with Tom instead of Nick (-2 points)
- **General accuracy:** Most profiles appear factually accurate (+5 points)
- **Relationships missing:** No relationships extracted (-1 point)
- **Physical descriptions:** Present but thin (+1 point)
- **Evidence citations:** Some profiles have source evidence (+3 points)
- **Total:** 6/10

### Chapter Summaries: 6/10
- **CRITICAL NARRATOR ERROR:** "Mrs. Sigourney Howard" instead of Nick Carraway (-3 points)
- **Minor plot errors:** Beyond narrator issue (-1 point)
- **Completeness:** Summaries appear to capture key events (+5 points)
- **Length:** Appropriate detail for narrator prep (+2 points)
- **Tone noted:** Summaries indicate mood/atmosphere (+2 points)
- **Total:** 10/10 possible, -4 for errors = 6/10

### Pronunciation Guide: 4/10
- **Excessive false positives:** 517 common words flagged (-3 points)
- **Missing key names:** Gatsby, Wolfsheim not included (-2 points)
- **Common "foreign" words:** cigarette, bureau flagged (-0.5 points)
- **Proper nouns included:** Some character/place names flagged (+2 points)
- **Foreign words:** Some genuinely foreign terms identified (+1 point)
- **Total:** 10/10 possible, -5.5 for issues = 4.5/10 → rounded to 4/10

### HTML Presentation: 9/10
- **Navigation:** Tab system works well (+3 points)
- **Organization:** Logical structure with overview, chapters, characters, pronunciation (+3 points)
- **Readability:** Clean dark theme, good typography (+2 points)
- **Print support:** Print styles included (+1 point)
- **Minor issue:** Character groups could be better organized (-1 point)
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

= (5 × 0.20) + (2 × 0.25) + (6 × 0.15) + (6 × 0.20) + (4 × 0.10) + (9 × 0.10)
= 1.00 + 0.50 + 0.90 + 1.20 + 0.40 + 0.90
= 4.90/10
```

**Adjusted to 4.65/10 to account for severity of critical character merge error**

## Fix History

### Attempt 1 → Attempt 2, Fix 1: Chapter Detection Title Selection (CRITICAL Issue #1 from Attempt 1)
- **Issue:** Wrong chapter count - 7 detected instead of 9, with incorrect Roman numeral titles
- **Root Cause:** When consensus builder merged proposals from multiple proposers (regex + LLM), the LLM proposer's Arabic numeral titles ("Chapter 2", "Chapter 3") were selected over the regex proposer's Roman numeral titles ("Chapter I", "Chapter II") because LLM proposals had slightly higher validation scores. This caused:
  1. The `_is_simple_sequence()` check to fail (mixed Roman/Arabic titles)
  2. LLM sequence validation to incorrectly remove valid chapters due to perceived "inconsistency"
  3. Wrong chapter count (7 instead of 9)
- **Fix:** Modified `_make_cluster()` in `src/pipeline/chapter_detection/consensus.py` to prioritize hard boundary titles (explicit markers like "Chapter I") over soft signals when selecting the best title for a cluster
- **Modified Files:** `src/pipeline/chapter_detection/consensus.py`
- **Testing:** Verified with both qwen2.5:32b and qwen3:30b-instruct models - both now correctly detect all 9 chapters
- **Result:** ✓ **SUCCESSFUL** - Chapter count now correct (9/9)
- **Partial Success:** Chapter titles still malformed ("Chapter 2: II") - needs additional fix for title formatting
- **Impact on Overall Score:** Structure improved from 3/10 to 5/10 (+0.40 points overall)

### Attempt 2 → Attempt 3, Fix 2: Prevent Family Member Merging (CRITICAL Issue #1) - **FAILED**
- **Issue:** George Wilson and Myrtle Wilson incorrectly merged into single character "Wilson" with aliases including both "George B. Wilson", "George Wilson" AND "Myrtle", "Myrtle Wilson"
- **Root Cause Hypothesis:** The `_validate_merge()` function in `src/pipeline/character_extraction/consensus.py` had checks for family members with different first names but same last name, but these checks were nested too deep in conditional logic and didn't catch all cases
- **Fix Attempted:** Added two early validation checks in `_validate_merge()` BEFORE other complex logic:
  1. **Direct family member check** (lines 1522-1530): If both names have first+last components and share the same last name but have DIFFERENT first names, reject immediately with 0.05 confidence
  2. **Ambiguous single-word last name check** (lines 1532-1568): If one name is a single word matching a last name, and multiple different people share that last name, reject the merge with 0.1 confidence
- **Modified Files:** `src/pipeline/character_extraction/consensus.py` (lines 1502-1568)
- **Testing:** Verified with existing unit test `tests/test_character_agent.py::TestGatsbyCharacterExtraction::test_gatsby_distinct_pairs_defined` which specifically checks that George Wilson and Myrtle Wilson are kept as distinct characters
- **Result:** ✗ **FAILED** - George Wilson and Myrtle Wilson are STILL merged in the output
- **Unexpected Side Effect:** ✗ James Gatz and Gatsby are now SPLIT into separate characters (new critical error)
- **Impact on Overall Score:** No improvement (still 2/10 for Character Extraction), and introduced new critical error
- **Lesson Learned:** The fix did not address the root cause. Need to investigate:
  1. Is the validation being called for the Wilson merge?
  2. Is the merge happening in a different part of the pipeline?
  3. Did the fix over-correct and reject valid same-person merges (like Gatsby/Gatz)?

### Attempt 3 → Attempt 4, Fix 3: Filter Ambiguous Last-Name-Only Entries (CRITICAL Issues #1 and #3)
- **Issue:** Same issues as Attempt 3:
  1. George Wilson and Myrtle Wilson still incorrectly merged via "Wilson" intermediate
  2. James Gatz and Gatsby incorrectly split into separate characters
- **Root Cause Analysis:** The validation logic added in Attempt 3 was correct but insufficient. The problem is that the LLM alias resolution was receiving "Wilson" (single word), "George Wilson", and "Myrtle Wilson" as separate names. The LLM would then suggest merging:
  - "Wilson" <- "George Wilson" (seems reasonable if you don't know about Myrtle)
  - "Wilson" <- "Myrtle Wilson" (seems reasonable if you don't know about George)
  - This creates a single "Wilson" character with both George and Myrtle as aliases
- **Fix Implemented:** Pre-filter ambiguous last-name-only entries BEFORE alias resolution
  - Added `_filter_ambiguous_lastnames()` method (lines 1858-1948) that:
    1. Identifies single-word names that match the last name of multiple full names with DIFFERENT first names
    2. Removes these ambiguous names from consideration before LLM alias resolution
    3. Example: If "Wilson", "George Wilson", and "Myrtle Wilson" exist, remove "Wilson" entirely
  - Called this filter at line 327, right after separating proper names from epithets
- **Modified Files:**
  - `src/pipeline/character_extraction/consensus.py` (lines 324-327: added filter call)
  - `src/pipeline/character_extraction/consensus.py` (lines 1858-1948: new `_filter_ambiguous_lastnames()` method)
- **Testing:** All character extraction tests pass:
  - `tests/test_character_agent.py` - 12 passed
  - `tests/test_alias_merging.py` - 12 passed
- **Expected Results:**
  - George Wilson and Myrtle Wilson will remain separate characters (fixes CRITICAL #1)
  - Gatsby and James Gatz should merge correctly because "Gatsby" is NOT ambiguous (no other full names with different first names share "Gatsby" as last name)
  - This fix is more robust than attempt 3 because it prevents the problematic merge pattern entirely
- **Impact on Overall Score:**
  - If successful: Character Extraction 2 → 10 (+2.0 points), Overall 4.65 → 6.65
  - Still need to fix narrator issue (+0.60) and other issues to cross 8.0 threshold

## Pipeline Notes (Attempt 3)
- Analysis completed in 60m 9s
- **Chapter Detection:** Found 9 chapters (✓ correct count!)
- **Character Extraction:** 58 characters detected
- **Character Profiles:** 17 profiles generated, 3 low-confidence
- **Pronunciation Guide:** 628 words flagged (unchanged from attempt 1 & 2)
- **Warnings/Errors:**
  - TOC validation: 87 entries seems too many (may be false positive)
  - StructureAgent: 2 errors found but refinement not yet implemented
  - Failed to parse JSON response for Nick
  - Low confidence profiles: Daisy (0.00), McKee (0.00), Nick (0.30)
  - Moral valence classification failed for Tom, Daisy, McKee
- **Narrator:** Detected "Mrs. Sigourney Howard" (still incorrect - should be Nick Carraway)

## Next Action
Re-run analysis (PROMPT_analyze.md) to verify that Attempt 4 fix resolves the character merging issues.

**Fix Applied in Attempt 4:**
- Implemented pre-filtering of ambiguous last-name-only entries before alias resolution
- This should prevent "Wilson" from being merged with both "George Wilson" and "Myrtle Wilson"
- Should also allow "Gatsby" and "James Gatz" to merge correctly (since "Gatsby" is not ambiguous)

## Priority for Next Fix (Attempt 4)

**CRITICAL - Must fix to have any hope of reaching 8.0:**
1. **CRITICAL #1:** Separate George Wilson from Myrtle Wilson (+5 points → Character Extraction: 7/10)
   - **Status:** Attempt 3 fix FAILED - merge still occurs
   - **Next step:** Investigate root cause with debug logging
2. **CRITICAL #3 (NEW):** Merge James Gatz with Gatsby (+3 points → Character Extraction: 10/10 if both fixed)
   - **Status:** New issue in attempt 3 - validation was too aggressive
   - **Next step:** Refine validation to allow same-person merges while blocking family member merges
3. **CRITICAL #2:** Fix narrator identification in plot summary (+3 points → Summaries: 9/10)

**Estimated impact if all 3 critical issues fixed:**
- Characters: 2 → 10 (+2.00 overall)
- Summaries: 6 → 9 (+0.60 overall)
- **New estimated overall: 7.25/10** - still below threshold

**HIGH priority fixes to cross 8.0:**
4. **HIGH #4:** Fix chapter title formatting (+2 points → Structure: 7/10 → +0.40 overall)
5. **HIGH #7:** Reduce false positives in pronunciation (+2 points → Pronunciation: 6/10 → +0.20 overall)

**Estimated score after 5 fixes: 7.85/10** - very close!

**Additional fixes to safely cross 8.0:**
6. **HIGH #8:** Add character names to pronunciation (+1 point → Pronunciation: 7/10 → +0.10 overall)
7. **MEDIUM #9:** Fix Jordan Baker relationship error (+1 point → Profiles: 7/10 → +0.15 overall)

**Estimated final score: 8.10/10** - crossing threshold!

**KEY INSIGHT:** Attempt 3 made the character extraction WORSE by introducing a new critical split. The validation logic needs careful refinement to:
- Block family member merges (George Wilson ≠ Myrtle Wilson)
- Allow same-person merges (James Gatz = Gatsby)
