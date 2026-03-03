# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 3/10 ✗
  - Completeness: 4/10
  - Identity Resolution: 2/10
  - Alias Grouping: 4/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 7/10 ✗
- **Overall: 6.60/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — MAJOR REGRESSION from attempt 4 (8.23 → 6.60). 3 categories below threshold.

**REGRESSION ALERT:** Score dropped from 8.23 (attempt 4) to 6.60. The characters.py `_is_valid_alias()` changes from attempt 5 caused The Red Death to be merged as an alias of the clock instead of existing as its own character. The grounding.py fix for "Prospero" alias DID work. Fix strategy: **revert characters.py changes only, keep grounding.py fix.**

## Evaluation Details

### Structure Detection: 9/10 ✓
Unchanged from attempt 4. Continuous short story correctly identified as single section. Minor "1 chapters" grammar issue persists.

### Character Extraction: 3/10 ✗ (REGRESSION from 7/10)

**CATASTROPHIC REGRESSION.** Attempt 4 had 2 correct characters (Prince Prospero, The Red Death), perfect identity resolution, and the clock removed as symbolic. Attempt 5 destroyed this:

**Characters in output:**
1. **Prince Prospero** (aliases: the Prince, Prospero) — CORRECT ✓
2. **the gigantic ebony clock** (aliases: the clock, **the Red Death**) — WRONG: clock should be symbolic/removed, Red Death should be its own character, not an alias of the clock
3. **the courtiers** (F6-reconciled, id=2dc5504206d2) — SPURIOUS: group noun, not a character
4. **the musicians** (F6-reconciled, id=2c119eeb2375) — SPURIOUS: group noun, not a character

**Expected:**
1. Prince Prospero (aliases: the Prince, Prospero)
2. The Red Death (aliases: the masked figure, the figure)

**Completeness: 4/10** — Prince Prospero correct. The Red Death (the story's PRIMARY ANTAGONIST and title entity) is completely missing as its own character — it exists only as a wrong alias of the clock. Two spurious group-noun characters (courtiers, musicians) pollute the output. The clock is present but should be removed as symbolic.

**Identity Resolution: 2/10** — Catastrophic false merge: The Red Death is listed as an alias of the ebony clock. These are entirely different entities — one is a physical object, the other is a supernatural personification of pestilence. Additionally, "the masked figure" and "the figure" (valid Red Death aliases from attempt 4) are now completely lost. The stderr from the analysis run shows they were BLOCKED by is_symbolic semantic mismatch checks ("core noun 'figure' vs 'death'").

**Alias Grouping: 4/10** — Mixed results:
- ✓ Prince Prospero's aliases are now perfect: "the Prince" and "Prospero" (the grounding.py fix worked!)
- ✗ "the Red Death" wrongly aliased to the clock
- ✗ Valid Red Death aliases (masked figure, the figure) lost entirely
- ✓ Courtiers/Musicians/Waltzers no longer wrongly aliased to Red Death (the _is_valid_alias Rule 0.6 did block them as aliases)

### Character Profiles: 5/10 ✗ (REGRESSION from 8.5/10)

- **Prince Prospero:** Excellent profile — accurate "bold and robust" description, personality arc (happy/dauntless → enraged), voice guidance with actual quote ("Who dares insult us..."). Still great.
- **the gigantic ebony clock:** Profile describes a clock (ebony material, brazen lungs, pendulum). Technically accurate for the object but useless for narrator prep since this should either be removed as symbolic or The Red Death should be its own character with its own profile.
- **The Red Death: NO PROFILE** — The story's primary antagonist (tall, gaunt, grave habiliments, stiffened corpse mask, vesture dabbled in blood) has no profile because it doesn't exist as its own character.
- **the courtiers / the musicians:** No physical descriptions (expected for groups that shouldn't be characters).
- Prospero's profile alone is not enough — missing the antagonist's profile is a major gap.

### Chapter Summaries: 9/10 ✓
Unchanged. Comprehensive single summary accurately captures all key events. No hallucinations.

### Pronunciation Guide: 8/10 ✓
Unchanged. 17 entries, 15 with IPA. Good coverage. 2 homographs (produce, deliberate) still have null IPA.

### HTML Presentation: 7/10 ✗ (DOWN from 8/10)
- Navigation functional, tabs work
- "1 chapters" grammar persists
- "the gigantic ebony clock" listed as a main character with "Also known as: the clock, the Red Death" is very misleading to a narrator
- Courtiers and musicians appear as character entries, adding noise
- Presentation score drops because the data quality issues make the report confusing and unreliable for its intended audience (audiobook narrators)

## Current Issues (Priority Order)

### CRITICAL
1. **REGRESSION: The Red Death merged as alias of the clock** [Identity Resolution, Completeness]
   - Problem: The Red Death (the story's title entity and primary antagonist) no longer exists as its own character. It appears only as an alias of "the gigantic ebony clock". In attempt 4 this was correct — Red Death was its own character, clock was removed as symbolic.
   - Evidence: `main_cast_3: "the gigantic ebony clock"` has aliases `["the clock", "the Red Death"]`. No separate Red Death character exists.
   - Root cause: The attempt 5 `_is_valid_alias()` changes in `src/agents/characters.py` appear to have disrupted the character extraction/merge pipeline. The stderr logs show that valid aliases ("the masked figure", "the figure", "the intruder") were being BLOCKED from The Red Death by an is_symbolic semantic mismatch check ("core noun 'figure' vs 'death'"). Without its key aliases, The Red Death entity likely became fragile and got merged into the clock.
   - **Fix: REVERT the characters.py changes from attempt 5.** The attempt 4 characters.py correctly produced The Red Death as its own character. The `_is_valid_alias()` Rule 0.6 addition caused more harm than good — it blocked valid Red Death aliases and destabilized the entity. Return to attempt 4 characters.py state.

2. **Clock not marked is_symbolic — regression** [Identity Resolution]
   - Problem: In attempt 4, the ebony clock was correctly detected as is_symbolic and removed. Now it's `is_symbolic: false` and persists as a main_cast character.
   - Evidence: `main_cast_3` has `is_symbolic: false`
   - Root cause: Likely the same characters.py changes disrupted the is_symbolic detection path.
   - Fix: Reverting characters.py to attempt 4 state should fix this too.

### HIGH
3. **Spurious F6-reconciled characters: courtiers, musicians** [Completeness]
   - Problem: "the courtiers" (id=2dc5504206d2) and "the musicians" (id=2c119eeb2375) are F6-reconciled entries that shouldn't be characters. They're generic group nouns.
   - Evidence: Both have hash IDs indicating F6 summary reconciliation origin
   - Root cause: With The Red Death missing as a character and the clock present, F6 reconciliation picks up "the courtiers" and "the musicians" from summary active_characters since they don't match any existing character.
   - Fix: Reverting characters.py should restore The Red Death as its own character. The group nouns were previously absorbed as (wrong) aliases of Red Death — after revert, they'll be aliases again. The Rule 0.6 in verify_aliases (from attempt 4, in main_cast.py) should block them. If they still appear as aliases after revert, that's the original issue from attempt 4 to address SEPARATELY.

### MEDIUM
4. **Two pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA values
   - Location: Pronunciation pipeline IPA generation
   - Fix: Deferred — pronunciation is at 8/10, above threshold

5. **"1 chapters" grammar error in HTML** [Presentation]
   - Problem: "This book contains 1 chapters"
   - Location: HTML report template
   - Fix: Deferred — not blocking with current regression priority

### LOW
6. **Missing additional Red Death aliases** [Alias Grouping]
   - "the stranger", "the mummer" could be additional aliases
   - Fix: Deferred until Red Death exists as its own character again

## What's Needed to Pass

**Step 1 (CRITICAL): Revert characters.py to attempt 4 state.** This should restore:
- The Red Death as its own character with aliases (masked figure, the figure)
- Clock removed as is_symbolic
- Courtiers/Musicians/Waltzers as (wrong) aliases of Red Death again

This brings us back to attempt 4's score of 8.23, with Character Extraction at 7/10.

**Step 2: KEEP grounding.py fix from attempt 5.** The substring alias exemption correctly preserved "Prospero" as an alias. This is a genuine improvement over attempt 4.

**Step 3: Address the original attempt 4 issues (Courtiers/Musicians/Waltzers aliases, missing Prospero).** With grounding.py already fixed, "Prospero" should now survive. For the group noun aliases, need a DIFFERENT approach than the `_is_valid_alias()` change that caused this regression. Options:
- (a) Add the Rule 0.6 check to `_process_consolidated_pass2()` in main_cast.py (where these aliases are actually added) instead of the global `_is_valid_alias()` in characters.py
- (b) Add a post-processing step specifically in main_cast.py that strips plural group aliases AFTER all merges are complete but BEFORE characters.py processes them
- (c) Investigate whether the LLM prompt for Pass 2 can be adjusted to not propose group-noun aliases (less reliable)

**Expected result after Step 1+2:** Back to ~8.23 with "Prospero" alias working → Character Extraction ~8/10, overall passes.

## Fix History

### Attempt 6 (Revert regression + keep grounding.py fix)
1. **REVERTED characters.py Rule 0.6** — Removed the `_is_valid_alias()` Rule 0.6 addition from attempt 5. The plural group suffix check blocked valid Red Death aliases ("the masked figure", "the figure") via an is_symbolic semantic mismatch cascade, destabilizing The Red Death entity and causing it to merge into the clock.
2. **KEPT grounding.py substring alias exemption** — Preserved the attempt 5 fix that allows aliases which are substrings of their canonical name (e.g., "Prospero" in "Prince Prospero") to pass through even with 0 unique mention count.
3. **Root cause:** Adding Rule 0.6 to the global `_is_valid_alias()` in characters.py affected ALL alias validation paths, including critical semantic mismatch checks. The fix location for group-noun alias blocking must be scoped to main_cast.py Pass 2 output only, not the global validator.
4. **Smoke test:** 332 tests pass (same as attempt 4 baseline).
- Modified: `src/agents/characters.py` (reverted to attempt 4 state)

### Attempt 5 (Score: 6.60/10 — REGRESSION from 8.23)
1. **Rule 0.6 added to `_is_valid_alias()` in characters.py** — Caused regression: blocked valid Red Death aliases via semantic mismatch, destabilized Red Death entity → merged into clock. **MUST REVERT.**
2. **Substring alias exemption in grounding.py** — Successfully preserved "Prospero" alias. **KEEP.**

### Attempt 4 (Score: 8.23/10 — BEST SO FAR)
1. **Reverted attempt 3 main_cast.py** — restored to attempt 2 state
2. **Improved is_symbolic detection** — lowered threshold, added all_lowercase check → Clock correctly removed ✓
3. **Re-added Rule 0.6** — plural group noun blocking → Smoke tests pass but aliases still appear in output ✗
4. **Re-added _add_title_stripped_aliases()** → Smoke tests pass but "Prospero" not in output ✗
5. **Kept original ALIAS_RESOLUTION_PROMPT** — avoided the attempt 3 regression

### Attempt 3 (REGRESSION — 6.10/10)
1. Rule 0.6, title-stripping, and prompt changes caused regression
2. Auto-reverted in attempt 4

### Attempt 2 (Previous Best before attempt 4: 7.98/10)
1. Rule 0.5 scoped to is_symbolic=True only ✓
2. Programmatic is_symbolic for multi-word descriptors ✓
3. Narrator detection prompt → Third-person correctly identified ✓
4. Pronunciation whitelist → 4 common words removed ✓

### Attempt 1 (Baseline: 6.85/10)
- Character Extraction: 3/10
- Profiles: 5/10
- Pronunciation: 7.5/10

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | **REGRESSION** — blocked valid aliases, destabilized Red Death entity |
| 5 | Missing "Prospero" alias | grounding.py | **Fixed ✓** — substring exemption works |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ (clock removed, Red Death as own character) |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 4 | Rule 0.6 re-added | main_cast.py | Smoke test pass, but aliases still in output ✗ |
| 4 | Title-stripping re-added | main_cast.py | Smoke test pass, but "Prospero" not in output ✗ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 3 | Missing "Prospero" alias | main_cast.py | Partial |
| 3 | Pass 2 prompt changes | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern confirmed:** characters.py changes are HIGH RISK. Both attempt 3 (main_cast.py prompt changes) and attempt 5 (characters.py _is_valid_alias changes) caused regressions. The safest approach is to: (1) revert characters.py, (2) keep grounding.py, (3) make any new alias-blocking changes in main_cast.py ONLY, scoped narrowly to the specific code path that adds group-noun aliases.

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION, auto-reverted
- Attempt 4: 8.23/10 (+2.13 from attempt 3, +0.25 from attempt 2) ← BEST
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION from attempt 4

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the regression is purely from characters.py code changes

## Next Action
Run PROMPT_fix.md with these directives:
1. **REVERT characters.py to attempt 4 state** — `git show a516bdd:src/agents/characters.py > src/agents/characters.py` (the evaluate commit from attempt 4 has the working state)
2. **KEEP grounding.py fix** — do NOT revert grounding.py
3. After reverting, if the Courtiers/Musicians/Waltzers alias problem persists (expected — it was present in attempt 4), apply a NARROW fix in main_cast.py to block plural group aliases at the point they're proposed, NOT in the global _is_valid_alias()
