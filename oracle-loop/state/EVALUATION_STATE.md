# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 21
- **Phase:** pending_analysis
- **baseline_score:** 7.35

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 20 | ~7.35 | No improvement: creature fragmentation, Elizabeth gender/rels, wrong Alphonse rel |
| 2 | 7.75 | Profiles improved |
| 3 | 7.58 | Profiles regressed |
| 4 | 7.08 | Summaries regressed (narrator substitution undid fix) |
| 5 | ~7.08 | Same root cause |
| 6 | ~5.5 | Regression: LLM hallucinated Elizabeth Lavenza as narrator |
| 7 | ~7.9 | Major recovery: 28 chapters ✓, letters/creature chapters misattributed |
| 8 | ~5.0 | REGRESSION: Step 4.5 early sub → all chapters attributed to outer narrator |
| 9-11 | ~1.5 | All chapters "Robert Walton" — Step 4.5 early sub regression |
| 12 | ~7.9 | Fix M: Victor chapters correct, creature chapters wrong, letters wrong |
| 13 | ~4.0 | Fix N/O/P: creature chapters fixed but Victor chapters still "Robert Walton" (narrator detection fragile) |

## Attempt 14 Fixes (commit 8d474af) — RESULT: ~7.35 (Step 6.9 picked Walton, not Victor)

### Root cause of attempt 14 failure
- Step 5.8.6 in characters.py fires for `pov="epistolary"` (not blocked by old exclusion list)
- It picks Walton (lowest mention count) as narrator via heuristic → sets Walton.is_narrator=True
- Step 6.9 preamble then finds Walton first in character list → narrator_detected="Robert Walton"

## Attempt 15 Fixes

### Fix T: characters.py Step 5.8.6 — exclude epistolary POV from heuristic
- Added "epistolary" to the `pov not in (...)` exclusion list
- Added guard: skip heuristic if any character ALREADY has is_narrator=True
- Rationale: epistolary/frame narratives have secondary narrators set by narrator.py (Fix Q);
  the heuristic incorrectly overwrites that by picking the lowest-mention char (Walton)

### Fix U: analyzer.py Step 6.9 preamble — pick most prominent is_narrator character
- When multiple is_narrator characters exist (e.g. Victor + creature as secondary narrators),
  previously picked the FIRST one in the list (nondeterministic)
- Now counts appearances in non-letter chapter summaries and picks the most frequent one
- Victor (appears in ~24/24 non-letter chapters) wins over creature (appears in ~6/24)
- Fallback: highest mention_count if no summary data

## Attempt 16 Fixes (commit c711e2c) — RESULT: ~7.5/10 (Narration improved but chars/pronunciation still <8)

### Fix V: narrator.py secondary path — skip symbolic entities (is_symbolic=True)
### Fix W: narrator.py secondary path — block ≤5 mention characters

### Attempt 16 Score Breakdown
- Structure: 8/10 ✓ (28 chapters)
- Characters: 7/10 ✗ — Mr. Kirwin + Magistrate Kirwin duplicate; Alphonse gender=female; Chamounix is a place
- Profiles: 7.5/10 ✗ — Victor missing Elizabeth/creature relationships
- Summaries: 8/10 ✓ — narrator attribution mostly correct; Ch15 says Victor instead of creature
- Pronunciation: 7/10 ✗ — "dæmon" not indexed (æ=non-ASCII, old regex missed it); missing Prometheus/Lucerne/Arveiron
- HTML: 8/10 ✓

## Attempt 17 Fixes

### Fix X: analyzer.py _is_likely_alias_of_existing TITLE_PATTERNS
- Added: `mr.`, `mr`, `mrs.`, `mrs`, `ms.`, `ms`, `miss`, `sir`, `lord`, `lady`, `judge`, `magistrate`, `inspector`, `constable`, `sheriff`, `detective`, `officer`
- Fixes: "Magistrate Kirwin" now blocked when "Mr. Kirwin" exists (identity resolution)

### Fix Y: word_index.py _build_index Unicode tokenization
- Changed: ASCII-only `[a-zA-Z]` pattern → Latin Extended `[a-zA-Z\xc0-\xd6\xd8-\xf6\xf8-\xff]`
- Uses lookahead/lookbehind for word boundaries (not \b which fails on non-ASCII)
- Fixes: "dæmon" now indexed and flagged for pronunciation (æ=U+00E6 in range)

### Fix AA: analyzer.py narrator_character_id selection
- Previously: picked FIRST is_narrator character (Robert Walton, main_cast_0)
- Now: prefers character whose name matches narrator_detected (Victor Frankenstein)
- Fallback: first is_narrator character if no narrator_detected match

## Attempt 17 Fixes (commit 63de4e8) — RESULT: REGRESSION (narrator=the dæmon → all summaries say "the creature")

### Root cause of attempt 17 regression
- LLM in this run extracted "the dæmon" as a SEPARATE entity from "the creature" with is_narrator=True
- Step 6.9 preamble (Fix U) used word-set intersection: {"the","dæmon"} ∩ {"the","creature"} = {"the"}
  → "the dæmon" matched ANY "the X" active_characters entry, got inflated count → picked as narrator
- "Finalizing narrator detection" returned "No definitive narrator" → preamble result (dæmon) stood
- Step 6.9 substitution: _nn_final = "the creature" (via alias lookup: dæmon → alias of creature)
  → ALL "the narrator" in summaries replaced with "the creature" → complete regression

## Attempt 18 Fixes (commit 8d474af → cc66e09) — RESULT: REGRESSION (creature merged into Arctic ice)

### Root cause of attempt 18 regression
- LLM Pass 2 consolidated "the creature", "the dæmon", "the blind father (De Lacey)" all into "the Arctic ice"
- verify_aliases Rule 0.5 (symbolic objects) should have blocked "the creature" as alias of "the Arctic ice"
- merge_descriptive_entities alias-based merge detected "creature" in aliases_b_norm (if "the creature" survived verify_aliases)
- Step 3.8 (_split_semantic_conflicts) didn't detect conflict because "arctic ice" is neither creature_terms nor human_descriptors

### Fix BB: analyzer.py Step 6.9 preamble — exclude stop words from word-set intersection
- Stop words filtered: {a, an, the, of, in, on, at, by, to, with, from, and, or, is/was/are/were, his/her/their/its/my/your/our}
- Content words only used for intersection: "the dæmon" → {"dæmon"}, "the creature" → {"creature"}
- {"dæmon"} ∩ {"creature"} = empty → no false match between generic "the X" names
- "Victor Frankenstein" → {"victor","frankenstein"} → matches "Victor" entries correctly
- Expected result: Victor wins preamble count (appears in 24/28 non-letter chapters)

## Attempt 19 Fixes (commit cc66e09)

### Guard CC2: characters.py _merge_descriptor_into_proper_name (Step 3.6b)
- Block person-entity descriptors (creature/being/monster/etc.) from merging into non-person targets
- Check: if last word of descriptor canonical is in _PERSON_NOUNS_MERGE_GUARD_CC2 and last word of target is NOT → block
- "the creature" (last="creature"=person) would not merge into "the Arctic ice" (last="ice"≠person)

### Guard CC3: main_cast.py merge_descriptive_entities alias-based merge
- Block alias-based merge when one entity is person/being and the other is non-living environment
- _NON_LIVING_NOUNS_CC3: ice, sea, ocean, water, river, lake, mist, etc.
- _PERSON_NOUNS_CC3: creature, being, monster, daemon, dæmon, man, woman, father, mother, etc.
- If one canonical is person and other is non-living → skip merge even if canonical in aliases

### Step 3.8 extended: _split_semantic_conflicts (characters.py)
- Added Group 3: non_living_terms (ice, sea, ocean, forest, mountain, snow, etc.)
- Extended creature_terms: added dæmon/demon/devil/beast/brute/ogre/phantom/specter/ghost/spirit
- Extended human_descriptors: added father/mother/son/daughter/brother/sister/husband/wife
- New conflict: canonical_is_non_living AND (alias_is_creature OR alias_is_human) → split
- "the Arctic ice" (canonical_is_non_living=True) + "the creature" (alias_is_creature=True) → SPLIT

### Rule 0.5b extended: _PERSON_NOUNS_R05B (main_cast.py)
- Added: father, mother, son, daughter, brother, sister, husband, wife, child, gentleman, lady, sailor
- "the blind father (De Lacey)" now correctly identified as person entity (last_word="father")

## Expected Chapter Attribution After Fixes
- Letters 1-4: "Robert Walton" (correct — his narrative frame)
- Chapters 1-10: "Victor Frankenstein" (inner narrator confirmed from is_narrator flag)
- Chapters 11-16: "The narrator" (creature's narration, fixed by Fix N/6)
- Chapters 17-24: "Victor Frankenstein" (back to Victor)
- Chapter 25+: "Robert Walton" (back to outer frame, not present in this text)

## Attempt 20 Fixes (commits cc0cdc8, fa1a5c6, 25a3988)

### Fix DD: main_cast.py Rule 0.5b extension
- Extended to block non-"the"-prefixed non-living aliases for person entities
- E.g., "Arctic ice" can no longer be alias of "the creature" even without "the" prefix
- New _NON_LIVING_NOUNS_R05B: ice, sea, ocean, water, river, lake, mist, storm, forest, etc.
- Fires when: canonical starts with "the" AND is person entity AND alias last word is non-living

### Fix EE: characters.py canonical name promotion for descriptor characters
- When a descriptor character has proper-name aliases, promote best alias to canonical
- E.g., "Father" with alias "Alphonse Frankenstein" → canonical = "Alphonse Frankenstein"
- Prefers clean aliases (no parentheticals) over annotated ones
- Enables the character to be properly recognized and profiled

### Fix FF: characters.py kinship terms in _common_descriptor_words
- Added: father, mother, son, daughter, brother, sister, husband, wife, uncle, aunt, etc.
- "Father", "Mother" etc. now classified as descriptors enabling Fix EE to operate

### Fix GG: characters.py non-living environment entity filter
- After all pipeline steps, filter out characters whose canonical last word is a non-living noun
- Removes "the ice" (and similar Arctic/nature descriptions extracted as characters)
- Guard: symbolic entities (is_symbolic=True) are exempt; entities with proper-name aliases are exempt
- Fixes: Victor's "the ice as rival" relationship, spurious "environmental antagonist" entity

### Fix HH: analyzer.py F9 relationship extraction augmented with F2 summary evidence
- When profile evidence is sparse (<3 items), supplement F9 with F2 summary evidence
- F2 summary items (what chapters say about the character) help populate relationships
- Fixes: Elizabeth (92 mentions, empty relationships) should now get Victor relationship

### Attempt 20 Expected Improvements
- Characters: Father → Alphonse Frankenstein canonical (Fix EE+FF); no spurious "the ice" (Fix GG)
- Profiles: Victor won't have "the ice as rival"; Elizabeth may get Victor relationship (Fix HH)
- Overall: Estimated 7.8-8.2/10

## Attempt 20 Result (commit b6fea39 baseline, run ~101 min) — RESULT: ~7.35/10 (no net improvement)

### Attempt 20 Score Breakdown
- Structure: 8/10 ✓ — 28 chapters detected; Letter 1 title=None (minor)
- Characters: 6.5/10 ✗ — creature fragmented (split_the_dæmon + split_the_being); Elizabeth gender=None; "the old man" not promoted; Felix wrong "De Lacey" alias
- Profiles: 6.5/10 ✗ — Elizabeth empty relationships; Victor→Alphonse "brother" (WRONG); Alphonse→Victor "brother" (WRONG)
- Summaries: 8/10 ✓ — Ch1 says "The narrator" not substituted; creature chapters (Ch11-16) correct; Victor chapters mostly correct
- Pronunciation: 7.5/10 ✗ — Arveiron missing (fix committed for attempt 21); dæmon ✓; Chamounix ✓
- HTML: 8/10 ✓

### Root causes of attempt 20 failures
1. **Creature fragmentation**: LLM this run extracted "the being" as a separate entity from "the dæmon". Step 3.8 split them because they had conflicting aliases. Now two creature-type split_ chars exist instead of one.
2. **Elizabeth gender=None**: Alias "his wife" should infer female gender but gender inference from kinship aliases not implemented.
3. **Elizabeth empty relationships**: Fix HH didn't fire or LLM failed to extract rels from F2 evidence.
4. **Victor/Alphonse "brother" (WRONG)**: LLM profiler labeled relationship as "brother" instead of "father/son". The `_propagate_missing_reverses` sibling-override guard exists but didn't catch this (Victor has no authoritative father label to override from).
5. **"the old man" not promoted**: Fix EE fires only for descriptor characters; LLM this run may have extracted "the old man" differently OR "De Lacey" was already associated with Felix, so old man's proper name alias wasn't set.

## Attempt 21 Fixes

### Fix KK: characters.py — post-split creature fragment merge
- After Step 3.8 `_split_semantic_conflicts`, merge any two split_ characters BOTH of which have creature_terms as their canonical last word
- creature_terms: creature, being, monster, daemon, dæmon, fiend, wretch, demon, beast, phantom
- If two split_ chars both qualify: merge the lower-mention one into the higher-mention one (alias-based merge)
- Guard: only merge if they originate from the same parent character (same prefix before the canonical name)

### Fix LL: characters.py — kinship alias → relationship infer
- When character A has alias like "his father", "her mother", "his son", etc. and there is a dominant co-mentioned character B:
  - bootstrap A→B with the kinship term relationship
  - bootstrap B→A with the inverse kinship term
- Prevents LLM profiler from hallucinating "brother" when the alias clearly says "father"

### Fix MM: characters.py — gender inference from kinship aliases
- When alias contains "wife"/"her wife" → gender=female
- When alias contains "husband"/"his husband" → gender=male
- When alias contains "mother"/"her mother" → gender=female
- When alias contains "his" prefix (possessive) → check referent gender from canonical name
- Fixes: Elizabeth alias "his wife" → gender=female
