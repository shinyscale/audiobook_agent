# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 12
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 4/10 <- CRITICAL (still 8 chapters, I+II merged)
- Character Extraction: 5/10 <- HIGH (Klipspringer/McKee false merge, duplicates, role-based entries)
- Character Profiles: 5/10 (Jay Gatsby profile is null, appearance="unknown" for all)
- Chapter Summaries: 6/10 (good quality but misaligned due to structure)
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
| 10 | 5.20 | -1.45 | Daisy merge FIXED, characters reduced 99->37, profiles exist but broken |
| 11 | 5.20 | -1.45 | Structure fix did NOT work in full pipeline (8 chapters) |
| 12 | 5.20 | -1.45 | Structure fix STILL not working (TOC-guided failed to find 'I') |

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

This indicates the TOC-guided bypass attempted to run but failed to locate chapter I in the text after the expected position.

### Root Cause Analysis: Why Structure Fix Keeps Failing

The TOC-guided bypass log message shows it's trying to find chapter markers but failing:
```
TOC-guided: could not find 'I' in text after position 5042
```

**The Problem:** The code is looking for a standalone "I" in the text, but in The Great Gatsby, the chapter markers appear as Roman numerals on their own lines. The search is likely failing because:
1. The text might have "I" followed immediately by a newline or other character
2. The search position (5042) may be calculated incorrectly
3. The regex/search pattern may not match the actual format in the text

**What Attempt 2 Got Right:** At attempt 2, the system achieved 9 chapters. Something changed between then and now that broke structure detection.

## Current Issues (Priority Order)

### CRITICAL

1. **Structure: Chapters I and II still merged**
   - Problem: First chapter has 9,317 words covering both Ch I AND Ch II
   - Evidence: Chapter 1 summary describes BOTH dinner at Buchanans AND valley of ashes/Myrtle's party
   - Expected: 9 chapters with ~4,000-6,000 words each
   - Impact: -4 points on Structure, -2 points on Summaries (misalignment)
   - Location: `src/pipeline/chapter_detection/` - the TOC-guided bypass is failing
   - Root Cause: `"TOC-guided: could not find 'I' in text after position 5042"` - the search for chapter "I" is failing
   - Fix: Debug WHY the search fails - check the actual text format at the expected chapter boundary

2. **False alias: Klipspringer merged with McKee**
   - Problem: "Mr. McKee" entry has aliases ["McKee", "Mr. Klipspringer", "Klipspringer"]
   - Evidence: McKee is photographer at Myrtle's party (Ch II). Klipspringer is "the boarder" at Gatsby's mansion who plays piano (Ch V, Ch IX).
   - Impact: Major factual error - two completely different characters merged
   - Location: `src/pipeline/character_extraction_v2/` - alias detection is incorrectly grouping these
   - Fix: Add validation that aliases should appear in similar contexts (same chapters, same scenes)

### HIGH

3. **Jay Gatsby profile is NULL**
   - Problem: The protagonist's profile fields are null (personality=null, appearance=null)
   - Evidence: `jq` query shows Jay Gatsby has null profile despite being main character with 268 mentions
   - Impact: -1.5 points on Profiles
   - Location: Profile generation in character extraction V2 - likely JSON parse failure

4. **Character duplicates: Wilson/George Wilson**
   - Problem: "Wilson" (65 mentions) and "George Wilson" (14 mentions) listed separately
   - Evidence: Both refer to George Wilson, the garage owner
   - Impact: Inflates character list, confuses narrator
   - Location: `src/pipeline/character_extraction_v2/` - need to merge "LastName" with "FirstName LastName"

5. **Character duplicates: Sloane/Mr. Sloane**
   - Problem: "Sloane" (10 mentions) and "Mr. Sloane" (1 mention) listed separately
   - Evidence: Same person - the man who rides horses with Tom
   - Location: `src/pipeline/character_extraction_v2/`

6. **Narrator entries not merged with Nick**
   - Problem: "Narrator" (4), "The narrator" (1), "the narrator" (1) exist separately from Nick Carraway
   - Evidence: Nick IS the narrator in first-person narrative
   - Location: `src/pipeline/character_extraction_v2/`

7. **Owl Eyes duplicated**
   - Problem: "Owl Eyes (the library patron)" and "Man with owl-eyed glasses" are separate entries
   - Evidence: Same person - the bespectacled man at Gatsby's party who appears at the funeral
   - Location: `src/pipeline/character_extraction_v2/`

8. **Role-based entries in character list (14+ false positives)**
   - Problem: Generic roles listed as characters: Butler, The butler, Chauffeur, Gardener, Detective, elevator boy, Lutheran minister, Policeman, New York reporter, The drunken driver, The sobbing singer, Woman in brown riding-habit, Pale well-dressed negro, The second man in the car
   - Evidence: These are role descriptions, not named characters
   - Impact: Dilutes character list, unprofessional for narrator
   - Location: `src/pipeline/character_extraction_v2/supporting_cast.py` - need stronger role filtering

### MEDIUM

9. **Appearance consistently "unknown"**
   - Problem: All main characters have appearance="unknown"
   - Evidence: Tom Buchanan is described in detail in Ch I ("hulking...two arrogant eyes"), yet appearance is "unknown"
   - Location: Profile generation prompts in V2

10. **Pronunciation 86% "unknown"**
    - Problem: 505/586 entries have flag_reason="unknown"
    - Evidence: Only 81 properly categorized (39 proper_noun, 23 homograph, 19 foreign)
    - Impact: Pronunciation guide is nearly useless
    - Location: `src/pipeline/pronunciation_guide/`

11. **Chapter titles partially missing**
    - Problem: Chapters 1, 7, 8 have title=null; others have Roman numerals
    - Evidence: Structure shows null, III, IV, V, VI, VII, null, null
    - Location: Title extraction in chapter detection

## Path to 8.0

**Current: 5.20/10, Need: 8.0/10, Gap: 2.8 points**

| Priority | Fix | Estimated Impact |
|----------|-----|------------------|
| P0 | **Debug TOC-guided search failure** - Why can't it find "I"? | Structure 4->9 = +1.0 overall |
| P0 | Fix chapter alignment when structure is fixed | Summaries 6->8 = +0.4 overall |
| P1 | Fix Klipspringer/McKee false merge | Characters +0.25 |
| P1 | Fix Gatsby profile parse failure | Profiles +0.3 |
| P1 | Merge Wilson/George Wilson, Sloane/Mr. Sloane | Characters +0.25 |
| P1 | Merge Narrator entries with Nick | Characters +0.1 |
| P1 | Filter role-based entries | Characters 5->7 = +0.5 overall |
| P2 | Fix appearance detection | Profiles +0.15 |
| P2 | Fix pronunciation categorization | Pronunciation 4->6 = +0.2 overall |
| **Total** | | **5.20 + 3.15 = ~8.35** |

## Fix History

### Attempt 11 - Structure Fix Applied but Failed
- **APPLIED**: TOC extraction fix, TOC-guided bypass, hard boundary preservation
- **LOCAL VERIFICATION**: Passed (9 chapters)
- **FULL PIPELINE**: Failed (8 chapters, I+II merged)
- **STATUS**: Need to debug why full pipeline doesn't use the fix

### Attempt 12 - Structure Fix Still Failing
- **LOG MESSAGE**: `"TOC-guided: could not find 'I' in text after position 5042"`
- **DIAGNOSIS**: The TOC-guided code IS running, but failing to find chapter "I" in the text
- **LIKELY CAUSE**: Text format mismatch - the actual text may have different formatting than expected

## Next Action

Run PROMPT_fix.md with focus on:

1. **DEBUG THE TOC-GUIDED FAILURE**
   - Look at the actual gatsby.txt around position 5042
   - Check what character/pattern the TOC-guided search is looking for
   - Check if there's a whitespace/encoding issue
   - Add debug logging to print what it's actually searching for vs what's in the text

2. **DO NOT attempt more character/profile fixes until structure is resolved** - it's the foundation for everything else

3. Once structure is fixed, address:
   - Klipspringer/McKee false merge (CRITICAL)
   - Gatsby profile null (HIGH)
   - Character duplicates (HIGH)
   - Role-based filtering (HIGH)

## Notes

- Best score was attempt 2 (7.45/10) with correct 9-chapter detection
- Score has regressed significantly since then (now 5.20)
- The TOC-guided fix IS being triggered but failing to find chapter markers
- Need to examine the actual text format in gatsby.txt to understand why
