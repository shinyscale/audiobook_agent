# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 8.08
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 7.5/10
  - Alias Grouping: 6.5/10 ← missing aliases for Mr./Mrs. White, false aliases on paw
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.2/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Fixed E and F Accomplished

**Fix E (descriptor merge) — SUCCESS:** The phantom "the old man" character with 45 mentions is GONE. No more duplicate character entry. The Monkey's Paw is now properly extracted as its own symbolic entity (18 mentions). This was the critical blocker from attempts 1-4.

**Fix F (cross-tier guard) — PARTIAL SUCCESS:** Parent-child labels are no longer universally replaced by spousal labels. Mrs. White → Herbert is now "mother" ✓. Herbert → Mr. White and Herbert → Mrs. White are both "son" ✓. However, Mr. White → Herbert is "son" instead of "father" — the `enforce_inverse_consistency` logic is not correcting this direction.

## Current Issues (Priority Order)

### HIGH
1. **Mr. White → Herbert relationship labeled "son" instead of "father"** [Profiles]
   - Problem: Mr. White's relationship to Herbert White is labeled "son" — but Mr. White is Herbert's FATHER. The inverse direction (Herbert → Mr. White = "son") is correct. The `enforce_inverse_consistency()` function should detect: if B→A = "son", then A→B must be "father" (not "son").
   - Evidence: JSON shows `Mr. White → Herbert White: "son"`. Herbert → Mr. White: "son" is correct. Mrs. White → Herbert: "mother" is correct. Only Mr. White's direction is wrong.
   - Pipeline Notes show: `'Mr. White'→'Herbert White'='child' AND 'Herbert White'→'Mr. White'='child' (removed as contradictory)` — so both were labeled "child" (contradictory), they were REMOVED, and then re-populated later — but the re-population set Mr. White's label to "son" instead of "father".
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enforce_inverse_consistency()`. The function needs to infer the inverse: if Herbert is "son" to Mr. White, then Mr. White is "father" to Herbert. Currently it appears to detect same-label contradictions but not correct the inverse direction.
   - Fix: In `enforce_inverse_consistency()`, add inverse mapping: when both A→B and B→A are "child"/"son"/"daughter", detect the parent via title/gender (Mr. = male parent = father) and set A→B = "father" instead of removing both. Alternatively, ensure the inverse-label mapping (`son` ↔ `father`, `daughter` ↔ `mother`, `child` ↔ `parent`) is applied correctly.

2. **Mrs. White has no physical description or personality traits** [Profiles]
   - Problem: Mrs. White's profile has `physical_description: null` and `personality_traits: null`. She's a main character who should have profile data.
   - Evidence: The text describes her as "the old woman" and "white-haired old lady". She shows distinct behavior: initial skepticism about the paw, desperate grief after Herbert's death, frenzied insistence on the second wish, struggling toward the door in the dark.
   - Location: LLM profile generation — the profile prompt may not be extracting enough for Mrs. White because she's described more through actions than explicit descriptors.
   - Fix: This may improve naturally if Mr./Mrs. White aliases are resolved (Issue #3), giving the profiler more text to work with. If not, the profile prompt in `src/pipeline/character_profiling/` may need to look for action-based characterization, not just explicit descriptors.

3. **Mr. and Mrs. White have zero aliases despite extensive descriptor usage** [Alias Grouping]
   - Problem: Mr. White has zero aliases. "the old man" (used ~45 times in Part III) should be his alias. Mrs. White also has zero aliases — "the old woman"/"the old lady" should be hers.
   - Evidence: Fix E's `_merge_descriptor_into_proper_name()` at `characters.py:1597` adds the descriptor canonical name as an alias (`target.aliases.append(desc_char.canonical_name)`). The pipeline log confirms the merge fired. But the final output shows zero aliases for Mr. White. Something downstream is stripping the alias after the merge.
   - Root cause hypothesis: After the descriptor merge at Step 3.6b, the pipeline runs Steps 3.7-3.9 (alias dedup, split titled, split semantic, post-split repair). One of these steps — likely `verify_aliases` — may be stripping "the old man" because Rule 2a blocks aliases not found in any summary, or Rule 3 detects a co-occurrence conflict. The merge happens BEFORE verification, so the alias gets added then removed.
   - Location: `src/agents/characters.py` Step 3.6b (merge works) → Steps 3.7+ (alias gets stripped)
   - Fix: Either (a) move the descriptor merge AFTER verify_aliases so it's the final alias step, or (b) whitelist descriptor-merged aliases so verify_aliases doesn't strip them, or (c) investigate which specific verification rule is removing the alias and add an exemption for descriptor-merged aliases.
   - Note: "the old woman" was never a separate character (it was a garbage alias of the phantom), so it wouldn't be covered by Fix E. Mrs. White getting "the old woman" as an alias requires a separate mechanism (e.g., Pass 2 alias resolution or a similar descriptor-matching step for non-extracted descriptors).

4. **The Monkey's Paw has 3 false aliases: "The Visitor", "The Old Fakir", "an old fakir"** [Identity Resolution / Alias Grouping]
   - Problem: The paw's alias list includes three entities that are NOT the paw:
     - "The Visitor" = the Maw & Meggins representative who delivers news of Herbert's death (Part II). A human, not the paw.
     - "The Old Fakir" / "an old fakir" = the Indian holy man who placed the spell on the paw (mentioned by Morris in Part I). The spell's creator, not the paw itself.
   - Evidence: JSON shows `aliases: ["monkey's paw", "the paw", "The Visitor", "The Old Fakir", "an old fakir"]`. Only the first two are correct.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2 alias resolution. The LLM is over-associating entities mentioned in proximity to the paw (the fakir created it, the visitor's arrival fulfills its wish) as aliases OF the paw.
   - Fix: This is a Pass 2 prompt issue. Entities that INTERACT with a symbolic object are not aliases of it. The prompt should clarify: "An alias must be another NAME for the same entity. A person who created, used, or is affected by an object is NOT an alias of that object."

### MEDIUM
5. **Morris ↔ Mr. White labeled "associated" instead of "friend"** [Profiles]
   - Problem: Text clearly establishes Morris as an old army friend of Mr. White's — they served together, share drinks and war stories. "associated" is too generic.
   - Location: LLM profile generation output.
   - Fix: May improve if character context is richer after alias fixes. Low priority.

6. **Morris → The Monkey's Paw labeled "friend"** [Profiles]
   - Problem: Morris is wary of the paw and tries to burn it. "friend" is the wrong relationship. Should be "associated" or "possessor".
   - Location: LLM profile generation output. Minor issue.

7. **Chapter 3 character list shows "the old man" and "the old woman" instead of canonical names** [Presentation]
   - Problem: Chapter 3's character tags display unresolved descriptors instead of "Mr. White" and "Mrs. White".
   - Evidence: HTML report chapter 3 section shows `<span class="tag">the old man</span>` and `<span class="tag">the old woman</span>`.
   - Location: Chapter-character linking in the summary pipeline. If aliases were properly resolved (Issue #3), the linker should map these descriptors to canonical characters.
   - Fix: Self-resolves if Issue #3 is fixed (aliases enable the linker to match descriptors to characters).

### LOW
8. **The Maw & Meggins representative missing as a character** [Completeness]
   - Very minor character who appears briefly in Part II. Currently his mention "the visitor" is incorrectly absorbed as a paw alias (Issue #4). Resolving Issue #4 would free "the visitor" but he still may not meet the mention threshold for extraction.
   - Not blocking — a narrator would understand who "the visitor" is from the summary.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. |
| 3 | 7.0 | **-1.08** | **REGRESSION.** Fix C over-fires — "the old man" becomes garbage 43-mention entry, paw disappears |
| 4 | 7.9 | -0.18 | Fix C reverted. Phantom "the old man" persists (45 mentions, garbage aliases). All family relationship labels wrong (spousal instead of parent-child). Monkey's paw absent. |
| 5 | 8.2 | +0.12 | Fix E eliminated phantom ✓. Fix F partially fixed relationships ✓. Paw re-extracted ✓. Remaining: alias gaps, one wrong relationship direction, Mrs. White profile sparse. |

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

- Attempt 4 (Fix E): Added `_merge_descriptor_into_proper_name()` post-extraction merge step (Step 3.6b)
  - Result: **SUCCESS** — phantom "the old man" eliminated. But "the old man" alias not retained in final output (stripped by downstream verification).
  - Modified: `src/agents/characters.py`

- Attempt 4 (Fix F): Added cross-tier guard in `verify_relationships_from_text`
  - Result: **PARTIAL** — parent/child no longer overridden by spousal ✓. But Mr. White → Herbert labeled "son" instead of "father" — the inverse-direction correction logic is incomplete.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw [Critical #1] | main_cast.py (CHARACTER_IDENTIFICATION_PROMPT) | Partial — 2 of 3 removed, 1 new appeared |
| 1 (Fix B) | Mrs. White "father"→"mother" [High #3→#2] | post_corrections.py, test_post_corrections.py | Herbert desc fixed ✓, relationship label changed form (father→husband) but still wrong |
| 2 (Fix C) | False aliases: "visitor"/"stranger" on monkey's paw [Critical #1] | main_cast.py (is_common_noun_phrase heuristic) | **REGRESSION** — over-fires on person-descriptors, creates garbage "the old man" entry |
| 2 (Fix D) | Mrs. White→Herbert = "husband" instead of "mother" [High #2] | post_corrections.py (enforce_inverse_consistency), test_post_corrections.py | Partial — "parent" ✓ but contradictions removed some valid relationships |
| 3 (Fix C REVERT) | Revert catastrophic regression [Critical #1] | main_cast.py, test_post_corrections.py | Alias contamination slightly reduced but phantom persists |
| 4 (Fix E) | Phantom "the old man" [Critical #1] | characters.py (_merge_descriptor_into_proper_name, Step 3.6b) | **SUCCESS** — phantom eliminated. But alias not retained in final output. |
| 4 (Fix F) | Parent/child labels overridden by spousal [Critical #2] | post_corrections.py (verify_relationships_from_text cross-tier guard) | **PARTIAL** — spousal override blocked ✓. But Mr. White→Herbert = "son" instead of "father" (wrong direction, not corrected). |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good
- 5 pipeline stages, 38 LLM calls, 80,563 tokens in 24m 40s

## Priority Fix Path for Attempt 6

To cross the 8.0 threshold in BOTH failing categories:

**Characters (7.5 → 8.0+):**
- Fix Issue #3 (alias stripping): Investigate why "the old man" alias is stripped after descriptor merge. Move merge step AFTER verify_aliases, or whitelist descriptor-merged aliases. Expected improvement: +0.5 to Alias Grouping → Characters ~8.0.
- Fix Issue #4 (paw false aliases): Tighten Pass 2 prompt for symbolic entities — "persons who interact with a symbolic entity are NOT aliases of it." Expected improvement: +0.5 to Identity Resolution.

**Profiles (7.0 → 8.0+):**
- Fix Issue #1 (Mr. White → Herbert = "son"): Add proper inverse-label correction in `enforce_inverse_consistency()`. If both directions have the same child-label, detect the parent by title/gender and set the correct inverse. Expected improvement: +0.5.
- Fix Issue #2 (Mrs. White profile): May self-resolve if aliases are fixed (more text context for profiler). If not, investigate profile extraction prompt. Expected improvement: +0.5.

**Focus on Issues #1 and #3 first** — they are most likely to have clean code fixes.

## Next Action
Run PROMPT_fix.md to address Issues #1-4.
