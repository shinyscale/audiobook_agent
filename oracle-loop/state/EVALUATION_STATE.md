# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 8.08
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 5/10 ← phantom "the old man" is primary blocker
  - Alias Grouping: 6/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.9/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Correction to Attempt 4 Analyze Notes

The analyze phase noted "the old man" aliases were "less contaminated (no 'old woman', 'son', 'paw' this time)." This is **INCORRECT**. Actual aliases on "the old man" are: `['the visitor', 'stranger', "the monkey's paw", "monkey's paw", 'the paw', 'the old woman']` — contamination with "the old woman", "the monkey's paw", and "the paw" is still fully present. Only "the son" was removed vs. attempt 3.

## Current Issues (Priority Order)

### CRITICAL
1. **Phantom character: "the old man" with 45 mentions steals Mr. White's identity** [Identity Resolution]
   - Problem: The LLM extracts "the old man" as a separate canonical character in Pass 1 because Part III refers to Mr. White exclusively as "the old man." This creates a 45-mention phantom while Mr. White drops to only 10 mentions. Furthermore, "the old man" accumulates garbage aliases: "the visitor" (Maw & Meggins rep), "stranger", "the monkey's paw", "monkey's paw", "the paw", "the old woman" (Mrs. White).
   - Evidence: `main_cast_7` = "the old man" with 45 mentions vs `main_cast_0` = "Mr. White" with 10 mentions. In the story, "the old man" IS Mr. White — the narrator uses this descriptive phrase as a pronoun-like reference throughout Part III.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 1 extraction (LLM generates "the old man" as canonical), Pass 2 alias resolution (fails to merge with Mr. White), Rule 3 (blocks cross-character merging)
   - **ESCALATION NOTE:** main_cast.py has been modified 3 times (Fix A, Fix C, Fix C revert) for variants of this issue without success. LLM-prompt and heuristic approaches both failed. The fix phase MUST try a different layer:
     - **Option A (recommended):** Add a post-extraction merge step in `main_cast.py` AFTER Pass 2 completes. If a character has NO proper nouns in its canonical name (only common nouns/articles like "the old man") AND a proper-name character exists with matching gender/context, merge the common-noun character INTO the proper-name character as an alias. This bypasses Rule 3 since it happens after verification.
     - **Option B:** Modify the Pass 1 prompt to explicitly instruct: "Common-noun descriptive phrases that refer to a named character (e.g., 'the old man' referring to Mr. White) should be listed as ALIASES of that named character, NOT as separate characters."
     - **Option C:** Add a confidence-weighted merge: if a common-noun character has 3x+ the mentions of a proper-name character of the same gender/role, flag for automatic merge.

2. **All parent-child relationship labels are wrong — labeled as spousal** [Profiles]
   - Problem: Every parent-child relationship is labeled with a spousal term. This is a post-corrections bug, likely in `enforce_gender_consistency` applying gendered spousal labels too broadly.
   - Evidence:
     - Mr. White → Herbert White: "husband" (should be "father")
     - Mrs. White → Herbert White: "wife" (should be "mother")
     - Herbert White → Mr. White: "wife" (should be "son")
     - Herbert White → Mrs. White: "husband" (should be "son")
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enforce_gender_consistency()` and/or `enforce_inverse_consistency()`
   - Root cause hypothesis: `enforce_gender_consistency` appears to be treating ALL relationships as spousal — detecting character gender from titles (Mr./Mrs.) and then assigning "husband"/"wife" regardless of whether the relationship is actually parent-child, sibling, etc. It should ONLY apply spousal labels when the original relationship type is already spousal (e.g., "spouse", "married to", "husband", "wife").
   - Fix: `enforce_gender_consistency` must check the ORIGINAL relationship type before replacing. If the original label is "father", "mother", "parent", "son", "daughter", "child", "sibling", "brother", "sister", etc., it should NOT be overwritten with a spousal label. Only labels like "spouse", "partner", "married" should be gender-corrected to "husband"/"wife".

### HIGH
3. **Monkey's paw absent as a character/symbolic entity** [Completeness]
   - Problem: The monkey's paw (the title object and central antagonistic force) is not extracted as its own character. It's listed as an alias of "the old man" — completely nonsensical.
   - Evidence: The paw is the driving force of the entire plot, granting wishes with horrific consequences. A narrator prep tool should identify it.
   - Location: This is downstream of Issue #1 — if "the old man" phantom is resolved, the paw should be re-extracted naturally (as it was in attempt 1 before Fix C).
   - Fix: Resolving Issue #1 (merging phantom into Mr. White) should free the paw's mentions. The LLM should then extract it as its own symbolic entity.

4. **Morris ↔ Mr. White relationship labeled "associated" instead of "friend"** [Profiles]
   - Problem: Morris visits as an old friend — they served together, share drinks and war stories. "associated" is too vague.
   - Evidence: Text explicitly shows Morris as an old army friend visiting the Whites.
   - Location: LLM profile generation output. Lower priority — may improve on re-analysis after character extraction fixes.

### MEDIUM
5. **Mr. White and Mrs. White have zero aliases** [Alias Grouping]
   - Problem: "the old man" and "the old woman"/"the old lady" are used extensively throughout the text but not listed as aliases.
   - Note: This is expected to self-resolve if Issue #1 is fixed (merging "the old man" into Mr. White would effectively create the alias).

6. **"the old man" profile duplicates Mr. White's profile** [Profiles]
   - Problem: "the old man" has its own full profile (appearance, personality, voice guidance, quotes) that duplicates Mr. White's. This is confusing for a narrator — which profile should they use?
   - Fix: Self-resolves if Issue #1 is fixed.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. |
| 3 | 7.0 | **-1.08** | **REGRESSION.** Fix C over-fires — "the old man" becomes garbage 43-mention entry, paw disappears |
| 4 | 7.9 | -0.18 | Fix C reverted. Phantom "the old man" persists (45 mentions, garbage aliases). All family relationship labels wrong (spousal instead of parent-child). Monkey's paw absent. |

## Fix History
- Attempt 1 (Fix A): Clarified `is_symbolic: true` in CHARACTER_IDENTIFICATION_PROMPT for non-person entities
  - Result: Partially worked — removed "the old fakir"/"an old fakir" but "the visitor" persisted, "stranger" appeared
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 1 (Fix B): Extended `enforce_gender_consistency` to detect gender from canonical name titles (Mr./Mrs./Ms./Miss)
  - Result: Herbert "tall and burly" physical description fixed ✓. But Mrs. White→Herbert label changed from "father" to "husband" (different wrong label, not caught)
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

- Attempt 2 (Fix C): Added `is_common_noun_phrase()` heuristic to trigger Rule 0.5 for all-lowercase non-creature canonical names
  - Result: **REGRESSION** — "the old man" treated as symbolic, blocked from merging with Mr. White, became garbage entry. Paw disappeared.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 2 (Fix D): Added `enforce_inverse_consistency()` for relationship cross-validation
  - Result: Mrs. White→Herbert changed to "parent" ✓ (partial success). But had contradictions ("both sides = child") that caused some relationships to be removed. Mrs. White→Mr. White still "husband" (not caught).
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

- Attempt 3 (Fix C REVERT): Removed `is_common_noun_phrase()` heuristic from `is_symbolic_or_personified` condition
  - Result: Reduced contamination slightly (no "the son" alias) but "the old man" phantom persists with 45 mentions. Garbage aliases still present.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`, `tests/test_post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw [Critical #1] | main_cast.py (CHARACTER_IDENTIFICATION_PROMPT) | Partial — 2 of 3 removed, 1 new appeared |
| 1 (Fix B) | Mrs. White "father"→"mother" [High #3→#2] | post_corrections.py, test_post_corrections.py | Herbert desc fixed ✓, relationship label changed form (father→husband) but still wrong |
| 2 (Fix C) | False aliases: "visitor"/"stranger" on monkey's paw [Critical #1] | main_cast.py (is_common_noun_phrase heuristic) | **REGRESSION** — over-fires on person-descriptors, creates garbage "the old man" entry |
| 2 (Fix D) | Mrs. White→Herbert = "husband" instead of "mother" [High #2] | post_corrections.py (enforce_inverse_consistency), test_post_corrections.py | Partial — "parent" ✓ but contradictions removed some valid relationships |
| 3 (Fix C REVERT) | Revert catastrophic regression [Critical #1] | main_cast.py, test_post_corrections.py | Alias contamination slightly reduced but phantom persists |

**ESCALATION REQUIRED:**
- main_cast.py has been modified 3 times for the phantom "the old man" issue without success → Fix phase MUST use a different approach (post-extraction merge, not Pass 1/Rule tweaks)
- post_corrections.py has been modified 3 times for relationship labels without success → Fix phase must examine `enforce_gender_consistency` logic carefully to understand WHY it overwrites non-spousal labels

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good
- 5 pipeline stages, 39 LLM calls, 84,932 tokens in 26m 30s

## Next Action
Run PROMPT_fix.md to address:
1. **Critical #1:** Add post-extraction merge step for common-noun phantom characters (new approach — stop modifying Pass 1 prompts or Rule conditions)
2. **Critical #2:** Fix `enforce_gender_consistency` to not overwrite parent-child labels with spousal labels
