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
- Character Extraction: 6.5/10 ← PRIMARY ISSUE (improved from 5/10)
- Character Profiles: 8/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.50/10** (threshold: 8.0)

## Progress From Previous Attempt
**FIXED in Attempt 3:**
- ✅ Myrtle Wilson / Mrs. Wilson - NOW MERGED (single entry with "Myrtle" alias)
- ✅ McKee - NOW MERGED (Mr. McKee with "McKee" alias)
- ✅ Owl Eyes partially improved - has aliases "the man with owl-eyed glasses" and "Owl-Eyes"

**Score improved from 7.25 to 7.50 (+0.25)**

## Current Issues (Priority Order)

### CRITICAL
1. **"Wilson" standalone entry with 65 mentions - MAJOR SPLIT**
   - Problem: "Wilson" (65 mentions) exists separately from "George Wilson" (14) and "Myrtle Wilson" (23)
   - Evidence: Most "Wilson" mentions in the text refer to George Wilson (at the garage, after Myrtle's death). This is a SIGNIFICANT character split affecting 65 mentions
   - Location: V2 character extraction - likely NER is extracting bare "Wilson" as separate entity
   - Fix: "Wilson" should be merged with "George Wilson" as an alias - in context of the novel, bare "Wilson" almost always refers to George (the garage owner who kills Gatsby)
   - Impact: This is the single biggest issue - 65 missed associations

2. **Wolfshiem / Meyer Wolfshiem still split**
   - Problem: "Wolfshiem" (23 mentions) and "Meyer Wolfshiem" (2 mentions) remain separate
   - Evidence: Same character - Meyer Wolfshiem, Gatsby's gangster associate
   - Location: V2 alias resolution - fuzzy matching should catch this but isn't
   - Fix: Need to check why fuzzy match (88.89% similar) isn't triggering merge between "Wolfshiem" and "Wolfsheim" variant, plus need first-name-to-full-name merge
   - Note: The text actually spells it "Wolfshiem" (without the 's'), so this may be a matching issue

### HIGH
3. **Narrator variants still split (2 entries)**
   - Problem: "Narrator" (5 mentions) and "Nick (narrator)" (1 mention) exist separately from "Nick Carraway"
   - Evidence: All refer to the same person - the first-person narrator Nick Carraway
   - Location: V2 narrator filtering - the `_filter_narrator_variants()` method added in attempt 2 isn't catching all cases
   - Fix: Filter should also catch "Nick (narrator)" pattern and any standalone "Narrator" entries when a narrator is already identified

4. **Owl-eyed man STILL has 3 entries (down from earlier but not fully merged)**
   - Problem: "Owl Eyes" (3 mentions, has good aliases), "Man with owl-eyed glasses" (1), and "Owl-Eyed Man" (1) are separate
   - Evidence: All refer to the same minor character - the bespectacled man at Gatsby's party and funeral
   - Location: V2 deduplication - "Man with owl-eyed glasses" IS an alias of "Owl Eyes" but also exists as separate entry
   - Fix: When a character has an alias that matches another character's canonical name, they should be merged (similar to the alias-canonical conflict fix)

5. **Sloane / Mr. Sloane split**
   - Problem: "Sloane" (10 mentions) and "Mr. Sloane" (1 mention) are separate
   - Evidence: Same character - the man who visits Gatsby with Tom
   - Location: V2 title-variant merging
   - Fix: "Mr. LastName" should merge with "LastName" when context suggests same person

### MEDIUM
6. **Excessive pronunciation entries (585)**
   - Problem: 585 entries includes many common English words
   - Evidence: Sample includes "Butler", "Chauffeur", "glasses", "Gardener", "minister", "nurse", "Orchestra"
   - Location: Pronunciation agent filtering
   - Fix: Improve common word filtering; job titles and common nouns should be excluded

7. **Chapter titles missing for I and V**
   - Problem: Chapters I and V have null titles instead of Roman numerals
   - Evidence: Structure shows: null, II, III, IV, null, null, VI, VII, VIII, IX
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction

### LOW
8. **Henry C. Gatz / Gatz ambiguity**
   - Problem: "Wilson" (65) could include some "Gatz" references meant for Gatsby's father vs James Gatz (Gatsby's birth name)
   - Evidence: Context-dependent - already handled as alias of Jay Gatsby ("James Gatz")
   - Location: May need context-aware disambiguation
   - Fix: Low priority - current handling is acceptable

9. **Mrs. McKee separate entry**
   - Problem: "Mrs. McKee" (1 mention) is separate from Mr. McKee entries
   - Evidence: This is CORRECT - she is a distinct character (Mr. McKee's wife)
   - Location: N/A
   - Fix: No fix needed - correctly identified as separate

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |
| 2 | 7.25 | +0.45 | Improvement but critical issues remain |
| 3 | 7.50 | +0.70 | Myrtle/McKee fixed, Wilson split discovered |

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

**Outcome:** Partial success - Myrtle/McKee fixed, but narrator fix didn't catch all variants

### Key Insights for Attempt 3 Fix

1. **The "Wilson" problem (65 mentions) is the single biggest issue.** This is likely happening because:
   - NER extracts bare "Wilson" as a character
   - The supporting→main cast merge doesn't recognize "Wilson" should become an alias of "George Wilson"
   - Need: When a single last name matches an existing character's last name, merge them

2. **The deduplication has a gap**: When a character has an alias that MATCHES another character's canonical name (e.g., "Owl Eyes" has alias "Man with owl-eyed glasses", but "Man with owl-eyed glasses" also exists as a canonical name), they should be merged.

3. **Narrator filtering is incomplete**: Need to also filter entries where canonical name contains "narrator" in parentheses like "Nick (narrator)"

## Next Action
Run PROMPT_fix.md to address:
1. Wilson → George Wilson merge (CRITICAL - 65 mentions)
2. Owl-eyed aliases-as-canonical merge
3. Narrator parenthetical filtering
4. Wolfshiem spelling variant handling
