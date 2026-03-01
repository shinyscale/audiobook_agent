# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 11
- **Phase:** awaiting_analysis
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_144611/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 7/10
- Character Profiles: 3/10 ✗ (CATASTROPHIC — Ollama crash)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (Character Profiles catastrophically below threshold)

## Root Cause: Ollama Infrastructure Failure

**Only 4/19 character profiles were generated.** Ollama dropped connections mid-run during profile generation (starting from Justine Moritz). Error: `[Errno 111] Connection refused`. This caused:
- 15/19 characters to have NO profile data (no physical description, personality, relationships)
- ALL pronunciation LLM enrichment to fail (0 LLM calls)
- Plot summary generation to fail
- First-appearance queries to fail

The 4 successful profiles (Victor, William, Felix, Agatha) produced correct relationships. But 14 characters have completely empty profiles.

## Co-Occurrence Enrichment: STILL NOT WORKING

Despite the attempt 11 Fix 1 (temp dict write bug), co-occurrence relationships are NOT appearing in the final output:
- Victor↔Elizabeth share 7 chapter summaries → no relationship in output
- Victor↔Henry share 7 chapter summaries → no relationship in output
- Walton↔Margaret share 3 chapter summaries → no relationship in output

Manual testing confirms: the name patterns match correctly, the summaries contain both names, the threshold (3) is met. The `add_cooccurrence_relationships()` method is in `run_all()` at line 725 and `chapter_summaries` is passed from the analyzer at line 2174.

**Hypothesis:** The post-corrections modify one set of character objects, but the final serialized output uses different objects. OR a later post-correction step is removing/overwriting the enrichment. This needs deeper debugging — trace the exact object lifecycle from `OutputCharacterCorrector.run_all()` through to JSON serialization.

## New Regression: "the dæmon" Alias Misassigned

"the dæmon" is now an alias of "the old man (De Lacey)" (main_cast_10) instead of "the creature" (split_the_creature). In attempt 10, "the dæmon" was correctly an alias of the monster. This is a non-deterministic LLM extraction regression — the main_cast pipeline assigned it to De Lacey this run.

## Current Issues (Priority Order)

### CRITICAL

1. **Ollama connection failure during profile generation** [Profiles]
   - Problem: Ollama dropped connections after 4/19 profiles, leaving 15 characters with completely empty profiles (no description, personality, or relationships)
   - Evidence: Profiling shows Character Profiles stage: 12 LLM calls, 4 high confidence, 15 LOW confidence. Physical descriptions: 1/18. Relationships: 4/18.
   - Location: Infrastructure issue — not a code bug. Ollama process crashed or unloaded model mid-run.
   - Fix: **Ensure Ollama is stable before re-running.** Check `ollama ps` before and during analysis. Consider adding a health check / retry with model reload in the analyzer.
   - Impact: Profiles 3/10 → likely 7+ if profiles generate. THIS IS THE ONLY BLOCKER.

2. **Co-occurrence enrichment still produces no output** [Profiles]
   - Problem: `add_cooccurrence_relationships()` fix from attempt 11 (temp dict write bug) was applied, but Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret still have no relationships.
   - Evidence: Manual pattern matching confirms 7 shared summaries for Victor+Elizabeth. Method is in `run_all()` at line 725. `chapter_summaries` is passed from analyzer at line 2174.
   - Location: `src/pipeline/character_profiling/post_corrections.py` line 853-915 + `src/analyzer.py` lines 2167-2175
   - Fix approach: **DEEP DEBUG REQUIRED.**
     1. Add temporary logging at the START of `add_cooccurrence_relationships()` to confirm it is being called and receiving summaries
     2. Log the number of character pairs found and their shared counts
     3. After `run_all()` completes, log the relationships of Victor and Elizabeth to confirm they were added
     4. Check if the character objects passed to `OutputCharacterCorrector.run_all()` are the SAME objects that get serialized to JSON. If not, the post-corrections are modifying copies that are discarded.
     5. Check if `clean_orphaned_relationships` (line 726) or `verify_relationships_from_text` (line 728) is removing the "associated" labels
   - Impact: If fixed, adds 3+ correct "associated" relationships → Profiles +1.0 minimum

### HIGH

3. **"the dæmon" alias on De Lacey instead of creature** [Alias Grouping]
   - Problem: "the dæmon" is an alias of "the old man (De Lacey)" (main_cast_10) — WRONG. "The dæmon" is what Walton/Victor call the creature.
   - Evidence: In the novel, Walton's Letter 4 says "a creature he calls a 'dæmon' across the ice" — referring to the creature/monster, not De Lacey. The JSON shows: old man aliases = ["the old man", "De Lacey", "the dæmon"], creature aliases = ["the monster", "the fiend", "the wretch", "the being"] (missing "the dæmon").
   - Location: Non-deterministic LLM extraction. The `_recover_creature_synonym_aliases()` method in `characters.py` should catch this but apparently didn't because "the dæmon" was assigned to De Lacey in the main_cast pipeline first.
   - Fix: In `_recover_creature_synonym_aliases()`, add logic to TRANSFER "the dæmon"/"the daemon" from any non-creature character to the creature entry, since these terms universally refer to the creature in Frankenstein context. BUT — this would be novel-specific. GENERIC fix: in `verify_aliases` or post-alias-recovery, if a creature-synonym term (matched by the creature recovery logic) is found on a DIFFERENT character, remove it from that character.
   - Impact: Alias Grouping 7/10 → 8/10. Character Extraction overall 8/10 → 8.5/10.

### MEDIUM

4. **Alphonse Frankenstein missing — 7th consecutive attempt** [Completeness]
   - Accept as limitation. Do NOT attempt to fix.

5. **"De Lacey" shared alias between Felix and old man** [Alias Grouping]
   - Persistent issue, low ROI. Accept.

6. **Creature listed as "supporting" role instead of "main"** [Completeness]
   - The creature is a protagonist/narrator. Should be "main" role. Minor impact on presentation.

### LOW

7. Ernest and Margaret lack full canonical names (Ernest Frankenstein, Margaret Walton Saville).
8. Letter 1 title null in JSON (displayed correctly as "Prologue 1" in HTML).
9. Caroline Beaufort regressed from attempt 9 — non-deterministic F6.

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
| 10 | 8.23 | +2.03 | Creature aliases FIXED ✓ (Characters 7.5→8.5). BUT co-occurrence enrichment DID NOT FIRE. New De Lacey↔monster "romantic interest" hallucination. Profiles 7.5→7.0. |
| 11 | 7.50 | +1.30 | **REGRESSION: Ollama crashed during profiles.** Only 4/19 profiles generated. Co-occurrence enrichment still not producing output despite bug fix. New dæmon alias regression. Profiles 7.0→3.0. |

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

- Attempt 10 (Fix 2): Co-occurrence relationship enrichment — `add_cooccurrence_relationships()` in OutputCharacterCorrector
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **DID NOT WORK** — Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret all still missing.

- Attempt 11 (Fix 1): Co-occurrence enrichment bug — `add_cooccurrence_relationships()` wrote to temp dict
  - Root cause: `rels_b = getattr(...) or {}` creates a new temp empty dict when `char_b.relationships` is `{}` (falsy). Writes to temp dict; `char_b.relationships` remains empty. Non-empty dicts were unaffected (one direction worked, other didn't).
  - Fix: Separate read-only check (keeps `or {}`) from write path (writes directly to `char.relationships`)
  - Smoke test: PASS — Victor+Elizabeth both get "associated" bidirectionally
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **STILL NOT PRODUCING OUTPUT** — despite smoke test passing, relationships not in final JSON. Deeper lifecycle issue suspected.

- Attempt 11 (Fix 2): Romantic label validation — new `reject_unfounded_romantic_labels()` method
  - Root cause: LLM profiler generated "romantic interest" for De Lacey↔monster. No post-correction validated romantic labels against text evidence.
  - Fix: New method checks for strong romantic evidence (love, kiss, marry, wed, betrothed, romance, fiancée) in co-mention windows. Downgrades to "associated" if no evidence found.
  - Smoke test: PASS — De Lacey↔monster "romantic interest" → "associated"; Felix↔Safie preserved
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **UNTESTABLE** — De Lacey and monster both had empty profiles due to Ollama crash, so the romantic label never appeared.

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
| 10 | Creature alias recovery | `characters.py` | Fixed ✓ |
| 10 | Co-occurrence enrichment | `post_corrections.py` | DID NOT WORK |
| 11 | Co-occurrence temp dict bug | `post_corrections.py` | Smoke pass, but still no output |
| 11 | Romantic label validation | `post_corrections.py` | Untestable (Ollama crash) |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-11): SIX consecutive attempts modifying this file. Co-occurrence enrichment has been added (attempt 10), bug-fixed (attempt 11), smoke-tested (PASS), but STILL does not produce results in the final output. The issue is likely NOT in the method logic itself, but in the object lifecycle — the corrector may be modifying objects that aren't the same as those serialized to JSON.
- Ollama infrastructure failures are now a recurring concern. Attempt 11 lost 15/19 profiles to connection drops.

## Priority Fix Guidance for Attempt 12

### PREREQUISITE: Ensure Ollama Stability

Before making ANY code changes, verify:
```bash
ollama ps  # Check model is loaded
curl http://localhost:11434/api/tags  # Verify Ollama is responsive
```

Consider adding a model health check before the profile generation stage. If the model has been unloaded, reload it. This is the MOST IMPORTANT fix — without stable Ollama, no amount of code changes can produce good profiles.

### Fix Priority 1: Debug co-occurrence enrichment object lifecycle (CRITICAL #2)

The method logic is correct (confirmed by manual testing and smoke tests). The issue is that enrichment results don't appear in the final JSON output. This has now persisted across 2 attempts despite targeted fixes.

**Required investigation:**
1. Add `print()` statements (not just logging) at the START and END of `add_cooccurrence_relationships()` to confirm it runs
2. After the method adds relationships, print the relationships of Victor and Elizabeth WITHIN the method
3. After `OutputCharacterCorrector.run_all()` returns (in `analyzer.py` line 2175), print Victor's and Elizabeth's relationships to see if they persisted
4. Check if `characters` in `analyzer.py` line 2173 are the same Python objects that get serialized to the AnalysisResult — if the analyzer converts to a different representation after post-corrections, the enrichment is lost

**If the objects are different:** The fix is to either (a) run post-corrections on the final objects, or (b) pass the enrichment results back to the serialized objects.

### Fix Priority 2: Transfer dæmon alias from De Lacey to creature (HIGH #3)

In `_recover_creature_synonym_aliases()` in `characters.py`, after identifying the creature entry, scan ALL other characters and REMOVE any creature-synonym aliases that were incorrectly assigned to them. Specifically:
- If a non-creature character has an alias matching a creature synonym (the dæmon, the daemon, the fiend, the wretch, etc.), remove it from that character and ensure it's on the creature entry.
- This is a generic fix (works for any creature-synonym list) not a novel-specific hardcode.

### Do NOT attempt in attempt 12:
- Alphonse missing — accepted limitation (7th consecutive absence)
- De Lacey shared alias — accepted
- Caroline Beaufort — non-deterministic
- Ernest/Margaret full names — low priority

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- **NEW CONCERN:** Ollama connection stability. Consider reducing parallel load or adding retry-with-reload logic for the profile generation stage.

## Attempt 12 Fixes Applied

### Fix 1: Co-occurrence enrichment pipeline chain (CRITICAL #2)
- **Root cause:** `add_cooccurrence_relationships()` adds "associated" → `verify_relationships_from_text()` upgrades it to family term (e.g., "wife") → `reject_unfounded_familial_labels()` unconditionally DELETES non-sibling family labels without shared surname → relationship disappears
- **Fix:** Changed `reject_unfounded_familial_labels()` to downgrade to "associated" instead of deleting for non-sibling family labels without shared surname. Spouses with different surnames (common in older novels) now retain "associated" instead of having the relationship deleted.
- **Universality:** Affects any book where spouses/parent-child pairs have different surnames
- **Smoke test:** PASS — Victor/Elizabeth "wife" downgraded to "associated" correctly
- **Modified:** `src/pipeline/character_profiling/post_corrections.py` (lines 1773-1801)

### Fix 2: "the dæmon" alias transfer from De Lacey to creature (HIGH #3)
- **Root cause:** `_recover_creature_synonym_aliases()` skipped adding "the dæmon" to the creature because it was already claimed by De Lacey's aliases. The check only prevented double-claiming, not correction of misassignment.
- **Fix:** When a creature synonym phrase is claimed by a NON-creature character, transfer it to the creature character (remove from claimer's aliases, add to creature). Non-deterministic LLM can misassign creature synonyms; this enforces the universal invariant that creature synonyms belong to the creature entity.
- **Universality:** Applies to any book with a creature/monster whose synonyms (monster, fiend, wretch, daemon, being) get misassigned during LLM extraction
- **Smoke test:** PASS — "the dæmon" removed from De Lacey, added to "the monster"
- **Modified:** `src/agents/characters.py` (`_recover_creature_synonym_aliases` lines 3319-3430)

## Next Action
**Phase:** awaiting_analysis
Re-run analysis to verify fixes. Ollama must be running before re-run.
