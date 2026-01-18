# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 2 of 5
- **Phase:** awaiting_fix

## Output Files
- HTML: output/gatsby/report.html
- JSON: output/gatsby/analysis.json
- Quality Report: output/gatsby_20260117_201435/quality.md

## Latest Scores
- Structure Detection: 5/10 ← FAILING
- Character Extraction: 2/10 ← CRITICAL FAILURE
- Character Profiles: 6/10 ← FAILING
- Chapter Summaries: 6/10 ← FAILING
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 4.65/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL

1. **False character merge: George Wilson + Myrtle Wilson**
   - Problem: "Wilson" character has aliases: "George B. Wilson, George Wilson, **Myrtle, Myrtle Wilson**, George, Mrs. Wilson"
   - Evidence: George Wilson and Myrtle Wilson are **HUSBAND AND WIFE** - two completely different people who should be separate characters
   - Location: Character alias resolution in `src/agents/character_agent.py` or `src/pipeline/character_extraction/`
   - Fix: Improve alias grouping to recognize that characters sharing only a surname (especially with gendered titles like Mr./Mrs.) are often different people (spouses, siblings)
   - **Score impact:** -5 points (catastrophic main character error - Myrtle is a major character)

2. **Narrator identified as "Mrs. Sigourney Howard" instead of Nick Carraway**
   - Problem: Plot summary begins "Mrs. Sigourney Howard, recounting her experiences from the summer of 1922..."
   - Evidence: The narrator is **Nick Carraway** (male), not "Mrs. Sigourney Howard" (who doesn't exist in the novel)
   - This is a hallucination - the system invented a non-existent character as the narrator
   - Location: Plot summary generation in `src/agents/summary_agent.py`
   - Fix: Either extract narrator identity from character metadata (Nick Carraway is tagged as narrator) or verify narrator name against character list before generating plot summary
   - **Score impact:** -3 points (fundamental misunderstanding of the narrative)

3. **False character split: James Gatz vs. Gatsby**
   - Problem: "James Gatz" is listed as a main character (269 mentions) with aliases "Mr. Gatz, Gatsby, Mr. Gatsby"
   - Evidence: This is backwards - **Jay Gatsby** should be the primary entry with "James Gatz" as an alias (his birth name)
   - The system treats them as if "James Gatz" is the main identity, which misrepresents the novel
   - Location: Character alias resolution and primary name selection
   - Fix: When selecting primary vs. alias names, prefer the name used most frequently in narrative prose (not dialogue) and the name most central to the character's identity
   - **Score impact:** -1 point (while technically merged, the primary/alias relationship is inverted)

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
- **CRITICAL MERGE:** George Wilson + Myrtle Wilson merged (-5 points)
- **False split/inversion:** James Gatz primary instead of Jay Gatsby (-1 point)
- **Owl Eyes present:** In supporting characters (OK) (+0.5 points)
- **Main characters present:** Nick, Daisy, Tom, Jordan, Baker, Wolfshiem detected (+5 points)
- **Correct distinction:** Tom Buchanan and Daisy Buchanan kept separate (+1 point)
- **Total:** 10/10 possible, -6 for critical errors = 4/10 → adjusted to 2/10 for severity

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

### Attempt 1 → Attempt 2, Fix 1: Chapter Detection Title Selection (CRITICAL Issue #1)
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

## Pipeline Notes (Attempt 2)
- Analysis completed in 64m 7s
- **Chapter Detection:** Found 9 chapters (✓ correct count!)
- **Character Extraction:** 58 characters detected
- **Character Profiles:** 16 profiles generated, 4 low-confidence
- **Pronunciation Guide:** 628 words flagged (unchanged from attempt 1)
- **Warnings/Errors:**
  - TOC validation: 87 entries seems too many (may be false positive)
  - StructureAgent: 2 errors found but refinement not yet implemented
  - Multiple "Failed to parse JSON response" errors for character profiles (Tom, McKee, Sloane, Meyer)
  - Low confidence profiles: Tom (0.30), McKee (0.30), Sloane (0.30), Meyer (0.30)
  - Moral valence classification failed for Tom, Daisy, Baker

## Next Action
Proceed to fix phase (PROMPT_fix.md) to address critical character merge issue (George + Myrtle Wilson) as top priority, followed by narrator hallucination error.

## Priority for Next Fix

**Must fix to reach 8.0 threshold:**
1. **CRITICAL #1:** Separate George Wilson from Myrtle Wilson (+5 points → Character Extraction: 7/10)
2. **CRITICAL #2:** Fix narrator identification in plot summary (+3 points → Summaries: 9/10)
3. **HIGH #4:** Fix chapter title formatting (+2 points → Structure: 7/10)

**Estimated impact of these 3 fixes:**
- Structure: 5 → 7 (+0.40 overall)
- Characters: 2 → 7 (+1.25 overall)
- Summaries: 6 → 9 (+0.60 overall)
- **New estimated overall: 6.90/10**

**Still need ~1.1 more points - likely from:**
4. **HIGH #7:** Reduce false positives in pronunciation (+1.5 points → Pronunciation: 5.5/10 → +0.15 overall)
5. **HIGH #8:** Add character names to pronunciation (+1 point → Pronunciation: 6.5/10 → +0.10 overall)
6. **MEDIUM #9:** Fix Jordan Baker relationship error (+1 point → Profiles: 7/10 → +0.15 overall)

**Estimated score after all 6 fixes: 7.30/10** - still below threshold

**Additional fixes needed to cross 8.0:**
7. **MEDIUM #10:** Extract relationships (+1 point → Profiles: 8/10 → +0.15 overall)
8. **Fix any remaining summary errors** (+1 point → Summaries: 10/10 → +0.20 overall)

**Estimated score after 8 fixes: 7.65/10** - closer but still below threshold

**Final push:**
9. **HIGH #5:** Investigate Chapter 4 length issue and fix boundary detection if needed (+1 point → Structure: 8/10 → +0.20 overall)

**Estimated final score: 7.85/10** - very close to threshold

The path to 8.0+ requires fixing **all critical issues** plus most high-priority issues. The system is improving (5.15 → 4.65 shows regression in character extraction despite structure improvement), indicating that the character merge issue introduced in attempt 2 is more severe than the chapter count issue that was fixed.
