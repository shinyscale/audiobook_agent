# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260228_220746/

## Pipeline Notes (Attempt 4)
- Total time: 127m 15s | 374 LLM calls | 685,688 tokens
- Characters: 21 found (was 19; F6 added 8 from summaries)
- **⚠️ Chapter Summaries: 0 LLM calls recorded** — summaries were likely CACHED from a prior run. This means Fix 2 (summarizer prompt change for proper names) may NOT have taken effect. Alphonse fix via summarizer may need to be verified separately.
- Fix 1 WORKING: Many Creature aliases correctly BLOCKED (De Lacey false alias not seen in summary; stop-word filter, cross-character conflict, absent-alias rules all firing)
- **⚠️ Over-blocking concern**: Valid Creature aliases also blocked — "the fiend", "the wretch", "the daemon", "the devil", "the thing" all blocked as "not found in any summary". If summaries were cached from pre-fix-2 run, they may not use these descriptors. Creature now only has "the being" and "the monster" as shown aliases.
- "the Turk": `No passages provided for the Turk, returning UNCERTAIN` — fate unclear, check JSON
- Competitive-all active: characters, structure, summaries all using 3-temperature consensus

## Latest Scores
- Structure Detection: 7.5/10 ✗
  - 28 elements detected (correct: 4 letters + 24 chapters)
  - Letter 1 title null → excluded from prologue display
  - Chapter titles all null (they're numbered "Chapter I" etc. in text — title detection misses these)
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 5/10
- Character Profiles: 4.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 6.83/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## What Improved from Attempt 2
- Victor Frankenstein is now a SINGLE entry (main_cast_1, 55 mentions) with aliases "Victor", "Frankenstein" ✓ — Fixes A/B/C worked
- Victor correctly marked as narrator ✓
- Three narrators correctly identified: Robert Walton, Victor Frankenstein, the creature ✓
- Beaufort no longer falsely merged with Caroline Beaufort ✓

## What REGRESSED from Attempt 2
- **The Turk was correctly a separate character in attempt 2** (0a5ef5ac589f, "the Turk") but is now GONE as a separate entry and instead appears as a FALSE ALIAS of the Creature ("the Turk", "the Turk (Safie's father)"). This is a regression.
- The Creature's alias list is WORSE: attempt 2 had correct aliases only ("the monster", "the fiend", "the wretch", "the being", "the thing"); attempt 3 added 3 false aliases ("De Lacey", "the Turk (Safie's father)", "the Turk") plus "the giant"
- **Fix E (De Lacey false alias) did NOT work** — Pipeline notes claimed "NO 'De Lacey' alias" but the actual JSON output shows it is still present. The smoke test during the fix phase did not catch this because the full pipeline produces different results than the partial test.

## Current Issues (Priority Order)

### CRITICAL

1. **The Creature has 3 FALSE aliases: "De Lacey", "the Turk (Safie's father)", "the Turk"** [Identity Resolution, Alias Grouping — REGRESSION]
   - Problem: main_cast_2 ("the creature") has these 3 completely wrong aliases in addition to its correct ones. The Creature is NOT a De Lacey, NOT the Turk. The Turk is Safie's father — a separate person. In attempt 2, "the Turk" was correctly a separate character (0a5ef5ac589f). Now it's been absorbed as a Creature alias.
   - Evidence: The De Lacey family (Felix, Agatha, old man) are observed by the Creature through a wall. The Turk (Safie's father) is a Turkish merchant who appears in the De Lacey backstory. Neither is the Creature.
   - ID pattern: `main_cast_2` → main cast pipeline
   - Root cause analysis: Fix E in attempt 3 targeted `_merge_surname_into_family_descriptive` but the false aliases may be injected at a DIFFERENT stage. Possible causes:
     - The main_cast LLM extraction itself may be returning these as aliases (LLM confusion from narrative proximity — the Creature narrates chapters 11-16 about the De Laceys and the Turk)
     - The competitive alias vote may be accepting them because the Creature co-occurs with these terms in its own narration
     - F6 reconciliation may be merging a separate "the Turk" character into the Creature
   - Fix approach: Need to trace WHERE these aliases enter the pipeline. Check: (a) raw LLM extraction output for the Creature, (b) competitive alias voting logs, (c) post-merge steps. The fix must happen at the correct stage.
   - **IMPORTANT**: Fix E's `_merge_surname_into_family_descriptive` change may still be correct but insufficient — the false aliases may enter through a different code path.

2. **Alphonse Frankenstein is STILL completely missing — 3rd consecutive attempt** [Completeness]
   - Problem: Victor's father does not appear in the 19-character list. This is the third attempt where he's absent despite Fix D lowering `min_grounding_mentions` from 3 to 1.
   - Evidence: Alphonse is a major character — sends letters, travels to care for Victor, takes him home from prison, dies of grief after Elizabeth's murder. He appears throughout.
   - Root cause: Fix D addressed grounding, but the issue may be UPSTREAM — the LLM may not extract "Alphonse Frankenstein" at all because:
     - He's referred to as "my father" throughout (first-person narration)
     - The name "Alphonse" appears rarely in the text
     - Supporting cast extraction may not look for relational references
   - Fix approach: This has been attempted 3 times. The same-layer fixes aren't working. **Escalation needed**: either (a) add a post-processing step that explicitly checks for family members referenced by relationship terms in first-person narratives, or (b) add Alphonse-style "relational character" detection to the prompt/extraction logic itself so the LLM specifically looks for characters referred to by relationship terms.
   - Files modified previously: `src/agents/characters.py` (grounding threshold) — didn't solve it
   - **Escalation flag**: Same issue, 3 attempts, same layer. Must try a fundamentally different approach.

### HIGH

3. **Fabricated relationships for major characters** [Profiles]
   - Problem: Multiple characters have relationships with people they never interact with. This is co-occurrence contamination.
   - Specific fabrications:
     - Victor → "the creature: employee" (should be "creation" or "creature", not employee)
     - Victor → "Felix De Lacey: acquaintance", "Agatha De Lacey: acquaintance", "Safie: acquaintance" — Victor NEVER meets the De Lacey family
     - Robert Walton → "Ernest: acquaintance" — they barely interact
     - Felix → "Agatha De Lacey: father" (WRONG — Felix is Agatha's BROTHER, the old man is their father)
     - Agatha → "Felix De Lacey: father" (WRONG — same error reversed)
     - Safie → "Beaufort: acquaintance", "Victor Frankenstein: acquaintance" — neither is true
     - Mr. Kirwin → "Victor Frankenstein: mentor" (wrong direction — Kirwin is the magistrate)
     - The Creature has NO relationships (should have: Victor Frankenstein as creator)
   - Location: `src/pipeline/character_extraction_v2/` — relationship extraction uses co-occurrence rather than explicit textual markers
   - Fix: Relationship extraction needs to prioritize explicit relationship words ("father", "brother", "creator", "friend") over mere co-occurrence in the same chapter.

4. **Physical descriptions missing for protagonists** [Profiles]
   - Problem: Only 6/19 characters (32%) have physical descriptions. Missing for all four leads: Victor Frankenstein, Elizabeth Lavenza, Henry Clerval, Robert Walton.
   - Evidence:
     - Victor is described as haggard, feverish, emaciated after his creation work; his eyes are dull and sunken
     - Elizabeth is described as having a celestial beauty, fair hair, blue eyes (in Shelley's 1831 edition)
     - Henry Clerval is described as having an expressive face full of benevolence
   - Characters WITH descriptions (correct): the creature ✓, the old man ✓, William ✓, M. Waldman ✓, M. Krempe ✓, Safie ✓
   - Location: `src/pipeline/character_extraction_v2/` — profile extraction stage
   - Fix: Profile extraction prompts may need to search harder for physical descriptions of first-person narrators (Victor, Walton) who describe themselves less explicitly.

5. **Caroline Beaufort / Caroline Frankenstein (Victor's mother) missing** [Completeness]
   - Problem: Victor's mother is a significant character in Chapters 1-3 but doesn't appear in the character list. She saves Elizabeth, raises the Frankenstein children, and dies of scarlet fever caught from nursing Elizabeth — her death is a pivotal plot point.
   - Evidence: Referred to as "my mother", "Caroline Beaufort", "Caroline Frankenstein" in the text.
   - Location: Same issue as Alphonse — relational references in first-person narration are not being extracted.
   - Fix: Part of the same "relational character detection" issue as Alphonse (#2).

### MEDIUM

6. **Structure: Letter 1 title not detected** [Structure]
   - Problem: First structure element has `title: null`. Should be "Letter 1". Only 3/4 letters classified as Prologue Materials.
   - Evidence: HTML shows "Prologue Materials" starting with "Prologue 1: Letter 2" — Letter 1 is missing from this section.
   - Location: `src/pipeline/chapter_detection/` — first structural marker not detected
   - Fix: Ensure the first boundary detects "Letter 1" heading.

7. **Supporting characters lack full canonical names** [Alias Grouping]
   - Problem: "William" should be "William Frankenstein" (supporting_0), "Ernest" should be "Ernest Frankenstein" (supporting_2). The text identifies them with surnames at least once.
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

8. **Pronunciation false positives** [Pronunciation]
   - Problem: Common English words flagged: "does", "than", "hero", "sympathised", "sympathise", "produce". "than" and "hero" have zero pronunciation ambiguity.
   - Evidence: 206 entries, ~6+ are unnecessary false positives.
   - Location: `src/pipeline/pronunciation/` — filtering logic

9. **All pronunciation type/context fields null** [Pronunciation]
   - Problem: All 206 entries have `type: null` and `context: null`, losing categorization information.
   - Location: `src/pipeline/pronunciation/`

10. **Book title displayed as "Contents"** [Presentation]
    - Problem: HTML header says "Contents" instead of "Frankenstein". Title extracted from table-of-contents page.
    - Location: `src/ingestion/` or title extraction

11. **"De Lacey" alias collision** [Alias Grouping]
    - Problem: "De Lacey" appears as alias for both the Creature (WRONG, see #1) and Felix De Lacey (correct).
    - Fix: Resolves when #1 is fixed.

### LOW

12. **Creature missing "the daemon" alias** [Alias Grouping]
    - Problem: "the daemon" is a frequently used descriptor for the Creature in the text but is not in its alias list.

13. **Cornelius Agrippa and Werter as character entries** [Completeness]
    - Problem: Historical/literary references (Agrippa is an alchemist Victor reads about; Werter is from a book the Creature reads) extracted as characters.
    - Low priority — doesn't significantly hurt narrator preparation.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED into Creature aliases. Alphonse still missing (3rd attempt). |

## Fix History
- Attempt 2 (Fix 1): Expanded competitive alias verification context from first-5-chapters (3000 chars) to ALL chapters (10000 chars)
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 2 (Fix 2): Added occupation titles (merchant, magistrate, officer, soldier) to `human_descriptors` in `_split_semantic_conflicts`
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix A): Changed `consensus_merge_threshold` from 0.67 to `2/3` to allow 2/3 supermajority votes to pass
  - Modified: `src/agents/config.py`, `src/cli.py`

- Attempt 3 (Fix B): Narrator placeholder preservation — `_filter_narrator_variants` now keeps main_cast narrators with proper-name aliases
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix C): Narrator placeholder canonical name upgrade — "The narrator" with alias "Victor Frankenstein" gets canonical name upgraded
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix D): Lowered `min_grounding_mentions` from 3 to 1 — DID NOT SOLVE Alphonse issue
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix E): `_merge_surname_into_family_descriptive` — mark surname consumed when "the X" already has it as alias — DID NOT FULLY WORK for De Lacey
  - Modified: `src/agents/characters.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Creature/Turkish merchant merge | `main_cast.py`, `characters.py` | Fixed ✓ |
| 2 | Alphonse missing | (not addressed) | No change |
| 3 | Victor/Frankenstein split | `config.py`, `cli.py`, `characters.py` | Fixed ✓ |
| 3 | Alphonse missing | `characters.py` (grounding threshold) | No change — grounding wasn't root cause |
| 3 | Creature De Lacey alias | `characters.py` (_merge_surname) | No change — aliases still present, possibly enter via different code path |
| 3 | (Side effect) Turk regression | Unknown — was separate in attempt 2, now merged as Creature alias | Regression |

**Escalation needed:** Alphonse has been attempted 3 times via same-layer fixes (`characters.py`). Must try upstream approach.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient for chapter sizes)
- No retries recorded (all stages: 0 retries)
- Stage timings: Structure 9m13s, Summaries 43m54s, Characters 29m42s, Profiles 32m59s, Pronunciation 18m55s
- Total: 140m 32s, 458 LLM calls, 874,774 tokens

## Priority Fix Guidance for Attempt 4

### Fix Priority 1: Creature False Aliases (CRITICAL #1 — regression fix)

The Creature's false aliases ("De Lacey", "the Turk", "the Turk (Safie's father)") are the highest-impact issue. They affect Identity Resolution AND Alias Grouping AND are a regression from attempt 2 where "the Turk" was correctly separate.

**Investigation steps:**
1. Trace where these aliases enter the pipeline. Check the raw LLM output from main_cast extraction for the Creature's initial alias list
2. Check whether "the Turk" is being extracted as a separate character and then merged into the Creature during post-processing
3. Check competitive alias voting logs — are these aliases being voted on and accepted?
4. If the LLM itself is proposing these aliases, the fix is in the main_cast extraction prompt (add guidance about narrator vs. subject confusion)
5. If post-processing is merging them, fix the specific merge step

**Key insight:** The Creature NARRATES about the De Laceys and the Turk in chapters 11-16. A naive extraction that associates frequently-mentioned names with the narrator/speaker will incorrectly alias them.

### Fix Priority 2: Alphonse Missing (CRITICAL #2 — escalation required)

Three attempts have failed. The grounding threshold fix didn't work because the issue is upstream — the LLM never extracts Alphonse in the first place. He's referred to as "my father" throughout the first-person narration.

**Escalation approaches:**
- Add explicit guidance in the character extraction prompt to look for characters referenced primarily by relationship terms ("my father", "his mother", "my cousin")
- Add a post-extraction pass that scans for proper names co-occurring with relationship terms and creates character entries
- Check if the summary agent mentions Alphonse — if so, F6 reconciliation should pick him up

### Fix Priority 3: Profile Fabrication (HIGH #3)

The relationship extraction is clearly using co-occurrence rather than explicit textual markers. Victor is listed as "acquaintance" of the De Lacey family (never meets them). Felix is listed as Agatha's "father" (he's her brother). The Creature has zero relationships (should have Victor as creator).

This is a profile-stage issue, likely in `src/pipeline/character_extraction_v2/` profile extraction prompts.

### Do NOT attempt to fix summaries (8.5/10) — they pass threshold.

## Next Action
Re-run analysis to verify fixes.

---

## Fix History (continued)

- Attempt 4 (Fix 1): Three algorithmic fixes to `verify_aliases()` in `main_cast.py`:
  - **Fix A (shared_parts stop-words)**: Filter stop words ("the", "a", "an", etc.) from `shared_parts` calculation in the non-co-occurrence escape hatch. Root cause: "the creature" and "the Turk" shared "the" as a name part → alias was ALLOWED despite no co-occurrence. After fix: canonical_parts={"creature"}, alias_parts={"turk"} → shared_parts={} → BLOCKED.
  - **Fix B (cross-character conflict)**: New Rule 3 — if an alias is already the name or alias of a DIFFERENT character in the cast, block it. Root cause: "De Lacey" co-occurs with "the creature" in summaries (creature narrates about De Laceys) and passes co-occurrence check. After fix: "De Lacey" is Felix De Lacey's alias → blocked for creature.
  - **Fix C (alias absent from summaries)**: New Rule 2a — if alias_found=False (alias not in any summary verbatim), block it as hallucinated. Root cause: "the Turk (Safie's father)" with parentheses doesn't appear in any summary → old code allowed it through because it skipped the `if canonical_found and alias_found:` block entirely.
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - Smoke test: All 44 V2 tests PASS

- Attempt 4 (Fix 2): Upstream summarizer fix for Alphonse missing — changed the "use relationship terms only" rule to "use proper names when stated in the text". Root cause: Alphonse appears only once in source text (as letter signature "Alphonse Frankenstein"), summaries used "his father" instead of the proper name, so F6 reconciliation never found him. New prompt: "Use characters' proper names when stated in the text (e.g., if text names 'his father John', write 'John' not 'his father')." Will cause summaries to include "Alphonse Frankenstein" in the chapter with his letter signature, enabling F6 to extract him.
  - Modified: `src/pipeline/chapter_summary/summarizer.py` (all 3 prompts: CHUNK_SUMMARY_PROMPT, CONSOLIDATE_PROMPT, SINGLE_CHAPTER_PROMPT)
  - Universality: ✓ Universal — helps any book where characters are named once but referred to by relationship terms throughout
