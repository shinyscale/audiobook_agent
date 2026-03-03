# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 7.4

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 7/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles)

## Improvements from Attempt 1
- Morris restored ✓ (was missing entirely — now main_cast_3, 5 mentions)
- Mr. White alias "the old man" ✓ (was missing)
- Mrs. White alias "the old woman" ✓ (was missing)
- Mrs. White → Herbert relationship fixed: "mother" ✓ (was "father")
- Pronunciation false positives removed: bedclothes/instalment/betokened gone ✓
- No JSON parse failures this run (5H/0M/0L profiles)

## Current Issues (Priority Order)

### CRITICAL
1. **Mr. White → Herbert relationship labeled "husband" instead of "father"** [Profiles]
   - Problem: Mr. White's relationships show Herbert White: "husband". This is the wrong relationship TYPE — Mr. White is Herbert's father, not his husband.
   - Evidence: The text explicitly describes "Mr. White, his son Herbert, and Mrs. White." Mr. White is Herbert's father.
   - Root cause: The LLM generated "husband" for this relationship during profile generation. `enforce_gender_consistency` cannot fix this — it only swaps gender variants (mother↔father, wife↔husband), not incorrect relationship types (spousal vs parent-child).
   - Also: Herbert → Mr. White is labeled "husband" (should be "son"). Same root cause.
   - Location: `src/analyzer.py` — `_generate_character_profile()` or `src/pipeline/post_corrections.py` — relationship validation
   - Fix approach: Add a relationship type validation rule: if character A's relationship to B is "husband"/"wife" AND B's relationship to A is also "husband"/"wife", but A is B's parent (inferred from B→A being "son"/"daughter" in another character's profile, or from summary text mentioning "his son"), then correct to "father"/"mother" ↔ "son"/"daughter". Alternatively: `enforce_inverse_consistency` should catch that if Herbert→Mrs. White is "son" then Herbert→Mr. White cannot be "husband" when they share a surname (family unit).

### HIGH
2. **All character genders are null** [Profiles]
   - Problem: Gender is null for all 5 characters despite clear Mr./Mrs. title cues.
   - Evidence: `jq '.characters[] | {name: .canonical_name, gender: .gender}'` shows all null.
   - Impact: Without gender, `enforce_gender_consistency` can only fix labels when the label itself implies gender. It can't proactively validate.
   - Location: Gender detection in `src/pipeline/character_extraction_v2/` or profile generation in `src/analyzer.py`
   - Fix approach: If gender is null but canonical name starts with "Mr." → male, "Mrs."/"Miss"/"Ms." → female. This is a trivial heuristic that could run as a post-processing step.

3. **"the visitor" aliased to monkey's paw** [Alias Grouping]
   - Problem: "the visitor" is assigned as an alias of "the monkey's paw". In the text, "the visitor" refers to Sergeant-Major Morris (Part I) and the Maw & Meggins representative (Part II) — both humans, never the paw.
   - Evidence: Part II summary: "a well-dressed stranger from the firm 'Maw and Meggins' arrives" — this is "the visitor." The paw is an inanimate object that doesn't "visit."
   - Location: Pass 2 alias resolution or `verify_aliases` in `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix approach: Since "the visitor" refers to two different people (Morris in I, Maw&Meggins man in II), it shouldn't be aliased to anyone. Objects/symbolic characters (is_symbolic or lowercase-only canonical names) should not receive human-descriptor aliases like "the visitor."
   - Note: This is the same issue from attempt 1. It was "blocked for Morris via Rule 3 — paw claimed it first." The real fix is preventing the paw from claiming it in the first place.

### MEDIUM
4. **Morris → monkey's paw relationship labeled "friend"** [Profiles]
   - Problem: Morris's relationship to the paw is "friend." A person is not "friends" with an object. Should be "associated" or "former owner/possessor."
   - Location: Profile generation in `src/analyzer.py`
   - Fix: Low priority — weird but not confusing for a narrator.

5. **Chapter titles: null / "2" / "3" instead of "I" / "II" / "III"** [Structure]
   - Problem: Part I has null title, Parts II/III show Arabic "2"/"3" instead of original Roman numerals.
   - Location: `src/pipeline/chapter_detection/consensus.py` — `_clean_title()`
   - Fix: Already documented in attempt 1 as medium. Same issue persists.

### LOW
6. **monkey's paw not marked is_symbolic** [Character Metadata]
   - Problem: `is_symbolic: false` for an inanimate cursed object.
   - Location: Symbolic detection heuristic in character extraction.
   - Impact: Minimal for narrator usability.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.4 | - | Baseline — Morris dropped, visitor alias wrong, Mr. White no aliases |
| 2 | 8.25 | +0.85 | Morris restored, aliases fixed, but new relationship label error |

## Fix History
- Attempt 1 (monkeys_paw):
  - **Morris missing (Completeness)**: Added military/clerical ranks to `_add_title_stripped_aliases()` in `main_cast.py` so "Sergeant-Major Morris" gets "Morris" as auto-alias → enough mentions to pass grounding. Also added `not pc.id.startswith("main_cast_")` guard to `_convert_characters` evidence filter in `analyzer.py` — main_cast characters (LLM-vetted) are never dropped by the false-positive filter.
  - **Mrs. White gender (Profiles)**: Added second call to `enforce_gender_consistency` at end of Phase B `run_all` (after `_propagate_missing_reverses`) in `post_corrections.py` — catches any re-introduced gender mismatches.
  - **Pronunciation false positives**: Added "bedclothes", "instalment", "betokened" (and variants) to `COMMON_WORDS_WHITELIST` in `cmu_proposer.py`.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Morris missing (Completeness) | `main_cast.py`, `analyzer.py` | Fixed ✓ |
| 1 | Mrs. White gender (Profiles) | `post_corrections.py` | Fixed ✓ (Mrs. White→Herbert now "mother") |
| 1 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 2 | Mr. White→Herbert "husband" (Profiles) | (pending) | — |
| 2 | All genders null | (pending) | — |
| 2 | "the visitor" aliased to paw | (pending) | — |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (chars, summaries, profiles) — appropriate
- Context length: 32768 — sufficient for this short story (3,954 words)
- Temperature: 0.7 — reasonable
- think_mode: false — correct for qwen3.5
- No JSON parse failures this run (0 retries, 0 parse failures across all stages)
- All 5 profiles generated at HIGH confidence
- Character Extraction: 1 medium confidence item (likely monkey's paw)

## Pipeline Notes (Attempt 2)
- Duration: 39m 33s, 37 LLM calls, 81,513 tokens
- 5 characters found (up from 4 — Morris now present)
- Morris restoration: ✓ "Sergeant-Major Morris (aka Morris) - 5 mentions"
- Mr. White aliases: ✓ "the old man" now assigned
- Mrs. White aliases: ✓ "the old woman" now assigned
- "the visitor" still aliased to monkey's paw (blocked for Morris via Rule 3 — paw claimed it first)
- BLOCKED: 'the husband'→Mr. White, 'the wife'→Mrs. White, 'the mother'→Mrs. White (different titled people rule)
- Pass 2 failed for Herbert White (kept without aliases except "Herbert" from title-strip)
- No JSON parse failures this run (5H/0M/0L profiles)
- Pronunciation false positives: ✓ bedclothes/instalment/betokened removed

## Next Action
Run PROMPT_fix.md to address:
1. **Primary blocker**: Mr. White ↔ Herbert "husband" relationship (Critical #1) — needs relationship type validation in post_corrections.py
2. **Root cause**: Gender null for all characters (High #2) — title-based gender heuristic needed
3. **Persistent**: "the visitor" alias on paw (High #3) — prevent objects from claiming human-descriptor aliases
