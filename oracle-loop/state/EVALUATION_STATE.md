# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 7
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.08
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8.5/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 7/10 ← Mr. White still missing "the old man", one false alias on paw
- Character Profiles: 7.5/10 ✗ (FAILING — only failing category)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.38/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles)

## What Attempt 6 Fixes Accomplished

**Fix G (bidirectional child labels) — SUCCESS:** Despite pipeline notes reporting "NOT WORKING" during analysis, the final JSON shows Mr. White → Herbert = "father" ✓. The contradiction detection and title-based parent inference worked end-to-end. This was the #1 issue from attempt 5.

**Fix H (alias prompt) — PARTIAL:** "The Old Fakir"/"an old fakir" are GONE from the paw's aliases ✓. But "the visitor" persists as a paw alias.

**Fix I (descriptor alias exemption) — PARTIAL:** Mrs. White gained "the old woman" alias ✓. But "Pass 2 failed for Mr. White" — Mr. White still has zero aliases.

**Fix J (is_symbolic detection) — DID NOT FIRE:** `is_symbolic` is still `false` for the monkey's paw. The possessive-pattern regex either didn't match or the flag was overwritten downstream.

**Bonus improvement:** Mrs. White now has a physical description ("old woman with trembling hands and burning eyes") — this was null in attempt 5 and appears to have self-resolved, likely because the alias resolution provided more text context.

**NEW: Spouse relations preserved.** Despite pipeline notes warning about a spouse-removal regression, the final output shows Mr. White→Mrs. White = "husband" ✓ and Mrs. White→Mr. White = "wife" ✓. No regression.

## Current Issues (Priority Order)

### HIGH
1. **All character genders are null — blocks gender-specific relationship labels** [Profiles]
   - Problem: Every character has `gender: null` in the output JSON. This means `enforce_gender_consistency()` cannot convert generic labels ("parent"→"mother", "child"→"son") because it doesn't know the character's gender.
   - Evidence: `jq '.characters[] | {name: .canonical_name, gender: .gender}' analysis.json` shows all null. Mrs. White→Herbert = "parent" (should be "mother"). Herbert→Mrs. White = "child" (should be "son").
   - Root cause: The V2 character extraction pipeline (`main_cast.py`) either doesn't ask the LLM to set gender, or the parsing doesn't capture it, or a later step clears it.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (Pass 1 extraction or parsing) and/or `src/pipeline/character_profiling/post_corrections.py` (gender inference from titles).
   - Fix: Add a post-extraction step that infers gender from titles in the canonical name: "Mr." → male, "Mrs."/"Ms."/"Miss" → female. This is already partially done in `enforce_gender_consistency` (Fix B from attempt 1 added title-based gender detection for label swapping) but the gender FIELD itself isn't being set. Either (a) set the gender field from titles before `enforce_gender_consistency` runs, or (b) enhance `enforce_gender_consistency` to use title-inferred gender for the parent/child → mother/father/son/daughter conversion.
   - Expected impact: +0.3 to Profiles (relationship labels become gender-specific)

2. **No personality_traits for any character** [Profiles]
   - Problem: `personality_traits` is null for all 5 characters. For a narrator, knowing Mr. White is impulsive/fearful, Mrs. White is desperate/emotional, Herbert is sardonic/humorous, and Morris is grave/world-weary would significantly help vocal characterization.
   - Evidence: All personality_traits fields are null in JSON.
   - Location: `src/pipeline/character_profiling/` — the profile generation LLM prompt and/or parsing.
   - Root cause hypothesis: The profiler may not be asking for personality traits, or the output schema doesn't capture them, or the LLM isn't generating them for short stories with limited explicit characterization.
   - Fix: Check if the profile prompt includes personality trait extraction. If the schema supports it but the LLM isn't populating it, add explicit instruction like "Infer personality traits from the character's ACTIONS and DECISIONS, not just explicit descriptions." For short stories, action-based inference is key since characters are shown through behavior, not narrated description.
   - Expected impact: +0.3 to Profiles

3. **Morris → Mr. White labeled "associated" instead of "friend"** [Profiles]
   - Problem: The text clearly establishes Morris as an old army friend of Mr. White's — they served together, share drinks, and reminisce. "associated" is too generic.
   - Evidence: Text says Morris is "late of the Seventy-Fourth Indian Regiment" and they share familiarity typical of old comrades.
   - Location: LLM profile generation output.
   - Fix: May improve if personality/context enrichment fixes are applied. Low priority — not blocking by itself.
   - Expected impact: +0.1

### MEDIUM
4. **"the visitor" still listed as alias of the monkey's paw** [Alias Grouping]
   - Problem: "the visitor" in Part II refers to the Maw & Meggins representative (a human), not the paw. Down from 3 false aliases (attempt 5) to 1, but still present.
   - Evidence: Chapter 2 summary says "a well-dressed stranger from the firm 'Maw and Meggins' arrives" — clearly a person, not the paw.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2 alias resolution.
   - Note: Characters category already at 8.0 threshold. Fixing this would provide margin but isn't strictly needed for Profiles.

5. **Mr. White still has zero aliases — "the old man" missing** [Alias Grouping]
   - Problem: Pass 2 alias resolution failed for Mr. White entirely. Mrs. White gained "the old woman" via Fix I, but Mr. White didn't benefit.
   - Evidence: Pipeline notes: "Pass 2 failed for Mr. White, keeping without aliases."
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2.
   - Note: Same as above — Characters at 8.0, not the blocking category.

6. **Morris → monkey's paw labeled "friend"** [Profiles]
   - Problem: Morris is wary of the paw and tried to burn it. "friend" is wrong — should be "former possessor" or "associated."
   - Minor issue, not enough to move the score.

7. **Chapter 3 character tags show "the old man"/"the old woman" instead of canonical names** [Presentation]
   - Problem: Chapter 3's character tags display unresolved descriptors. Mrs. White's "the old woman" alias should enable resolution, but it doesn't. Mr. White's "the old man" can't resolve because the alias is missing.
   - Not blocking — Presentation is at 8.0.

### LOW
8. **Herbert has no physical_description** — text provides minimal physical detail for Herbert. Acceptable for a short story.
9. **No speech_patterns for any character** — W.W. Jacobs uses fairly uniform dialogue. Low priority.
10. **Paw is_symbolic = false** — Fix J didn't fire. Cosmetic issue since the paw is correctly extracted as a character regardless.

## Priority Fix Path for Attempt 7

**Target: Profiles 7.5 → 8.0+** (the only failing category)

The minimum fix to cross threshold: **Issue #1 (gender detection)**. If gender is inferred from Mr./Mrs. titles, `enforce_gender_consistency` can convert:
- Mrs. White → Herbert: "parent" → "mother"
- Herbert → Mrs. White: "child" → "son"
- (Mr. White → Herbert already correct as "father")

This alone provides +0.3. Combined with any partial improvement on personality traits (Issue #2), Profiles reaches 8.0.

**Recommended approach:**
1. In the character profiling pipeline or post-corrections, add a step that sets `gender` based on canonical name titles (Mr.→male, Mrs./Ms./Miss→female, also infer from first names like "Herbert"→male).
2. Ensure `enforce_gender_consistency` uses the inferred gender to convert "parent"→"mother"/"father" and "child"→"son"/"daughter".
3. If time permits, enhance the profile prompt to extract personality traits from character actions.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. |
| 3 | 7.0 | **-1.08** | **REGRESSION.** Fix C over-fires — "the old man" becomes garbage 43-mention entry, paw disappears |
| 4 | 7.9 | -0.18 | Fix C reverted. Phantom "the old man" persists (45 mentions, garbage aliases). All family relationship labels wrong (spousal instead of parent-child). Monkey's paw absent. |
| 5 | 8.2 | +0.12 | Fix E eliminated phantom ✓. Fix F partially fixed relationships ✓. Paw re-extracted ✓. Remaining: alias gaps, one wrong relationship direction, Mrs. White profile sparse. |
| 6 | 8.38 | +0.30 | Fix G fixed father/son ✓. Fix I gave Mrs. White alias ✓. Fix H removed 2 false aliases ✓. Only Profiles still failing (7.5). |

## Fix History
- Attempt 1 (Fix A): Clarified `is_symbolic: true` in CHARACTER_IDENTIFICATION_PROMPT for non-person entities
  - Result: Partially worked — removed "the old fakir"/"an old fakir" but "the visitor" persisted, "stranger" appeared
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 1 (Fix B): Extended `enforce_gender_consistency` to detect gender from canonical name titles (Mr./Mrs./Ms./Miss)
  - Result: Herbert "tall and burly" physical description fixed ✓. But Mrs. White→Herbert label changed form (father→husband) but still wrong
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

- Attempt 4 (Fix E): Added `_merge_descriptor_into_proper_name()` post-extraction merge step (Step 3.6b)
  - Result: **SUCCESS** — phantom "the old man" eliminated. But "the old man" alias not retained in final output (stripped by downstream verification).
  - Modified: `src/agents/characters.py`

- Attempt 4 (Fix F): Added cross-tier guard in `verify_relationships_from_text`
  - Result: **PARTIAL** — parent/child no longer overridden by spousal ✓. But Mr. White → Herbert labeled "son" instead of "father" — the inverse-direction correction logic is incomplete.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

- Attempt 5 (Fix G): Bidirectional child label resolution in `enforce_inverse_consistency()` using formal title
  - Result: **SUCCESS** — Mr. White → Herbert = "father" ✓ in final output.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

- Attempt 5 (Fix H): Clarified ALIAS_RESOLUTION_PROMPT — descriptor aliases + interacting-party exclusion
  - Result: **PARTIAL** — "The Old Fakir"/"an old fakir" removed ✓, but "the visitor" persists.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 5 (Fix I): Descriptor alias exemption in verify_aliases co-occurrence check
  - Result: **PARTIAL** — Mrs. White gained "the old woman" alias ✓, but Pass 2 failed entirely for Mr. White.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 5 (Fix J): Programmatic `is_symbolic` detection for possessive-pattern names
  - Result: **DID NOT FIRE** — paw still has is_symbolic=false in output.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw | main_cast.py | Partial — 2 of 3 removed, 1 new appeared |
| 1 (Fix B) | Gender detection from titles | post_corrections.py, test_post_corrections.py | Herbert desc fixed ✓, relationship label still wrong |
| 2 (Fix C) | Common noun phrase heuristic | main_cast.py | **REGRESSION** — over-fires, creates garbage entry |
| 2 (Fix D) | Inverse consistency | post_corrections.py, test_post_corrections.py | Partial — some relationships removed as contradictory |
| 3 (Fix C REVERT) | Revert regression | main_cast.py, test_post_corrections.py | Reduced contamination, phantom persists |
| 4 (Fix E) | Descriptor merge step | characters.py | **SUCCESS** — phantom eliminated |
| 4 (Fix F) | Cross-tier relationship guard | post_corrections.py, test_post_corrections.py | **PARTIAL** — spousal override blocked, but direction wrong |
| 5 (Fix G) | Bidirectional child labels | post_corrections.py, test_post_corrections.py | **SUCCESS** — father/son correct |
| 5 (Fix H) | Alias prompt for symbolic entities | main_cast.py | **PARTIAL** — 2 false aliases removed, 1 persists |
| 5 (Fix I) | Descriptor alias exemption | main_cast.py | **PARTIAL** — Mrs. White alias ✓, Mr. White failed |
| 5 (Fix J) | is_symbolic detection | main_cast.py | **DID NOT FIRE** |

**Pattern note:** `post_corrections.py` has been modified 5 times across attempts. Fix B (gender detection from titles) was added in attempt 1 but gender fields remain null — the gender detection may only apply to relationship label swapping, NOT to setting the `gender` field on the character object. Fix for attempt 7 should verify whether Fix B's code sets the gender field or only uses inferred gender locally.

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good
- 5 pipeline stages, 38 LLM calls, 81,021 tokens in 39m 36s

## Fix History (continued)

- Attempt 6 (Fix K): Neutral kinship label specialization in `enforce_gender_consistency`
  - Root cause: `enforce_gender_consistency` only corrected gender-WRONG labels (e.g., male can't be "mother"), but never specialized gender-NEUTRAL labels ("parent"→"mother/father", "child"→"son/daughter")
  - Fix: Added a third branch in the relationship iteration loop that maps neutral kinship labels to gender-specific equivalents when character gender is known from title (Mr./Mrs.) or description pronouns
  - Tiebreaker: When gender is ambiguous from description (e.g., Herbert's description mentions "Mrs. White" creating false female signal), use character's own other gendered relationship labels to resolve (Herbert already had "son" → Mr. White, so male)
  - Expected fixes: Mrs. White→Herbert "parent"→"mother", Herbert→Mrs. White "child"→"son"
  - Smoke test: PASS — confirmed both corrections fire in isolation test
  - All 332 tests pass (56 in test_post_corrections.py, 276 others)
  - Modified: `src/pipeline/character_profiling/post_corrections.py` (`enforce_gender_consistency()`)

## Attempt 7 Pipeline Notes
- Run time: 19m 22s, 36 LLM calls, 75,424 tokens
- **Mr. White gained "the old man" alias** — Pass 2 now succeeds for Mr. White
- **Herbert White gained "his son" alias** — new alias not present in attempt 6
- **Mrs. White has NO aliases** — BLOCKED messages show "the old woman" alias blocked ("already claimed by another character")
- **Monkey's paw NOT extracted** — only 4 characters found (vs 5 in attempt 6); paw is missing entirely
- **Spouse contradiction removed** — "Removing contradictory relationship: Mr. White→Mrs. White='spouse' AND Mrs. White→Mr. White='spouse'" — potential regression (attempt 6 had husband/wife preserved)
- Fix K (neutral kinship → gender-specific) is the key change this attempt; needs evaluation to confirm Profiles improvement

## Next Action
Evaluate attempt 7 output: verify Fix K improved Profiles (parent→mother, child→son), check for spouse regression, note paw absence.

**Phase:** awaiting_evaluation
