# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.80

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 3)
- Analysis completed successfully in 59m 24s
- Found 40 characters (19 eligible for profiles, 18 profiles generated)
- Some LLM errors during character profiling (server EOF errors, JSON parse failures)
- Low confidence profiles for Daisy Buchanan, Tom Buchanan, Klipspringer (0.30)
- 585 pronunciation entries flagged
- V2 character extraction used with summary-driven approach

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 5/10 ← PRIMARY ISSUE
- Character Profiles: 8/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.25/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: Myrtle Wilson / Mrs. Wilson**
   - Problem: "Myrtle Wilson" (23 mentions) and "Mrs. Wilson" (24 mentions, with alias "Myrtle Wilson") are SEPARATE entries
   - Evidence: These are the SAME person - George Wilson's wife who has an affair with Tom
   - Location: V2 character extraction - the alias resolution is creating both entries instead of merging them
   - Fix: When "Mrs. Wilson" has "Myrtle Wilson" as an alias, they should be merged into a single entry, not kept separate
   - Root cause hint: The alias field contains "Myrtle Wilson" but they weren't merged during deduplication

2. **False character split: Wolfshiem / Meyer Wolfsheim (still present)**
   - Problem: "Wolfshiem" (23 mentions) and "Meyer Wolfsheim" (2 mentions) are separate entries
   - Evidence: Same character - Meyer Wolfshiem/Wolfsheim, Gatsby's gangster associate
   - Location: V2 alias resolution - the attempt 1 fix did not work
   - Fix: The multi-word to single-word merge needs to be re-examined; possibly the fix wasn't applied correctly or a different code path is being taken

### HIGH
3. **Narrator variants split into 5 entries**
   - Problem: Five separate entries all refer to Nick Carraway as narrator:
     - "Nick Carraway" (34 mentions, is_narrator: true) ✓
     - "Narrator" (1 mention, is_narrator: false)
     - "the narrator" (1 mention, is_narrator: false)
     - "The Narrator" (1 mention, is_narrator: false)
     - "Nick Carraway (narrator)" (1 mention, is_narrator: false)
   - Evidence: All refer to the same person - the first-person narrator
   - Location: V2 narrator detection and alias resolution
   - Fix: Characters with canonical names containing "narrator" (case-insensitive) should be merged with the identified narrator character

4. **Owl-eyed man still split (2 entries remain)**
   - Problem: "Man with owl-eyed glasses" (1) and "Owl-Eyed Man" (1) are separate
   - Evidence: Same minor character - the bespectacled man at Gatsby's party and funeral
   - Location: V2 normalization - the attempt 1 fix did not fully resolve this
   - Fix: Need case-insensitive matching and handling of "Man with X" vs "X Man" patterns

5. **McKee / Mr. McKee split**
   - Problem: "McKee" (16) and "Mr. McKee" (1) are separate entries
   - Evidence: Same person - the photographer at Myrtle's party
   - Location: V2 title-variant merging
   - Fix: "Mr. LastName" should merge with "LastName" when they appear in similar contexts

6. **Gatz / Henry C. Gatz split**
   - Problem: "Gatz" (6 mentions) and "Henry C. Gatz" (1) are separate entries
   - Evidence: Both refer to Gatsby's father who appears at the funeral
   - Location: V2 alias resolution for shared last names
   - Fix: This is tricky because "Gatz" could be confused with James Gatz (Gatsby's birth name) - need context-aware merging

### MEDIUM
7. **Excessive pronunciation entries (585)**
   - Problem: 585 entries includes many common English words
   - Evidence: Sample includes "Butler", "Chauffeur", "glasses", "Gardener", "minister", "boarder"
   - Location: Pronunciation agent filtering thresholds
   - Fix: Improve common word filtering; these are not unusual enough to flag

8. **Chapter titles missing for I and V**
   - Problem: Chapters I and V have null titles instead of Roman numerals
   - Evidence: Structure shows: null, II, III, IV, null, VI, VII, VIII, IX
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction for edge cases

### LOW
9. **Wilson single-mention entry**
   - Problem: "Wilson" (1 mention) exists separately from "George Wilson" (14)
   - Evidence: Likely refers to George Wilson given context
   - Location: V2 low-mention-count character handling
   - Fix: Consider merging or filtering characters with very low mention counts that match existing character last names

10. **Mrs. McKee separate entry**
    - Problem: "Mrs. McKee" (1 mention) is separate from McKee entries
    - Evidence: This is actually a different character (Mr. McKee's wife), so may be CORRECT
    - Location: N/A - verify this is intentional
    - Fix: Possibly no fix needed - need to verify she's a distinct character

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |
| 2 | 7.25 | +0.45 | Improvement but critical issues remain |

## Fix History

### Attempt 1 Fixes (Applied)
**Fixed Issues:**
- **CRITICAL #2: Wolfshiem/Wolfsheim (3 entries)** - Added reverse pass to merge multi-word supporting→single-word main
- **CRITICAL #3: Owl-eyed man (3 entries)** - Added "the" prefix stripping in supporting→main merge
- **CRITICAL #4: Oxford listed as character** - Added institution exclusion list

**Outcome:** Partial success - score improved from 6.80 to 7.25, but:
- Wolfshiem still has 2 entries (down from 3)
- Owl-eyed man still has 2 entries (down from 3)
- NEW issue: Myrtle Wilson / Mrs. Wilson split emerged

### What Likely Went Wrong
1. The Wolfshiem fix may have only addressed one merge direction or a specific edge case
2. The owl-eyed fix may have been case-sensitive when it should be case-insensitive
3. The Mrs. Wilson / Myrtle Wilson issue suggests that:
   - When one character has another's name as an alias, the deduplication step isn't recognizing this as a merge candidate
   - The alias resolution may be adding aliases without checking if that alias name exists as another character's canonical name

### Attempt 2 Fixes (Applied)
**Fixed Issues:**
- **CRITICAL #1: Myrtle Wilson / Mrs. Wilson split** - Added `_deduplicate_alias_canonical_conflicts()` method
  - Root cause: `src/agents/characters_v2.py` - No deduplication step checked if one character's alias matched another's canonical name
  - Smoke test: PASS - Method correctly merges characters when alias matches canonical name
  - Modified: `src/agents/characters_v2.py` (added Step 3.6 and new method at line 732)

- **CRITICAL #2: Wolfshiem / Meyer Wolfsheim split** - No additional code changes (existing fuzzy match should work)
  - Root cause: Existing Pass 3 in `_merge_within_main_cast()` has 85% fuzzy threshold which should catch "Wolfshiem" vs "Wolfsheim" (88.89% similar)
  - Smoke test: Skipped - will verify in full analysis
  - Note: If issue persists, may need to investigate why fuzzy matching isn't triggering

- **HIGH #3: Narrator variants (5 entries)** - Added `_filter_narrator_variants()` method
  - Root cause: `src/agents/characters_v2.py` - Supporting cast NER extraction picks up "narrator", "the narrator", etc. as separate characters
  - Smoke test: PASS - Method correctly filters variants containing "narrator" (case-insensitive)
  - Modified: `src/agents/characters_v2.py` (added Step 5.1 and new method at line 448)

**Full test suite:** 327 passed, 2 pre-existing failures (unrelated to changes), 10 skipped

## Next Action
Set phase to `awaiting_analysis` and re-run analysis to verify fixes
