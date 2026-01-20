# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score:** 6.275

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json
- Analysis completed: 2026-01-20 00:41:37
- Pipeline time: 14m 31s

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 7.05/10** (threshold: 8.0)

---

## CRITICAL FINDING: BUG IN TITLE VARIANT DETECTION

**ROOT CAUSE IDENTIFIED:** The title variant merge fix at line 1725 of `consensus.py` has a bug.

The code checks:
```python
titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}
if len(multi_words) == 2 and multi_words[0] in titles:
```

But for "Mr. White", `multi_words[0]` is `'mr.'` (with a period), NOT `'mr'`.

**The period is not stripped**, so `'mr.' in {'mr', 'mrs', ...}` is **FALSE**.

**Fix needed:** Change line 1725 to:
```python
if len(multi_words) == 2 and multi_words[0].rstrip('.') in titles:
```

This is a ONE-LINE FIX that should finally resolve the "Mr. White" / "White" merge.

---

## Score Breakdown

### Structure Detection: 9/10 ✓

**What works:**
- Correctly identified 3 chapters matching the original's I, II, III structure
- All chapters have HIGH confidence
- Word counts and durations are reasonable (1734, 936, 4182 words)
- Chapter boundaries appear accurate

**Minor issue:**
- Chapter 3 has unusually high word count (4182) because it includes Project Gutenberg license text

### Character Extraction: 5/10 ← CRITICAL ISSUES

**What works:**
- Mr. White, Mrs. White, Sergeant-Major Morris correctly identified
- Morris has aliases ["Morris", "the sergeant-major"] ✓
- "Stranger from Maw and Meggins" correctly identified as separate character
- Chapters 1 and 2 characters_present are correct

**CRITICAL ISSUES:**

1. **FALSE CHARACTER SPLIT: "White" vs "Mr. White"**
   - "Mr. White" (10 mentions) and "White" (44 mentions) are SEPARATE characters
   - These should be merged - the text uses both interchangeably for the father
   - **ROOT CAUSE:** Period not stripped from "Mr." in title variant check (line 1725)

2. **HERBERT WHITE WRONGLY ALIASED TO "WHITE"**
   - "White" entry has aliases: ["Herbert White", "Herbert"]
   - Herbert is the SON who DIES - he is NOT the same as the father
   - The family relationship detection completely failed

3. **NONSENSICAL "the stranger" ENTRY**
   - Character "the stranger" has aliases: ["the old man", "the old woman", "the soldier"]
   - This is COMPLETELY WRONG:
     - "the old man" = Mr. White (the father)
     - "the old woman" = Mrs. White (the mother)
     - "the soldier" = Sergeant-Major Morris
   - These are THREE different people merged into one nonsensical entry

4. **ORPHAN ENTRY: "his wife"**
   - "his wife" (2 mentions) exists as separate character
   - Should merge with "Mrs. White"

5. **CHAPTER 3 CHARACTERS_PRESENT WRONG**
   - Shows: ["the old man", "the old woman"]
   - Should show: ["Mr. White", "Mrs. White"]
   - This is downstream of the broken character entries

### Character Profiles: 6/10

**What works:**
- Mr. White's profile is accurate: elderly, thin grey beard, white-haired
- Mrs. White's profile captures her emotional arc from skeptic to desperate
- Sergeant-Major Morris has good physical description (tall, burly, beady-eyed, rubicund)

**Issues:**
- "White" character profile is confused - mixes father and son traits
- Missing Herbert's actual profile (he's wrongly aliased)
- All relationship fields are empty `{}`
- "the stranger" has no useful profile data

### Chapter Summaries: 9/10 ✓

**What works:**
- All three chapter summaries are accurate and capture key events
- Chapter 1: Setup, Morris's arrival, the paw, first wish
- Chapter 2: Maw and Meggins representative, Herbert's death, £200 compensation
- Chapter 3: Grief, second wish, knocking, third wish
- Appropriate length for narrator preparation

### Pronunciation Guide: 4/10 ← CRITICAL ISSUES

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
   - Plus legal terms from license text

3. **80 pronunciation entries for a 7000-word story is excessive**

**Root cause:** Words from the broken character entries (like "the old man", "the soldier") are being extracted as pronunciation candidates.

**What IS useful:**
- Actual character names (White, Herbert, Morris, Meggins, Maw, Sergeant-Major)

### HTML Presentation: 9/10 ✓

**What works:**
- Character profiles with evidence quotes
- Chapter summaries with characters present
- Pronunciation entries with context examples

---

## Current Issues (Priority Order)

### CRITICAL

1. **Title variant merge bug - period not stripped**
   - Problem: Line 1725 checks `multi_words[0] in titles` but `'mr.'` ≠ `'mr'`
   - Evidence: Debug confirms `'mr.'` is the actual value, not `'mr'`
   - Location: `src/pipeline/character_extraction/consensus.py` line 1725
   - Fix: Change `multi_words[0] in titles` to `multi_words[0].rstrip('.') in titles`
   - Impact: This ONE-LINE FIX should enable "Mr. White" + "White" to merge

2. **Herbert wrongly aliased to "White" (father)**
   - Problem: Son's name merged as alias of ambiguous "White" entry
   - Evidence: Herbert works at Maw and Meggins and DIES in Chapter 2
   - Location: `src/pipeline/character_extraction/consensus.py` - family detection
   - Fix: After fixing #1, "Mr. White" + "White" merge will leave Herbert separate

3. **"the stranger" has aliases for 3 different characters**
   - Problem: ["the old man", "the old woman", "the soldier"] are NOT one person
   - Evidence: These are generic epithets for Mr. White, Mrs. White, and Morris respectively
   - Location: Epithet merging logic
   - Fix: Generic epithets like "the old man/woman" should NOT merge with "the stranger"

### HIGH

4. **Pronunciation flagging common English words**
   - Problem: "his", "old", "from", "man", "wife", "woman" flagged
   - Root cause: Words from character names (including broken entries) are all flagged
   - Fix: Add common English word filter (top 5000-10000 words)
   - Note: This is partially DOWNSTREAM of character issues

5. **Project Gutenberg boilerplate contamination**
   - Problem: Legal text analyzed as story content
   - Evidence: "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/refine.py`
   - Fix: Add Gutenberg license detection and removal

### MEDIUM

6. **"his wife" orphan character entry**
   - Problem: Should merge with "Mrs. White"
   - Location: Relational descriptor handling
   - Fix: "his wife" → "Mrs. White" when in same context

7. **Missing relationship data**
   - Problem: All relationship fields empty
   - Evidence: Mr./Mrs. White married, Herbert their son, Morris old friend - none captured
   - Fix: May need separate relationship extraction pass

8. **Chapter 3 characters_present uses epithet names**
   - Problem: Shows ["the old man", "the old woman"] instead of proper names
   - Root cause: Downstream of character extraction issues
   - Fix: Will be resolved when character extraction is fixed

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
- Modified `src/pipeline/character_extraction/consensus.py`
- Added explicit title variant handling in `_validate_merge()`
- Fixed family member count to include title-only names
- All 179 character-related unit tests PASS
- **Result: NEVER TESTED - analysis.json from 23:43, fix committed at 23:53**

### Attempt 7 → 8: Re-ran analysis to test fix
- No new code changes, just re-ran analysis
- **Result: FIX STILL DOESN'T WORK - period not stripped from "Mr."**

### Attempt 8 → 9: FIX NEEDED
- **BUG:** Line 1725 checks `multi_words[0] in titles` but 'mr.' ≠ 'mr'
- **Fix:** Change to `multi_words[0].rstrip('.') in titles`

---

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAILED | - | LLM validation error |
| 2 | FAILED | - | Same error |
| 3 | FAILED | - | Response truncation |
| 4 | FAILED | - | Same truncation |
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated with consistent rubric |
| 7 | 7.05 | +0.775 | Fix never tested |
| 8 | 7.05 | +0.775 | **BUG FOUND: period not stripped in title check** |

*Note: Attempt 5 baseline of 6.275 from inconsistent scoring. Attempt 6-8 use integer component scores = 7.05.

---

## Next Action

**Phase: awaiting_fix**

Run PROMPT_fix.md to apply the one-line fix at `consensus.py` line 1725:
```python
# Change FROM:
if len(multi_words) == 2 and multi_words[0] in titles:

# Change TO:
if len(multi_words) == 2 and multi_words[0].rstrip('.') in titles:
```

This should finally enable "Mr. White" + "White" to merge correctly.
