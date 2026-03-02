# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 8.08
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7/10
  - Alias Grouping: 6.5/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7/10, Character Profiles 7/10)

## Current Issues (Priority Order)

### CRITICAL
1. **"the visitor" and "stranger" falsely aliased to the monkey's paw** [Identity Resolution, Alias Grouping]
   - Problem: Two aliases on the paw entry refer to a completely separate human character — the representative from Maw and Meggins who delivers news of Herbert's death in Part II
   - Evidence: Part II summary confirms "a well-dressed stranger from the firm 'Maw and Meggins' arrives" — this is a person, not the paw. "The visitor" is used in the text to describe this same man.
   - Root cause: `is_symbolic` is **still false** for the monkey's paw despite Fix A adding prompt clarification. The LLM (qwen3.5:122b-a10b) ignores the `is_symbolic: true` instruction. Because `is_symbolic=false`, Rule 0.5 (semantic coherence check, line ~828 in main_cast.py) never activates. Rule 0.5 WOULD block these aliases — "visitor" and "stranger" have no substring relationship with "paw".
   - Fix A result: Partially worked — "the old fakir" and "an old fakir" were removed, but "the visitor" persisted and "stranger" appeared as a new false alias.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` lines 828-867
   - **Fix approach:** Don't rely on the LLM setting `is_symbolic`. Extend Rule 0.5's activation condition (line 828) to also trigger for canonical names that are common-noun phrases. Heuristic: if the canonical name (after stripping articles "the/a/an") is entirely lowercase AND doesn't match creature/being patterns ("creature", "monster", "beast", "daemon", "fiend", "spirit", "ghost"), treat it as symbolic for Rule 0.5 purposes. This catches "the monkey's paw" → "monkey's paw" (all lowercase, not a creature) → Rule 0.5 fires → blocks "the visitor" and "stranger". This won't affect proper names (capitalized) or creatures.

### HIGH
2. **Mrs. White → Herbert White relationship labeled "husband" instead of "mother"** [Profiles]
   - Problem: Mrs. White's relationship entry for Herbert says "husband" — completely wrong relationship type. She is his mother.
   - Evidence: Herbert→Mrs. White is correctly labeled "son". Mrs. White→Mr. White is labeled "husband" (correct — Mr. White IS her husband). But Mrs. White→Herbert is also "husband" — the LLM lazily duplicated the label.
   - Previous state: Was "father" in attempt 1 baseline. Fix B's gender consistency correction was designed to catch "father"→"mother" for female characters, but the LLM regenerated a different wrong label ("husband") that the fix doesn't cover.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - **Fix approach:** Add inverse-relationship cross-validation. Build a relationship pair map: if A→B = "son", then B→A must be the gender-appropriate inverse ("mother" if B is female, "father" if B is male). Define an inverse table: {son↔mother/father, daughter↔mother/father, husband↔wife, brother↔sister/brother, nephew↔aunt/uncle}. When the existing B→A label contradicts the required inverse, overwrite it. This is strictly more robust than the current gender-only fix because it catches ANY wrong label (not just gendered parent labels). Mrs. White is female (detected from "Mrs." prefix per Fix B), Herbert→Mrs. White = "son", so Mrs. White→Herbert must be "mother".

### MEDIUM
3. **Morris ↔ Mr. White relationship labeled "associated" instead of "friend"** [Profiles]
   - Problem: Sergeant-Major Morris and Mr. White are old friends — Morris visits them specifically, they share drinks and stories. "associated" is too vague.
   - Location: Profile generation in `src/analyzer.py` or V2 profiling pipeline
   - Fix approach: Lower priority — may resolve naturally with better LLM output on re-analysis. If it persists, consider adding "friend" as a preferred label when characters share extended dialogue scenes.

4. **Morris → paw relationship labeled "friend"** [Profiles]
   - Problem: Morris was a previous owner/possessor of the paw, not its "friend". Semantically wrong.
   - Fix approach: Same root cause as #3 — LLM label generation. Low-impact; "associated" would be better but this is minor.

### LOW
5. **Mr. White and Mrs. White have zero aliases** [Alias Grouping]
   - Problem: The text uses "the old man" for Mr. White and "the old woman"/"the old lady" for Mrs. White. These were blocked by verification rules (correctly, in general — ambiguous descriptive phrases).
   - Not worth fixing — loosening verification rules risks regressions on other texts. These aliases are unambiguous in this short story but ambiguous in general.

6. **is_symbolic still false for the monkey's paw** [Character Extraction]
   - Problem: Fix A's prompt clarification didn't cause the LLM to set is_symbolic=true
   - This is the root cause of Issue #1. Fixed by the heuristic proposed in Issue #1's fix approach.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. Mrs. White relationship changed form but still wrong. |

## Fix History
- Attempt 1 (Fix A): Clarified `is_symbolic: true` in CHARACTER_IDENTIFICATION_PROMPT for non-person entities
  - Result: Partially worked — removed "the old fakir"/"an old fakir" but "the visitor" persisted, "stranger" appeared
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 1 (Fix B): Extended `enforce_gender_consistency` to detect gender from canonical name titles (Mr./Mrs./Ms./Miss)
  - Result: Herbert "tall and burly" physical description fixed ✓. But Mrs. White→Herbert label changed from "father" to "husband" (different wrong label, not caught)
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw [Critical #1] | main_cast.py (CHARACTER_IDENTIFICATION_PROMPT) | Partial — 2 of 3 removed, 1 new appeared |
| 1 (Fix B) | Mrs. White "father"→"mother" [High #3→#2] | post_corrections.py, test_post_corrections.py | Herbert desc fixed ✓, relationship label changed form (father→husband) but still wrong |

**When updating this table:**
- Fix A targeted the same file (main_cast.py) — the prompt approach is insufficient, need heuristic code change
- Fix B targeted post_corrections.py — need to extend with inverse-relationship logic, not just gender consistency

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good
- All 5 characters high confidence — no profiling red flags

## Pipeline Notes (Attempt 2 Re-analysis)
- "the old fakir" / "an old fakir" successfully removed from paw aliases (Fix A partial success)
- "the visitor" persists as paw alias, "stranger" is new
- is_symbolic still false — LLM ignores prompt instruction
- Herbert White physical description no longer misattributed (Fix B success)
- Mrs. White→Herbert label changed from "father" to "husband" (LLM generated different wrong label)
- Pass 2 still failed for Mr. White and Sergeant-Major Morris (kept without aliases)

## Next Action
Run PROMPT_fix.md to address:
1. **Critical #1**: Add common-noun-phrase heuristic to Rule 0.5 activation in main_cast.py (line ~828) — don't rely on LLM setting is_symbolic
2. **High #2**: Add inverse-relationship cross-validation in post_corrections.py — if A→B="son" and B is female, B→A must be "mother"
