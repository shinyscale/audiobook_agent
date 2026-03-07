# Oracle Loop Escalation: frankenstein

## Status: Requires Human Investigation

**Generated:** 2026-03-02 05:28:49
**Text:** frankenstein
**Attempt:** 15
**Current Score:** 8.20
**Stuck Duration:** 4 consecutive attempts with score ±0.15

---

## Why This Escalation Was Triggered

The oracle loop has been stuck on the same score (±0.15) for 4 consecutive attempts. This indicates:

1. The fixes being attempted are not addressing the root cause
2. The root cause may be in a code layer the loop hasn't been examining
3. Human investigation is needed to identify blind spots

---

## Recent Score History

| Attempt | Score |
|---------|-------|
| 12 | 8.33 |
| 13 | 8.28 |
| 14 | 8.28 |
| 15 | 8.20 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### CRITICAL

*(none)*

### HIGH

1. **"friend" label misapplied to antagonistic/murderous relationships** [Profiles - Relationships]
   - Problem: `verify_relationships_from_text()` upgraded "associated" to "friend" for 4 character pairs where "friend" appears contextually but does NOT describe their relationship:
     - Victor→Creature: "friend" (should be "creator")
     - Creature→Victor: "friend" (should be "creation")
     - William→Creature: "friend" (Creature murders William)
     - Creature→Justine: "friend" (Creature frames Justine for murder)
   - Root cause: The word "friend" is very common in Frankenstein's text. Victor discusses wanting a "friend", Walton seeks a "friend", the Creature wants a "companion/friend". The keyword scan detects "friend" in co-mention windows with the Creature and upgrades the label, but the word describes a DESIRE, not the actual relationship.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text()`, specifically the non-family term matching logic added in attempt 15
   - Fix approach: **Increase the evidence threshold for "friend" upgrades.** Currently any non-zero count upgrades "associated". Require a minimum of 5+ co-mention hits for "friend" to upgrade (Victor↔Henry had 9 hits which is genuine; Victor↔Creature likely had 2-3 which is contextual noise). Alternatively, require "friend" to appear in a possessive/direct pattern ("his friend X", "my friend X") rather than just co-occurring in a window.
   - Impact: This is the PRIMARY new regression preventing Profiles from reaching 8.0.

2. **De Lacey father↔children labeled "sibling"** [Profiles - Relationships]
   - Problem: The Old Man (De Lacey) is Felix and Agatha's father. All 4 relationships (Old Man↔Felix, Old Man↔Agatha) are labeled "sibling".
   - Root cause: Two-step failure:
     1. `verify_relationships_from_text()` finds "father" keyword near both Old Man and Felix/Agatha. It upgrades BOTH directions to "father" (Old Man→Felix: "father" AND Felix→Old Man: "father").
     2. `fix_bidirectional_parent_labels()` sees bidirectional "parent" labels + shared surname "lacey" → converts to "sibling".
   - The fundamental issue: text keyword matching is direction-unaware. When "Felix's father" appears in text, both characters are nearby, so both directions get "father". But only Old Man→Felix should be "father"; Felix→Old Man should be "child"/"son".
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text()` and `fix_bidirectional_parent_labels()`
   - Fix approach: Make `verify_relationships_from_text()` direction-aware for asymmetric labels. When "father" is detected:
     - Check which character's name appears BEFORE the keyword: "Felix's father" → Felix is the child, the matched character is the parent
     - OR: If bidirectional "father" is detected AND characters share a surname, use age/generational heuristic (character with "old man" or senior indicators → parent; others → child)
     - OR simpler: In `fix_bidirectional_parent_labels()`, when detecting shared surname and bidirectional parent labels, check if either character's name contains generational markers ("old man", "senior", "father") and assign parent/child accordingly instead of defaulting to "sibling"

3. **69% of relationships still "associated"** [Profiles - Relationships]
   - Problem: 59/86 relationships are "associated". Key missing specific labels:
     - Victor↔Elizabeth: "associated" → should be "fiancée"/"romantic interest" (they're betrothed and marry)
     - Walton↔Margaret: "associated" → should be "sibling" (brother/sister, the letter framing)
     - Ernest↔Victor: "associated" → should be "sibling" (brothers)
     - Safie↔Felix: "associated" → should be "romantic interest"/"fiancée" (they fall in love)
   - Root cause: These character pairs either don't co-mention with relationship keywords in the summaries (Walton writes TO Margaret so both names don't appear together near "sister"), or the LLM profiler generates "associated" as default.
   - Location: `src/pipeline/character_profiling/post_corrections.py`, `src/analyzer.py` (_generate_character_profile prompt)
   - Fix approach: This is a LOWER priority than #1 and #2. Fixing the wrong "friend" labels and De Lacey family would bring Profiles to ~7.5-8.0. The "associated" epidemic can be addressed incrementally.

### MEDIUM

4. **Elizabeth alias "more than sister"** [Character Extraction - Alias Grouping]
   - Status: NOT PRESENT in this run. Elizabeth's only alias is "Elizabeth". This issue appears resolved (possibly by LLM variability).

5. **Alphonse Frankenstein absent (LLM variability)** [Character Extraction - Completeness]
   - Problem: Victor's father, present in attempt 12 with 10 mentions, absent in attempts 13-15. No code changes to extraction.
   - Do NOT attempt a code fix — LLM variability.

6. **Victor's misattributed example quotes** [Profiles - Voice Guidance]
   - Problem: Victor's first example quote is "I have no friend, Margaret" — this is WALTON's line from Letter 1. Victor wouldn't address "Margaret".
   - Accept as LLM limitation. Do NOT attempt to fix.

7. **Creature physical description very sparse** [Profiles - Physical Description]
   - Problem: "Towering; grotesque; unearthly ugliness; inhuman speed." — the text describes the Creature in much more detail (8 feet, yellow watery eyes, black lips, dun-white skin, shriveled complexion, lustrous black hair).
   - Accept as LLM limitation. Minor impact on score.

8. **Victor has no physical description** [Profiles - Physical Description]
   - Problem: `physical_description: None` for the protagonist. The text describes Victor as increasingly ill/wasted throughout the narrative.
   - Accept as LLM limitation.

### LOW

9. Ernest and Margaret lack full canonical names (Ernest Frankenstein, Margaret Walton Saville).
10. Letter 1 title null in JSON (displayed correctly as "Prologue 1" in HTML).
11. Creature role "supporting" — debatable; is the co-protagonist/deuteragonist.
12. Victor's verbal_tics includes empty string "".
13. 6 pronunciation entries missing IPA (desert, lead, produce, and 3 others).
14. Henry→William: "friend" — not necessarily wrong but they barely interact. Minor.
15. Safie→Beaufort: "acquaintance" — Safie and Beaufort are connected through their fathers' story but likely never met.
16. Cornelius Agrippa labels "subject of dismissal"/"subject of respectful acknowledgment" — creative but unusual for narrator prep.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED. |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk separated ✓. Profiles (5/10) now primary blocker. |

---

## Fix History (Recent Attempts)

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

- Attempt 4 (Fix 1): Three algorithmic fixes to `verify_aliases()` in `main_cast.py`:
  - **Fix A (shared_parts stop-words)**: Filter stop words from `shared_parts` calculation
  - **Fix B (cross-character conflict)**: New Rule 3 — block alias if already name/alias of DIFFERENT character
  - **Fix C (alias absent from summaries)**: New Rule 2a — block alias if not found in any summary verbatim
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 4 (Fix 2): Upstream summarizer fix for Alphonse — changed prompt from "use relationship terms only" to "use proper names when stated in text"
  - Modified: `src/pipeline/chapter_summary/summarizer.py`

- Attempt 5 (Fix 1): Profile relationships — changed prompt to require EXPLICIT textual evidence for relationships; removed "acquaintance"/"unknown" fallback labels; removed "MUST use these exact names" obligation from character_names_text; updated summary evidence instructions.
  - Modified: `src/analyzer.py` (lines ~2764-2868)

- Attempt 5 (Fix 2): Creature false aliases "De Lacey" and "the blind father (De Lacey)"
  - Fix A: Extend `profile_names` to include surname-only fragments
  - Fix B: New Rule 3b — block aliases whose parenthetical content references another character
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 5 (Fix 3): Chapter titles null for Arabic-numbered chapters
  - Modified: `src/pipeline/chapter_detection/consensus.py`

- Attempt 6 (Fix 1): Monster/dæmon false split — F6 ligature normalization
  - Modified: `src/analyzer.py` (_normalize_descriptor: add æ→ae, œ→oe normalization)

- Attempt 6 (Fix 2): Turkish merchant/old man false merge — canonical base form in co-occurrence check
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py` (verify_aliases canonical_base)

- Attempt 6 (Fix 3): Profile relationships — contradictory bidirectional removal
  - Modified: `src/pipeline/character_profiling/post_corrections.py` (remove_contradictory_relationships)
  - OVER-FIRED — caused regression

- Attempt 6 (Fix 4): Pronunciation false positives — British -ise/-ised forms, -ful suffix, "than"
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`

- Attempt 7 (Fix 1): Symmetric relationship labels — added missing labels to _SYMMETRIC_RELATIONSHIPS
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - PARTIAL — fix correct but LLM didn't regenerate the key relationships

- Attempt 7 (Fix 2): Alias surname fragments — rewrote profile_names to include fragments from BOTH canonical names and aliases
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - WORKED ✓ — De Lacey blocked from creature

- Attempt 7 (Fix 3): Title pattern expansion — added Professor, Captain, Lord, etc. to _are_different_titled_people
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - WORKED ✓ — Professor Krempe recognized as different from M. Waldman

- Attempt 7 (Fix 4): F6 pronoun filter — reject single-letter names and common pronouns
  - Modified: `src/analyzer.py`
  - WORKED ✓ — "I" no longer extracted

- Attempt 8 (Fix 1): Summary-based relationship enrichment for zero-relationship characters
  - New method `enrich_zero_relationships_from_summaries` in `OutputCharacterCorrector`
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `src/analyzer.py`
  - PARTIALLY WORKED — added Walton↔Margaret "sister" ✓ but also added ~6 wrong relationships ✗

- Attempt 8 (Fix 2): Bidirectional parent label → sibling conversion
  - New method `fix_bidirectional_parent_labels` in `OutputCharacterCorrector`
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - DID NOT WORK — ran before verify_relationships_from_text which overwrote it

- Attempt 8 (Fix 3): Book title "Contents" fallback to filename
  - Modified: `src/ingestion/txt.py`
  - WORKED ✓

- Attempt 8 (Fix 4): Letter 1 null title → prologue classification
  - Modified: `src/export/html_report.py`
  - WORKED ✓

- Attempt 9 (Fix 1): Reorder post-corrections: move `fix_bidirectional_parent_labels` to run LAST (after `verify_relationships_from_text` and `reject_unfounded_familial_labels`)
  - Modified: `src/pipeline/character_profiling/post_corrections.py` — `run_all()` order
  - WORKED ✓ — Felix↔Agatha and Victor↔William now "sibling"

- Attempt 9 (Fix 2): Remove `enrich_zero_relationships_from_summaries` from `run_all()` (method preserved but not called)
  - Modified: `src/pipeline/character_profiling/post_corrections.py` — `run_all()` order
  - WORKED ✓ — all wrong enrichment relationships removed, Safie's "father" labels not re-introduced

- Attempt 10 (Fix 1): Creature synonym alias recovery — `_recover_creature_synonym_aliases()` in CharacterAgent
  - Modified: `src/agents/characters.py`, `tests/test_character_extraction_v2.py`
  - **WORKED ✓** — "the monster" now has aliases: "the creature", "the fiend", "the wretch", "the dæmon", "the being"

---

## Code Analysis

### Files Modified During Fix Attempts (last 7 days)

```

```

### Files NOT Modified (Potential Blind Spots)

These key pipeline files have NOT been touched during fix attempts. The bug may be here:

```
src/ingestion/base.py
src/ingestion/refine.py
src/pipeline/chapter_detection/profiler.py
src/pipeline/chapter_detection/proposers/regex.py
src/pipeline/chapter_detection/proposers/llm.py
src/pipeline/chapter_detection/validator.py
src/pipeline/chapter_detection/consensus.py
src/pipeline/chapter_detection/pipeline.py
src/agents/structure.py
src/analyzer.py
```

**IMPORTANT:** When fixes in one layer don't work, the bug is often in an upstream layer:
- If `consensus.py` fixes don't work → check `profiler.py`, `proposers/`, or `ingestion/`
- If `character_extraction` fixes don't work → check `ingestion/` text normalization
- If structure detection fails → check if ingestion is destroying formatting

---

## Recommended Investigation Steps

1. **Check data flow from ingestion to detection:**
   ```bash
   # Verify source text has expected patterns
   grep -n "^[[:space:]]*V[[:space:]]*$" Test_Texts/frankenstein.txt

   # Check what ingestion does to the text
   LOG_LEVEL=DEBUG python -c "
   from src.ingestion import ingest_document
   text = ingest_document('Test_Texts/frankenstein.txt')
   # Check if patterns survive
   import re
   centered = re.findall(r'^\s{10,}[IVXLC]+\s*$', text, re.MULTILINE)
   print(f'Centered roman numerals after ingestion: {len(centered)}')
   print(centered[:5])
   "
   ```

2. **Run isolated pipeline tests:**
   ```bash
   # Test structure detection in isolation
   python -c "
   from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
   from src.pipeline.llm import LLMClient, LLMConfig

   with open('Test_Texts/frankenstein.txt', 'r') as f:
       text = f.read()

   config = LLMConfig.ollama(model='qwen3:4b-instruct')
   pipeline = ChapterDetectionPipeline(llm_client=LLMClient(config))
   result = pipeline.run(text)

   for ch in result.chapters:
       print(f'{ch.index}: {ch.title}, {ch.word_count} words')
   "
   ```

3. **Compare isolated test vs full CLI:**
   - If isolated test passes but CLI fails, bug is in ingestion or agent layer
   - If both fail, bug is in the pipeline itself

4. **Add diagnostic logging to blind spot files:**
   - Add logging to ingestion showing text patterns before/after normalization
   - Add logging to profiler showing TOC detection and front_matter_end

---

## State Files for Reference

- `oracle-loop/state/EVALUATION_STATE.md` - Full evaluation state
- `oracle-loop/state/manifest.json` - Test manifest
- `oracle-loop/state/checkpoints.json` - Checkpoint history
- `oracle-loop/logs/` - Recent iteration logs

---

## Resolution

Once the root cause is identified and fixed:

1. Update this PRD with the resolution
2. Restart the oracle loop: `cd oracle-loop && ./oracle-loop.sh`
3. The loop will continue from where it left off

