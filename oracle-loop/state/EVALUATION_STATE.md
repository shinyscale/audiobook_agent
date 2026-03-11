# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35

## Latest Scores (Attempt 3)
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 7/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 6.5/10 ✗ (FAILING)
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.58/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Progress Since Attempt 1 (Δ+0.23)

**Fixed in attempt 2→3:**
- dæmon→Felix "beloved" removed ✓
- Victor→Margaret "brother" removed ✓
- Caroline Beaufort→Caroline Beaufort self-reference removed ✓

**Regressions in attempt 3:**
- Victor→Clerval: "cousin" NEW WRONG (was absent in attempt 2)
- Elizabeth→Justine: "cousin" NEW WRONG
- Clerval→Victor: "cousin" NEW WRONG
- Victor→Alphonse: "brother" STILL WRONG (attempt 3 propagation fix ineffective — LLM regenerated "brother" on both sides, so no authoritative "father"/"son" side to trigger override)
- Letter 4 (index 3) now has dual attribution "Victor Frankenstein, Captain Walton" — was correct "Captain Walton" in attempt 2

**Note:** Attempt 3 score (7.58) is lower than attempt 2 (7.75) due to profile regressions and letter 4 regression.

## Current Issues (Priority Order)

### CRITICAL

1. **Creature's chapters (11-16) misattributed to Victor Frankenstein** [Summaries]
   - Problem: All 6 chapters narrated by the Creature (indices 14-19) say "Victor Frankenstein" as the acting subject
   - Evidence:
     - Ch 11 (index 14): "The chapter follows Victor Frankenstein's earliest conscious experiences as he awakens to sensory overload in the forest near Ingo..." — this is THE CREATURE describing its awakening
     - Ch 12 (index 15): "Victor Frankenstein, living in a hovel near a cottage, spends the winter observing the cottagers" — THE CREATURE in the hovel
     - Ch 16 (index 19): "Victor Frankenstein, a created being, burning the De Lacey cottage" — internally contradictory ("created being" + "Victor Frankenstein")
   - Root cause: Two prompt-engineering iterations have both FAILED. The LLM ignores explicit "I says I" instructions and uses training knowledge. Victor IS mentioned in Creature chapters ("my creator Victor Frankenstein"), so "use only text" is insufficient.
   - Fix approach: **Deterministic post-processing correction** (not prompt engineering):
     - After summary generation, detect "created being" / "newly conscious" / "awakening" descriptors in a summary paired with "Victor Frankenstein" as subject → replace with "the narrator"
     - OR: Detect internal contradiction: if summary contains "[Name]... [action]... to confront [Name]" (same name as both agent AND target/object in the same sentence), the "Name" used as agent is likely wrong → replace with "the narrator"
     - OR: Pass chapter text explicitly looking for "I remember the original era of my being" / "I, the narrator" / letter signatures to override narrator attribution

2. **Letters (0-3) have wrong or dual attribution** [Summaries]
   - Problem: Letter 1 null title + dual attribution "Victor Frankenstein, Robert Walton, writes..."; Letter 2 dual attribution; Letter 3 "Victor Frankenstein, writing from a ship" (wrong); Letter 4 now also dual "Victor Frankenstein, Captain Walton" (regression from attempt 2)
   - Root cause: Same LLM training-knowledge override. Letters contain "Dear Sister" and are signed "R.W." — but LLM ignores these structural cues.
   - Fix approach: **Deterministic letter-narrator detection**: If chapter text contains "To Mrs. Saville" or ends with "R.W." or "Robert Walton", the narrator is Robert Walton. Pass this as an explicit override to the summarizer via a pre-computed `narrator_hint` parameter.
     - The structure detection could extract the letter signature/salutation to set narrator_hint = "Robert Walton" for these chapters
     - OR: Post-process summaries for letter chapters — if "Victor Frankenstein" is named as narrator in a chapter whose text is signed "R.W." or "Robert Walton", replace with "Robert Walton"

### HIGH

3. **Victor→Alphonse and reverse: "brother" (should be "son"/"father")** [Profiles]
   - Problem: Victor→Alphonse: "brother" and Alphonse→Victor: "brother" BOTH generated wrong by profiler. The `_propagate_missing_reverses` fix from attempt 2 requires one side to have "father"/"son" — if LLM generates "brother" on BOTH sides, there's nothing to trigger the override.
   - Root cause: `reject_unfounded_familial_labels` accepts "brother" for Victor because it finds "Victor Frankenstein" near "brother" somewhere in text (Victor HAS a brother — William). Current check uses only ONE canonical name as anchor. Text evidence test passes because "Victor Frankenstein...William...brother" exists somewhere.
   - Fix approach: **Both-names check** — require BOTH characters' canonical names to appear within a 500-char window near the relationship label. For "Victor→Alphonse: brother" to be valid, text must have "Victor Frankenstein" AND "Alphonse" within 500 chars of "brother". This should NOT match because Alphonse and Victor are never described as brothers in text.
   - Location: `reject_unfounded_familial_labels` in `post_corrections.py`

4. **Victor→Clerval: "cousin" / Clerval→Victor: "cousin" / Elizabeth→Justine: "cousin"** [Profiles]
   - Problem: Multiple spurious "cousin" labels introduced in attempt 3
   - Root cause: Same as above — one-name check accepts "cousin" if one name appears near "cousin" in text
   - Fix approach: Same both-names check as issue 3

5. **Walton→Victor: "mentor" (direction wrong)** [Profiles]
   - Problem: Robert Walton→Victor: "mentor" — Walton is not Victor's mentor. Victor tells Walton his tragic story; Walton is the listener/frame narrator.
   - Fix approach: Add "mentor"↔"student/protégé" to `enforce_inverse_consistency`. If Walton→Victor is "mentor", enforce Victor→Walton: "student" (or "protégé"). The direction issue will then be visible and the profiler's "protégé" for Victor→Walton can be checked.
   - Note: Victor→Walton: "protégé" (current) means "Walton is Victor's protégé" — doubly wrong direction

### MEDIUM

6. **"Captain Walton" and "R.W." as separate characters (F6 duplicates)** [Identity Resolution]
   - Problem: Captain Walton (1m) and R.W. (1m) are separate characters that should be aliases of Robert Walton
   - Fix approach: `_is_likely_alias_of_existing` in analyzer.py should match:
     - "Captain Walton" → last name "Walton" matches "Robert Walton"
     - "R.W." → initials R+W match "Robert Walton"

7. **"De Lacey" alias shared by both Felix and the old man** [Alias Grouping]
   - Problem: Felix has alias "De Lacey" AND the old man has alias "De Lacey"
   - Fix approach: Old man's canonical should be "De Lacey" (no standalone alias for Felix)

8. **Elizabeth→Justine: "cousin" (wrong)** — same as issue 4 above

### LOW

9. **Letter 1 null title** [Structure] — pre-existing

10. **"his father" as alias for Alphonse** [Alias Grouping] — relational descriptor, not a name

11. **3 pronunciations missing IPA** [Pronunciation] — Roncesvalles, resume, alternate — pre-existing

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | - | Baseline. Profiles (5/10) and Summaries (6/10) failing |
| 2 | 7.75 | +0.40 | Profiles improved (5→6.5): fabrications fixed. Summaries improved (6→7): Victor chapters correct, Creature chapters still wrong |
| 3 | 7.58 | +0.23 | Profiles regressed (6.5→6): fixed 3, added 4 new. Summaries regressed (7→6.5): letter 4 regression. Narrator fix (attempt 2) failed. |

## Fix History (attempt 3 → 4)

- **Attempt 3 fixes applied:**
  - Summarizer (3rd pass): No further changes (attempt 2 change already in place)
    - Result: FAIL — narrator prompt engineering cannot overcome LLM training knowledge. Must switch to deterministic post-processing.
  - Profiles - "beloved": Added to romantic_labels
    - Result: SUCCESS ✓
  - Profiles - narrator exception: Narrowed to spouse-only
    - Result: SUCCESS ✓
  - Profiles - cross-tier guard pc↔sibling: Added
    - Result: PARTIAL — only fires if one side has pc label; fails when LLM generates sibling on BOTH sides
  - Profiles - propagate sibling→pc: Added _is_wrong_sibling_for_pc
    - Result: PARTIAL — same limitation; requires authoritative pc side
  - Profiles - self-reference: Added removal
    - Result: SUCCESS ✓

## Next Action

Fix phase for attempt 4. Priority:
1. **Summarizer**: Switch from prompt-only to deterministic narrator post-correction. Detect letter signatures (R.W., Robert Walton) and internal contradictions (agent = target) to override misattribution.
2. **post_corrections.py**: Implement both-names check in `reject_unfounded_familial_labels` — require BOTH char canonical names near the relationship label in source text.
3. **analyzer.py**: Fix F6 `_is_likely_alias_of_existing` to match "Captain Walton" and "R.W." to Robert Walton.
