# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 6.65

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 4/10 ← FAILING (unchanged)
- Character Profiles: 5/10 ← FAILING (unchanged)
- Chapter Summaries: 8/10
- Pronunciation Guide: 6/10
- HTML Presentation: 9/10
- **Overall: 6.65/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | 0.00 | Baseline - Mr. White missing (merged with Mrs. White) |
| 2 | 6.65 | 0.00 | Fix failed - Mrs. White still merged as alias of Mr. White |

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: Mrs. White merged into Mr. White (FIX FAILED)**
   - Problem: Mrs. White is listed as an alias of Mr. White, but they are husband and wife (DIFFERENT people)
   - Evidence: `analysis.json` shows Mr. White's aliases as `["White", "Mrs. White"]`
   - This is the SAME bug as attempt 1, just merged in the opposite direction
   - **Root cause analysis**: The fix in `main_cast.py` added a rule about different titles, but the LLM is still merging them. This suggests:
     - Either the rule isn't being parsed correctly by the LLM
     - Or the merge is happening in a different stage (alias deduplication?)
     - Or the prompt changes weren't sufficient
   - Location: Need to investigate entire V2 pipeline:
     - `src/pipeline/character_extraction_v2/main_cast.py` (extraction stage)
     - `src/pipeline/character_extraction_v2/alias_deduplication.py` (if exists)
     - `src/pipeline/character_extraction_v2/merge.py` (if exists)
   - Fix: Need deeper investigation - the prompt fix alone is insufficient

### HIGH
2. **Chapter 3 uses generic character references instead of names**
   - Problem: Chapter 3's `characters_present` lists "old man" and "old woman" instead of "Mr. White" and "Mrs. White"
   - Evidence: `jq '.structure[2].characters_present'` returns `["old man", "old woman"]`
   - This is downstream of the character extraction issue - the system creates separate "old man"/"old woman" characters instead of linking to Mr./Mrs. White
   - Likely cause: Chapter 3 summary uses these generic terms, and character linking can't map them to proper characters
   - Location: Character presence detection or summary character extraction
   - Fix: May resolve if character extraction is fixed properly, OR need explicit alias handling for descriptive references

3. **Spurious characters: "old man" and "old woman" exist as separate character entries**
   - Problem: These should not be separate characters - they refer to Mr. White and Mrs. White in Chapter 3
   - Evidence: Both have `mention_count: 1` and no aliases
   - These are creating noise in the character list
   - Location: Main cast extraction or character deduplication
   - Fix: Either prevent extraction of generic descriptors as characters, or merge them with canonical characters

### MEDIUM
4. **Pronunciation guide missing IPA for all entries**
   - Problem: All 53 pronunciation entries have `ipa: null`
   - Evidence: `jq '.pronunciations[:5] | .[].ipa'` returns all nulls
   - Location: `src/pipeline/pronunciation_detection.py` or IPA generation logic
   - Fix: Enable IPA generation or check why it's not being populated

5. **Missing key pronunciation terms**
   - Problem: "fakir" (Indian holy man who enchanted the paw) and "rubicund" (describing Morris) are not flagged
   - These are genuinely unusual words a narrator would need help with
   - Location: Pronunciation detection word list or rules

6. **Chapter titles are null**
   - Problem: Structure entries have `title: null` instead of "I", "II", "III"
   - Evidence: The original text uses Roman numerals for part divisions
   - Minor issue but worth fixing for completeness
   - Location: Chapter detection regex or title extraction

### LOW
7. **Some unnecessary pronunciation flags (false positives)**
   - "to-night" (archaic spelling, pronounced normally)
   - "slushy" (common English word)
   - "out-of-the-way" (common phrase)
   - "house" (extremely common word)
   - These clutter the pronunciation guide

## Investigation Required

**The prompt fix from attempt 1 did not work.** Before the next fix attempt, investigate:

1. **Where is the merge actually happening?**
   - Is it in main_cast.py extraction, or in a later deduplication/merge stage?
   - Check the V2 pipeline stages in order:
     ```
     src/pipeline/character_extraction_v2/
     ├── __init__.py
     ├── main_cast.py        ← extraction (fix was here)
     ├── ??? deduplication   ← could be re-merging after extraction
     └── ??? merge           ← could be combining characters
     ```

2. **Check the raw LLM output from main_cast.py**
   - Did the LLM correctly output Mr. White and Mrs. White as separate characters?
   - Or did the prompt changes not affect the LLM behavior?

3. **Check for post-processing that might be re-merging**
   - Are there alias deduplication rules that use surname matching?
   - Is there fuzzy matching that's too aggressive?

## Fix History

### Attempt 1 - Fix 1: Title-based character distinction (FAILED)
**Issue:** CRITICAL - False character merge: Mr. White merged into Mrs. White
**Root Cause (believed):**
- File: `src/pipeline/character_extraction_v2/main_cast.py`
- Problem: Prompt didn't explicitly prevent title+surname merging

**Fix Applied:**
- Modified `main_cast.py` prompt rules:
  - Added new rule 8: "Characters with DIFFERENT titles before the same surname (Mr./Mrs./Miss/Dr. + Surname) are DIFFERENT people"
  - Clarified old rule (now 9): Titles with FULL names are aliases
  - Added example showing Mr. Smith and Mrs. Smith as separate characters

**Smoke Test:** PASS - But smoke test may not have been representative

**Result: FIX FAILED**
- The same bug persists, just merged in opposite direction (Mrs. White → Mr. White instead of Mr. White → Mrs. White)
- The prompt changes were insufficient or the merge is happening elsewhere

### Attempt 2 - Fix 1: Block title-variant merge in post-processing
**Issue:** CRITICAL - False character merge: Mrs. White merged into Mr. White

**Root Cause (CONFIRMED):**
- File: `src/agents/characters_v2.py`
- Function: `_merge_title_variants()` lines 441-529
- Problem: Post-processing step merges characters when one name contains another as a word
  - Both "Mr. White" and "Mrs. White" contain the word "White"
  - The function doesn't distinguish between:
    - "Sergeant-Major Morris" + "Morris" → SHOULD merge (same person)
    - "Mr. White" + "Mrs. White" → SHOULD NOT merge (different people with different titles)

**Data Flow Trace:**
1. Summaries → MainCastExtractor → LLM correctly extracts TWO separate characters (Mr. White, Mrs. White)
2. `_merge_title_variants()` runs at line 124
3. Function compares all pairs and merges "Mr. White" and "Mrs. White" because both contain "White"
4. Result: Mrs. White becomes an alias of Mr. White

**Fix Applied:**
- Added new helper function `_are_different_titled_people()` (lines 568-621)
  - Detects when two names have DIFFERENT honorific titles (Mr./Mrs./Miss/Ms./Dr.)
  - Returns True if titles differ and stripped names match (e.g., "Mr. White" + "Mrs. White")
- Modified `_merge_title_variants()` to call this check before merging (lines 473, 495)
  - If check returns True, skip the merge (they're different people)
  - Otherwise, allow merge as before

**Smoke Test:** PASS
- Code compiles successfully
- Logic verified: "Mr. White" + "Mrs. White" → blocked from merging
- Logic verified: "Sergeant-Major Morris" + "Morris" → allowed to merge

**Test Results:** 342/345 tests pass (3 pre-existing failures unrelated to this fix)

**Confidence:** HIGH - This fix targets the exact code location where the merge occurs

## Next Action
Re-run analysis to verify fix resolves the character merge issue. Phase set to `awaiting_analysis`.
