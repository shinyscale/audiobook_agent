# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 12
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 4/10 ← CRITICAL (still only 8 chapters, I+II merged)
- Character Extraction: 5/10 ← HIGH (duplicates, wrong aliases, role-based entries)
- Character Profiles: 5/10 (Jay Gatsby null, appearance consistently "unknown")
- Chapter Summaries: 6/10 (good quality but wrong chapter alignment)
- Pronunciation Guide: 4/10 (86% "unknown" categorization)
- HTML Presentation: 8/10 (functional)
- **Overall: 5.20/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |
| 4 | 7.20 | +0.55 | Chapter V back, Wolfsheim merged, pronunciation categories work |
| 5 | 6.70 | +0.05 | REGRESSION: Chapter IV split, profile fix didn't work |
| 6 | 6.15 | -0.50 | REGRESSION: Chapter V MISSING, profiles still broken |
| 7 | - | - | Pipeline crashed (Character model field mismatch) |
| 8 | - | - | Pipeline crashed (same error) |
| 9 | 5.10 | -1.55 | MAJOR REGRESSION: 2 chapters missing, character explosion, 0 profiles |
| 10 | 5.20 | -1.45 | Daisy merge FIXED, characters reduced 99→37, profiles exist but broken |
| 11 | 5.20 | -1.45 | Structure fix did NOT work in full pipeline (8 chapters) |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Last Updated: 2026-01-21 19:12

## Analysis Summary (Attempt 12)

### Pipeline Run Results

**Analysis completed:** 2026-01-21 19:12
**V2 Character Extraction:** Enabled
**Models Used:**
- Structure: qwen3:30b-instruct
- Characters: qwen3-next:80b-a3b-instruct-q8_0
- Summaries: qwen3-next:80b-a3b-instruct-q8_0
- Pronunciation: qwen3:30b-instruct

**Chapter Detection:**
```
Chapter 1: null    - 9,317 words (I+II still merged)
Chapter 2: III     - 5,734 words
Chapter 3: IV      - 5,456 words
Chapter 4: V       - 4,233 words
Chapter 5: VI      - 4,036 words
Chapter 6: VII     - 8,766 words
Chapter 7: null    - 4,530 words (VIII)
Chapter 8: null    - 5,225 words (IX)
```

**Character Count:** 39 characters extracted

**Warning from Log:**
- `TOC-guided: could not find 'I' in text after position 5042`

This indicates the TOC-guided bypass attempted to run but failed to locate chapter I, falling back to the standard detection which merged I+II again.

---

## Analysis Summary (Attempt 11)

### What Was Expected to Work
The structure detection fix was locally verified and showed 9 chapters:
```
Chapters detected: 9
  1: 'I' at 1400 (5,892 words)
  2: 'II' at 34475 (4,280 words)
  ...
```

### What Actually Happened
Full pipeline only detected 8 chapters:
```
Chapter 1: null    - 9,317 words (I+II merged)
Chapter 2: III     - 5,734 words
Chapter 3: IV      - 5,456 words
Chapter 4: V       - 4,233 words
Chapter 5: VI      - 4,036 words
Chapter 6: VII     - 8,766 words
Chapter 7: null    - 4,530 words (VIII)
Chapter 8: null    - 5,225 words (IX)
```

**Root Cause Unknown**: The isolated test works, but the full pipeline doesn't. Possible causes:
1. Different text preprocessing in full pipeline vs test
2. Different LLM client configuration
3. Different caching/state between runs
4. TOC-guided bypass being skipped in full pipeline

### Character Issues Found

**Critical False Alias:**
- "Mr. McKee" has aliases: ["McKee", "Mr. Klipspringer", "Klipspringer"] - WRONG! Klipspringer is a completely different character (the boarder at Gatsby's mansion, nicknamed "the boarder")

**Duplicate Pairs:**
1. "Wilson" (65 mentions) vs "George Wilson" (14 mentions) - same person
2. "Sloane" (10 mentions) vs "Mr. Sloane" (1 mention) - same person
3. "Narrator" (4 mentions), "The narrator" (1), "the narrator" (1) - all Nick Carraway
4. "Owl Eyes (the library patron)" vs "Man with owl-eyed glasses" - same person

**Role-Based False Entries (not real characters):**
- Butler, The butler, Chauffeur, Gardener, Detective, elevator boy, Lutheran minister, Policeman, New York reporter, The drunken driver, The sobbing singer, Woman in brown riding-habit, Pale well-dressed negro, The second man in the car

**Missing Character:**
- Klipspringer (Gatsby's boarder, plays piano at Gatsby's request) - wrongly merged as alias of McKee

### Profile Issues

| Character | Has Profile | Issues |
|-----------|-------------|--------|
| Nick Carraway | ✓ Complete | appearance="unknown" despite being described |
| Jay Gatsby | ✗ null | JSON parse failure noted in profiling |
| Tom Buchanan | ✓ Partial | appearance="unknown" despite detailed description |
| Daisy Buchanan | ✓ | Not checked |
| Jordan Baker | ✓ | Not checked |

## Current Issues (Priority Order)

### CRITICAL

1. **Structure: Chapters I and II still merged**
   - Problem: First chapter has 9,317 words covering both Ch I (Nick's background, dinner at Buchanans) AND Ch II (valley of ashes, Myrtle's party)
   - Evidence: Chapter 1 summary describes: Nick arriving, Buchanan dinner, green light observation, THEN valley of ashes trip, Myrtle's apartment, Tom breaking her nose
   - Expected: 9 chapters with ~4,000-6,000 words each
   - Impact: -4 points on Structure, -2 points on Summaries
   - Location: `src/pipeline/chapter_detection/` - the local fix worked but full pipeline didn't use it
   - Root Cause: **INVESTIGATION NEEDED** - Why did the locally-verified fix not work in the full pipeline?

2. **False alias: Klipspringer merged with McKee**
   - Problem: "Mr. McKee" entry has aliases ["McKee", "Mr. Klipspringer", "Klipspringer"]
   - Evidence: McKee is the photographer at Myrtle's party (Ch II). Klipspringer is the "boarder" living at Gatsby's mansion who plays piano.
   - Impact: Major factual error - two completely different characters merged
   - Location: `src/pipeline/character_extraction_v2/` - alias detection is incorrectly grouping these

### HIGH

3. **Character duplicates: Wilson/George Wilson**
   - Problem: "Wilson" (65 mentions) and "George Wilson" (14 mentions) listed separately
   - Evidence: Both refer to George Wilson, the garage owner
   - Impact: Inflates character list, confuses narrator
   - Location: `src/pipeline/character_extraction_v2/` - need to merge "LastName" with "FirstName LastName"

4. **Character duplicates: Sloane/Mr. Sloane**
   - Problem: "Sloane" (10 mentions) and "Mr. Sloane" (1 mention) listed separately
   - Evidence: Same person - the man who rides horses with Tom
   - Location: `src/pipeline/character_extraction_v2/` - need to merge "Name" with "Mr./Mrs. Name"

5. **Narrator entries not merged with Nick**
   - Problem: "Narrator" (4 mentions), "The narrator" (1), "the narrator" (1) exist separately from Nick Carraway
   - Evidence: Nick IS the narrator in first-person narrative
   - Location: `src/pipeline/character_extraction_v2/` - narrator detection should merge these

6. **Role-based entries in character list (14 false positives)**
   - Problem: Generic roles listed as characters: Butler, Chauffeur, Gardener, Detective, elevator boy, etc.
   - Evidence: These are role descriptions, not named characters
   - Impact: Dilutes character list, unprofessional for narrator
   - Location: `src/pipeline/character_extraction_v2/supporting_cast.py` - need role filtering

### MEDIUM

7. **Jay Gatsby profile is null**
   - Problem: The protagonist's profile failed to generate
   - Evidence: `jq '.characters[] | select(.canonical_name == "Jay Gatsby") | .personality'` returns null
   - Log note: "2 JSON parse failures (Jay Gatsby, Meyer Wolfsheim profiles)"
   - Impact: -1 point on Profiles
   - Location: Profile generation in character extraction V2

8. **Appearance consistently "unknown"**
   - Problem: All main characters have appearance.summary="unknown"
   - Evidence: Tom Buchanan is described in detail in Ch I ("hulking...eyes had two arrogant eyes"), yet appearance is "unknown"
   - Location: Profile generation prompts

9. **Pronunciation 86% "unknown"**
   - Problem: 505/586 entries have flag_reason="unknown"
   - Evidence: Only 81 properly categorized (39 proper_noun, 23 homograph, 19 foreign)
   - Impact: Useless for narrator preparation
   - Location: `src/pipeline/pronunciation_guide/`

10. **Chapter titles partially missing**
    - Problem: Chapters 1, 7, 8 have title=null; others have Roman numerals
    - Evidence: Structure shows null, III, IV, V, VI, VII, null, null
    - Location: Title extraction in chapter detection

## Investigation Required

### Why Did the Structure Fix Fail?

The locally-verified fix (commits 34476d9, 8f42d66) showed:
```
TOC-guided complete: 9 chapters found - bypassing validation/consensus for reliability
Built ChapterMap from TOC: 9 chapters, 51,058 words
```

But the full pipeline produced only 8 chapters. Need to investigate:

1. **Check if TOC-guided bypass was triggered**: Look for the log message in the full pipeline run
2. **Check text preprocessing differences**: Is the full pipeline using a different text input?
3. **Check LLM client differences**: Different model or configuration?
4. **Check caching**: Could stale cache have been used?

The fix MUST work in the full pipeline before other issues can be addressed - structure is foundational.

## Path to 8.0

**Current: 5.20/10, Need: 8.0/10, Gap: 2.8 points**

| Priority | Fix | Estimated Impact |
|----------|-----|------------------|
| P0 | Debug why structure fix didn't work in full pipeline | Structure 4→9 = +1.0 overall |
| P0 | Fix chapter alignment when structure is fixed | Summaries 6→8 = +0.4 overall |
| P1 | Fix Klipspringer/McKee false merge | Characters +0.25 |
| P1 | Merge Wilson/George Wilson, Sloane/Mr. Sloane | Characters +0.25 |
| P1 | Merge Narrator entries with Nick | Characters +0.25 |
| P1 | Filter role-based entries | Characters 5→7 = +0.5 overall |
| P2 | Fix Gatsby profile parse failure | Profiles +0.15 |
| P2 | Fix pronunciation categorization | Pronunciation 4→6 = +0.2 overall |
| **Total** | | **5.20 + 3.0 = ~8.2** |

## Fix History

### Attempt 1-10
(See previous evaluation states)

### Attempt 11 - Structure Fix FAILED
- **APPLIED**: TOC extraction fix, TOC-guided bypass, hard boundary preservation
- **LOCAL VERIFICATION**: Passed (9 chapters)
- **FULL PIPELINE**: Failed (8 chapters, I+II merged)
- **STATUS**: Need to debug why full pipeline doesn't use the fix

## Next Action

Run PROMPT_fix.md with focus on:
1. **DEBUG FIRST**: Understand why the structure detection fix works locally but not in the full pipeline
2. Add logging to identify where chapters I and II boundary detection fails
3. Check if TOC-guided bypass is being triggered in full pipeline

DO NOT attempt more character/profile fixes until structure is resolved - it's the foundation for everything else.

## Notes

- Best score was attempt 2 (7.45/10) with correct 9-chapter detection
- Score has regressed significantly since then (now 5.20)
- The Klipspringer/McKee merge is a new critical bug not seen before
- Character count (39) is reasonable, but quality issues remain
