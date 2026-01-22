# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 14
- **Phase:** analysis_in_progress
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 5/10 ← (I+II now separated, but IV split into 2)
- Character Extraction: 6/10 ← (Klipspringer/McKee fixed, but duplicates and role entries remain)
- Character Profiles: 4/10 ← CRITICAL (Tom, Jordan have NULL profiles)
- Chapter Summaries: 6/10 (good quality but misaligned due to IV split)
- Pronunciation Guide: 3/10 ← CRITICAL (88% "unknown" categorization)
- HTML Presentation: 8/10 (functional)
- **Overall: 5.40/10** (threshold: 8.0)

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
| 13 | 5.40 | -1.25 | I+II separated ✓, IV split ✗, Klipspringer/McKee fixed ✓, profiles regressed |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Last Updated: 2026-01-21

## Analysis Summary (Attempt 13)

### Key Changes from Attempt 12
**Improvements:**
- Chapters I and II are NOW CORRECTLY SEPARATED (was merged before)
- Klipspringer and McKee are NOW SEPARATE characters (was incorrectly merged)
- Character count reduced to 41 (down from higher numbers in earlier attempts)

**Regressions:**
- Chapter IV incorrectly split into 2 parts (763 words + 4693 words)
- Tom Buchanan profile is completely NULL
- Jordan Baker profile is completely NULL
- Pronunciation 88% "unknown" (worse than earlier attempts)

### Structure Analysis (10 chapters detected, expected 9)

| # | Title | Words | Content | Status |
|---|-------|-------|---------|--------|
| 1 | (null) | 5037 | Chapter I - Nick's arrival, Buchanan dinner | ✓ Correct |
| 2 | II | 4280 | Chapter II - Valley of ashes, Myrtle's party | ✓ Correct |
| 3 | III | 5734 | Chapter III - Gatsby's party, meeting Gatsby | ✓ Correct |
| 4 | IV | 763 | **ONLY party guest list intro** | ✗ SPLIT |
| 5 | (null) | 4693 | **Rest of Ch IV** - Gatsby bio, Wolfsheim, Jordan backstory | ✗ SPLIT |
| 6 | V | 4233 | Chapter V - Gatsby/Daisy reunion | ✓ Correct |
| 7 | VI | 4036 | Chapter VI - Gatsby's past revealed | ✓ Correct |
| 8 | VII | 8766 | Chapter VII - Plaza confrontation | ✓ Correct |
| 9 | (null) | 4530 | Chapter VIII - Gatsby's vigil, Wilson's search | Missing title |
| 10 | (null) | 5225 | Chapter IX - Aftermath, funeral | Missing title |

**Root Cause of IV Split:** The chapter detection is incorrectly identifying a boundary within Chapter IV, likely at the transition between the guest list preamble and the narrative proper.

### Character Duplicates Identified

| Primary | Duplicates | Should Merge |
|---------|------------|--------------|
| Wolfshiem (20) | Meyer Wolfsheim (1), Meyer Wolfshiem (1) | Yes - spelling variants |
| Sloane (10) | Mr. Sloane (1) | Yes |
| Klipspringer (8) | Mr. Klipspringer (1) | Yes |
| Nick Carraway | Narrator (4), The narrator (1), the narrator (2) | Yes - narrator is Nick |
| Owl Eyes? | The drunken man with owl-eyed spectacles (1), The man with owl-eyed glasses (1) | Yes - same character |

### Role-Based Entries to Filter (11 entries)
- Butler, Gatsby's butler, Chauffeur, Gardener, The detective
- Lutheran minister, New York reporter, The postman, Servants
- Chorus girl, Unnamed drunk driver

## Current Issues (Priority Order)

### CRITICAL

1. **Chapter IV incorrectly split into 2 parts**
   - Problem: 10 chapters detected instead of 9; Ch IV split at guest list boundary
   - Evidence: Chapter 4 = 763 words (guest list only), Chapter 5 = 4693 words (rest of Ch IV)
   - Location: `src/pipeline/chapter_detection/` - boundary detection
   - Fix: Adjust boundary detection to not split on guest list section break

2. **Tom Buchanan profile is NULL**
   - Problem: Major character (194 mentions) has personality=null, appearance=null
   - Evidence: `jq` shows completely null profile despite being 2nd most mentioned character
   - Location: `src/pipeline/character_extraction_v2/` - profile generation
   - Root Cause: Likely JSON parse failure during profile extraction (noted in logs)

3. **Jordan Baker profile is NULL**
   - Problem: Major character (98 mentions) has personality=null, appearance=null
   - Evidence: Same issue as Tom - profile fields completely null
   - Location: Same as above

### HIGH

4. **Pronunciation 88% uncategorized**
   - Problem: 508/580 entries (88%) have flag_reason="unknown"
   - Evidence: Only 36 proper_noun, 23 homograph, 13 foreign categorized
   - Impact: Pronunciation guide nearly useless for narrator
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Debug why categorization is failing for most entries

5. **Wolfshiem spelling variants not merged**
   - Problem: "Wolfshiem" (20), "Meyer Wolfsheim" (1), "Meyer Wolfshiem" (1) separate
   - Evidence: All refer to Meyer Wolfsheim/Wolfshiem (Fitzgerald uses variant spellings)
   - Location: `src/pipeline/character_extraction_v2/` - alias/fuzzy matching
   - Fix: Add spelling variant detection (Levenshtein distance or similar)

6. **Character duplicates: Sloane, Klipspringer**
   - Problem: "Sloane" (10) / "Mr. Sloane" (1) and "Klipspringer" (8) / "Mr. Klipspringer" (1)
   - Evidence: Same characters, different formality
   - Location: `src/pipeline/character_extraction_v2/`
   - Fix: Merge "Name" with "Mr./Mrs. Name" patterns

7. **Narrator entries not merged with Nick**
   - Problem: "Narrator" (4) + "The narrator" (1) + "the narrator" (2) separate from Nick Carraway
   - Evidence: Nick IS the narrator - these should be aliases or merged
   - Location: `src/pipeline/character_extraction_v2/`

8. **Owl Eyes duplicated**
   - Problem: "The drunken man with owl-eyed spectacles" and "The man with owl-eyed glasses" separate
   - Evidence: Both refer to "Owl Eyes" - the recognizable minor character
   - Location: `src/pipeline/character_extraction_v2/`

### MEDIUM

9. **11 role-based entries in character list**
   - Problem: Generic roles listed as characters (Butler, Chauffeur, etc.)
   - Evidence: These have 1 mention each and are role descriptions, not named characters
   - Location: `src/pipeline/character_extraction_v2/supporting_cast.py`
   - Fix: Strengthen role-based filtering

10. **Chapters VIII and IX missing titles**
    - Problem: Chapters 9 and 10 have null titles (should be "VIII" and "IX")
    - Evidence: Structure shows null instead of Roman numerals
    - Location: `src/pipeline/chapter_detection/` - title extraction

11. **Appearance consistently "unknown"**
    - Problem: All characters have appearance="unknown" or null
    - Evidence: Even Tom Buchanan (described in detail in Ch I) has unknown appearance
    - Location: Profile generation prompts in V2

## Path to 8.0

**Current: 5.40/10, Need: 8.0/10, Gap: 2.6 points**

| Priority | Fix | Estimated Impact |
|----------|-----|------------------|
| P0 | **Fix Chapter IV split** | Structure 5->9 = +0.8 overall |
| P0 | **Fix Tom/Jordan NULL profiles** | Profiles 4->7 = +0.45 overall |
| P1 | Fix pronunciation categorization | Pronunciation 3->7 = +0.4 overall |
| P1 | Merge Wolfshiem variants | Characters +0.1 |
| P1 | Merge Sloane, Klipspringer duplicates | Characters +0.1 |
| P1 | Filter role-based entries | Characters 6->7.5 = +0.4 overall |
| P2 | Merge narrator entries with Nick | Characters +0.05 |
| P2 | Fix appearance detection | Profiles +0.15 |
| P2 | Fix missing chapter titles | Structure +0.1 |
| **Total** | | **5.40 + 2.55 = ~7.95** |

**NOTE:** This score (5.40) is below baseline (6.65) by 1.25 points. The fix phase should consider reverting if the changes caused this regression. However, some improvements were made (I+II separation, Klipspringer/McKee fix), so selective revert may be needed.

## Fix History

### Attempt 13 - Mixed Results
- **FIXED**: Chapters I and II are now correctly separated
- **FIXED**: Klipspringer and McKee are now separate characters
- **REGRESSED**: Chapter IV incorrectly split into 2 parts
- **REGRESSED**: Tom Buchanan and Jordan Baker profiles are NULL
- **REGRESSED**: Pronunciation categorization worse (88% unknown)

### Previous Attempts Summary
- Attempt 2 was best (7.45) with correct 9-chapter structure
- Multiple attempts since have tried to fix structure but caused other regressions
- Profile generation has been unstable - sometimes works, sometimes NULL

## Next Action

**REGRESSION DETECTED:** Score 5.40 < baseline 6.65 - 0.3

Run PROMPT_fix.md with focus on:

1. **Investigate Chapter IV split root cause**
   - Why is the chapter boundary being placed within Chapter IV?
   - Check what boundary detection sees at the guest list section

2. **Fix Tom/Jordan NULL profiles**
   - Check JSON parse errors in log for these characters
   - Ensure profile generation doesn't fail silently

3. **Fix pronunciation categorization regression**
   - Was 86% unknown in attempt 12, now 88% - getting worse
   - Check if categorization logic changed

4. **Consider selective revert if needed**
   - Some changes helped (I+II, Klipspringer/McKee)
   - Some changes hurt (IV split, profiles, pronunciation)
   - May need to preserve good changes while reverting bad ones
