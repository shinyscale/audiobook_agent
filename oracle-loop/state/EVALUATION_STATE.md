# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 5/10 (REGRESSION: Chapter V now MISSING entirely)
- Character Extraction: 7/10 (unchanged)
- Character Profiles: 4/10 (REGRESSION: fix didn't work, main cast still blank)
- Chapter Summaries: 7/10 (quality good but missing Chapter V)
- Pronunciation Guide: 6/10 (whitelist working)
- HTML Presentation: 8/10 (unchanged)
- **Overall: 6.15/10** (threshold: 8.0, REGRESSION -0.55 from attempt 5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |
| 4 | 7.20 | +0.55 | Chapter V back, Wolfsheim merged, pronunciation categories work |
| 5 | 6.70 | +0.05 | REGRESSION: Chapter IV split, profile fix didn't work |
| 6 | 6.15 | -0.50 | REGRESSION: Chapter V MISSING, profiles still broken |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## What Changed in Attempt 6

### What Failed
1. **Profile fix DID NOT WORK** - Despite updating `mention_results` dict after alias merges, main cast (Nick, Gatsby, Daisy, Tom, Jordan) still have `appearance.summary: "unknown"` or `appearance: null`. Only 3 supporting characters (Dan Cody, Catherine, Wolfshiem) have appearance data.

2. **Structure REGRESSED FURTHER** - Now detecting 8 chapters instead of 9. Chapter V is COMPLETELY MISSING:
   - Titles: null, II, III, IV, VI, VII, VIII, IX
   - Chapter V (Gatsby-Daisy reunion at Nick's house) is not detected at all
   - This is worse than attempt 5 which had Chapter IV split but still 9 chapter-like entries

### LLM Non-Determinism
The structure issues have been non-deterministic across attempts:
- Attempt 2: 9 chapters ✓
- Attempt 3: Chapter V missing ✗
- Attempt 4: 9 chapters ✓
- Attempt 5: Chapter IV split (10 entries)
- Attempt 6: Chapter V missing (8 entries) ✗

## Current Issues (Priority Order)

### CRITICAL

1. **Chapter V MISSING from structure**
   - Problem: Only 8 chapters detected. Sequence is I, II, III, IV, VI, VII, VIII, IX
   - Evidence: Chapter V (Gatsby's reunion with Daisy at Nick's house) is completely absent
   - Impact: Structure score 5/10, Summaries lose 1 chapter (11% of book)
   - Location: `src/pipeline/chapter_detection.py` or structure agent
   - Root cause: LLM non-determinism with temperature > 0
   - Fix: Set `temperature=0.0` for structure agent to ensure deterministic chapter detection

2. **Character Profiles STILL Empty for Main Cast**
   - Problem: Nick, Gatsby, Daisy, Tom, Jordan all have `appearance.summary: "unknown"` or `appearance: null`
   - Evidence: Only 3 supporting characters have appearance data (Cody, Catherine, Wolfshiem)
   - Impact: Profile score 4/10 (worth 0.60 overall points)
   - Location: Profile generation in `src/pipeline/character_extraction_v2/`
   - Previous fix: Attempt 6 modified `mention_results` dict updates - THIS DID NOT WORK
   - Debug needed: The fix may have been correct but profile LLM calls may be failing for main characters
   - Check: Look at `_profiling` for profile generation errors/retries

### HIGH

3. **Chapter I Title is Null**
   - Problem: First chapter has `title: null` instead of "I"
   - Evidence: Other chapters (II, III, IV, VI, VII, VIII, IX) have titles
   - Location: `src/pipeline/chapter_detection.py` - title extraction for first chapter
   - Fix: Ensure first detected chapter gets its roman numeral title

4. **"Narrator" as Separate Character**
   - Problem: "Narrator" (5 mentions) listed as separate character
   - Evidence: Nick Carraway is correctly marked as `is_narrator: true`
   - Location: `src/pipeline/character_extraction_v2/` - filter generic "Narrator"
   - Fix: Add "Narrator" to character exclusion list

### MEDIUM

5. **Wilson Surname Ambiguity**
   - Problem: "Wilson" (65 mentions) separate from George B. Wilson (14) and Myrtle Wilson (23)
   - Note: May be intentionally correct - "Wilson" in text often genuinely ambiguous
   - Impact: Minor

6. **Pronunciation Unknown Category (76%)**
   - Problem: 481 entries (76%) have flag_reason "unknown"
   - Location: `src/pipeline/pronunciation_guide/` - categorization logic
   - Fix: Improve categorization to reduce "unknown" entries

## Path to 8.0

**Current: 6.15/10, Need: 8.0/10, Gap: 1.85 points**

This is the largest gap so far due to compounding regressions.

| Fix | Effort | Estimated Impact |
|-----|--------|------------------|
| Fix Chapter V detection (deterministic) | MEDIUM | +3 on Structure (5→8) = +0.60 overall |
| Fix chapter I title | LOW | +1 on Structure (8→9) = +0.20 overall |
| Fix main cast profiles | HIGH | +4 on Profiles (4→8) = +0.60 overall |

If structure fixed: 6.15 + 0.80 = 6.95
If structure + profiles fixed: 6.95 + 0.60 = 7.55
Still need ~0.45 more to reach 8.0

**Root Cause Analysis:**

The core problem is **LLM non-determinism** for structure detection. Across 6 attempts:
- Sometimes we get 9 chapters (correct)
- Sometimes Chapter IV splits
- Sometimes Chapter V disappears

**Recommended Fix for Attempt 7:**
1. **Set temperature=0.0 for structure agent** - Eliminate non-determinism
2. **Debug profile extraction** - Add logging to understand why main cast profiles fail
3. Consider using a stronger model for structure detection if available

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

### Attempt 5
- **FAILED FIX:** Modified `_convert_to_pipeline_characters()` to pass mentions - did not improve profiles
- **SUCCESSFUL FIX:** Added common first names to pronunciation whitelist
- **REGRESSION:** Structure worse (Chapter IV split)

### Attempt 6
- **FAILED FIX:** Updated `mention_results` dict after alias merges - did not improve profiles
- **REGRESSION:** Structure worse (Chapter V now missing entirely)
- Analysis ran for 60m 6s
- Only 3 characters got profiles (Dan Cody, Catherine, Wolfshiem)

## Next Action
**Phase:** awaiting_fix

Run PROMPT_fix.md to:
1. Set temperature=0.0 for structure agent to eliminate non-determinism
2. Add detailed logging to profile extraction to debug why main cast fails
3. Verify the mention_results fix is actually being used during profile generation
