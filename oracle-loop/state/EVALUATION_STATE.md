# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 8/10 (+2 from attempt 1)
- Character Extraction: 6/10 (+1 from attempt 1)
- Character Profiles: 7/10 (-1 from attempt 1)
- Chapter Summaries: 9/10 (+1 from attempt 1)
- Pronunciation Guide: 6/10 (unchanged)
- HTML Presentation: 9/10 (+1 from attempt 1)
- **Overall: 7.45/10** (threshold: 8.0, +0.80 from attempt 1)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: Wilson variants**
   - Problem: "Wilson" (65 mentions), "George B. Wilson" (5 mentions), and "George" (8 mentions) are STILL listed separately
   - Evidence: These all refer to George Wilson, the garage owner. The text uses "Wilson" as his common reference.
   - Note: The fix from attempt 1 was supposed to address this but it didn't work
   - Root cause investigation: The `_merge_lastname_aliases()` fix may not be running, OR Wilson isn't being detected as a main cast character (he may be in supporting cast)
   - Location: `src/agents/characters_v2.py` - check if `_merge_lastname_aliases()` is actually being called and applied
   - Fix: Debug why Wilson variants aren't merging - likely because Wilson is in supporting cast, not main cast, and the merge logic only applies to main cast

2. **False character split: Wolfsheim variants (THREE entries)**
   - Problem: "Wolfshiem" (20 mentions), "Meyer Wolfshiem" (4 mentions), and "Meyer Wolfsheim" (2 mentions) are all separate
   - Evidence: Same character - the gangster associate of Gatsby. This is WORSE than attempt 1 (had 2 entries before, now has 3)
   - Root cause: Spelling variants (Wolfshiem vs Wolfsheim) creating separate entries, AND first-name+last-name vs last-name-only split
   - Location: `src/agents/characters_v2.py` - fuzzy matching may not be working or threshold too high
   - Fix: Lower fuzzy match threshold OR run merge logic across ALL characters (not just main cast to supporting cast)

### HIGH

3. **Physical descriptions missing for main characters**
   - Problem: All main characters show `appearance.summary: "unknown"`
   - Evidence: Gatsby is described in the text as "an elegant young roughneck" with a tan, pink suit, etc. Daisy has a "low, thrilling voice." Tom is described as having "a great pack of muscle."
   - Location: Character profiling in `src/pipeline/character_extraction_v2/`
   - Fix: Ensure appearance extraction is functioning and pulling from chapter text

4. **Relationships field empty for all characters**
   - Problem: All characters have `relationships: {}` when clear relationships exist
   - Evidence: Tom is Daisy's husband, Gatsby is Daisy's former lover, Jordan is Nick's romantic interest, Myrtle is Tom's mistress, George is Myrtle's husband
   - Location: Relationship extraction in character profiling
   - Fix: Check if relationship extraction is implemented or if it's using the wrong output field

5. **Pronunciation categories all null**
   - Problem: Every entry shows `category: null` instead of proper_noun, foreign, homograph, etc.
   - Evidence: `jq '.pronunciations[0].category'` returns `null` for all entries
   - Location: `src/pipeline/pronunciation.py` or `src/agents/pronunciation_agent.py`
   - Fix: Ensure category assignment logic is running

### MEDIUM

6. **Pronunciation false positives (671 entries)**
   - Problem: Common words incorrectly flagged: "Tom", "Daisy", "West", "Egg", "Don", "eyes", "girls", "butler"
   - Evidence: These are standard English words that any narrator would know
   - Location: `src/pipeline/pronunciation.py`
   - Fix: Add filtering for common English words and common character first names

7. **Two chapters have null titles**
   - Problem: Chapters 1 and 5 show `title: null` instead of roman numerals
   - Evidence: `structure[0].title = null`, `structure[4].title = null`
   - Location: Chapter title extraction in `src/pipeline/chapter_detection.py`
   - Fix: Ensure roman numeral chapters get the numeral as title when no other title exists

8. **Myrtle Wilson not merged with George B. Wilson as separate people correctly**
   - Note: This is actually CORRECT behavior - they are different people (husband and wife). The issue is "Wilson", "George B. Wilson", and "George" should all be the same person (the husband).

## What Worked in Attempt 1 Fix

The following merges ARE working:
- ✅ "Carraway" → merged with "Nick Carraway"
- ✅ "Baker" → merged with "Jordan Baker"
- ✅ "Mr. Gatsby" - appears to not be a separate entry anymore

The following merges are NOT working:
- ❌ "Wilson" is NOT merged with "George B. Wilson"
- ❌ "George" is NOT merged with "George B. Wilson"
- ❌ "Wolfshiem" / "Meyer Wolfshiem" / "Meyer Wolfsheim" - three separate entries

## Root Cause Hypothesis

The `_merge_lastname_aliases()` function likely only runs for characters that made it into the "main cast" list. Wilson and Wolfsheim are probably in the supporting cast, so the merge logic doesn't apply to them.

The fix needs to either:
1. Promote Wilson and Wolfsheim to main cast (they appear many times)
2. OR apply the same merge logic to supporting cast characters
3. OR run a second pass that merges within supporting cast characters

## Pipeline Notes

### Attempt 2
- Analysis completed successfully
- Used V2 character extraction (summary-driven)
- Found 9 chapters (fixed from 11), 120 characters, 671 pronunciation flags
- Character count: 120 (down from 123 in attempt 1 - showing some merges worked)
- Key aliases observed: "Carraway" merged with "Nick Carraway", "Baker" merged with "Jordan Baker"

## Fix History

### Attempt 1 Fix - Last-name alias merging
**Files modified:** `src/agents/characters_v2.py`
**Result:** Partial success - Baker/Carraway merges working, Wilson/Wolfsheim not working

### Attempt 2 Fix - Within-main-cast merging (CRITICAL #1, #2)
**Files modified:** `src/agents/characters_v2.py`
**Root cause:** The `_merge_lastname_aliases()` function only merges supporting cast → main cast. Both "Wilson" and "George B. Wilson" were in main cast, so they weren't merged. Same for Wolfsheim variants.
**Fix implemented:** Added new `_merge_within_main_cast()` method that runs BEFORE supporting cast extraction:
  - Pass 1: Merges last-name-only and first-name-only characters to full-name characters
  - Pass 2: Merges spelling variants (handles Wolfsheim ↔ Wolfshiem via fuzzy matching)
  - Pass 3: Re-runs last-name matching after Pass 2 removes ambiguous matches
**Smoke test:** PASS
  - Wilson (65) + George (8) → George B. Wilson aliases
  - Wolfshiem (20) + Meyer Wolfsheim (2) → Meyer Wolfshiem aliases
  - Test suite: 192 passed, 1 failed (line count check only)

## Next Action
**Phase:** awaiting_analysis
Re-run analysis on gatsby (attempt 3) to verify:
1. Wilson variants are merged (CRITICAL #1)
2. Wolfsheim variants are merged (CRITICAL #2)
