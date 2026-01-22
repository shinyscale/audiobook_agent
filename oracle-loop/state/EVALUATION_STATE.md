# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.80

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 5/10 ← CRITICAL REGRESSION (down from 6.5)
- Character Profiles: 8/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.25/10** (threshold: 8.0)

## ⚠️ REGRESSION ALERT

**Score dropped from 7.50 (attempt 2) to 7.25 (attempt 3)**

The title-based disambiguation fix for Wilson did NOT take effect in this analysis run:
- "Wilson" (65 mentions) still exists as separate entry
- "George Wilson" (14 mentions) still exists as separate entry
- Expected: "Wilson" should be an alias of "George Wilson"

**Root cause investigation needed:**
1. Was the fix actually deployed to the code used for this analysis?
2. Is there a logic error in the title-based disambiguation?
3. Is the fix being bypassed by another code path?

## Current Issues (Priority Order)

### CRITICAL
1. **Wilson split - FIX DID NOT WORK (65 mentions lost)**
   - Problem: "Wilson" (65 mentions), "George Wilson" (14), and "Wilson (referenced in actions)" (1) remain as 3 separate entries
   - Evidence: Sanity check shows all three still separate after fix was supposedly applied
   - Expected: "Wilson" should be alias of "George Wilson" (per title-based disambiguation fix)
   - Investigation needed: Check if `_merge_lastname_aliases()` title disambiguation code is being reached
   - Location: `src/agents/characters_v2.py:1275-1342`
   - Fix: Debug why the title-based merge isn't triggering. Likely causes:
     - Code path not being executed
     - Condition not matching (check "Mrs. Wilson" alias detection)
     - Merge happening but then undone by later step

2. **Wolfshiem / Meyer Wolfshiem split (25 mentions total)**
   - Problem: "Wolfshiem" (23) and "Meyer Wolfshiem" (2) remain separate
   - Evidence: Same character - the gangster associate of Gatsby
   - Location: V2 alias resolution in `characters_v2.py`
   - Fix: First-name + last-name should merge with bare last-name

### HIGH
3. **Narrator variants still split (7 extra mentions)**
   - Problem: "the narrator" (1) and "Narrator" (6) exist separately from "Nick Carraway" (34)
   - Evidence: All refer to Nick Carraway, the first-person narrator
   - Location: `_filter_narrator_variants()` in `characters_v2.py`
   - Fix: Expand filter to catch "the narrator" (lowercase 'the'), "Narrator" (capitalized), and "Nick (narrator)" pattern

4. **Owl Eyes split (3 entries → should be 1)**
   - Problem: "Owl-eyed man" (1) and "Owl Eyes (the intoxicated man with owl-eyed spectacles)" (1) exist separately
   - Evidence: Same character - the bespectacled man at Gatsby's party
   - Location: V2 deduplication
   - Fix: Improve "owl" keyword matching to merge these variants

5. **Sloane / Mr. Sloane split (11 mentions total)**
   - Problem: "Sloane" (10) and "Mr. Sloane" (1) remain separate
   - Evidence: Same character - Tom's acquaintance who visits Gatsby
   - Location: Title-variant merging in V2
   - Fix: "Mr. LastName" should merge with bare "LastName"

### MEDIUM
6. **Excessive pronunciation entries (582)**
   - Problem: Too many false positives including common English words
   - Evidence: Contains "Butler", "Chauffeur", "Doctor", "Gardener", "minister", "drunk", "brown"
   - Location: Pronunciation agent filtering
   - Fix: Add exclusion list for common occupational titles and basic adjectives

7. **Chapter titles missing for I and V**
   - Problem: Chapters show as null instead of Roman numerals
   - Evidence: Structure list shows "None" for chapters 1 and 5
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction

### LOW
8. **Minor character name variants**
   - Various minor characters have slight name variations not merged
   - Low impact - doesn't affect main character recognition

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |
| 2 | 7.25 | +0.45 | Improvement but critical issues remain |
| 3 | 7.25 | +0.45 | ⚠️ Wilson fix did NOT work - regression from 7.50 expected |

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

### Attempt 4 Fixes (Applied)
**Fixed Issues:**
- **CRITICAL #1: Wilson split** - Two-layer fix:
  1. **Prompt fix:** Updated `MAIN_CAST_PROMPT` (src/pipeline/character_extraction_v2/main_cast.py lines 50-56) to instruct LLM to include bare surnames as aliases based on actual usage in summaries
  2. **Code fix:** Updated `_merge_lastname_aliases()` (src/agents/characters_v2.py lines 1334-1350) to merge bare surnames to ALL matching characters when disambiguation fails (instead of skipping)
  - Root cause: LLM wasn't providing "Wilson" as alias because prompt showed Mr. Smith example with bare surname but Mrs. Smith without
  - Smoke test: Skipped (too slow) - logic verified by code inspection

**Outcome:** Awaiting re-analysis to verify

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify Wilson fix and address remaining issues:
- Wolfshiem/Meyer Wolfshiem merge
- Narrator variant filtering
- Owl Eyes deduplication
- Sloane/Mr. Sloane merge
