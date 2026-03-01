# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 6.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## What Improved from Attempt 1
- The Creature is now correctly extracted as a standalone character (main_cast_1, 103 mentions) ✓
- The Creature is correctly marked as narrator (chapters 11-16) ✓
- The Turkish merchant is correctly separated as "the Turk" (0a5ef5ac589f) ✓
- Creature aliases include "the monster", "the fiend", "the wretch", "the being", "the thing" ✓

## Current Issues (Priority Order)

### CRITICAL

1. **Victor Frankenstein — protagonist is FALSE SPLIT into two entries** [Identity Resolution]
   - Problem: "Victor" (supporting_1, 28 mentions) and "Frankenstein" (supporting_3, 27 mentions) are listed as separate characters with NO aliases. These are the SAME PERSON — Victor Frankenstein, the novel's protagonist. Combined mentions would be 55+.
   - Evidence: The text uses "Victor" and "Frankenstein" interchangeably for the same person throughout. He is the narrator of chapters 1-24 (within Walton's frame). No other character is called "Frankenstein" by first name or surname alone in this novel.
   - ID pattern: Both are `supporting_*` → they came from the supporting cast pipeline, not main cast. This is doubly wrong — the protagonist should be in main cast.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` produced both as separate entries; `src/pipeline/character_extraction_v2/main_cast.py` failed to detect Victor at all (he's not in main_cast)
   - Fix approach: Victor Frankenstein should be a single entry in main_cast with aliases: "Victor", "Frankenstein", "Victor Frankenstein". The supporting cast entries should merge or the main_cast pipeline needs to extract him. This is likely a name-frequency issue — the text usually uses just "I" (first person) so both "Victor" and "Frankenstein" have low individual mention counts, causing both to fall into supporting cast and not be merged.

2. **Alphonse Frankenstein is STILL completely missing** [Completeness]
   - Problem: Victor's father does not appear in the character list at all. He is a significant character throughout the novel — sends letters, travels to care for Victor, takes Victor home from prison, dies of grief after Elizabeth's murder.
   - Evidence: Referred to as "my father", "his father", "Alphonse Frankenstein", "M. Frankenstein" (when referring to the elder). He appears in letters, chapters 1, 6, 7, 19, 21-23.
   - ID pattern: Absent from both main_cast and supporting
   - Location: The pipeline fails to extract him because he's primarily referred to as "my father" rather than by name, and the first-person narration makes relational references hard to resolve.
   - Fix: This is a recurring issue — pipeline notes from this run say "Alphonse's relational aliases ('Victor's father', 'the narrator's father') BLOCKED by co-occurrence check". The co-occurrence validation is too strict and rejecting valid character references.

### HIGH

3. **The Creature has "De Lacey" as a FALSE alias** [Alias Grouping, Identity Resolution]
   - Problem: main_cast_1 ("The creature") has "De Lacey" in its alias list. The Creature is NOT a De Lacey. The De Lacey family (Felix, Agatha, the old man) is a separate family the Creature observes. Felix De Lacey (main_cast_7) also has "De Lacey" as alias — creating a collision.
   - Evidence: The Creature watches the De Lacey family through a chink in the wall. He is never called "De Lacey" by anyone.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias resolution incorrectly linked "De Lacey" to the Creature, possibly because the Creature's narrative heavily discusses the De Laceys.
   - Fix: Remove "De Lacey" from the Creature's aliases. This is a false association from narrative proximity.

4. **Beaufort and Caroline Beaufort are falsely merged** [Identity Resolution]
   - Problem: "Beaufort" (main_cast_10) has "Caroline Beaufort" as an alias. Beaufort is a merchant who dies in poverty. Caroline Beaufort is his DAUGHTER who later marries Alphonse Frankenstein and becomes Victor's mother. They are two different people.
   - Evidence: Chapter 1: "Beaufort...sunk into poverty...died in Caroline's arms." Caroline subsequently marries Alphonse. Beaufort is male, Caroline is female.
   - ID pattern: `main_cast_10` → main cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — surname-matching alias logic merged father and daughter because both are "Beaufort"
   - Fix: Same-surname characters need disambiguation when they have different first names AND different genders or generational context.

5. **Relationships are deeply fabricated for major characters** [Profiles]
   - Problem: Multiple characters have relationships with people they never interact with. This appears to be co-occurrence contamination rather than actual relationship extraction.
   - Evidence of fabricated relationships:
     - Victor → "the old man: acquaintance", "Felix De Lacey: acquaintance", "Agatha De Lacey: acquaintance" — Victor never meets the De Lacey family
     - Robert Walton → "Cornelius Agrippa: acquaintance", "the Turk: acquaintance" — Walton never interacts with either
     - Frankenstein → "Ernest: parent" — wrong direction (Ernest is Victor's younger brother, not his child)
     - Henry Clerval → only "M. Krempe: acquaintance" — his primary relationship is Victor (best friend)
     - Elizabeth → NO relationships at all (should have: Victor as fiancé/husband, Alphonse as adoptive father)
   - Location: `src/pipeline/character_extraction_v2/` — relationship extraction appears to use chapter co-occurrence rather than actual described relationships
   - Fix: Relationship extraction should look for explicit relationship markers (family terms, role descriptions) not just co-occurrence in the same chapter.

6. **Physical descriptions missing for most characters** [Profiles]
   - Problem: Only 7/21 characters (33%) have physical descriptions. Neither Victor nor Henry Clerval — the two male leads — have any description.
   - Evidence: Victor is described as haggard, feverish, and emaciated after his creation work. The Creature has vivid descriptions (yellow skin, watery eyes, shrivelled complexion, black lips). Safie has dark eyes and satin skin.
   - Location: `src/pipeline/character_extraction_v2/` — profile extraction stage

### MEDIUM

7. **Structure: Letter 1 title not detected, chapter numbers shifted** [Structure]
   - Problem: The first structure element has `title: null`, causing it to display as "Chapter 1" instead of "Letter 1". Only 3 of 4 letters are detected as Prologue Materials. All subsequent chapter numbers are shifted — "Chapter 5" in the output = Chapter 1 in the book, "Chapter 28" = Chapter 24.
   - Evidence: HTML shows "3 Prologue Materials" instead of 4. Pronunciation section confirms: "Chapter 1" (Letter 1), "Letter 2", "Letter 3", "Letter 4", "Chapter 5"..."Chapter 28".
   - Location: `src/pipeline/chapter_detection/` — regex/LLM missed "Letter 1" heading
   - Fix: Ensure the first structural marker ("Letter 1") is detected.

8. **Supporting characters lack full canonical names** [Alias Grouping]
   - Problem: "William" should be "William Frankenstein", "Ernest" should be "Ernest Frankenstein", "Margaret" should be "Margaret Saville", "Kirwin" should be "Mr. Kirwin". These characters are identified by surname/full name at least once in the text but their canonical names are incomplete.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — canonical name resolution for supporting cast
   - Fix: Supporting characters need full name lookup during extraction.

9. **"De Lacey" alias conflict between two entries** [Alias Grouping]
   - Problem: "De Lacey" appears as alias for both The creature (main_cast_1, WRONG) and Felix De Lacey (main_cast_7). Additionally, "the old man" (split_the_old_man) represents the father, whose canonical name should probably be "De Lacey" or "Old De Lacey" rather than "the old man".
   - Location: Alias deduplication in main_cast.py
   - Fix: Remove "De Lacey" from Creature's aliases (issue #3), keep for Felix or the old man only.

10. **Pronunciation false positives** [Pronunciation]
    - Problem: Common English words flagged: "does", "than", "hero", "sympathised", "sympathise", "desert", "produce". While some are legitimate homographs, "than" and "hero" have no pronunciation ambiguity.
    - Evidence: 206 entries, ~15-20 are unnecessary false positives.
    - Location: `src/pipeline/pronunciation/` — filtering logic
    - Fix: Add common unambiguous words to exclusion list.

11. **Book title displayed as "Contents"** [Presentation]
    - Problem: The HTML report header says "Contents" instead of "Frankenstein". The title was likely extracted from a table-of-contents page rather than the book's actual title.
    - Location: `src/ingestion/` or title extraction in the ingestion pipeline.

### LOW

12. **Pronunciation type/context fields all null**
    - Problem: All 206 pronunciation entries have `type: null` and `context: null`, losing categorization info.
    - Location: `src/pipeline/pronunciation/`

13. **Cornelius Agrippa and Werter as character entries**
    - Problem: Historical/literary references extracted as characters. Agrippa is an alchemist Victor reads about; Werter is from a book the Creature reads. Neither appears as an actual character.
    - Low priority — doesn't significantly affect narrator preparation.

14. **Creature missing "the daemon" alias**
    - Problem: The Creature's aliases include "the monster", "the fiend", "the wretch", "the being", "the thing" but NOT "the daemon" — a frequently used descriptor in the text.
    - Location: `src/pipeline/character_extraction_v2/main_cast.py`

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |

## Fix History
- Attempt 2 (Fix 1): Expanded competitive alias verification context from first-5-chapters (3000 chars) to ALL chapters (10000 chars)
  - Root cause: `main_cast.py:competitive_verify_aliases:1344-1347` used only first 5 chapters as context, which for Frankenstein (28 chapters) only covered Walton's letters. The Creature doesn't appear until chapter 5+, so all Creature aliases ("daemon", "monster") were rejected, and the false "the Creature → Turkish merchant" alias was accepted because neither character appeared in the limited context.
  - Smoke test: PASS — verified competitive context now uses all chapters; confirmed Turkish merchant/Creature conflict correctly split
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 2 (Fix 2): Added occupation titles (merchant, magistrate, officer, soldier) to `human_descriptors` in `_split_semantic_conflicts` as safety net
  - These are universally human occupation titles; prevents creature terms from being accepted as aliases of human-titled characters even if competitive voting fails
  - Smoke test: PASS — "the Turkish merchant" + "the Creature" conflict now detected and split
  - Modified: `src/agents/characters.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | CRITICAL #1: Creature/Turkish merchant merge | `src/pipeline/character_extraction_v2/main_cast.py`, `src/agents/characters.py` | Fixed — Creature now standalone with 103 mentions |
| 2 | CRITICAL #2: Alphonse missing | (not addressed by fix) | No change |
| 3 | CRITICAL #1: Victor/Frankenstein protagonist split | `src/agents/config.py`, `src/cli.py`, `src/agents/characters.py` | Pending verification |
| 3 | CRITICAL #2: Alphonse missing | `src/agents/characters.py` | Pending verification |
| 3 | HIGH #3: Creature "De Lacey" false alias | `src/agents/characters.py` | Pending verification |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient for chapter sizes)
- No retries recorded (all stages: 0 retries)
- Stage timings: Structure 547s, Characters 2586s, Summaries (profiles?) 1338s, Summaries 2304s, Pronunciation 1104s
- No obvious config issues — the character extraction issues are algorithmic, not config-related

## Pipeline Notes (Attempt 2)
- Runtime: 136m 53s | 424 LLM calls | 805,453 tokens
- 21 characters found (6 added via reconciliation)
- The creature: standalone ✓ (aliases: "the monster", "the fiend" — 103 mentions)
- Semantic conflict detection fired: "old man (De Lacey)" correctly NOT aliased to "The creature" ✓
- Robert Walton: epistolary narrator detected ✓
- Alphonse's relational aliases ("Victor's father", "the narrator's father") BLOCKED by co-occurrence check — needs evaluation
- Structure: 27 boundaries found vs 31 expected (TOC mismatch — ongoing issue)
- LLM marker proposer returned non-list (dict) for all 30 structure proposers — recurring issue

## Priority Fix Guidance for Attempt 3

The **primary blockers** preventing score improvement are:

1. **Victor/Frankenstein split** (CRITICAL #1) — This is the highest-impact fix. The protagonist being split into two supporting cast entries with no aliases is the single biggest scoring drag across Characters, Profiles, and Identity Resolution. Both entries are in `supporting_*` IDs, meaning main_cast pipeline completely missed Victor Frankenstein.

2. **Alphonse missing** (CRITICAL #2) — Second attempt, still missing. Pipeline notes say co-occurrence check blocks his relational aliases. The co-occurrence validation may need a carve-out for characters primarily referenced via family terms in first-person narratives.

3. **Creature "De Lacey" false alias** (HIGH #3) — Quick alias cleanup that would boost both Identity Resolution and Alias Grouping scores.

Focus on #1 and #2. If those are fixed, Character Extraction could jump from 5/10 to 7-8/10, which cascades into Profile improvements as well.

## Fix History (Attempt 3)

### Fix A: Alias Vote Threshold (Critical #1 enabler)
- **Root cause**: `consensus_merge_threshold = 0.67` caused 2/3 votes (ratio 0.6667) to fail by a tiny margin — effectively requiring unanimity (3/3) for 3 voters. The intended "2/3 supermajority" threshold was 0.6667 but the approximation 0.67 was used.
- **Fix**: Changed to `2/3` (Python expression = 0.6667...) in `src/agents/config.py` and `src/cli.py`
- **Impact**: "Victor Frankenstein" (2/3 YES votes) and "Victor" (2/3 YES votes) now pass as aliases for "The narrator" character extracted from summaries
- **Smoke test**: Verified threshold is now 0.666667 and 2/3 votes pass correctly
- **Files**: `src/agents/config.py`, `src/cli.py`

### Fix B: Narrator Placeholder Preservation (Critical #1)
- **Root cause**: Step 5.2 `_filter_narrator_variants` unconditionally removed any main cast character with "narrator" in canonical name, including "The narrator" (Victor) which was extracted by the LLM and had proper-name aliases
- **Fix**: Added `is_main_cast=True` parameter; when True, narrator placeholders with proper-name aliases (capitalized, non-placeholder) are KEPT instead of filtered
- **Files**: `src/agents/characters.py`

### Fix C: Narrator Placeholder Canonical Name Upgrade (Critical #1)
- **Root cause**: Even if "The narrator" was kept in main cast with alias "Victor Frankenstein", `_merge_lastname_aliases` (Step 5.5) would compare the CANONICAL NAME "The narrator" against supporting cast "Victor" and "Frankenstein" — finding no match. The canonical name needed to be the proper name for fragment merging to work.
- **Fix**: Added Step 5.2b: after filter, if a narrator placeholder has proper-name aliases, upgrade canonical_name to fullest alias. "The narrator" (alias "Victor Frankenstein") → canonical becomes "Victor Frankenstein". Then Step 5.5 merges supporting "Victor" (firstname) and "Frankenstein" (lastname) into this character.
- **Files**: `src/agents/characters.py`

### Fix D: Grounding Threshold (Critical #2 — Alphonse)
- **Root cause**: "Alphonse Frankenstein" appears only once in the raw text (he's called "my father" throughout). With `min_grounding_mentions=3`, his single mention was below threshold → filtered as hallucination.
- **Fix**: Lowered `min_grounding_mentions` default from 3 to 1 in `CharacterAgent.__init__`. Purpose of grounding is to catch 0-mention hallucinations; 1 mention confirms existence.
- **Files**: `src/agents/characters.py`

### Fix E: De Lacey False Alias (High #3)
- **Root cause**: `_merge_surname_into_family_descriptive` was looking for a descriptive "the X" character to host the bare surname "De Lacey". It skipped "the old man" (already had "De Lacey" as alias) but continued iterating and found "The creature" whose description mentions "Felix", "father" etc. (because the Creature narrates about the De Lacey family). The `break` only fired on SUCCESSFUL merge, not on skip.
- **Fix**: When a "the X" character ALREADY has the surname as alias, mark the supporting surname char as consumed (`chars_to_remove.add(supp_idx)`) and `break` — preventing it from being merged into any other character.
- **Files**: `src/agents/characters.py`

### Also Kept: Kinship Term Carve-out (Pre-existing uncommitted change)
- In `main_cast.py`: kinship terms ("father", "mother", etc.) bypass co-occurrence check so they can reach the competitive vote
- This is a universal reference lexicon (kinship terms exist in all cultures/genres)
- Reverted: incorrect `post_corrections.merge_narrator_fragments` approach and corresponding `analyzer.py` changes

## Pipeline Notes (Attempt 3)
- Runtime: 140m 32s | 458 LLM calls | 874,774 tokens
- 23 characters found + 4 from reconciliation = 19 after deduplication/filtering
- Victor Frankenstein: MERGED as single character with aliases "Victor, Frankenstein" (55 mentions) ✓ — FIX A/B/C verified
- The creature: 112 mentions, aliases "the monster, the fiend" (NO "De Lacey" alias) ✓ — FIX E verified
- "the old man" has alias "the old man (De Lacey)" — correct (he is a De Lacey)
- Semantic conflict split fired: 2 pairs split ("the old man (De Lacey)" and "the old man" correctly NOT aliased to "the creature") ✓
- Book title still "Contents" (pre-existing issue #11)
- Stage timings: Structure 9m13s, Summaries 43m54s, Characters 29m42s, Profiles 32m59s, Pronunciation 18m55s
- Structure: 28 chapters found (vs 27 in attempt 2 — slight improvement)
- Alphonse: Not visible in preview; need evaluation to confirm if present

## Next Action
Evaluate attempt 3 output.
