# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 7.35

## Latest Scores (Attempt 4)
- Structure Detection: 7.5/10 ✗ (FAILING)
- Character Extraction: 7.0/10 ✗ (FAILING)
  - Completeness: 7.5/10
  - Identity Resolution: 8.0/10 ✓
  - Alias Grouping: 5.5/10
- Character Profiles: 7.0/10 ✗ (FAILING)
- Chapter Summaries: 4.0/10 ✗ (FAILING)
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9.5/10 ✓
- **Overall: 7.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Attempt 4 Net Changes vs Attempt 3

**Fixed in attempt 4:**
- Victor→Alphonse "brother" → FIXED to "son" ✓ (both-names check worked)
- Alphonse→Victor "brother" → FIXED to "father" ✓
- Victor→Clerval "cousin" → FIXED to "close friend" ✓ (canonical-name pat_b worked)
- Clerval→Victor "cousin" → FIXED to "close friend" ✓
- Captain Walton / R.W. no longer separate characters ✓ (title+surname and initials F6 fix worked)

**Regressions in attempt 4:**
- Chapter Summaries: 6.5→4.0 REGRESSION — narrator fix was undone by narrator substitution in analyzer.py (lines 2133-2148 replace "the narrator" → "Victor Frankenstein" AFTER the fix ran)
- De Lacey alias contamination: "the blind father (De Lacey)" aliases assigned to the dæmon instead of the blind father character → Felix→dæmon "son" fabricated relationship
- Victor→Elizabeth relationship MISSING from profiles (was present in earlier attempts)
- Elizabeth→Justine "cousin" STILL WRONG (both-names check should have fixed this — investigate why it didn't)
- Letter 2 grammar broken: "Robert Walton this letter written..." (partial fix but grammatically awkward)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | - | Baseline. Profiles (5/10) and Summaries (6/10) failing |
| 2 | 7.75 | +0.40 | Profiles improved (5→6.5): fabrications fixed. Summaries improved (6→7): Victor chapters correct, Creature chapters still wrong |
| 3 | 7.58 | +0.23 | Profiles regressed (6.5→6): fixed 3, added 4 new. Summaries regressed (7→6.5): letter 4 regression. Narrator fix (attempt 2) failed. |
| 4 | 7.08 | -0.27 | Profiles improved for Victor→Alphonse/Clerval. F6 fixed. BUT summaries regressed 6.5→4.0: narrator fix undone by narrator substitution code. De Lacey alias contamination new regression. |

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator fix undone by narrator substitution** [Summaries — root cause of 4.0 score]
   - Problem: `_fix_narrator_attribution` in summarizer.py runs DURING summarization and replaces wrong names with "the narrator". Then analyzer.py lines 2133-2148 replace "the narrator" → narrator_name ("Victor Frankenstein") for ALL first-person summaries. The fix is undone.
   - Fix approach: Move `_fix_narrator_attribution` to run AFTER the narrator substitution in analyzer.py. After line 2148, add a second pass that loops through `summary_map.summaries`, gets chapter text from `chapter_map`+`doc.text`, and calls `ChapterSummarizer._fix_narrator_attribution(summary_obj, chapter_text)`. Also make `_fix_narrator_attribution` a `@staticmethod` so it can be called without an instance.
   - Impact: All 10 non-Victor chapters (4 letters + 6 Creature chapters) will be re-fixed after narrator substitution

2. **Creature's chapters (11-16) misattributed to Victor Frankenstein** [Summaries]
   - Problem: Chapters 11-16 narrated by the Creature (indices 15-20) say "Victor Frankenstein" as subject
   - Evidence from attempt 4:
     - Ch 11 (idx 15): "Victor Frankenstein's earliest days of consciousness" — pattern mismatch ("days" not "experiences")
     - Ch 12 (idx 16): "Victor Frankenstein, living in a hovel near a cottage" — no appositive pattern
     - Ch 13 (idx 17): "Victor Frankenstein, hidden near a cottage" — no appositive pattern
     - Ch 14 (idx 18): "Victor Frankenstein recounts the tragic history of the De Lacey family" — no pattern
     - Ch 15 (idx 19): "Victor Frankenstein, a newly sentient creature" — "sentient" not in pattern
     - Ch 16 (idx 20): "Victor Frankenstein, a created being" — PATTERN MATCHED but fix was UNDONE (see issue 1 above)
   - Fix approach: EXTEND patterns in `_fix_created_being_attribution`:
     - Add "days of consciousness" to awakening_re pattern
     - Add "sentient" to appositive_re pattern: `(?:newly\s+|recently\s+)?(?:created|conscious|sentient)\s+(?:being|creature)`
     - Add "creator" heuristic: if summary text mentions "creator, [NarratorName]" or "[Name]'s creator" implying Name is referenced as creator (not narrator), replace leading [Name] with "the narrator"
   - Note: Ch 12, 13, 14 still lack structural signals — may need more patterns

3. **Letters (1-4) have wrong attribution** [Summaries]
   - Same root cause as issue 1 — fix will resolve most letter issues once narrator substitution override is in place

### HIGH

4. **De Lacey alias contamination → dæmon has wrong aliases** [Alias Grouping / Profiles]
   - Problem: "the blind father (De Lacey)", "De Lacey", "the blind father" assigned to the dæmon (not the blind father character)
   - Impact: Felix→dæmon "son" fabricated from blind father alias on dæmon
   - Fix approach: Extract blind father De Lacey as separate character; or reject "De Lacey" alias from dæmon via verify_aliases Rule 3 (another cast member Felix has "De Lacey" as alias)
   - Note: The canonical "the blind father (De Lacey)" is inside the dæmon's alias list — Rule 3b parenthetical check should block it if Felix has "De Lacey" alias

5. **Elizabeth→Justine "cousin" STILL WRONG** [Profiles]
   - Problem: The both-names check was supposed to fix this but didn't
   - Need to investigate: Is "Elizabeth" + "Justine" + "cousin" within 100 chars in text? Or does the canonical-name-only check fail because Elizabeth's canonical is just "Elizabeth" (no surname to contrast with Justine)?

6. **Victor→Elizabeth relationship MISSING** [Profiles]
   - Problem: Victor has no relationship entry for Elizabeth in profiles
   - Root cause: Profile generation may fail to capture this central relationship; may need to check if Elizabeth's canonical "Elizabeth" is what's used as relationship key vs "Elizabeth Lavenza"

### MEDIUM

7. **Letter 1 null title** [Structure] — pre-existing

8. **Pronunciation Guide missing primary proper nouns** [Pronunciation]
   - Missing: Frankenstein, Walton, Geneva, Justine, De Lacey, Waldman
   - Fix approach: These may be filtered as "common English words" by the CMU proposer whitelist or treated as self-evident

### LOW

9. **"his father" as alias for Alphonse** [Alias Grouping] — relational descriptor, not a name

10. **3 pronunciations missing IPA** [Pronunciation] — Roncesvalles, resume, alternate — pre-existing

## Fix History (attempt 4 → 5)

- **Attempt 4 fixes applied:**
  - Summarizer: Added `_fix_narrator_attribution` + `_detect_letter_signatory` + `_apply_letter_narrator` + `_fix_self_referential_narrator` + `_fix_created_being_attribution` methods
    - Result: FAIL — narrator fix runs during summarization, then narrator substitution in analyzer.py (lines 2133-2148) replaces "the narrator" → "Victor Frankenstein", undoing all fixes
  - post_corrections.py: Both-names check in `reject_unfounded_familial_labels` (sibling bypass removal + canonical-only pat_b + specific-term check)
    - Result: SUCCESS for Victor→Alphonse, Victor→Clerval ✓ — FAIL for Elizabeth→Justine (investigate)
  - analyzer.py: F6 title+surname and initials matching for Captain Walton / R.W.
    - Result: SUCCESS ✓

## Next Action

Fix phase for attempt 5. Priority:
1. **analyzer.py**: Add second pass after narrator substitution (line 2148) to re-run `_fix_narrator_attribution` on all summaries using chapter texts. Make the method callable statically.
2. **summarizer.py**: Extend `_fix_created_being_attribution` patterns (sentient, days of consciousness, creator heuristic).
3. **Investigate**: Why did Elizabeth→Justine "cousin" survive the both-names check? Check if "Elizabeth" (no surname) + "Justine" + "cousin" within 100 chars in text.
