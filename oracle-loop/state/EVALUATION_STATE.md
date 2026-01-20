# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 10
- **Phase:** awaiting_fix
- **baseline_score:** 6.275

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json
- Analysis completed: 2026-01-20 01:25:30
- Pipeline time: 14m 53s

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10 ✓
- **Overall: 7.05/10** (threshold: 8.0)

---

## CRITICAL FINDING: CASE SENSITIVITY FIX DID NOT SOLVE THE PROBLEM

**The `.lower()` fix was applied correctly, but "Mr. White" and "White" still did not merge.**

After investigation, the root cause is **NOT** just case sensitivity. The real issues are:

### Analysis of Why the Fix Didn't Work

1. **Herbert White got incorrectly aliased to "White" first**
   - Current state: "White" (44 mentions) has aliases: ["Herbert White", "Herbert"]
   - This is WRONG - Herbert is the SON who DIES in Chapter 2
   - Once Herbert was merged into "White", the system may have avoided merging "Mr. White" because the "White" entry now represents "Herbert" (wrong person)

2. **The title+lastname merge logic may not be triggered**
   - Even with `.lower()` fixed, the merge may be blocked by other conditions
   - Need to check: family member blocking, LLM rejection, or ordering issues

3. **Multiple White family members exist**
   - Mr. White (father), Mrs. White (mother), Herbert White (son)
   - The system correctly keeps "Mrs. White" separate
   - But it incorrectly merged Herbert to "White" instead of keeping him separate
   - And it failed to merge "Mr. White" with "White"

### The CORRECT Merge Should Be:
- "Mr. White" + "White" → SAME (title variant of father)
- "Herbert White" + "Herbert" → SAME (first name variant of son)
- "Mrs. White" → separate entry (mother)
- Herbert ≠ Mr. White ≠ Mrs. White (different people)

### What Went Wrong:
- "Herbert White" + "Herbert" were merged into "White" entry
- This created a "White" entry that represents Herbert (the son)
- "Mr. White" stayed separate (correctly not merging with Herbert)
- BUT "Mr. White" should have been the one to merge with "White"

---

## Score Breakdown

### Structure Detection: 9/10 ✓

**What works:**
- Correctly identified 3 chapters matching the original's I, II, III structure
- All chapters have HIGH confidence
- Word counts reasonable (1734, 936, 4182 words)
- Chapter boundaries appear accurate

**Minor issue:**
- Chapter 3 has unusually high word count (4182) because it includes Project Gutenberg license text

### Character Extraction: 5/10 ← CRITICAL ISSUES

**What works:**
- Mr. White correctly identified as separate character
- Mrs. White correctly identified as separate character
- Sergeant-Major Morris has correct aliases ["Morris", "the sergeant-major"]
- "Stranger from Maw and Meggins" correctly identified
- Chapters 1 and 2 characters_present are correct

**CRITICAL ISSUES:**

1. **FALSE CHARACTER SPLIT: "Mr. White" vs "White"** (still not merged after fix!)
   - "Mr. White" (10 mentions) and "White" (44 mentions) are SEPARATE
   - The text uses both interchangeably for the father
   - **FIX APPLIED BUT DID NOT WORK**

2. **HERBERT WHITE WRONGLY ALIASED TO "White"**
   - "White" entry has aliases: ["Herbert White", "Herbert"]
   - Herbert is the SON who DIES - he is NOT "White" (the father)
   - This is the WRONG direction - Herbert should stay separate, Mr. White should merge with White

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
   - Downstream of broken character entries

### Character Profiles: 6/10

**What works:**
- Mr. White's profile is accurate: elderly, thin grey beard, white-haired
- Mrs. White's profile captures her emotional arc
- Sergeant-Major Morris has good physical description (tall, burly, beady-eyed, rubicund)

**Issues:**
- "White" character profile mixes father and son traits (because Herbert wrongly merged)
- Missing Herbert's actual profile (wrongly aliased to "White")
- All relationship fields are empty `{}`

### Chapter Summaries: 9/10 ✓

**What works:**
- All three chapter summaries are accurate and capture key events
- Chapter 1: Setup, Morris's arrival, the paw, first wish
- Chapter 2: Herbert's death, £200 compensation
- Chapter 3: Grief, second wish, knocking, third wish
- Appropriate length for narrator preparation

### Pronunciation Guide: 4/10 ← CRITICAL ISSUES

**Major problems:**

1. **COMMON WORD FALSE POSITIVES (8+ entries)**
   - "his" (99 occurrences) flagged as proper_noun
   - "old" (42 occurrences) flagged as proper_noun
   - "from" (38 occurrences) flagged as proper_noun
   - "man" (23 occurrences) flagged as proper_noun
   - "wife" (15 occurrences) flagged as proper_noun
   - "woman" (11 occurrences) flagged as proper_noun
   - "soldier" (5 occurrences) flagged as proper_noun
   - "does" (2 occurrences) flagged as proper_noun

2. **Project Gutenberg boilerplate contamination**
   - "GutenbergTM" (57 occurrences!)
   - Legal terms from license text analyzed as story content

3. **80 pronunciation entries for a 7000-word story is excessive**

**Root cause:** Words extracted from broken character entries (like "the old man", "the soldier") are being flagged.

**What IS useful:**
- Actual character names (White, Herbert, Morris, Meggins, Maw)
- Some genuinely useful entries: rubicund, fakir, Laburnam, antimacassar

### HTML Presentation: 9/10 ✓

**What works:**
- Clean, professional styling with dark theme
- Tab navigation functional
- Character profiles with evidence quotes
- Chapter summaries with characters present
- Pronunciation entries with context examples
- Print styles included

---

## Current Issues (Priority Order)

### CRITICAL

1. **Herbert wrongly merged INTO "White" entry**
   - Problem: "White" (44 mentions) has aliases ["Herbert White", "Herbert"]
   - Evidence: Herbert is the SON who dies at work in Chapter 2, not the father
   - Root cause: The merging chose the WRONG canonical name - "Herbert White" should NOT merge with "White"
   - Location: `src/pipeline/character_extraction/consensus.py` - alias candidate pairing/selection
   - Fix: When merging "Herbert White" with "Herbert", the canonical should be "Herbert White" or "Herbert", NOT "White"
   - Impact: Once Herbert is correctly separated, "Mr. White" can merge with "White"

2. **"Mr. White" and "White" still not merged**
   - Problem: Despite case sensitivity fix, they remain separate
   - Evidence: "Mr. White" (10 mentions) separate from "White" (44 mentions)
   - Root cause: May be blocked because "White" now represents Herbert (wrong merge happened first)
   - Location: `src/pipeline/character_extraction/consensus.py` - `_validate_merge()`
   - Fix: Fix Herbert first (Critical #1), then this should work

3. **"the stranger" has aliases for 3 different characters**
   - Problem: ["the old man", "the old woman", "the soldier"] merged as one person
   - Evidence: These are Mr. White, Mrs. White, and Morris respectively
   - Root cause: Generic epithets being over-merged
   - Location: Epithet merging logic
   - Fix: Epithets like "the old man/woman" should NOT merge with "the stranger" - they're different referents

### HIGH

4. **Pronunciation flagging common English words**
   - Problem: "his", "old", "from", "man", "wife", "woman" flagged
   - Root cause: Words from character names (including broken entries) are all flagged
   - Location: Pronunciation flagging pipeline
   - Fix: Add common English word filter (top 5000-10000 words)
   - Note: Partially DOWNSTREAM of character issues

5. **Project Gutenberg boilerplate contamination**
   - Problem: Legal text analyzed as story content
   - Evidence: "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/refine.py`
   - Fix: Add Gutenberg license detection and removal

### MEDIUM

6. **"his wife" orphan character entry**
   - Should merge with "Mrs. White"
   - Location: Relational descriptor handling

7. **Missing relationship data**
   - All relationship fields empty
   - Mr./Mrs. White married, Herbert their son, Morris old friend - none captured

8. **Chapter 3 characters_present uses epithet names**
   - Shows ["the old man", "the old woman"] instead of proper names
   - Downstream of character extraction issues

---

## Fix History

### Attempt 1 → 2: Fixed character validation for company names
- Result: Pipeline still failed with same error

### Attempt 2 → 3: Fixed LLM response type handling
- Result: NEW error - LLM responses truncated

### Attempt 3 → 4: Applied max_tokens from AgentConfig
- Result: SAME truncation error

### Attempt 4 → 5: Reduced character extraction chunk size
- Result: Pipeline completed successfully

### Attempt 5 → 6: Improved character merging prompts
- Result: ZERO EFFECT - output unchanged

### Attempt 6 → 7: Fixed title variant merge validation
- Result: NEVER TESTED - analysis ran before fix

### Attempt 7 → 8: Re-ran analysis to test fix
- Result: FIX STILL DOESN'T WORK - period not stripped from "Mr."

### Attempt 8 → 9: Fixed title period stripping bug (INCOMPLETE)
- Result: FIX STILL DOESN'T WORK - need `.lower()` for case-insensitive comparison

### Attempt 9 → 10: Fixed case sensitivity in title check
- Added `.lower()` to line 1725
- Smoke test passed
- Unit tests passed
- **Result: FIX DID NOT SOLVE THE PROBLEM**
- **Root cause identified: Herbert is wrongly merged INTO "White" first**

---

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1-4 | FAILED | - | Various pipeline errors |
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated with consistent rubric |
| 7-9 | 7.05 | +0.775 | Various fix attempts |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't work - deeper issue found |

*Note: Baseline from inconsistent scoring.

---

## Analysis: Why the Case Sensitivity Fix Didn't Work

The `.lower()` fix at line 1725 is technically correct - it makes the title check case-insensitive. BUT the merge still doesn't happen because:

**Hypothesis:** The "White" entry already has Herbert's data merged into it by the time "Mr. White" is considered for merging. The system may be:
1. Looking at the "White" entry and seeing aliases ["Herbert White", "Herbert"]
2. Deciding "Mr. White" should NOT merge with an entry that represents "Herbert"
3. This is actually CORRECT behavior given the corrupted state

**Real fix needed:**
1. Prevent "Herbert White"/"Herbert" from merging into bare "White"
2. When a first name + last name pattern exists, it should be canonical, not reduced to just last name
3. "Herbert White" + "Herbert" → canonical should be "Herbert White" or "Herbert"
4. "Mr. White" + "White" → canonical should be "Mr. White" (title+lastname is more specific)

---

## Next Action

**Phase: awaiting_fix**

The case sensitivity fix was applied but the real problem is that Herbert is incorrectly merged into "White" before "Mr. White" is considered. Need to:

1. **FIX CRITICAL #1:** Prevent "FirstName LastName" from merging into bare "LastName" when there are multiple family members with that lastname
   - "Herbert White" should NOT merge with "White" when "Mr. White" and "Mrs. White" also exist
   - Instead, "Herbert White" + "Herbert" should create a "Herbert White" or "Herbert" entry
   - Then "Mr. White" + "White" can correctly merge

2. **Location:** `src/pipeline/character_extraction/consensus.py` - look at how canonical names are chosen when merging, and how family member detection works

3. **Key insight:** The family member blocking logic may need to work BOTH ways:
   - Currently: Blocks "Mr. White" + "Mrs. White" (correct - different people)
   - Missing: Block "Herbert White" + "White" when other family members exist
   - The bare "White" is AMBIGUOUS and should not be chosen as canonical
