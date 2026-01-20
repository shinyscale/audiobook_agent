# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 7
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.275

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Pipeline Notes
- Analysis completed successfully
- LLM identity detection warning occurred but did not affect pipeline execution

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 5/10 <- FAILING
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 4/10 <- FAILING
- HTML Presentation: 9/10
- **Overall: 7.05/10** (threshold: 8.0)

## Score Breakdown

### Structure Detection: 9/10

**What works:**
- Correctly identified 3 chapters matching the original's I, II, III structure
- All chapters have HIGH confidence
- Word counts and durations are reasonable (1734, 936, 4182 words)
- Chapter boundaries appear accurate

**Minor issue:**
- Chapter 3 has unusually high word count (4182) because it includes the Project Gutenberg license text at the end

### Character Extraction: 5/10 <- CRITICAL ISSUES (UNCHANGED FROM ATTEMPT 5)

**What works:**
- Mr. White, Mrs. White, Sergeant-Major Morris correctly identified
- Morris has aliases ["Morris", "the sergeant-major"] ✓
- "The stranger from Maw and Meggins" correctly identified as separate character

**CRITICAL ISSUES (NOT FIXED BY ATTEMPT 6):**

1. **FALSE CHARACTER SPLIT: "White" vs "Mr. White"**
   - "Mr. White" (10 mentions) and "White" (44 mentions) are STILL listed as SEPARATE characters
   - The prompt improvements in attempt 5→6 had NO EFFECT

2. **HERBERT WHITE WRONGLY ALIASED TO "WHITE"**
   - "White" entry still has aliases: ["Herbert White", "Herbert"]
   - Herbert should be his own entry - he's the son who dies, not the father
   - The family relationship detection did NOT work

3. **NONSENSICAL "the stranger" ENTRY (UNCHANGED)**
   - Character entry "the stranger" still has aliases: ["the old man", "the old woman", "the soldier"]
   - This is COMPLETELY WRONG - these are THREE different people
   - The epithet alias prompt improvements had NO EFFECT

4. **ORPHAN ENTRY: "his wife" (UNCHANGED)**
   - "his wife" (2 mentions) still exists as separate character
   - Should merge with "Mrs. White"

5. **CHAPTER 3 CHARACTERS_PRESENT STILL WRONG**
   - Shows: ["the old man", "the old woman"]
   - Should show: ["Mr. White", "Mrs. White"]

### Character Profiles: 6/10

**What works:**
- Mr. White's profile is accurate: elderly, white-haired, thin grey beard
- Mrs. White's profile captures her emotional arc well
- Sergeant-Major Morris has good physical description

**Issues:**
- "White" character profile is confused - describes elderly man but aliases include young Herbert
- Missing Herbert's actual profile
- All relationship fields are empty `{}`

### Chapter Summaries: 9/10

**What works:**
- All three chapter summaries are accurate and capture key events
- Chapter 1: Setup, Morris's arrival, the paw, first wish
- Chapter 2: Maw and Meggins representative, Herbert's death, £200 coincidence
- Chapter 3: Grief, second wish, knocking, third wish

**Minor issues:**
- Summaries are on the long side but still useful

### Pronunciation Guide: 4/10 <- CRITICAL ISSUES (UNCHANGED)

**Major problems:**

1. **COMMON WORD FALSE POSITIVES (50%+ of entries)**
   - "his" (99 occurrences) flagged as proper_noun
   - "old" (42 occurrences) flagged as proper_noun
   - "from" (38 occurrences) flagged as proper_noun
   - "man" (23 occurrences) flagged as proper_noun
   - "wife" (15 occurrences) flagged as proper_noun
   - "woman" (11 occurrences) flagged as proper_noun
   - "soldier" (5 occurrences) flagged as proper_noun

2. **Project Gutenberg boilerplate contamination**
   - "GutenbergTM" (57 occurrences!)
   - "eBooks" (7 occurrences)
   - Plus "AS-IS", "MERCHANTABILITY", "nonproprietary"

3. **80 pronunciation entries for a 7000-word story is excessive**

**What IS useful:**
- "fakir" / "fakirs" - correctly flagged
- "rubicund" - correctly flagged
- "antimacassar" - correctly flagged
- "bibulous" - correctly flagged
- "Laburnam" - correctly flagged
- Homograph entries (house, read, wind, live, minute) are helpful

### HTML Presentation: 9/10

**What works:**
- Clean, professional dark theme
- Tab navigation works
- Statistics clearly displayed
- Character profiles well-formatted

**Minor issues:**
- Empty timing values for "started_at"/"ended_at"

---

## CRITICAL FINDING: ATTEMPT 6 FIX HAD ZERO EFFECT

The prompt improvements made in commit `ec42d22` ("Fix: Improve character merging prompts for title variants and family relationships") **did not change the output at all**. The character extraction results are identical to attempt 5:

| Issue | Attempt 5 | Attempt 6 | Status |
|-------|-----------|-----------|--------|
| "Mr. White" vs "White" split | YES | YES | UNFIXED |
| Herbert aliased to "White" | YES | YES | UNFIXED |
| "the stranger" with 3 different people | YES | YES | UNFIXED |
| "his wife" orphaned | YES | YES | UNFIXED |
| 80 pronunciation entries | YES | YES | UNFIXED |

**Root Cause Analysis:**

The fix modified the prompt text in `PAIRWISE_ALIAS_PROMPT` and `EPITHET_ALIAS_PROMPT`, but:

1. **The prompts may not be reaching the LLM** - Need to verify the modified prompts are actually being used
2. **The LLM may be ignoring the guidance** - Even with better prompts, the model may still make wrong decisions
3. **The issue may be earlier in the pipeline** - Character candidates may not be paired correctly before LLM evaluation

**Investigation needed:** Check if the prompt changes are actually being applied by:
- Adding logging to verify which prompt text is sent to LLM
- Checking if there's prompt caching that bypasses changes
- Verifying the consensus.py changes are in the correct code path

---

## Current Issues (Priority Order)

### CRITICAL

1. **FIX ATTEMPT HAD NO EFFECT - INVESTIGATE WHY**
   - Problem: Prompt improvements in consensus.py didn't change output
   - Evidence: All character issues identical between attempt 5 and 6
   - Location: Verify `src/pipeline/character_extraction/consensus.py` changes are applied
   - Fix: Add logging to confirm prompt changes reach LLM, then try different approach

2. **False character split: "White" vs "Mr. White"**
   - Problem: Same person split into 2 entries (44 + 10 = 54 mentions total)
   - Evidence: The text uses "White" and "Mr. White" interchangeably for the father
   - Fix: If prompts don't work, try heuristic pre-merge for "Title + LastName" = "LastName"

3. **Herbert wrongly aliased to "White" (father)**
   - Problem: Son's name merged as alias of ambiguous "White" entry
   - Evidence: Herbert is the son who works at Maw and Meggins and dies
   - Fix: Prevent merging when contexts show parent-child relationship

4. **"the stranger" has aliases for 3 different characters**
   - Problem: ["the old man", "the old woman", "the soldier"] are NOT one person
   - Evidence: "the old man" = Mr. White, "the old woman" = Mrs. White, "the soldier" = Morris
   - Fix: Generic epithets like "the old man/woman" should NOT create new characters OR merge with other epithets

### HIGH

5. **Pronunciation flagging common English words**
   - Problem: "his", "old", "from", "man", "wife", "woman" flagged
   - Root cause: Words from character names (including broken entries like "the old man") are all flagged
   - Fix: This is DOWNSTREAM of character issues - fixing characters may partially fix this
   - Additional fix: Add common English word filter (top 5000-10000 words)

6. **Project Gutenberg boilerplate contamination**
   - Problem: Legal text analyzed as story content
   - Evidence: "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/refine.py`
   - Fix: Add Gutenberg license detection and removal

### MEDIUM

7. **"his wife" orphan character entry**
   - Problem: Should merge with "Mrs. White"
   - Location: Relational descriptor handling
   - Fix: "his wife" → "Mrs. White" when in same context

8. **Missing relationship data**
   - Problem: All relationship fields empty
   - Evidence: Mr./Mrs. White married, Herbert their son, Morris old friend - none captured
   - Fix: May need separate relationship extraction pass

---

## Fix History

### Attempt 1 → 2: Fixed character validation for company names
- Added rejection criteria for organizations
- Result: Pipeline still failed with same error

### Attempt 2 → 3: Fixed LLM response type handling
- Made `_extract_json()` type-safe
- Result: NEW error - LLM responses truncated

### Attempt 3 → 4: Applied max_tokens from AgentConfig
- Fixed configuration propagation bug
- Result: SAME truncation error

### Attempt 4 → 5: Reduced character extraction chunk size
- Reduced `character_llm_chunk_chars` from 8000 to 5000
- Result: Pipeline completed successfully

### Attempt 5 → 6: Improved character merging prompts
- Modified PAIRWISE_ALIAS_PROMPT and EPITHET_ALIAS_PROMPT
- Added title variant handling, family relationship guidance
- Increased epithet context size from 140 to 250 chars
- **Result: ZERO EFFECT - output unchanged**

### Attempt 6 → 7: Fixed title variant merge validation
- Root cause: `src/pipeline/character_extraction/consensus.py:_validate_merge():1682`
- Problem: When counting family members with shared last names, the code excluded "Mr. White" and "Mrs. White" because their first word was a title. This caused the substring pre-merge check to never execute.
- Fix #1: Include title-only names in family member count (line 1682)
- Fix #2: Add explicit title variant handling (lines 1698-1752) to merge "Mr. White" + "White" while rejecting "Herbert White" + "White"
- Smoke test: All 179 character-related unit tests PASS
- Modified: `src/pipeline/character_extraction/consensus.py`
- **Expected result:**
  - "Mr. White" and "White" should merge
  - "Herbert White" should remain separate from father
  - "his wife" may still be orphaned (different root cause)

---

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAILED | - | LLM validation error |
| 2 | FAILED | - | Same error |
| 3 | FAILED | - | Response truncation |
| 4 | FAILED | - | Same truncation |
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated with consistent rubric; FIX HAD NO EFFECT |

*Note: Attempt 5 score of 6.275 appears to use non-integer component scores. Attempt 6 evaluated with integer scores per rubric = 7.05. The underlying issues are identical.

---

## Next Action

**Phase: awaiting_analysis**

Re-run the analysis pipeline to verify the character extraction fix. Expected improvements:
- Character Extraction score should increase (currently 5/10)
- "Mr. White" and "White" should be merged
- "Herbert White" should remain separate from his father

Note: The "his wife" orphan issue and pronunciation false positives are separate problems that may require additional fixes.
