# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 (attempt 2 analysis)

## Latest Scores
- Structure Detection: 7.5/10 ✗ (FAILING - most chapter titles null)
- Character Extraction: 7/10 ✗ (FAILING - Walton fragmented, Alphonse undercounted, generic groups)
- Character Profiles: 8/10 ✓ (appearance/personality data present via structured fields)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.88/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Improvement from Attempt 1

**Fixes that WORKED:**
1. ✅ Victor Frankenstein now in main_cast (main_cast_1, 55 mentions, is_narrator=true)
2. ✅ Professor Krempe and M. Waldman are NOW SEPARATE - false merge FIXED
3. ✅ The Creature has proper appearance description in structured format
4. ✅ Victor and Creature correctly marked as narrators

**Character Extraction improved from 4/10 to 7/10**
**Character Profiles improved from 5/10 to 8/10** (appearance/personality fields populated)

## Current Issues (Priority Order)

### HIGH

1. **Robert Walton fragmented and not recognized as framing narrator**
   - Problem: "Walton" (supporting_5, 8m) exists but is not main cast and `is_narrator: false`
   - Evidence: Letters 1-4 are written by Robert Walton; he frames the entire narrative
   - Related: "R.W." (f1b39c083608, 1m), "Margaret Saville" (main_cast_15, 14m) - Margaret is his sister/recipient
   - ID Pattern: supporting_5 - extracted by supporting cast, not promoted to main cast
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - narrator detection didn't catch Walton
   - Fix: The narrator detection fix helped Victor but not Walton. Walton signs letters with "R.W." and "Your affectionate brother" - need to handle epistolary narrator detection for frame narratives.

2. **M. Waldman not merged with Professor Waldman concept**
   - Problem: "M. Waldman" (supporting_4, 9m) stands alone without "Professor" title
   - Evidence: Text refers to him as "Professor Waldman", "M. Waldman", and just "Waldman"
   - Note: Krempe correctly has "Professor Krempe" (main_cast_9, 9m) with alias "M. Krempe"
   - ID Pattern: supporting_4 - cross-pipeline fragmentation
   - Location: The fix prevented false merge but now Waldman isn't properly consolidated
   - Fix: Waldman should be "Professor Waldman" in main_cast with "M. Waldman" as alias

3. **Alphonse Frankenstein severely undercounted (1 mention)**
   - Problem: Victor's father has only 1 mention (hash ID cf652e4d2e68)
   - Evidence: "my father", "Alphonse Frankenstein", letters from father - he appears throughout
   - Also: "The narrator's father" (4542ed769e00, 1m) is a DUPLICATE referring to same person
   - ID Pattern: Hash IDs - only caught by F6 summary reconciliation
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - Pass1 failed to extract
   - Fix: Add guidance for family members referenced by relationship ("my father") to resolve to full names

### MEDIUM

4. **Chapter titles mostly null (24/28 chapters)**
   - Problem: Only Letters 2-4 have titles; Letter 1 and all Chapters have `title: null`
   - Evidence: The 1831 edition clearly has "Letter 1", "Chapter 1", etc. as section headers
   - Location: `src/pipeline/chapter_detection/` - title extraction
   - Fix: Title extraction should recognize "Letter" and "Chapter" patterns in source text
   - Impact: Structure score 7.5/10

5. **Generic groups listed as characters**
   - Problem: "the court officials" (d7065e27fa05), "the people of the inn" (0976d73b1ce1), "Witnesses (fishermen, women)" (db133e3e3060)
   - Evidence: These are generic groups, not named individuals with narrative agency
   - ID Pattern: All hash IDs from F6 summary reconciliation
   - Location: `src/agents/characters.py` F6 step - needs filtering for generic nouns
   - Fix: Add check in F6 to exclude entries that are clearly groups (plural nouns, "the people of", etc.)

6. **"The narrator's father" duplicate of Alphonse Frankenstein**
   - Problem: Two entries refer to same person: "Alphonse Frankenstein" and "The narrator's father"
   - Evidence: Victor's father is Alphonse Frankenstein
   - ID Pattern: Both hash IDs from F6
   - Location: `src/agents/characters.py` F6 reconciliation
   - Fix: F6 should resolve "narrator's X" references to actual character names when narrator is known

### LOW

7. **Werter still listed as character**
   - Problem: "Werter" (supporting_10, 5m) is a book title, not a Frankenstein character
   - Evidence: References to "Sorrows of Werter" - a book the Creature reads
   - Location: Supporting cast extraction
   - Fix: Filter out literary work references

8. **Caroline Beaufort duplicate**
   - Problem: "Caroline Beaufort" (1b0ca2c5dd62, 1m) exists separately from "Caroline Beaufort Frankenstein" (main_cast_7, 10m)
   - Evidence: Same person - maiden name vs married name
   - Fix: Should be merged as alias

## Fix History
- Attempt 1: Initial analysis (baseline 6.35/10)
- Attempt 2: Fixed Victor Frankenstein narrator detection and Waldman/Krempe separation
  - Victor: Now main_cast_1 with is_narrator=true ✓
  - Professors: Krempe and Waldman now correctly separate ✓
  - Modified: src/pipeline/character_extraction_v2/main_cast.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline score 6.35 |
| 2 | Victor missing, Walton missing, Waldman/Krempe merge | src/pipeline/character_extraction_v2/main_cast.py | Victor FIXED, Walton still failing, Waldman/Krempe now separate but Waldman fragmented |

## Next Action

Focus on HIGH priority issues to reach 8.0 threshold in both failing categories:

**Character Extraction (7/10 → 8/10):**
1. Fix Walton narrator detection for epistolary frame narrative
2. Merge M. Waldman with Professor Waldman properly
3. Filter generic groups from F6 reconciliation

**Structure Detection (7.5/10 → 8/10):**
4. Fix chapter title extraction for "Letter X" and "Chapter X" patterns

Run PROMPT_fix.md to address these issues.

## Configuration Notes
- Total runtime: ~2.5 hours
- 717 LLM calls, 860K tokens
- Model: qwen3-next:80b-a3b-instruct-q8_0

## Root Cause Analysis

The narrator detection fix for attempt 2 worked for **Victor** (first-person nested narrator with "I" + character name in dialogue) but failed for **Walton** because:

1. Walton's narrative is EPISTOLARY (letters), not continuous first-person
2. He signs as "R.W." not "Robert Walton"
3. The letters' recipient (Margaret Saville) appears more prominently than the writer
4. Frame narrators in nested narratives need special detection: Walton → Victor → Creature

The Waldman/Krempe separation worked, but now Waldman isn't properly consolidated because:
1. "M. Waldman" (supporting) wasn't matched with any main_cast entry
2. Unlike Krempe who has "Professor Krempe" as canonical, there's no "Professor Waldman" entry
3. The disambiguation prevented false merge but didn't create correct merge
