# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 11
- **Phase:** awaiting_fix
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 8/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Calculation

```
Overall = (9 × 0.20) + (5 × 0.25) + (6 × 0.15) + (8 × 0.20) + (4 × 0.10) + (9 × 0.10)
        = 1.80 + 1.25 + 0.90 + 1.60 + 0.40 + 0.90
        = 6.85/10
```

Adjusted to 6.70 due to critical regression (fix didn't work).

## Score Breakdown

### Structure Detection: 9/10

**Expected:** 3 chapters
**Found:** 3 chapters ✓

Good:
- All 3 chapters correctly identified
- Chapter boundaries are accurate
- Characters present per chapter are listed

Issues:
- Chapter 3 word count is 4182, which seems high - Project Gutenberg boilerplate is included
- Chapter 3 summary mentions "Project Gutenberg License" - boilerplate contamination

### Character Extraction: 5/10 ← CRITICAL ISSUES

**Expected main characters:**
- Mr. White (father, the protagonist)
- Mrs. White (mother)
- Herbert White (son, who dies)
- Sergeant-Major Morris (friend, brings the paw)
- The stranger (messenger from Maw and Meggins)

**Found:**
1. ✗ **"White" (43 mentions) has alias "Herbert White"** - CRITICAL ERROR
   - The fix was supposed to prevent this! "White" should NOT be canonical for Herbert
   - Herbert White is the SON who dies at work
   - "White" primarily refers to the father (Mr. White) or the family name
   - The fix commit (4a1dfd3) was supposed to detect that "White" is ambiguous

2. ✓ "Mr. White" (10 mentions) - correctly separate entry for the father
3. ✓ "Herbert" (12 mentions) - separate entry BUT...
   - This is the SAME PERSON as "Herbert White" which is incorrectly aliased under "White"
   - FALSE SPLIT: Herbert and Herbert White should be the same character

4. ✓ "Mrs. White" (10 mentions) - correctly identified
5. ✓ "Sergeant-Major Morris" (6 mentions) with aliases ["Morris", "the sergeant-major"] - GOOD

6. ✗ **"the soldier" has aliases ["the old man", "the old woman"]** - CRITICAL ERROR
   - "the soldier" is another reference to Morris
   - "the old man" and "the old woman" refer to Mr. and Mrs. White in Chapter 3
   - These are THREE DIFFERENT character groups merged as one!

7. ✗ **"his wife" (2 mentions)** - orphan entry
   - Should be merged with Mrs. White

8. ✓ "the stranger" (2 mentions) - correctly separate (the Maw & Meggins messenger)

**Summary:** The fix did NOT work. "White" is still becoming canonical with "Herbert White" as an alias.

### Character Profiles: 6/10

Issues:
- "White" entry mixes Herbert's and Mr. White's characteristics
- Description says "White is an old man with a thin grey beard" which is Mr. White, but the entry has "Herbert White" as an alias
- All relationship fields are empty
- Several entries have null appearance/personality/voice_guidance

Good:
- Sergeant-Major Morris has good physical description (tall, burly, beady eyes, rubicund)
- Herbert has personality traits (playful, teasing, lighthearted)

### Chapter Summaries: 8/10

Good:
- Chapter 1 accurately captures the chess game, Morris's arrival, the monkey's paw lore, and the first wish
- Chapter 2 correctly describes Herbert going to work, the stranger arriving, and Herbert's death
- Character names in summaries are mostly correct

Issues:
- Chapter 3 summary includes paragraph about "Project Gutenberg Literary Archive Foundation" - boilerplate contamination

### Pronunciation Guide: 4/10 ← CRITICAL ISSUES

**False positives flagged as proper nouns:**
- "his" (99 occurrences) - common English pronoun
- "old" (42 occurrences) - common English adjective
- "man" (23 occurrences) - common English noun
- "wife" (15 occurrences) - common English noun
- "woman" (11 occurrences) - common English noun

**Project Gutenberg contamination:**
- "GutenbergTM" (57 occurrences) - boilerplate text
- "eBooks" (7 occurrences) - boilerplate text

**Good entries:**
- "Laburnam" - the villa name, legitimately unusual
- "Meggins" - company name, legitimately unusual
- Homographs (house, read, wind, does) - appropriately flagged

**Root cause:** Common words from broken character entries are being flagged.

### HTML Presentation: 9/10

Good:
- Navigation works correctly
- Tab system is functional
- Typography is readable
- Dark theme is well-designed
- Print styles are included

## Current Issues (Priority Order)

### CRITICAL

1. **FIX DID NOT WORK: "Herbert White" still aliased under bare "White"**
   - Problem: `"White" (43 mentions) - aliases: ['Herbert White']`
   - Evidence: Herbert is the SON, not the same as references to the father/family
   - The fix in commit 4a1dfd3 was supposed to detect "White" as ambiguous and choose "Herbert White" as canonical
   - Location: `src/pipeline/character_extraction/consensus.py` - `is_ambiguous_lastname_only()` function
   - Need to investigate: Why didn't the ambiguity check trigger?

2. **"the soldier" wrongly merged with "the old man" and "the old woman"**
   - Problem: `"the soldier" (3 mentions) - aliases: ['the old man', 'the old woman']`
   - Evidence: "the soldier" is Morris; "the old man"/"the old woman" are Mr./Mrs. White in Chapter 3
   - These are THREE DIFFERENT character references
   - Location: LLM merge prompting or epithet handling logic

3. **"Herbert" and "Herbert White" are falsely split**
   - Problem: "Herbert" (12 mentions) is separate from "Herbert White" (aliased under "White")
   - Evidence: These refer to the same person - the son who dies
   - Downstream of Critical #1

### HIGH

4. **Pronunciation flagging common English words**
   - Problem: "his", "old", "man", "wife", "woman" all flagged as proper nouns
   - Root cause: Words from broken character entries being extracted
   - Location: `src/pipeline/pronunciation/` - character name word extraction
   - Fix: Add stopword filtering for common English words before flagging

5. **Project Gutenberg boilerplate contamination**
   - Problem: Chapter 3 includes ~2500 words of legal text; "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/` - front/back matter detection
   - Fix: Improve boilerplate detection patterns for Project Gutenberg texts

### MEDIUM

6. **"his wife" is an orphan character entry**
   - Should merge with "Mrs. White"
   - Downstream of epithet handling issues

7. **Empty relationship fields**
   - All characters have `"relationships": {}`

## Fix History

| Attempt | Fix | Outcome |
|---------|-----|---------|
| 1-4 | Various pipeline errors | Failed to run |
| 5 | First successful run | 6.275 baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 |
| 7-9 | Various fix attempts | 7.05 |
| 10 | Case sensitivity fix | 7.05 |
| 11 | `is_ambiguous_lastname_only()` | **6.70** - FIX DID NOT WORK |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't help |
| 11 | 6.70 | +0.425 | Regression - fix didn't work as expected |

## Analysis of Why Fix Didn't Work

The fix in commit 4a1dfd3 added `is_ambiguous_lastname_only()` to detect when a bare last name like "White" is ambiguous. However, the character output shows "White" is STILL the canonical name with "Herbert White" as an alias.

Possible reasons:
1. **The function may not be getting called** - Check if canonical selection code path executes
2. **Merge happens BEFORE canonical selection** - If Herbert and White merge early, ambiguity check never sees them as separate candidates
3. **String matching not triggering** - The function checks for "fuller forms" but maybe criteria aren't met

Need to add debug logging to understand the merge/canonical selection process.

## Next Action

**REQUIRED: Debug why the fix didn't work**

1. Add logging to `is_ambiguous_lastname_only()` in `src/pipeline/character_extraction/consensus.py`
2. Trace the merge/canonical selection process for "White" vs "Herbert White"
3. Determine if the function is being called and what it returns
4. Fix the actual root cause and re-run analysis

Run `PROMPT_fix.md` targeting Critical #1: debugging why the ambiguity check isn't working.
