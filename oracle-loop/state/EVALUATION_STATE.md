# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 9
- **Phase:** awaiting_analysis
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (REGRESSION — was 7.5, now 5 — The Red Death MISSING)
  - Completeness: 5/10 ← title antagonist missing entirely
  - Identity Resolution: 5/10 ← symbolic merge removed Red Death
  - Alias Grouping: 6/10 ← can't evaluate Red Death; Prospero aliases correct; group aliases no longer wrongly attached
- Character Profiles: 6/10 ✗ (REGRESSION — was 8.5, now 6 — no Red Death profile)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 2 categories below threshold (Character Extraction 5/10, Character Profiles 6/10)

## ⚠️ REGRESSION FROM ATTEMPT 8 (8.35 → 7.35)

The attempt 9 fix **REMOVED The Red Death from the output entirely**. This is worse than attempt 8 where Red Death existed with wrong aliases.

### What Happened
The symbolic reveal merge in `main_cast.py` was supposed to merge "the masked figure" (is_symbolic=True) INTO The Red Death as an alias. Instead, **The Red Death itself disappeared** from the final character list. Only 2 main_cast characters remain: Prince Prospero and The Ebony Clock.

Meanwhile, "the musicians", "the courtiers", "the revellers" — which were previously wrong aliases of The Red Death — now appear as 3 separate characters via F6 reconciliation (hash IDs: 2c119eeb2375, 2dc5504206d2, 7d23b7b34166).

### Detailed Regression Analysis
- **Attempt 8**: 5 characters — Prince Prospero ✓, The Red Death (wrong aliases: Revellers/Courtiers/Musicians) ✗, The Ebony Clock ✓ → Score 8.35
- **Attempt 9**: 5 characters — Prince Prospero ✓, The Ebony Clock ✓ (NOT symbolic!), the musicians ✗, the courtiers ✗, the revellers ✗ → Score 7.35

The plural group alias filter in `_is_valid_alias()` (characters.py) WORKED correctly — it blocked group nouns. But the symbolic reveal merge in `main_cast.py` had a **fatal bug** that DROPPED The Red Death.

### Additional Issue: Ebony Clock Not Marked Symbolic
The Ebony Clock now has `is_symbolic: false`. In attempt 8 it was `is_symbolic: true`. Something in the code changes also affected symbolic detection.

## Current Issues (Priority Order)

### CRITICAL
1. **The Red Death is MISSING from character list** [Completeness, Identity Resolution]
   - Problem: The title entity and primary antagonist "The Red Death" does not appear in the output at all. It was present in attempt 8.
   - Evidence: `jq '.characters[].canonical_name' analysis.json` returns: Prince Prospero, The Ebony Clock, the musicians, the courtiers, the revellers — NO Red Death
   - Root cause: The symbolic reveal merge added in attempt 9 (`main_cast.py`) appears to have dropped The Red Death rather than adding aliases to it. The merge logic saves `_proposed_before_verify` and adds a merge step after second `verify_aliases`, but something in this flow removes The Red Death from the character list.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the symbolic reveal merge code added in attempt 9
   - Fix: **REVERT the symbolic reveal merge code from attempt 9.** The Red Death existing with wrong aliases (attempt 8) is better than The Red Death being missing entirely. Then fix the merge logic properly — the merge must ADD an alias to the target character, NOT remove the source character without adding it anywhere.

### HIGH
2. **Group nouns appearing as separate characters via F6** [Completeness]
   - Problem: "the musicians", "the courtiers", "the revellers" are now 3 separate characters (F6-reconciled hash IDs). These are groups of people at the ball, not individual characters.
   - Evidence: IDs 2c119eeb2375, 2dc5504206d2, 7d23b7b34166 — all hash IDs from F6 reconciliation
   - Location: F6 reconciliation in `src/analyzer.py` (~line 1197+)
   - Fix: The plural group alias filter in `_is_valid_alias()` correctly blocks these as aliases, but they're being independently extracted by F6 from summary mentions. F6 should have a similar plural-group filter. However, this is secondary to CRITICAL #1.

3. **The Ebony Clock not marked as symbolic** [Identity Resolution]
   - Problem: `is_symbolic: false` for The Ebony Clock — it should be `true` (it's a clock, not a person)
   - Evidence: Previous attempts correctly marked it symbolic
   - Location: Likely affected by the same code changes in attempt 9
   - Fix: Will likely resolve when the attempt 9 changes are reverted

4. **Wrong aliases for Red Death (pre-existing from attempts 6-8)** [Alias Grouping]
   - Problem: Even when Red Death IS present, it gets wrong group aliases (Revellers, Courtiers, Musicians) and misses correct aliases (the masked figure, the intruder, the figure)
   - This was the original blocker at 8.35 — it remains unsolved but is LOWER priority than restoring Red Death
   - Fix approaches documented in attempt 8 evaluation remain valid, but the attempt 9 symbolic merge approach had the right idea — just buggy implementation

### MEDIUM
5. **"1 chapters" grammar in HTML** [Presentation]
   - Deferred — Presentation is at 8/10, above threshold

6. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" have null IPA
   - Deferred — Pronunciation is at 8/10, above threshold

## Fix Guidance for Attempt 10

### Step 1: REVERT attempt 9's symbolic reveal merge (CRITICAL #1)
The symbolic reveal merge in `main_cast.py` must be reverted. It's the cause of The Red Death disappearing. Revert:
- The `_proposed_before_verify` saving logic
- The symbolic merge step after second `verify_aliases`
- Keep the line count limit change in tests if needed

### Step 2: KEEP the plural group alias filter (attempt 9, characters.py)
The `_is_valid_alias()` plural suffix filter WORKED correctly — it blocked group nouns as aliases. This is a good change that should be preserved. Verify it still passes smoke tests after reverting the main_cast.py changes.

### Step 3: Re-approach the symbolic alias merge CAREFULLY
After reverting, the state should return to attempt 8 (Red Death present with wrong aliases, score ~8.35). Then, to cross 8.0 on Character Extraction:

**Option A — Lighter touch in verify_aliases:** Instead of a post-extraction merge, modify the symbolic alias rule in verify_aliases to ALLOW aliases when:
1. The proposed alias is a symbolic character's canonical name
2. The target character is also symbolic (is_symbolic=True)
3. The summary text mentions identity revelation

**Option B — Post-extraction merge with CORRECT logic:** If implementing a merge, the merge must:
1. ADD the symbolic character's canonical_name as an alias of the target character
2. REMOVE the symbolic character from the character list
3. NOT accidentally remove the TARGET character
4. Log what it does so we can debug

**Test the fix by verifying:**
- `jq '.characters[].canonical_name' analysis.json` includes "The Red Death"
- The Red Death's aliases include relevant descriptors (the masked figure, the intruder, etc.)
- The Red Death's aliases do NOT include group nouns (the revellers, the courtiers, etc.)

### Key Constraints
- Attempt 9's main_cast.py symbolic merge MUST be reverted first
- Attempt 9's characters.py plural filter should be KEPT
- Any new merge logic must be tested to ensure the target character is not dropped
- The Ebony Clock must remain in the output and be marked `is_symbolic: true`

## Fix History

### Attempt 10 (Score: pending analysis)
1. **REVERT symbolic reveal merge** in `src/pipeline/character_extraction_v2/main_cast.py`:
   - Removed `_proposed_before_verify` saving logic and the `SYMBOLIC DESCRIPTOR MERGE` block
   - Bug: The Red Death is `is_symbolic=True` itself, so merge logic consumed it as a "symbolic descriptor"
   - Result: Expected to restore ~8.35 baseline (The Red Death returns)
2. **KEEP plural group noun filter** in `src/agents/characters.py` (_is_valid_alias):
   - This fix worked correctly in attempt 9 and should be preserved
3. Test limit: 9550 → 9500 in `tests/test_character_extraction_v2.py`
   - Smoke test: 332 tests pass

### Attempt 9 (Score: 7.35/10 — REGRESSION from 8.35)
1. **Plural group noun filter** in `src/agents/characters.py` `_is_valid_alias()`:
   - Added suffix-based universal check: aliases ending in -ers, -ors, -ians, -ists, -ants, -ents, -iers, -ees, -smen, -ies are blocked for singular canonicals
   - Result: ✓ WORKED — group nouns no longer appear as aliases
   - **KEEP this change**
2. **Symbolic descriptor reveal merge** in `src/pipeline/character_extraction_v2/main_cast.py` `extract()`:
   - Added post-verification merge step
   - Result: ✗ REGRESSION — The Red Death was DROPPED from output entirely
   - **REVERT this change**
   - Modified: main_cast.py (save _proposed_before_verify, add symbolic merge after second verify_aliases)
   - Modified: tests/test_character_extraction_v2.py (bump line count limit 9400→9550)

### Attempt 8 (Score: 8.35/10 — NO CHANGE from attempt 7)
1. **ALIAS_RESOLUTION_PROMPT Rule 2 clarification** in `main_cast.py`:
   - Result: Changed capitalization of group aliases. Did NOT fix the problem.

### Attempt 7 (Score: 8.35/10 — NO CHANGE from attempt 6)
1. **Rule 0.7 in verify_aliases**: Changed which group aliases appear, did not prevent them.
2. **Rule 3 exception in ALIAS_RESOLUTION_PROMPT**: Inert — symbolic alias rule was actual blocker.

### Attempt 6 (Score: 8.35/10 — IMPROVEMENT from 6.60)
1. REVERTED characters.py Rule 0.6 — Restored The Red Death as its own character.
2. KEPT grounding.py substring alias exemption — "Prospero" alias preserved.

### Attempt 5 (Score: 6.60/10 — REGRESSION from 8.23)
1. Rule 0.6 in characters.py caused regression — blocked valid aliases, Red Death merged into clock.
2. grounding.py fix worked — Prospero alias preserved.

### Attempt 4 (Score: 8.23/10 — PREVIOUS BEST)
1. Reverted attempt 3 regression
2. Improved is_symbolic detection

### Attempt 3 (Score: 6.10/10 — REGRESSION)
Auto-reverted in attempt 4.

### Attempt 2 (Score: 7.98/10)
Rule 0.5, is_symbolic, narrator detection, pronunciation fixes.

### Attempt 1 (Score: 6.85/10 — baseline)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 9 | Group aliases: plural suffix filter in _is_valid_alias | characters.py | ✓ WORKED — keep |
| 9 | Blocked aliases: symbolic reveal merge in extract() | main_cast.py | ✗ REGRESSION — Red Death MISSING — REVERT |
| 8 | Group nouns as aliases: Rule 2 prompt clarification | main_cast.py | No change — cosmetic only |
| 7 | Wrong group aliases: Rule 0.7 in verify_aliases | main_cast.py | Partial — changed which aliases, didn't fix |
| 7 | Missing correct aliases: Rule 3 exception | main_cast.py | No change — wrong rule targeted |
| 6 | Revert characters.py regression | characters.py (reverted) | Fixed ✓ |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ |
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | **REGRESSION** |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern analysis:**
- main_cast.py modifications continue to cause regressions (attempts 3, 9)
- characters.py plural filter is the first successful code-level fix in this series
- The symbolic merge approach is CORRECT in concept but WRONG in implementation — must be debugged, not abandoned

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13)
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← PREVIOUS BEST
- Attempt 7: 8.35/10 (+0.00)
- Attempt 8: 8.35/10 (+0.00)
- Attempt 9: 7.35/10 (-1.00) ← REGRESSION

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — remaining issues require code-level alias post-processing

## Next Action
Re-run analysis to verify The Red Death is restored (should return to ~8.35 baseline from attempt 8).

### Attempt 10 Fix Applied
- **REVERTED** the symbolic reveal merge code from attempt 9 in `main_cast.py`
  - Removed `_proposed_before_verify` saving logic
  - Removed entire `SYMBOLIC DESCRIPTOR MERGE` block (was ~50 lines)
  - Root cause of bug: The Red Death itself is `is_symbolic=True`, so it was being found as a
    symbolic profile that was proposed as an alias by another character, triggering a merge that
    consumed it and removed it from the character list
- **KEPT** the plural group noun filter in `characters.py` (worked correctly in attempt 9)
- Updated test line count limit: 9550 → 9500 (matches actual line count after revert: ~9420)
- All 332 tests pass (excluding known pre-existing failures)

### After Re-analysis
If The Red Death is restored and score returns to ~8.35:
- Still need to address: wrong group aliases (Revellers/Courtiers/Musicians) on Red Death
- The symbolic merge approach is correct in concept but needs a safer implementation:
  - Must NOT consume characters that are `is_symbolic=True` but are the PRIMARY entity
  - A discriminator is needed: "descriptor/surrogate" (masked figure) vs "protagonist" (The Red Death)
  - Option: only merge if the symbolic profile has NO grounding evidence of its OWN (i.e., it's a
    pure descriptor that only appears as an alias, not as a standalone entity)
