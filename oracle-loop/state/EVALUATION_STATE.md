# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 8/10 (+1 from attempt 3, Chapter V now detected)
- Character Extraction: 7/10 (+1 from attempt 3, Wolfsheim merged!)
- Character Profiles: 5/10 (unchanged - main cast still "unknown")
- Chapter Summaries: 9/10 (unchanged, excellent quality)
- Pronunciation Guide: 5/10 (+1 from attempt 3, categories working)
- HTML Presentation: 8/10 (unchanged)
- **Overall: 7.20/10** (threshold: 8.0, +0.25 from attempt 3)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |
| 4 | 7.20 | +0.55 | Chapter V back, Wolfsheim merged, pronunciation categories work |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## What Improved in Attempt 4

1. ✅ **Chapter V Detection Fixed** - 9 chapters now detected correctly (was 8 in attempt 3)
2. ✅ **Wolfsheim Merge Working** - "Meyer Wolfshiem" (32 mentions) with alias "Wolfshiem" - was 2 separate entries!
3. ✅ **Role Field Populated** - Characters now have roles (protagonist/antagonist/supporting/minor)
4. ✅ **Pronunciation Categories Working** - flag_reason field shows 148 proper_noun, 23 homograph, 15 foreign, 477 unknown
5. ✅ **George → George Wilson Merge** - "George" now alias of "George Wilson" (14 mentions total)

## Current Issues (Priority Order)

### CRITICAL

1. **Character Profiles Empty for Main Cast**
   - Problem: Nick Carraway, Jay Gatsby, Daisy Buchanan, Tom Buchanan, Jordan Baker all have `appearance.summary: "unknown"` and `relationships: {}`
   - Evidence: Only 3 characters have appearance descriptions (George Wilson, Catherine, Wilson)
   - Impact: -4 points on Character Profiles score (currently 5/10)
   - Location: `src/pipeline/character_extraction_v2/` - profile extraction phase
   - Root cause: Profile extraction appears to only run for supporting cast, not main cast
   - Fix: Debug why main cast profiles aren't being extracted. Check if there's a threshold or filter issue.

### HIGH

2. **Wilson Surname Ambiguity**
   - Problem: "Wilson" (65 mentions) is separate from both "George Wilson" (14) and "Myrtle Wilson" (23)
   - Evidence: In the text, "Wilson" can refer to either character depending on context
   - Note: This may be CORRECT BEHAVIOR - "Wilson" is genuinely ambiguous
   - Impact: Not necessarily a bug, but reduces character extraction score
   - Location: `src/agents/characters_v2.py` - merge logic
   - Recommendation: Consider adding "Wilson" as alias to BOTH George Wilson and Myrtle Wilson, or document this as expected behavior for ambiguous surnames

3. **Buchanan Surname Not Merged**
   - Problem: "Buchanan" (4 mentions) is a separate entry from Tom/Daisy Buchanan
   - Evidence: References to "Buchanan" in text usually mean Tom, rarely both
   - Location: `src/agents/characters_v2.py` - surname merge logic
   - Fix: Apply same surname merge logic to Buchanan as applied to other names

4. **Pronunciation False Positives - Common First Names**
   - Problem: Common first names flagged: Tom, Daisy, Nick, Jordan, George, Catherine, Dan, Jay
   - Evidence: These are standard English names that don't need pronunciation guidance
   - Impact: 663 entries still too high, many false positives
   - Location: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` - COMMON_WORDS_WHITELIST
   - Fix: Add common first names to whitelist: Tom, Nick, Dan, Jay, George, Catherine, etc.

### MEDIUM

5. **Chapter Titles Null for I and V**
   - Problem: Chapters 1 and 5 have `title: null` instead of roman numerals "I" and "V"
   - Evidence: Other chapters have correct titles (II, III, IV, VI, VII, VIII, IX)
   - Location: `src/pipeline/chapter_detection.py` or structure agent
   - Fix: Ensure all roman numeral chapters get the numeral as title

6. **"Narrator" as Separate Character**
   - Problem: "Narrator" (5 mentions) is listed as a separate character with role "supporting"
   - Evidence: Nick Carraway is correctly marked as `is_narrator: true`
   - Location: `src/pipeline/character_extraction_v2/` - should filter generic "Narrator" references
   - Fix: Filter out "Narrator" as a character name since the actual narrator (Nick) is already identified

7. **Location Words as Proper Nouns**
   - Problem: "West", "East", "Egg", "War" flagged as proper nouns
   - Evidence: These are common English words, even in place name contexts
   - Location: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
   - Fix: Add location/direction words to whitelist

## Path to 8.0

**Current: 7.20/10, Need: 8.0/10, Gap: 0.80 points**

Fastest path to reach threshold:

| Fix | Effort | Estimated Impact |
|-----|--------|------------------|
| Character Profiles for Main Cast | HIGH | +1.5 on Profiles (5→8) = +0.45 overall |
| Pronunciation Whitelist (first names) | LOW | +1 on Pronunciation (5→6) = +0.10 overall |
| Buchanan merge | LOW | +0.5 on Characters (7→7.5) = +0.125 overall |

**Recommended focus for Attempt 5:**
1. Fix character profiles for main cast - highest impact
2. Add common first names to pronunciation whitelist - easy win
3. (Optional) Fix Buchanan merge

If profiles are fixed: 7.20 + 0.45 = 7.65
If profiles + pronunciation: 7.65 + 0.10 = 7.75
If all three: 7.75 + 0.125 = 7.875 (very close!)

## Fix History

### Attempt 2
- Fixed chapter detection (was splitting chapter 7 at section break)
- Added character merge logic for main cast

### Attempt 3
- Investigated Chapter V missing (non-deterministic)
- Added role field to character export
- Expanded pronunciation whitelist (115→162 entries)

### Attempt 4
- Added `_merge_within_supporting_cast` function
- Enhanced `_merge_lastname_aliases` with first-name matching
- Chapter V detection improved (now working)
- Wolfsheim merge now working
- George → George Wilson merge working

## Next Action
**Phase:** awaiting_fix
Run PROMPT_fix.md to address:
1. Character profiles for main cast (CRITICAL #1) - highest priority
2. Common first names in pronunciation whitelist (HIGH #4) - easy win
