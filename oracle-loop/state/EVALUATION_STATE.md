# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 6.80

## Latest Scores
- Structure Detection: 7/10
- Character Extraction: 5/10 ← PRIMARY ISSUE
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 7/10
- **Overall: 6.80/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: Wilson / George B. Wilson**
   - Problem: "Wilson" (65 mentions) and "George B. Wilson" (14 mentions) are listed as separate characters
   - Evidence: These refer to the same person - George Wilson, the garage owner. Text uses "Wilson" as short form
   - Location: V2 character extraction alias resolution (`src/pipeline/character_extraction_v2/`)
   - Fix: Improve alias detection for LastName matching "FirstName LastName" patterns

2. **False character split: Wolfshiem/Wolfsheim (3 entries)**
   - Problem: "Wolfshiem" (23 mentions), "Meyer Wolfsheim" (1 mention), and "Meyer Wolfshiem" (1 mention) are THREE separate entries
   - Evidence: Same character - Meyer Wolfshiem/Wolfsheim, the gangster. Text uses variant spellings
   - Location: V2 fuzzy matching in alias resolution
   - Fix: Improve spelling variant detection (ei/ie variations, FirstName LastName matching)

3. **False character split: Owl-eyed man (3 entries)**
   - Problem: "the man with owl-eyed glasses" (3), "Man with owl-eyed glasses" (1), and "Owl-eyed man" (1) are separate
   - Evidence: Same minor character - the owl-eyed man at Gatsby's party
   - Location: V2 normalization/deduplication
   - Fix: Case-insensitive matching for descriptive character names

4. **False positive: Oxford listed as character**
   - Problem: "Oxford" (6 mentions) is listed as a character
   - Evidence: Oxford refers to Oxford University, not a person. Gatsby claims he attended there
   - Location: V2 character extraction NER filtering
   - Fix: Add educational institutions to exclusion list or improve context-based filtering

### HIGH
5. **False character split: Narrator variants (4 entries)**
   - Problem: "Nick Carraway" (34), "Narrator" (4), "the narrator" (1), and "Nick (narrator)" (2) are separate
   - Evidence: All refer to Nick Carraway, the first-person narrator
   - Location: V2 narrator detection / alias resolution
   - Fix: Merge narrator references with identified narrator character

6. **False character split: Mr. Gatsby**
   - Problem: "Mr. Gatsby" (1 mention) is separate from "Jay Gatsby" (268 mentions)
   - Evidence: Same person - the title "Mr." should be recognized as an alias pattern
   - Location: V2 alias resolution for title variants
   - Fix: Already partially works (Mr. Buchanan → Tom Buchanan), but missed for Gatsby

7. **False character split: McKee / Mr. McKee**
   - Problem: "McKee" (16) and "Mr. McKee" (1) are separate entries
   - Evidence: Same person - the photographer at Myrtle's party
   - Location: V2 title-variant merging
   - Fix: Title variant matching should apply consistently

8. **False character split: Sloane / Mr. Sloane**
   - Problem: "Sloane" (10) and "Mr. Sloane" (1) are separate entries
   - Evidence: Same person - visitor with Tom at Gatsby's
   - Location: V2 title-variant merging

### MEDIUM
9. **Structure: Chapter titles incorrect**
   - Problem: Chapter I has null title, Chapter V labeled "Section 1", numbering inconsistent
   - Evidence: Chapter list shows: null, II, III, Section 1, IV, VI, VII, VIII, IX
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction for first chapter, handle edge cases

10. **Pronunciation: Excessive false positives**
    - Problem: 587 entries includes common words like "butler", "chauffeur", "glasses", "brown"
    - Evidence: These are standard English words that narrators don't need pronunciation help for
    - Location: Pronunciation agent filtering
    - Fix: Improve common word filtering, raise threshold for flagging

11. **Character profiles: Raw JSON visible in HTML**
    - Problem: Some character profile sections show unrendered JSON in the HTML output
    - Evidence: Gatsby profile shows raw JSON for appearance/personality fields
    - Location: HTML template rendering
    - Fix: Ensure all profile fields are properly rendered

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |

## Fix History

### Attempt 1 Fixes
**Fixed Issues:**
- **CRITICAL #2: Wolfshiem/Wolfsheim (3 entries)**
  - Root cause: `characters_v2.py:_merge_lastname_aliases()` line 943+ only merged supporting→main for single-word names, not multi-word supporting→single-word main
  - Fix: Added reverse pass to merge multi-word supporting characters with single-word main cast characters when last names match
  - Smoke test: PASS - "Meyer Wolfshiem" (supporting) now merges with "Wolfshiem" (main) as alias
  - Modified: `src/agents/characters_v2.py` lines 1069-1138

- **CRITICAL #3: Owl-eyed man (3 entries)**
  - Root cause: `characters_v2.py:_merge_lastname_aliases()` line 976+ didn't handle "the X" ↔ "X" normalization
  - Fix: Added "the" prefix stripping in supporting→main merge to match "Owl-eyed man" with "the owl-eyed man" alias
  - Smoke test: PASS - Both "Owl-eyed man" and "Man with owl-eyed glasses" now merge with main character
  - Modified: `src/agents/characters_v2.py` lines 1011-1052

- **CRITICAL #4: Oxford listed as character**
  - Root cause: `supporting.py:_is_valid_name()` line 158+ didn't exclude educational institutions
  - Fix: Added institution exclusion list (Oxford, Cambridge, Harvard, Yale, etc.)
  - Modified: `src/pipeline/character_extraction_v2/supporting.py` lines 188-194

**NOT Fixed (deferred):**
- **CRITICAL #1: Wilson / George B. Wilson**
  - Reason: Genuine ambiguity - "Wilson" matches both "George B. Wilson" and "Myrtle Wilson" last names
  - Code correctly avoids merge to prevent incorrect family member merging
  - Would require context-aware LLM analysis to resolve safely
  - Accepting minor quality impact rather than risk false merges

## Next Action
Re-run analysis via PROMPT_analyze.md to verify fixes and measure score improvement

**Expected improvements:**
- Character Extraction: 5/10 → 7-8/10 (fixed 3 of 4 CRITICAL splits)
- Overall: 6.80/10 → 7.5-8.0/10 (if other categories hold)
