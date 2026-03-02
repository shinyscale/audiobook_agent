# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 8.08
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 3.5/10 ✗ (CRITICAL REGRESSION)
  - Completeness: 5/10
  - Identity Resolution: 2/10
  - Alias Grouping: 3/10
- Character Profiles: 5/10 ✗ (REGRESSION)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — REGRESSION (overall 7.0 vs baseline 8.08, delta -1.08)

## Regression Analysis

Fix C (common-noun-phrase heuristic for Rule 0.5) caused a catastrophic regression:

1. **"the old man" became a separate character (43 mentions)** instead of being recognized as Mr. White. The heuristic treated all-lowercase common-noun canonical names as symbolic for Rule 0.5, but "the old man" is a *person descriptor* used as a pronoun for Mr. White throughout the text. Rule 0.5 then blocked it from merging with "Mr. White" because "old man" is semantically unrelated to "White".

2. **The monkey's paw disappeared** as its own character entry — it got absorbed as an alias of "the old man" (nonsensical).

3. **Multiple descriptors collapsed into "the old man"** as aliases: "the old woman" (Mrs. White), "the son" (Herbert), "the visitor" (Maw & Meggins rep), "the monkey's paw", "the paw". This is a garbage dump of unrelated descriptors.

4. **Mr. White dropped to 10 mentions** (from ~53) because most references via "the old man" went to the garbage entry.

**Fix C must be reverted.** The common-noun-phrase heuristic is too broad — it catches person-descriptors like "the old man" and "the old woman" that are used as pronoun-like references to named characters.

Fix D (inverse-relationship consistency) partially worked: Mrs. White→Herbert is now "parent" instead of "husband". However, the relationship fix is moot if the character extraction itself is broken.

## Current Issues (Priority Order)

### CRITICAL
1. **REVERT Fix C — common-noun-phrase heuristic causes catastrophic regression** [Identity Resolution]
   - Problem: Fix C's `is_common_noun_phrase()` heuristic in `main_cast.py` treats ALL lowercase common-noun canonical names as symbolic for Rule 0.5. This causes "the old man" (a person-descriptor for Mr. White) to be blocked from merging, creating a garbage 43-mention entry.
   - Evidence: "the old man" has aliases ["the man", "the visitor", "the monkey's paw", "the paw", "the old woman", "the son"] — a nonsensical grab-bag. Mr. White dropped to 10 mentions.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the `is_common_noun_phrase()` function and its use in Rule 0.5 condition (around lines 828-867)
   - Fix: **Revert Fix C entirely** (git revert the relevant changes to main_cast.py). Then try a more targeted approach:
     - Instead of treating all lowercase common-noun names as symbolic, specifically target *object* names: canonical names containing words like "paw", "ring", "sword", "stone", "letter", "book", "key", "coin" etc. — inanimate object nouns.
     - OR: Check if `is_symbolic` is set AND the canonical name has no person-indicator words (old, man, woman, boy, girl, lady, gentleman, sir, etc.)
     - OR: Simply hardcode nothing and instead fix the LLM's `is_symbolic` field to actually work (the real root cause — the LLM ignores the is_symbolic instruction)

### HIGH
2. **Mrs. White → Mr. White relationship labeled "husband" instead of "wife"** [Profiles]
   - Problem: Mrs. White's perspective toward Mr. White says "husband" — should say "wife" (she IS the wife) or the label should be from the other character's perspective.
   - Evidence: Mr. White→Mrs. White = "husband" ✓, but Mrs. White→Mr. White = "husband" ✗ (should be "wife")
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enforce_inverse_consistency()` or `enforce_gender_consistency()`
   - Fix: The inverse consistency logic should catch this: if Mr. White→Mrs. White = "husband", then Mrs. White→Mr. White must be "wife"

3. **Morris ↔ Mr. White relationship labeled "associated" instead of "friend"** [Profiles]
   - Problem: Morris visits specifically as an old friend, they share drinks and war stories. "associated" is too vague.
   - Location: Profile generation LLM output
   - Fix: Lower priority — may resolve with better LLM output on re-analysis after reverting Fix C

### MEDIUM
4. **Mr. White and Mrs. White have zero aliases** [Alias Grouping]
   - Problem: "the old man" and "the old woman"/"the old lady" are used throughout for Mr. and Mrs. White
   - Not worth fixing — these are ambiguous descriptive phrases in general; verification rules correctly block them

5. **Morris → paw relationship labeled "friend"** [Profiles]
   - Problem: Morris was a previous possessor of the paw, not its "friend"
   - Low impact; depends on Fix C revert restoring the paw as a character

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. |
| 3 | 7.0 | **-1.08** | **REGRESSION.** Fix C over-fires — "the old man" becomes garbage 43-mention entry, paw disappears |

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
  - **ACTION: REVERT THIS FIX**

- Attempt 2 (Fix D): Added `enforce_inverse_consistency()` for relationship cross-validation
  - Result: Mrs. White→Herbert changed to "parent" ✓ (partial success). But had contradictions ("both sides = child") that caused some relationships to be removed. Mrs. White→Mr. White still "husband" (not caught).
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw [Critical #1] | main_cast.py (CHARACTER_IDENTIFICATION_PROMPT) | Partial — 2 of 3 removed, 1 new appeared |
| 1 (Fix B) | Mrs. White "father"→"mother" [High #3→#2] | post_corrections.py, test_post_corrections.py | Herbert desc fixed ✓, relationship label changed form (father→husband) but still wrong |
| 2 (Fix C) | False aliases: "visitor"/"stranger" on monkey's paw [Critical #1] | main_cast.py (is_common_noun_phrase heuristic) | **REGRESSION** — over-fires on person-descriptors, creates garbage "the old man" entry |
| 2 (Fix D) | Mrs. White→Herbert = "husband" instead of "mother" [High #2] | post_corrections.py (enforce_inverse_consistency), test_post_corrections.py | Partial — "parent" ✓ but contradictions removed some valid relationships |

**Pattern detected:** main_cast.py has been modified 3 times (Fix A, Fix C + revert) for the same underlying issue (false aliases on monkey's paw). The LLM-prompt approach (Fix A) and the heuristic approach (Fix C) both failed. The fix phase should consider a more targeted approach:
- Check if the alias candidate's primary referent in the text is a DIFFERENT character than the canonical name's referent
- OR: Only apply Rule 0.5 stricter filtering when `is_symbolic=true` is explicitly set AND the canonical name fails a person-indicator check

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good

## Next Action
1. **Revert Fix C** (the `is_common_noun_phrase` heuristic in main_cast.py) — this caused the regression
2. Keep Fix D (inverse relationship consistency) — it partially worked
3. Try a more targeted approach for the paw's false aliases (see Critical #1 for options)
4. Re-run analysis
