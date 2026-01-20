# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 11
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.275

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json
- Analysis completed: 2026-01-20 02:51:10
- Pipeline time: 37m 47s

## Pipeline Notes
- Analysis completed successfully with qwen3:32b models
- Used smaller character model (32b instead of 80b) to avoid timeouts
- 8 characters extracted, 5 profiles generated
- 78 pronunciation flags generated
- Some low-confidence profiles for Mr. White and Mrs. White (0.30)

---

## Fix Applied in Attempt 11

**Commit:** `4a1dfd3 - Fix: Prevent ambiguous bare last names from becoming canonical`

**What the fix does:**
- Added `is_ambiguous_lastname_only()` helper function to `src/pipeline/character_extraction/consensus.py`
- Detects bare last names (single-word) that are ambiguous when fuller forms exist in the same merge component
- Example: "White" is marked as ambiguous if "Herbert White" or "Mr. White" are also present
- Updated canonical name selection to prioritize non-ambiguous names BEFORE mention count
- New priority order: 1) Not ambiguous, 2) Mention count, 3) More parts, 4) No title, 5) Alpha

**Expected outcome:**
- "Herbert White" should become canonical instead of "White" (when Herbert-related names are in the same component)
- "Mr. White" should be able to merge with "White" once the Herbert issue is resolved
- This addresses the root cause identified in attempt 10: Herbert was being merged INTO "White" because "White" had the highest mention count despite being ambiguous

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1-4 | FAILED | - | Various pipeline errors |
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated with consistent rubric |
| 7-9 | 7.05 | +0.775 | Various fix attempts |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't work - deeper issue found |
| 11 | PENDING | PENDING | Fixed canonical selection - awaiting re-analysis |

*Note: Baseline from inconsistent scoring.

---

## Previous Scores (from attempt 10, STALE DATA)

These scores are from BEFORE the fix was applied. Do not use for evaluation.

- Structure Detection: 9/10
- Character Extraction: 5/10
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 4/10
- HTML Presentation: 9/10
- **Overall: 7.05/10** (threshold: 8.0)

---

## Known Issues (from attempt 10)

These issues were identified BEFORE the fix. The fix targets Critical #1 and #2.

### CRITICAL

1. **Herbert wrongly merged INTO "White" entry** ← FIX TARGETS THIS
   - Problem: "White" (44 mentions) has aliases ["Herbert White", "Herbert"]
   - Evidence: Herbert is the SON who dies at work in Chapter 2, not the father
   - Root cause: Canonical selection prioritized mention count, choosing ambiguous "White"
   - **FIX APPLIED:** `is_ambiguous_lastname_only()` now prevents "White" from becoming canonical

2. **"Mr. White" and "White" still not merged** ← FIX SHOULD HELP THIS
   - Problem: Despite case sensitivity fix, they remain separate
   - Evidence: "Mr. White" (10 mentions) separate from "White" (44 mentions)
   - Root cause: May be blocked because "White" now represents Herbert (wrong merge happened first)
   - **Expected:** Once Herbert is separate, title+lastname merge should work

3. **"the stranger" has aliases for 3 different characters**
   - Problem: ["the old man", "the old woman", "the soldier"] merged as one person
   - Evidence: These are Mr. White, Mrs. White, and Morris respectively
   - Root cause: Generic epithets being over-merged
   - **FIX DOES NOT ADDRESS THIS** - separate LLM prompt issue

### HIGH

4. **Pronunciation flagging common English words**
   - Problem: "his", "old", "from", "man", "wife", "woman" flagged
   - Root cause: Words from character names (including broken entries) are all flagged
   - **PARTIALLY DOWNSTREAM** of character issues

5. **Project Gutenberg boilerplate contamination**
   - Problem: Legal text analyzed as story content
   - Evidence: "GutenbergTM" flagged 57 times

### MEDIUM

6. **"his wife" orphan character entry** - Should merge with "Mrs. White"
7. **Missing relationship data** - All relationship fields empty
8. **Chapter 3 characters_present uses epithet names** - Downstream of character issues

---

## Next Action

**REQUIRED: Re-run analysis pipeline with the fix applied.**

The analysis from attempt 10 predates the fix commit. Cannot evaluate until fresh analysis is generated.

Run:
```bash
cd /home/zacharymandrews/Tools/audiobook_agent
audiobook-prep analyze Test_Texts/The_Monkey\'s_Paw.txt --output output/monkeys_paw/analysis.json --html output/monkeys_paw/report.html
```

Then update this state file with:
- Output Files section with new timestamps
- Phase changed to `awaiting_evaluation`
