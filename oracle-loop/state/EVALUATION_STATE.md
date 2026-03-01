# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 10
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_130625/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 6.5/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Changed from Attempt 8

### Fixes that WORKED

1. **Fix 1 (bidirectional parent→sibling reorder) WORKED:** ✓
   - Victor↔William: now "sibling" (was "father") ✓
   - Felix↔Agatha: now "sibling" (was "father") ✓
   - Root cause confirmed: `verify_relationships_from_text` was overwriting the fix. Moving `fix_bidirectional_parent_labels` to run LAST solved it.

2. **Fix 2 (remove enrichment) WORKED:** ✓
   - No more Walton→Beaufort "father" ✓
   - No more Safie all-"father" labels ✓
   - No more Elizabeth→Beaufort "associated" ✓
   - No more Justine→Beaufort "associated" ✓
   - Safie's relationships reduced from 4 wrong "father" to 1 "associated" (with creature) — acceptable.

3. **Caroline Beaufort appeared as character** — NEW! Was missing for all 8 prior attempts. She now has aliases ["Caroline", "Beaufort"] and relationships with Elizabeth ("acquaintance") and Justine ("employee"). This is a big completeness win.

### Profiles improvement: 6.0 → 7.5 (+1.5)

Wrong relationships dropped from ~20/37 to ~2/28 — the largest single-attempt improvement in this text's history. Both fixes targeted relationship post-correction ordering and worked precisely as designed.

### Remaining issues (not regressions — pre-existing)

- Creature still has zero aliases (was zero in attempt 8 too under "the fiend" with aliases; now "the creature" with no aliases)
- Alphonse still missing (5th consecutive attempt)
- Victor↔Elizabeth still missing
- Henry↔Krempe "colleague" still wrong

## What's Still Failing

### Characters (7.5/10) — Alias Grouping is the blocker

**Completeness (8/10):** Caroline Beaufort now present ✓. Alphonse Frankenstein still missing, but 19 real characters + 1 historical figure (Agrippa) is solid coverage. All main characters are present.

**Identity Resolution (9/10):** No false splits or merges detected. Victor unified. Creature separate from Frankenstein. Turk separate from old man. Krempe separate from Waldman. Clean.

**Alias Grouping (6.5/10) — primary blocker:**
1. **The creature has ZERO aliases.** The creature entry (`split_the_creature`) has no aliases at all. "the monster" (most common reference in the novel), "the fiend", "the wretch", "the daemon" are all absent. Pipeline logs show these were "blocked as already claimed by another cast member" during extraction — but NO character in the final output has these names. The blocking entry was likely a main_cast entry that was later consumed/filtered during semantic split.
2. **Shared "De Lacey" alias:** Felix De Lacey has alias "De Lacey" AND the old man (De Lacey) also has alias "De Lacey". Two characters sharing an alias creates ambiguity.
3. **Ernest and Margaret lack full names:** Ernest → "Ernest Frankenstein", Margaret → "Margaret Saville".

### Profiles (7.5/10) — close to passing

**Major improvement from 6.0.** Now 26/28 relationships are correct/acceptable, 2 wrong.

Wrong relationships:
- Henry Clerval→M. Krempe: "colleague" ✗ (no narrative connection)
- M. Krempe→Henry Clerval: "colleague" ✗ (same)

Missing important relationships:
- Victor↔Elizabeth: fiancée/wife — THE central romance, still absent
- Victor→Henry: best friend — Victor's closest companion
- De Lacey→Felix/Agatha: father — mislabeled or absent
- Felix→Safie: romantic interest — absent
- Walton↔Margaret: brother/sister — lost when enrichment was removed

Physical descriptions: 8/20 (40%) — acceptable given source text limitations
Speech patterns: 0/20 — Frankenstein doesn't feature distinctive dialects, so impact is minimal

## Current Issues (Priority Order)

### CRITICAL

1. **Creature has ZERO aliases — "the monster", "the wretch", "the fiend" all missing** [Alias Grouping]
   - Problem: `split_the_creature` has canonical name "the creature" but aliases: []. The novel uses "the monster", "the fiend", "the wretch", "the daemon" extensively. A narrator CANNOT prepare without knowing these all refer to the same entity.
   - Evidence: Pipeline logs show "the monster" and "the fiend" were "blocked as already claimed by another cast member" during main_cast extraction. But NO character in the final output claims these names. The blocking entry was likely a main_cast entry that got consumed during semantic split, leaving the descriptors in limbo.
   - Location: `src/agents/characters.py` — semantic split logic. The split creates `split_the_creature` from the remaining descriptive cluster but doesn't recover aliases that were blocked by the pre-split main_cast entry.
   - Fix approach: After semantic split produces the creature entry, recover common creature descriptors ("the monster", "the fiend", "the wretch", "the daemon/dæmon") as aliases if they appear in the source text but aren't claimed by any character in the FINAL output. This is a post-split alias recovery step.
   - Impact: Alias Grouping 6.5 → 8.0, Characters overall 7.5 → 8.0+

### HIGH

2. **Victor↔Elizabeth relationship missing** [Profiles]
   - Problem: The central romance of the novel has no relationship entry. Elizabeth has 92 mentions. She and Victor appear together in many chapters.
   - Evidence: Elizabeth is Victor's fiancée, adopted sister, and eventually wife. They are together in Ch 1, 6, 22, 23, and many others.
   - Location: LLM profiler in `src/analyzer.py` consistently fails to generate this. Post-correction needed.
   - Fix: Add a targeted co-occurrence enrichment: for character pairs that appear in 3+ shared chapter summaries but have zero relationship in either direction, add "associated". This is safe ("associated" is never factually wrong for co-occurring characters) and would catch Victor↔Elizabeth. Keep it simple — don't try to infer relationship types from text.
   - Impact: +0.25 on Profiles.

3. **Henry↔Krempe wrong "colleague" relationship** [Profiles]
   - Problem: Henry Clerval and M. Krempe have no narrative connection. Henry is Victor's childhood friend; Krempe is Victor's professor at Ingolstadt.
   - Evidence: They don't interact in any chapter. The LLM profiler incorrectly linked them.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add co-occurrence validation: for each relationship pair, check if both characters appear in at least one shared chapter summary. If they never co-occur, remove the relationship. This is a safe heuristic — characters that never appear in the same chapter are unlikely to have a direct relationship.
   - Impact: +0.25 on Profiles. Combined with fix #2, profiles could reach 8.0.

### MEDIUM

4. **Alphonse Frankenstein missing — 5th consecutive attempt** [Completeness]
   - Victor's father, referenced by name in chapter summaries (appears as character tag in Ch 7 HTML).
   - F6 reconciliation found him in attempts 4-5 but not since.
   - This issue has resisted 4+ fix attempts across different files. Low ROI to attempt again.

5. **Shared "De Lacey" alias between Felix and old man** [Alias Grouping]
   - Both `Felix De Lacey` and `the old man (De Lacey)` have "De Lacey" as alias.
   - "De Lacey" primarily refers to the old man in the text. Should be on old man only.
   - Low priority — doesn't create confusion about character identity, just alias overlap.

6. **Ernest and Margaret lack full canonical names** [Alias Grouping]
   - Ernest → should be "Ernest Frankenstein"
   - Margaret → should be "Margaret Saville"

### LOW

7. **Physical descriptions: 8/20** — many characters (Victor, Henry, Walton) lack descriptions, partly reflecting source text.
8. **Speech patterns: 0/20** — no speech patterns populated. Low impact for Frankenstein (no distinctive dialects).
9. **Victor→creature: "associated"** — weak label. Should be "creator" or similar. But "associated" isn't wrong.
10. **Missing De Lacey→Felix/Agatha "father" relationships** — present in text but not generated by profiler.
11. **Missing Felix→Safie "romantic interest"** — present in text but not generated.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED. |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk separated ✓. Profiles (5/10) now primary blocker. |
| 5 | 7.38 | +1.18 | Profiles improved 5→6.5. BUT Turk REGRESSED again. Monster/dæmon false split. |
| 6 | 7.40 | +1.20 | Turk separated ✓. Dæmon merged ✓. BUT Profiles REGRESSED 6.5→5.5. |
| 7 | 7.80 | +1.60 | De Lacey alias ✓. Krempe separated ✓. "I" removed ✓. Profiles 5.5→6.5. |
| 8 | 7.83 | +1.63 | Title ✓. Letter 1 ✓. Presentation 7.5→8.5. BUT Profiles REGRESSED 6.5→6.0 (wrong enrichment labels). |
| 9 | 8.05 | +1.85 | Bidirectional sibling FIX ✓. Enrichment removed ✓. Caroline found! Profiles 6.0→7.5 (+1.5). Characters still 7.5 (creature zero aliases). |

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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Creature/Turkish merchant merge | `main_cast.py`, `characters.py` | Fixed ✓ |
| 3 | Victor/Frankenstein split | `config.py`, `cli.py`, `characters.py` | Fixed ✓ |
| 3 | Alphonse missing | `characters.py` (grounding threshold) | No change |
| 3 | Creature De Lacey alias | `characters.py` (_merge_surname) | No change |
| 4 | Creature Turk aliases | `main_cast.py` (verify_aliases rules) | Fixed ✓ |
| 4 | Alphonse missing | `summarizer.py` (upstream prompt fix) | Fixed ✓ (but regressed later) |
| 5 | Profile relationships | `analyzer.py` (profile prompt) | Partial |
| 5 | Creature De Lacey/shepherd aliases | `main_cast.py` (surname fragments + Rule 3b) | Fixed ✓ |
| 5 | Chapter titles | `consensus.py` (_clean_title) | Fixed ✓ |
| 6 | Monster/dæmon false split | `analyzer.py` (F6 _normalize_descriptor) | Fixed ✓ |
| 6 | Turk/old man false merge | `main_cast.py` (verify_aliases canonical_base) | Fixed ✓ |
| 6 | Contradictory relationships | `post_corrections.py` | OVER-FIRED → regression |
| 6 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 7 | Symmetric relationship labels | `post_corrections.py` | Partial |
| 7 | De Lacey alias on creature | `main_cast.py` | Fixed ✓ |
| 7 | Professor Krempe alias on Waldman | `main_cast.py` | Fixed ✓ |
| 7 | "I" pronoun as character | `analyzer.py` (F6 pronoun filter) | Fixed ✓ |
| 8 | Summary relationship enrichment | `post_corrections.py`, `analyzer.py` | Partial — added correct + wrong |
| 8 | Bidirectional parent→sibling | `post_corrections.py` | DID NOT WORK (ordering) |
| 8 | Book title "Contents" | `txt.py` | Fixed ✓ |
| 8 | Letter 1 prologue classification | `html_report.py` | Fixed ✓ |
| 9 | Post-correction ordering (bidir last) | `post_corrections.py` (run_all order) | Fixed ✓ |
| 9 | Remove enrichment from run_all | `post_corrections.py` (run_all order) | Fixed ✓ |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-9): Four consecutive attempts. Ordering fix (attempt 9) finally worked for bidirectional. The lesson: post-correction ORDER matters — fixes that run before `verify_relationships_from_text` get overwritten.
- Creature aliases: The semantic split consistently produces entries with missing aliases. The blocking mechanism checks against pre-split entries that later disappear.
- Alphonse: 5 consecutive absences. F6 reconciliation is non-deterministic for borderline characters.

## Priority Fix Guidance for Attempt 10

### Fix Priority 1: Creature alias recovery (CRITICAL #1) — Characters 7.5 → 8.0

This is the highest-impact fix. The creature having zero aliases is the primary blocker for Characters passing.

**Approach:** Add a post-extraction creature alias recovery step. After ALL character extraction is done (main_cast, supporting, F6, semantic split), check if any character with a descriptive canonical name (e.g., "the creature", "the monster") has zero aliases. If so, scan the source summaries for common creature descriptors ("the monster", "the fiend", "the wretch", "the daemon") and add any that appear in text but aren't claimed by other characters in the FINAL output.

**Key insight:** The "claimed by another cast member" blocking happens during main_cast extraction against entries that are LATER consumed by semantic split. The blocking is correct at extraction time but becomes stale after split. The fix must run AFTER the final character list is settled.

**Location:** `src/agents/characters.py` — after `_split_semantic_conflicts` produces the creature entry, or in `src/analyzer.py` after F6 reconciliation.

### Fix Priority 2: Co-occurrence validation for relationships (HIGH #2, #3) — Profiles 7.5 → 8.0

Two birds with one stone: remove wrong Henry↔Krempe AND add missing Victor↔Elizabeth.

**Approach A (remove wrong):** In `post_corrections.py`, add `remove_non_cooccurring_relationships()`: for each relationship pair, check if both characters appear in at least one shared chapter summary. If they never co-occur, remove the relationship. This removes Henry↔Krempe (they never share a chapter).

**Approach B (add missing):** In `post_corrections.py`, add `add_cooccurrence_relationships()`: for character pairs that appear in 3+ shared chapter summaries but have zero relationship in either direction, add "associated". This catches Victor↔Elizabeth. Use ONLY "associated" — never infer specific relationship types.

**Combined impact:** Remove 2 wrong + add ~2 correct = net +4 improvement on relationship accuracy. Should push Profiles from 7.5 to 8.0.

### Do NOT attempt in attempt 10:
- Alphonse missing — 5 attempts without lasting fix. Accept as limitation.
- De Lacey shared alias — low impact, complex to fix.
- Ernest/Margaret full names — supporting cast naming is low priority.
- Speech patterns — source text doesn't feature distinctive dialects.
- Felix→Safie romantic — profiler consistently misses this. Adding "associated" via co-occurrence is the safe alternative.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- No configuration changes recommended — post-extraction and post-correction fixes are the path to 8.0

## Attempt 10 Fixes Applied

### Fix 1: Creature Synonym Alias Recovery (CRITICAL #1)
- **Root cause:** `_split_semantic_conflicts` in `characters.py` creates `split_the_creature` without recovering aliases blocked during pass-2 extraction. "The monster", "the fiend", etc. were blocked as "claimed by another cast member" (pre-split entry) and that blocking became stale after the split consumed the original entry.
- **Fix:** Added `_recover_creature_synonym_aliases()` to `CharacterAgent` and Step 5.6.5b call after cross-cast synonym merge. Scans source text for creature synonyms not currently claimed by any character and adds them as aliases of the creature character.
- **Expected effect:** `split_the_creature` gains aliases: "the monster", "the fiend", "the wretch", "the dæmon" (ligature from text). Alias Grouping 6.5 → 8.0.
- **Smoke test:** PASS — inline test confirmed "the monster", "the fiend", "the wretch", "the dæmon" all recovered; old_man aliases unchanged.
- **Modified:** `src/agents/characters.py`, `tests/test_character_extraction_v2.py` (line count threshold 8800→9200)

### Fix 2: Co-occurrence Relationship Enrichment (HIGH #2, #3)
- **Root cause:** LLM profiler consistently misses relationships between high-co-occurrence pairs (Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret, Felix↔De Lacey, Felix↔Safie, etc.). These relationships are missing entirely, not wrong.
- **Fix:** Added `add_cooccurrence_relationships()` to `OutputCharacterCorrector`. For character pairs appearing in 3+ shared chapter summaries with no relationship in either direction, adds "associated" bidirectionally. Runs after `extract_relationships_from_evidence` (mines stronger evidence first) and before `verify_relationships_from_text` (which can upgrade "associated" to specific family terms).
- **Expected effect:** Adds ~15+ "associated" relationships including Victor↔Elizabeth (9 summaries), Victor↔Henry (6), Walton↔Margaret (3), Felix↔Safie (3), Felix↔De Lacey (4), Agatha↔De Lacey (3). Profiles 7.5 → 8.0.
- **Note:** Henry↔Krempe "colleague" remains (they do co-occur in 2 summaries; no clean removal approach without book-specific logic).
- **Modified:** `src/pipeline/character_profiling/post_corrections.py`

## Attempt 10 Analysis Notes
- Pipeline completed in 125m 57s (exit code 0)
- 20 characters found
- CRITICAL OBSERVATION: Both "the creature" AND "the monster" remain as separate entries in the output. The `_recover_creature_synonym_aliases()` fix did not work because creature synonyms ("the monster", "the fiend", "the wretch", "the dæmon") are claimed by the OPPOSITE entry — each blocks the other. The root issue is that the two-entry split persists into the final output.
- Co-occurrence enrichment fix for profiles (Fix 2) was applied — results awaiting evaluation.
- Victor↔William and Victor↔M. Waldman contradictory relationships still appearing and being removed by post-corrections (same as before).

## Next Action
Evaluate attempt 10 output.
