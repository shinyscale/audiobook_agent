# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Last modified: 2026-01-31 00:12:30 (attempt 5 analysis complete)

## Pipeline Notes
- **LLM chapter detection fix: SUCCESS** ✓
  - Structure detection completed successfully (9 chapters found)
  - No error objects returned from LLM marker proposer
  - Competitive structure mode working correctly
- **Analysis completed in 110m 38s**
- Model: qwen3-next:80b-a3b-instruct-q8_0
- Competitive stages: characters, structure, summaries (via --competitive-all)
- **Pronunciation stage warnings**: Model returned error objects for some pronunciation batches
  - These were logged as warnings but did not block completion
  - 402 pronunciation entries generated, 61 high confidence, 341 medium confidence
- **GATSBY-TRACK logs**: NO GATSBY/GATZ in supporting cast (Steps 5, 5.5)
  - But summary shows "Jay Gatsby (aka Gatsby, James Gatz) - 268 mentions"
  - Suggests Gatsby is in main_cast, not supporting (logging only checked supporting)
- **Character extraction**: 35 characters total, 23 from main pass, 12 from summaries

## Latest Scores (Attempt 4 - FRESH EVALUATION)

- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Detailed Score Justification

### Structure Detection: 10/10 ✓
- 9 chapters detected (I through IX) - matches expected count exactly
- All chapter boundaries correct
- Roman numeral titles handled properly
- No merged or split chapters

### Character Extraction: 8/10 ✓ (IMPROVED from 7/10)
**Major improvement:** Wolfsheim fix WORKED!
- main_cast_7 "Meyer Wolfsheim" now has aliases: `["Meyer Wolfshiem", "Wolfshiem"]`
- Both spelling variants successfully merged

**All major characters present:**
- Nick Carraway (narrator ✓), James Gatz/Jay Gatsby (271 mentions), Daisy Buchanan, Tom Buchanan
- Jordan Baker, Myrtle Wilson, George Wilson, Meyer Wolfsheim
- Henry C. Gatz (now with full name and aliases - improved from just "Gatz")

**Alias handling improved:**
- James Gatz correctly has aliases: `["Jay Gatsby", "Gatsby", "the host", "Gatsby of West Egg"]`
- Henry C. Gatz has aliases: `["Mr. Gatz", "Gatsby's father", "Gatz"]`

**Remaining minor issues (not blocking):**
- "Town Tattle" (supporting_9) is a publication, not a character - false positive but minor
- "Doctor T. J. Eckleburg" (main_cast_9) extracted as character - ACCEPTABLE per rubric (symbolic presence with narrative significance)
- "The man with owl-eyed glasses" could use "Owl Eyes" nickname but text may not use that term

### Character Profiles: 7.5/10 ✗ (FAILING)

**Major gap: Physical appearance data sparse**
- Only 6/38 characters have non-"unknown" appearance data
- Characters with appearance: Tom Buchanan, Henry C. Gatz, Catherine, Mr. McKee, Dan Cody, Miss Baedeker
- Missing appearances for MAJOR characters: Nick, Gatsby, Daisy, Jordan

**What's working well:**
- 28/38 characters have relationship data
- Personality profiles present (e.g., Nick: "observant, reserved, diplomatic")
- Voice guidance present with example quotes
- Temperament data present

**Why this is 7.5 instead of 8:**
- Appearance is a key component of character profiles for narrators
- Major characters like Gatsby and Daisy have "unknown" appearance despite having textual descriptions
- The text describes Gatsby ("an elegant young rough-neck") and Daisy ("a face... bright eyes and a bright passionate mouth")

### Chapter Summaries: 9.5/10 ✓
- All 9 chapters have summaries
- Verified sample summaries are accurate:
  - Chapter I: Nick's father's advice, moving to West Egg ✓
  - Chapter II: Valley of Ashes, Doctor T. J. Eckleburg reference ✓
  - Chapter III: Gatsby's lavish party ✓
- Key events captured with appropriate detail
- Narrator-useful tone information present

### Pronunciation Guide: 9/10 ✓ (IMPROVED from 8.5)
- 405 entries with 386 having IPA (95% coverage)
- Wolfsheim/Wolfshiem correctly handled with IPA `/ˈwʊlfʃiːm/`
- Detailed notes provided (e.g., "Pronounce 'Wolf' as in the animal")
- Foreign terms and unusual names properly flagged
- Context examples included for each entry

### HTML Presentation: 9/10 ✓
- Clean tabbed navigation (Chapters, Characters, Pronunciation)
- Character profiles well-organized with expandable evidence sections
- Confidence badges displayed
- Relationships shown as tags
- Voice guidance section formatted with example quotes

## Current Issues (Priority Order)

### BLOCKING (NEW - 2026-01-30 Evening)

-1. **LLM chapter marker detection fails in competitive structure mode**
   - Problem: `qwen3-next:80b-a3b-instruct-q8_0` returns error objects instead of chapter arrays
   - Error message: `{"error": "No explicit chapter or section markers found in the provided text"}`
   - Impact: Structure detection cannot complete, blocks entire analysis pipeline
   - Location: `src/pipeline/chapter_detection/marker_detection.py` - LLM marker proposer
   - Observed: Attempt 5 (2026-01-30 evening) - multiple analysis runs all stuck at structure detection
   - Context: Same model succeeded in attempt 4, but attempt 4 evaluation state doesn't show `--competitive-structure` flag usage
   - Hypothesis: Competitive structure mode (`--competitive-structure`) triggers different code path that breaks with qwen3-next
   - Required fix: Either (a) fix json_mode handling in competitive structure, or (b) disable competitive structure for qwen3-next
   - Note: The model KNOWS about Roman numerals I-IX (mentions them in error message) but refuses to extract them

### CRITICAL (NEW - 2026-01-30)

0. **Jay Gatsby missing from main_cast entirely**
   - Problem: The title character "Jay Gatsby" is NOT in main_cast
   - Evidence: supporting_11 is "James Gatz" (only 4 actual text occurrences) with 271 mentions
   - "James Gatz" has aliases: `["Jay Gatsby", "Gatsby", "the host", "Gatsby of West Egg"]`
   - But "Gatsby" appears ~262 times in text - should be canonical name
   - Missing ID: main_cast_1 is missing from the ID sequence (0, 2, 3, 4...)
   - **Debug logging added** - see "Debug Logging" section below
   - Location: Likely `src/agents/characters.py` Step 3.6 (`_deduplicate_alias_canonical_conflicts`)
   - Root cause: Unknown - debug logging will identify exact failure point

### HIGH

1. **Physical appearance data missing for major characters**
   - Problem: 32/38 characters have `appearance.summary: "unknown"` including Gatsby, Nick, Daisy, Jordan
   - Evidence: The text contains physical descriptions (e.g., Tom is described as "a sturdy straw-haired man of thirty")
   - Location: `src/pipeline/character_profiling/` - appearance extraction
   - ID patterns: Affects main_cast_* characters
   - Fix: Improve appearance extraction prompts to find physical descriptions from text evidence

### MEDIUM

2. **False positive: "Town Tattle" extracted as character**
   - Problem: Publication listed as character (supporting_9, 3 mentions)
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Prompt clarification to exclude publications/media titles

3. **Canonical name ordering for Gatsby** (SUPERSEDED by issue #0)
   - Problem: supporting_11 uses "James Gatz" as canonical name with "Jay Gatsby" as alias
   - Impact: Minor - narrators more likely to recognize "Jay Gatsby" as primary name
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or cross-pipeline merge logic
   - Note: This is actually a symptom of issue #0 - Jay Gatsby should be in main_cast

## Debug Logging (NEW - 2026-01-30)

Added GATSBY-TRACK logging to trace where Jay Gatsby disappears from the pipeline.

**How to use:**
```bash
./oracle-loop/oracle-loop.sh analyze gatsby 2>&1 | grep "GATSBY-TRACK"
```

**Logging locations:**
| Step | File | What it tracks |
|------|------|----------------|
| Pass1 | main_cast.py:547-554 | Characters found in Pass 1 |
| Pass2 | main_cast.py:594-598 | Aliases resolved for Gatsby/Gatz |
| Step3-grounding | characters.py:206 | After grounding gate |
| Step3.4-firstname | characters.py:214 | After firstname merge |
| Step3.5-within-main | characters.py:219 | After within-main merge |
| Step3.6-alias-dedupe | characters.py:226 | After alias-canonical dedup (CRITICAL) |
| Step5-NER | characters.py:470 | Supporting cast from NER |
| Step5.5-lastname | characters.py:569-570 | After lastname merge |

**Expected output format:**
```
GATSBY-TRACK [StepName] main_cast: ['Jay Gatsby (262m, id=main_cast_1, aliases=[Gatsby, ...])]
```
Or if missing:
```
GATSBY-TRACK [StepName] main_cast: NO GATSBY/GATZ FOUND!
```

**What to look for:**
1. Does Pass1 find "Jay Gatsby" or "James Gatz"?
2. Does Pass2 add "James Gatz" as alias of "Jay Gatsby" or vice versa?
3. At which step does "Jay Gatsby" disappear from main_cast?
4. When does "James Gatz" appear in supporting cast with Gatsby's aliases?

## Fix History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed |
| 2 | Main cast extraction failure | src/pipeline/character_extraction_v2/main_cast.py | Diagnostic logging |
| 3 | JSON format for qwen3-next | src/pipeline/character_extraction_v2/main_cast.py | Wrapped object prompts - MAJOR IMPROVEMENT (+1.15) |
| 4 | Wolfsheim/Wolfshiem spelling variants | src/agents/characters.py:2419-2445 | **VERIFIED FIXED** - both variants now merged |
| 5 | Missing physical appearance data | src/analyzer.py:2608-2645 | Improved mention sampling: first 3 mentions (was 1), 800-char context (was 400), 12 samples (was 10) |
| 5b | Jay Gatsby missing from main_cast | src/agents/characters.py, src/pipeline/character_extraction_v2/main_cast.py | Added GATSBY-TRACK debug logging to identify exact failure point |
| 5c | LLM chapter detection returns error objects | src/pipeline/chapter_detection/proposers/llm.py:71-93, 107-129 | **VERIFIED FIXED** - Added explicit "NEVER return error objects" at start and end of prompts |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |
| 2 | 7.35 | 0.00 | First scoreable run - character fragmentation + missing profiles |
| 3 | 8.5 | +1.15 | Character consolidation fixed, 2 categories still below 8.0 |
| 4 | 8.6 | +1.25 | Character Extraction now passes (8/10), only Profiles failing |

## Configuration Notes

Model: qwen3-next:80b-a3b-instruct-q8_0 (user-specified, DO NOT CHANGE)
Competitive Mode: single
Output files: Verified fresh - last modified 2026-01-30 19:14:52

## Next Action

**Re-run analysis to verify LLM chapter detection fix and check profile improvements.**

**Fix Applied (Attempt 5c - LLM Chapter Detection):**
- **Root cause:** `qwen3-next:80b` in json_mode was returning `{"error": "No markers found..."}` instead of `{"markers": []}` when no markers found, despite prompt instructions.
- **Change:** Added explicit warnings at **start and end** of prompts:
  - `CRITICAL: Return ONLY valid JSON in this EXACT format: {"markers": [...]}`
  - `NEVER return {"error": "..."} - that format will crash the system`
  - `REMINDER: If NO markers found, return {"markers": []} - Do NOT return an error object`
- **Files modified:**
  - `src/pipeline/chapter_detection/proposers/llm.py` - MARKER_PROMPT_TEMPLATE (lines 71-93), NARRATIVE_PROMPT_TEMPLATE (lines 107-129)
- **Smoke test:** ✅ PASSED - Model now returns `{"markers": [{"marker_text": "I", "title": "Chapter 1", ...}]}` instead of error object
- **Expected impact:** Structure detection stage should now complete successfully in competitive mode

**Previous Fixes Still Active:**
- **Attempt 5a (Profiles):** Improved mention sampling (first 3 mentions, 800-char context, 12 total samples)
- **Attempt 5b (Debug Logging):** GATSBY-TRACK logging to identify where Jay Gatsby disappears

**What to check in next analysis:**
1. Does structure detection complete without errors?
2. Did profile improvements raise Character Profiles from 7.5 → 8.0+?
3. Do GATSBY-TRACK logs show where Jay Gatsby disappears?
