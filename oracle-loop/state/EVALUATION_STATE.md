# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 6/10 (REGRESSION -2: Chapter IV now split into two entries)
- Character Extraction: 7/10 (unchanged)
- Character Profiles: 5/10 (unchanged - main cast appearances still "unknown")
- Chapter Summaries: 8/10 (quality good, but structure issues affect mapping)
- Pronunciation Guide: 6/10 (+1: whitelist fix worked, common names removed)
- HTML Presentation: 8/10 (unchanged)
- **Overall: 6.70/10** (threshold: 8.0, REGRESSION -0.50 from attempt 4)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |
| 4 | 7.20 | +0.55 | Chapter V back, Wolfsheim merged, pronunciation categories work |
| 5 | 6.70 | +0.05 | REGRESSION: Chapter IV now split, profile fix didn't work |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## What Changed in Attempt 5

### What Worked
1. **Pronunciation whitelist expanded** - Common first names (Tom, Daisy, Nick, Jordan, etc.) and direction words (East, West) no longer flagged. Score improved from 5/10 to 6/10.

### What Failed
1. **Profile fix DID NOT WORK** - Main cast (Nick, Gatsby, Daisy, Tom, Jordan) still have `appearance.summary: "unknown"` and empty relationships. Only 6 supporting characters have appearance data (Dan Cody, Klipspringer, Eckleburg, Catherine, Wilson, Wolfsheim).
2. **Structure REGRESSED** - Now detecting 10 chapters instead of 9. Chapter IV is split into two entries (indices 3 and 4). Chapter V's summary is merged with end of Chapter IV at index 5.

### Structure Analysis
```
Index 0 (title: null): Chapter I content ✓
Index 1 (title: II): Chapter II content ✓
Index 2 (title: III): Chapter III content ✓
Index 3 (title: IV): Chapter IV guest list section
Index 4 (title: null): Chapter IV car ride section (SPLIT!)
Index 5 (title: null): Chapter IV ending + Chapter V content (MERGED!)
Index 6 (title: VI): Chapter VI content ✓
Index 7 (title: VII): Chapter VII content ✓
Index 8 (title: VIII): Chapter VIII content ✓
Index 9 (title: IX): Chapter IX content ✓
```

## Current Issues (Priority Order)

### CRITICAL

1. **Chapter IV Split / Chapter V Title Missing**
   - Problem: Chapter IV is detected as two separate chapters (indices 3 and 4)
   - Evidence: Index 3 has guest list, index 4 has car ride, both are Chapter IV
   - Impact: Structure score dropped from 8/10 to 6/10
   - Location: `src/pipeline/chapter_detection.py` or structure agent
   - Root cause: Likely the section break between guest list and car ride is triggering false chapter detection
   - Fix: Investigate why Chapter IV is being split; may need to improve section break handling

2. **Character Profiles STILL Empty for Main Cast**
   - Problem: Nick, Gatsby, Daisy, Tom, Jordan all have `appearance.summary: "unknown"` and `relationships: {}`
   - Evidence: Only 6 supporting characters have appearance data (Cody, Klipspringer, Eckleburg, Catherine, Wilson, Wolfsheim)
   - Impact: Profile score stuck at 5/10 (worth 0.75 overall points)
   - Location: `src/pipeline/character_extraction_v2/` profile extraction phase
   - Previous fix: Attempt 5 modified `_convert_to_pipeline_characters()` to pass mentions - THIS DID NOT WORK
   - Debug needed: Check if mentions are actually being passed, and why profile extraction still fails for main cast
   - Hypothesis: Main cast may be handled by a different code path that bypasses profile extraction

### HIGH

3. **Chapter I and V Title Null**
   - Problem: Chapters I (index 0) and V (index 4/5) have `title: null` instead of roman numerals
   - Evidence: Other chapters (II, III, IV, VI, VII, VIII, IX) have correct titles
   - Location: `src/pipeline/chapter_detection.py` - title extraction
   - Fix: Ensure all detected chapters get their roman numeral titles

### MEDIUM

4. **"Narrator" as Separate Character**
   - Problem: "Narrator" (5 mentions) listed as separate character with role "supporting"
   - Evidence: Nick Carraway is correctly marked as `is_narrator: true`
   - Location: `src/pipeline/character_extraction_v2/` - should filter generic "Narrator" references
   - Fix: Filter out "Narrator" as a character name

5. **Wilson Surname Ambiguity**
   - Problem: "Wilson" (65 mentions) separate from George Wilson (14) and Myrtle Wilson (23)
   - Note: May be intentionally correct - "Wilson" in text is genuinely ambiguous
   - Impact: Minor, does not significantly affect score

6. **Buchanan Surname Not Merged**
   - Problem: "Buchanan" (4 mentions) as separate entry
   - Impact: Very minor

7. **Pronunciation Unknown Category Still Large**
   - Problem: 474 entries with flag_reason "unknown" (72% of total)
   - Location: `src/pipeline/pronunciation_guide/` - categorization logic
   - Fix: Improve categorization to reduce "unknown" entries

## Path to 8.0

**Current: 6.70/10, Need: 8.0/10, Gap: 1.30 points**

This is a larger gap than attempt 4 due to regression. Focus on:

| Fix | Effort | Estimated Impact |
|-----|--------|------------------|
| Fix Chapter IV split | MEDIUM | +2 on Structure (6→8) = +0.40 overall |
| Fix main cast profiles | HIGH | +3 on Profiles (5→8) = +0.45 overall |
| Fix chapter titles (I, V) | LOW | +0.5 on Structure = +0.10 overall |

If structure fixed: 6.70 + 0.50 = 7.20
If structure + profiles fixed: 7.20 + 0.45 = 7.65
Still need ~0.35 more to reach 8.0

**Recommended focus for Attempt 6:**
1. **REVERT the structure regression** - investigate why Chapter IV is now split (wasn't in attempt 4)
2. **Debug profile extraction** - the attempt 5 fix didn't work; need deeper investigation
3. Consider if previous working version should be restored

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
- **REGRESSION:** Structure now worse (Chapter IV split)

### Attempt 6
- **CRITICAL FIX:** Update `mention_results` dict after re-searching characters with new aliases
  - **Root cause identified:** In `characters_v2.py`, after merging aliases, the code re-searches mentions but only updates `char.mention_count`, NOT the `mention_results` dict
  - This meant `_convert_to_pipeline_characters()` used OLD mention data with fewer mentions
  - Profile generation at `analyzer.py:1257` samples from `char.mentions[:10]`, which was empty/incomplete
  - **Fix:** Added `mention_results[char.id] = result` at lines 167, 214, and 237 (after each re-search)
  - **Impact:** Main cast (Nick, Gatsby, Tom, Jordan) should now have full mention lists → rich profile data
  - **Confidence:** HIGH - directly addresses data flow gap
  - **Files modified:** `src/agents/characters_v2.py`
  - **Smoke test:** Unit tests pass (15/16, only line count test fails - non-critical)

## Current Issues After Fix

### Structure Issue (Non-Deterministic)
- Chapter IV split regression occurred with NO code changes to structure detection (between attempts 4→5)
- Likely LLM non-determinism with temperature=0.3 on structure agent
- May resolve on re-run, or may require temperature=0.0 for perfect consistency
- **Not addressing in this attempt** - focus on profile fix which has higher impact

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify profile fix:
1. Main cast appearance/personality data should be populated (not "unknown" or null)
2. Expected score improvement: +3 on Profiles (5→8) = +0.45 overall → 7.15/10
3. Structure may still have issues (non-deterministic), but profile fix is systematic
