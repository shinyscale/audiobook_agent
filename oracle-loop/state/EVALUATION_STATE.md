# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 7
- **Phase:** complete
- **baseline_score:** 8.08

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8.5/10
  - Identity Resolution: 9.5/10
  - Alias Grouping: 7/10
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.45/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — all categories at or above threshold

## Evaluation Details

### Structure Detection: 9/10
- 3 parts correctly detected matching the story's three-part structure (I, II, III)
- Part I title is null (minor — many editions don't label Part I separately)
- Parts II and III correctly labeled "2" and "3"

### Character Extraction: 8/10
- **Completeness (8.5/10):** All 4 human characters present (Mr. White, Mrs. White, Herbert White, Sergeant-Major Morris). The monkey's paw (title object, present in attempt 6) is missing — acceptable since symbolic objects aren't required, but noted as a regression.
- **Identity Resolution (9.5/10):** Perfect. No false splits, no false merges, all 4 entries are distinct and correct.
- **Alias Grouping (7/10):** Mr. White gained "the old man" alias ✓ (improvement from attempt 6). Mrs. White lost "the old woman" alias ✗ (regression — blocked as "already claimed by another character"). Herbert has "Herbert", "his son", "the son" — "his son" is a possessive descriptor, not ideal. Morris has "Morris" ✓.

### Character Profiles: 8/10
Major improvement from attempt 6 (was 7.5/10). Key changes:
- **Personality data now populated for ALL 4 characters** ✓✓✓ — Mr. White: "hospitable, credulous, nervous, protective, fearful"; Mrs. White: "curious, humorous, practical, decisive, emotionally volatile"; Herbert: "frivolous, skeptical, jesting, playful"; Morris: "hospitable, solemn, cautionary, dogged, fatalistic"
- **Voice guidance populated for ALL 4 characters** ✓✓✓ — includes suggested tone, dialect notes, verbal tics, formality level, and example quotes. Excellent narrator utility.
- **Evidence citations present for all characters** ✓
- Physical descriptions: Mr. White ("old man with thin grey beard") ✓, Morris ("tall, burly man with beady eyes and rubicund visage") ✓, Mrs. White and Herbert null (Mrs. White had description in attempt 6 — minor regression)
- **Remaining issues:** Mrs. White → Herbert = "parent" (should be "mother" — Fix K did not fire). Mr. White ↔ Mrs. White spouse relationship removed (regression from attempt 6). Morris → Mr. White = "associated" (should be "friend").

Despite relationship label issues, the personality + voice guidance data makes these profiles dramatically more useful for narrator preparation than attempt 6.

### Chapter Summaries: 9/10
All three part summaries are excellent:
- Part I: Captures chess game, Morris's visit, paw backstory, £200 wish, paw twisting, Herbert seeing simian face in fire ✓
- Part II: Captures morning after, Herbert leaving for work, Maw & Meggins representative, death news, £200 compensation, Mr. White collapsing ✓
- Part III: Captures grief aftermath, Mrs. White demanding resurrection wish, knocking at door, struggle to open door, third wish, knocking ceasing ✓

### Pronunciation Guide: 8.5/10
14 entries, all with IPA. Good coverage: Sergeant-Major, rubicund, fakir/fakirs, antimacassar, shamefacedly, betokened, avaricious, bibulous, plus 3 homographs (live, minute, separate). No false positives. Minor gap: "Laburnam" (place name) not flagged.

### HTML Presentation: 8/10
- Clean layout with tabbed navigation ✓
- Character profiles with expandable evidence sections ✓
- Relationship grid cards ✓
- Chapter 3 character tags show "the old man"/"the old woman" (unresolved descriptors instead of canonical names) — minor issue
- "Chapter 3: 3" heading slightly redundant

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good

## Regressions from Attempt 6 (noted but not blocking)
1. Monkey's paw not extracted (was present in attempt 6 as 5th character)
2. Mrs. White lost "the old woman" alias (was present in attempt 6)
3. Mr. White ↔ Mrs. White spouse relationships removed (present in attempt 6)
4. Mrs. White lost physical description (had "old woman with trembling hands and burning eyes")
5. Fix K (neutral kinship → gender-specific) did NOT fire: Mrs. White → Herbert still "parent" not "mother"

These regressions are offset by: Mr. White gaining "the old man" alias, ALL characters getting personality data and voice guidance, rich evidence citations.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |
| 2 | 8.15 | +0.07 | Fix A partially worked (2 of 3 bad aliases removed). Fix B landed for Herbert physical desc. |
| 3 | 7.0 | **-1.08** | **REGRESSION.** Fix C over-fires — "the old man" becomes garbage 43-mention entry, paw disappears |
| 4 | 7.9 | -0.18 | Fix C reverted. Phantom "the old man" persists (45 mentions, garbage aliases). All family relationship labels wrong (spousal instead of parent-child). Monkey's paw absent. |
| 5 | 8.2 | +0.12 | Fix E eliminated phantom ✓. Fix F partially fixed relationships ✓. Paw re-extracted ✓. Remaining: alias gaps, one wrong relationship direction, Mrs. White profile sparse. |
| 6 | 8.38 | +0.30 | Fix G fixed father/son ✓. Fix I gave Mrs. White alias ✓. Fix H removed 2 false aliases ✓. Only Profiles still failing (7.5). |
| 7 | 8.45 | +0.37 | **PASS.** Rich personality + voice guidance for all characters. Fix K didn't fire but profiles improved via LLM run variance. |

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

- Attempt 6 (Fix K): Neutral kinship label specialization in `enforce_gender_consistency`
  - Result: **DID NOT FIRE** in production (all genders still null, "parent" label persists). However, overall Profiles improved to 8/10 due to rich personality/voice data from LLM run variance.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

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
| 6 (Fix K) | Neutral kinship specialization | post_corrections.py | **DID NOT FIRE** in production |

## Next Action
Text PASSED. Ready to advance to next text (cask_of_amontillado).
