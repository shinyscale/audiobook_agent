# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 4/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 8/10
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10
- **Overall: 6.90/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | 0.00 | Baseline - Mr. White missing (merged with Mrs. White) |
| 2 | 6.90 | +0.25 | Improved IPA, but character merge bug PERSISTS |

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: Mr. White merged into Mrs. White (ROOT CAUSE FOUND)**
   - Problem: Mrs. White's aliases include "Mr. White" - they are husband and wife (DIFFERENT people)
   - Evidence: `analysis.json` shows `"aliases": ["White", "Mr. White"]` for Mrs. White
   - **ROOT CAUSE IDENTIFIED:**
     - Previous fix added `_are_different_titled_people()` check to `_merge_title_variants()` only
     - But the actual merge happens in `_merge_within_main_cast()` Pass 2 (lines 816-872)
     - Pass 2 uses fuzzy spelling match with 85% threshold
     - "Mr. White" vs "Mrs. White" has 95% similarity → exceeds threshold → MERGED
     - The `_are_different_titled_people()` check is NOT called in Pass 2
   - Location: `src/agents/characters_v2.py` lines 840-871 (`_merge_within_main_cast` Pass 2)
   - Fix: Add `_are_different_titled_people()` check before fuzzy merge at line 840

### HIGH
2. **Spurious characters: "old man" and "old woman" exist as separate entries**
   - Problem: These generic descriptors should not be characters - they refer to Mr. and Mrs. White in Chapter 3
   - Evidence: Both have `mention_count: 1`, no aliases, appear only in Part III's `characters_present`
   - Location: Main cast extraction accepting generic noun phrases as character names
   - Fix: Filter out generic descriptors like "old man", "old woman", "stranger", "visitor" during extraction

3. **Chapter 3 uses generic references instead of named characters**
   - Problem: Part III's `characters_present` lists "old man" and "old woman" instead of "Mr. White" and "Mrs. White"
   - Evidence: `structure[2].characters_present = ["old man", "old woman"]`
   - Likely cause: Downstream of character extraction issue - if spurious characters are removed, this may self-correct
   - May also need character presence detection improvement

### MEDIUM
4. **Chapter titles are null**
   - Problem: Structure entries have `title: null` instead of "I", "II", "III"
   - Evidence: The original text uses Roman numerals for part divisions
   - Location: Chapter detection regex or title extraction
   - Fix: Improve Roman numeral title detection

5. **Some pronunciation false positives remain**
   - Problem: Common words flagged unnecessarily: "house", "slushy", "out-of-the-way"
   - Evidence: These are standard English words that don't need pronunciation help
   - Location: Pronunciation detection filtering
   - Fix: Add common word filter or improve detection criteria

### LOW
6. **Empty relationships section in character profiles**
   - Problem: Character profiles have `"relationships": {}`
   - Evidence: Mrs. White should have husband relationship to Mr. White, mother to Herbert
   - Lower priority since fixing character merge would enable proper relationship detection

## Investigation Summary

### Why the Previous Fix Failed

**Attempt 1 Fix:** Modified `main_cast.py` prompt rules about title+surname characters
- Result: LLM extraction may have been correct, but post-processing re-merged them

**Attempt 2 Fix:** Added `_are_different_titled_people()` check to `_merge_title_variants()`
- Result: Fix was in WRONG LOCATION - that function checks name containment, not fuzzy spelling
- The actual merge happens via FUZZY SPELLING MATCH in `_merge_within_main_cast()` Pass 2

### Data Flow Trace (Corrected)
1. LLM correctly extracts Mr. White and Mrs. White as separate characters
2. `_merge_title_variants()` runs - characters survive (fix works here but wasn't needed here)
3. `_merge_same_firstname_variants()` runs - characters survive (no first name match)
4. `_merge_within_main_cast()` Pass 1 runs - characters survive (different name lengths)
5. **`_merge_within_main_cast()` Pass 2 runs - MERGES characters** because:
   - `SequenceMatcher("mr. white", "mrs. white").ratio() = 0.95`
   - 0.95 >= 0.85 threshold
   - No `_are_different_titled_people()` check exists here
6. Mrs. White (more mentions) absorbs Mr. White as alias

### Correct Fix Location
File: `src/agents/characters_v2.py`
Function: `_merge_within_main_cast()`
Lines: 840-871 (Pass 2: spelling variant merge)

Add the same safety check that exists in `_merge_title_variants()`:
```python
# Around line 840, before the similarity >= 0.85 check:
if similarity >= 0.85:
    # SAFETY CHECK: Don't merge if both have different title prefixes
    if self._are_different_titled_people(char_name, other_name):
        continue  # Skip - they're different people
    # ... rest of merge logic
```

## Fix History

### Attempt 1 - Fix 1: Title-based character distinction in prompts (FAILED)
- Modified `main_cast.py` prompt rules
- Result: Didn't prevent post-processing merge

### Attempt 2 - Fix 1: Block title-variant merge in post-processing (WRONG LOCATION)
- Added `_are_different_titled_people()` to `_merge_title_variants()`
- Result: Fix works but was placed in wrong function - the merge happens elsewhere
- Tests passed (342/345) but bug persisted

## Next Action
Run PROMPT_fix.md to add `_are_different_titled_people()` check to `_merge_within_main_cast()` Pass 2 at line 840.
