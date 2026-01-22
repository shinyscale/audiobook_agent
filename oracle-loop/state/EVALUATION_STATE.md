# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.80

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 6/10
- Character Profiles: 8/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.50/10** (threshold: 8.0)

## Progress Notes

**Wilson Fix PARTIALLY Worked:**
- Both George Wilson (91 mentions) and Myrtle Wilson (100 mentions) now have "Wilson" as alias
- "George B. Wilson" (1 mention) still separate - should be alias of George Wilson
- Net improvement in mention consolidation

**Still Failing:**
- Multiple character splits remain (Wolfshiem, Owl Eyes, Sloane, narrator variants)
- Pronunciation has too many false positives (587 entries)

## Current Issues (Priority Order)

### CRITICAL
1. **Wolfshiem / Meyer Wolfshiem split (25 mentions total)**
   - Problem: "Wolfshiem" (23) and "Meyer Wolfshiem" (2) remain separate
   - Evidence: Same character - Gatsby's gangster associate who fixed 1919 World Series
   - Location: V2 alias resolution in `src/agents/characters_v2.py`
   - Fix: First-name + last-name should merge with bare last-name when names match

### HIGH
2. **Narrator variants still split (7 extra mentions across 4 entries)**
   - Problem: "Narrator" (4), "Nick (narrator)" (1), "the narrator" (1), "Nick Carraway (narrator)" (1) exist separately from "Nick Carraway" (34)
   - Evidence: All refer to Nick Carraway, the first-person narrator
   - Location: `_filter_narrator_variants()` in `src/agents/characters_v2.py`
   - Fix: Expand filter patterns:
     - Match "narrator" case-insensitively
     - Match patterns like "Name (narrator)"
     - Match "the narrator" with lowercase "the"

3. **George B. Wilson should merge with George Wilson**
   - Problem: "George B. Wilson" (1) is separate from "George Wilson" (91)
   - Evidence: Same person - full name with middle initial vs. common usage
   - Location: V2 name matching
   - Fix: "FirstName MiddleInitial. LastName" should match "FirstName LastName"

4. **Owl Eyes split (2 entries → should be 1)**
   - Problem: "Man with owl-eyed glasses" (1) and "The man with owl-eyed spectacles (Owl Eyes)" (1)
   - Evidence: Same character - the bespectacled man at Gatsby's party/funeral
   - Location: V2 deduplication - should detect "owl-eyed" / "owl eyes" as same
   - Fix: Add fuzzy matching for hyphenated variants (owl-eyed ↔ owl eyes)

5. **Sloane / Mr. Sloane split (11 mentions total)**
   - Problem: "Sloane" (10) and "Mr. Sloane" (1) remain separate
   - Evidence: Same character - Tom's acquaintance who visits Gatsby in Chapter 6
   - Location: Title-variant merging in V2
   - Fix: "Mr. LastName" should merge with bare "LastName" when no other LastName exists

### MEDIUM
6. **Excessive pronunciation entries (587)**
   - Problem: Too many false positives including common English words
   - Evidence: Contains "yellow", "week", "use", "star", "Postman", "Reporter", "Servants", "City"
   - Location: Pronunciation agent filtering
   - Fix: Add exclusion list for:
     - Common occupational titles (postman, reporter, butler, gardener, chauffeur)
     - Common adjectives/nouns (yellow, star, week, city)
     - Basic service roles (servants)

7. **Chapter titles missing for I and V**
   - Problem: Chapters show as null instead of Roman numerals
   - Evidence: Structure list shows "None" for chapters 1 and 5 (should be "I" and "V")
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction

8. **Myrtle Wilson profile has JSON rendering bug**
   - Problem: Raw JSON appears in profile-body div instead of formatted text
   - Evidence: Line 2136 in report.html shows unescaped JSON
   - Location: HTML export template
   - Fix: Ensure profile body is properly escaped/formatted

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |
| 2 | 7.25 | +0.45 | Improvement but critical issues remain |
| 3 | 7.25 | +0.45 | Wilson fix did not take effect |
| 4 | 7.50 | +0.70 | Wilson fix partially worked; other splits remain |

## Fix History

### Attempt 1 Fixes (Applied)
**Fixed Issues:**
- **CRITICAL #2: Wolfshiem/Wolfsheim (3 entries)** - Added reverse pass to merge multi-word supporting→single-word main
- **CRITICAL #3: Owl-eyed man (3 entries)** - Added "the" prefix stripping in supporting→main merge
- **CRITICAL #4: Oxford listed as character** - Added institution exclusion list

**Outcome:** Partial success - score improved from 6.80 to 7.25

### Attempt 2 Fixes (Applied)
**Fixed Issues:**
- **CRITICAL #1: Myrtle Wilson / Mrs. Wilson split** - Added `_deduplicate_alias_canonical_conflicts()` method
- **HIGH #3: Narrator variants (5 entries)** - Added `_filter_narrator_variants()` method

**Outcome:** Partial success - Myrtle/McKee fixed

### Attempt 3 Fixes (Applied but NOT WORKING)
**Fixed Issues:**
- **Wilson split** - Added title-based disambiguation (lines 1292-1342)

**Outcome:** FIX DID NOT TAKE EFFECT
- The analysis output still shows "Wilson" as separate from "George Wilson"
- Root cause identified: Title-based disambiguation expected "Mrs. Wilson" to be in Myrtle's aliases, but LLM didn't provide it

### Attempt 4 Fixes (Applied - PARTIAL SUCCESS)
**Fixed Issues:**
- **CRITICAL #1: Wilson split** - Two-layer fix:
  1. **Prompt fix:** Updated `MAIN_CAST_PROMPT` to instruct LLM to include bare surnames as aliases
  2. **Code fix:** Updated `_merge_lastname_aliases()` to merge bare surnames to ALL matching characters when disambiguation fails

**Outcome:** PARTIAL SUCCESS
- Wilson is now an alias on both George Wilson (91) and Myrtle Wilson (100)
- BUT George B. Wilson (1) still separate
- Other splits (Wolfshiem, Owl Eyes, Sloane, narrator) not addressed

### Attempt 5 Fixes (Applied)
**Fixed Issues:**
1. **HIGH #2: Narrator variants (7 mentions)**
   - Root cause: `_filter_narrator_variants()` line 490-507 had overly complex logic
   - Fix: Simplified to single check: if "narrator" in canonical_name.lower()
   - This catches: "Narrator", "the narrator", "Nick (narrator)", "Nick Carraway (narrator)"
   - File: `src/agents/characters_v2.py` line 486-496

2. **CRITICAL #1: Wolfshiem/Meyer Wolfshiem (25 mentions)**
   - Root cause: Existing `_merge_within_main_cast()` should handle this but may have had edge case
   - No code change - existing Pass 1 logic should merge single-word last-name to full name
   - Will verify in re-analysis

3. **HIGH #3: George B. Wilson → George Wilson (1 mention)**
   - Root cause: Middle initial handling not implemented
   - Fix: Added Pass 0 to `_merge_within_main_cast()` to detect and merge middle initial variants
   - Pattern: "FirstName I. LastName" matches "FirstName LastName"
   - Merges the one with fewer mentions into the one with more mentions
   - File: `src/agents/characters_v2.py` line 923-988

4. **HIGH #5: Sloane/Mr. Sloane (11 mentions)**
   - Root cause: Pass 1 didn't check title-stripped names
   - Fix: Added title-stripping check before last-name matching in Pass 1
   - Pattern: "Sloane" matches "Mr. Sloane" after stripping "Mr."
   - File: `src/agents/characters_v2.py` line 1004-1008

**Smoke Test:** Syntax validated, code compiles successfully

**Expected Impact:**
- Narrator filtering: +7 mentions consolidated → improves Character Extraction
- Middle initials: +1 mention consolidated → minor improvement
- Title variants: +1 mention consolidated → minor improvement
- Wolfshiem: +2 mentions if merge works → minor improvement
- Total: ~11 mentions consolidated, should improve Character Extraction from 6/10 to 7-8/10

## Pipeline Notes (Attempt 5)
- Analysis completed successfully in 57m 25s
- Output files: ../output/gatsby/analysis.json, ../output/gatsby/report.html
- Total characters detected: 42 (vs 18 pre-merge)
- Notable warnings:
  - Several JSON parsing errors for character profiles (Tom Buchanan, Myrtle Wilson, Meyer Wolfsheim)
  - Low confidence profiles (0.30) for some characters
  - Pronunciation guide: 585 entries (506 unknown, 37 proper nouns, 23 homographs, 19 foreign)
- V2 character extraction with summary-driven merge applied
- Key fixes tested: narrator filtering, middle initial handling, title variant merging
