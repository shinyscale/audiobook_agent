# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 10
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_130625/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9.5/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## What Changed from Attempt 9

### Fix 1 (Creature Alias Recovery) — WORKED ✓

The analysis phase notes claimed "Both 'the creature' AND 'the monster' remain as separate entries" — **this is WRONG**. The actual JSON output has a SINGLE entry:

- `split_the_monster` with canonical name "the monster" and aliases: ["the creature", "the fiend", "the wretch", "the dæmon", "the being"]

This is exactly what was intended. All major creature descriptors are now unified under one character. **Alias Grouping jumps from 6.5 to 8.0.** Character Extraction overall moves from 7.5 to 8.5 — NOW PASSING.

### Fix 2 (Co-occurrence Enrichment) — DID NOT WORK

The `add_cooccurrence_relationships()` method was added to `OutputCharacterCorrector` but appears to have NOT added the expected relationships:

- Victor↔Elizabeth: STILL MISSING (expected from 9+ shared chapter summaries)
- Victor↔Henry: STILL MISSING (expected from 6+ shared summaries)
- Walton↔Margaret: STILL MISSING (expected from 3+ shared summaries)
- Felix↔Safie: STILL MISSING
- De Lacey↔Felix/Agatha: STILL MISSING

Elizabeth has 0 relationships. Victor has no relationship to Elizabeth in either direction. The co-occurrence enrichment should have triggered for this pair but didn't.

**Possible causes:** The method was added but may not have been called in `run_all()`, or there's a bug in the character name matching against chapter summaries.

### New Regression: De Lacey↔monster "romantic interest"

A NEW wrong relationship appeared that wasn't in attempt 9: the old man (De Lacey) ↔ the monster is labeled "romantic interest" bidirectionally. This is COMPLETELY WRONG — the monster seeks acceptance/friendship from the blind De Lacey, not romance. This is an LLM profiler hallucination that the post-corrections failed to catch.

### Caroline Beaufort — REGRESSED

Caroline Beaufort appeared as a new character in attempt 9 but is absent in attempt 10. The entry "Beaufort" (id: `0e0a948fd562`) refers to Caroline's father, not Caroline herself. This is a minor regression (non-deterministic F6 extraction).

## What's Now Passing (vs Attempt 9)

| Category | Attempt 9 | Attempt 10 | Delta |
|----------|-----------|------------|-------|
| Structure | 8.5 ✓ | 8.5 ✓ | — |
| Characters | 7.5 ✗ | 8.5 ✓ | +1.0 ✓ |
| Profiles | 7.5 ✗ | 7.0 ✗ | -0.5 |
| Summaries | 8.5 ✓ | 8.5 ✓ | — |
| Pronunciation | 8.0 ✓ | 8.0 ✓ | — |
| Presentation | 8.5 ✓ | 8.5 ✓ | — |

Characters now PASSES thanks to creature alias recovery. But Profiles REGRESSED due to De Lacey↔monster "romantic interest" and co-occurrence enrichment not firing.

## What's Still Failing

### Profiles (7.0/10) — the ONLY remaining blocker

**Relationship accuracy: 17/20 correct, 2 grossly wrong, 1 borderline**

Present relationships (20 total across 12 characters):
- ✓ Victor→Krempe: "mentor"
- ✓ Victor→monster: "associated"
- ✓ Victor→William: "sibling"
- ✓ Victor→Waldman: "associated"
- ✗✗ Henry→Krempe: "acquaintance" — borderline (they meet but barely interact)
- ✓ William→Victor: "sibling"
- ✓ Felix→Agatha: "sibling"
- ✓ Agatha→Felix: "sibling"
- ✗✗✗ De Lacey→monster: "romantic interest" — COMPLETELY WRONG
- ✓ monster→Walton: "interlocutor"
- ✗✗✗ monster→De Lacey: "romantic interest" — COMPLETELY WRONG
- ✓ Kirwin→Victor: "magistrate and benefactor"
- ✓ Waldman→Krempe: "colleague"
- ✓ Waldman→Victor: "associated"
- ✓ Krempe→Victor: "protégé"
- ✓ Krempe→Waldman: "colleague"
- ✗ Krempe→Henry: "acquaintance (mentioned in context of shared conversation)" — weak
- ✓ Agrippa→Krempe: "subject of dismissal by"
- ✓ Agrippa→Waldman: "subject of respectful acknowledgment by"
- ✓ Werter→monster: "literary influence"

**Missing critical relationships:**
- Victor↔Elizabeth: fiancée/wife — THE central romance (92 mentions, 9+ shared chapters)
- Victor↔Henry: best friend (82 mentions, 6+ shared chapters)
- Walton↔Margaret: siblings (10 mentions each)
- De Lacey→Felix/Agatha: father
- Felix→Safie: romantic interest

**Physical descriptions:** 6/20 with high accuracy (William, De Lacey, monster, Safie, Waldman, Krempe). Acceptable given Shelley's sparse character descriptions.

## Current Issues (Priority Order)

### CRITICAL

1. **De Lacey↔monster "romantic interest" — NEW hallucination** [Profiles]
   - Problem: The old man (De Lacey) and the monster have bidirectional "romantic interest" labels. This is a completely wrong LLM hallucination. The monster seeks acceptance/friendship from the blind De Lacey.
   - Evidence: The novel's De Lacey scene (Ch 15) shows the monster pleading for compassion: "I am a wretched outcast... I beg you to listen." There is zero romantic content.
   - Location: LLM profiler generates this. `verify_relationships_from_text` in `post_corrections.py` doesn't catch it.
   - Fix approach: Add a validation rule in post-corrections: if a relationship label is "romantic interest" but neither character has any romantic language in shared chapter summaries (love, beloved, marry, wedding, kiss, etc.), downgrade to "associated". This is a generic rule — don't mention specific characters.
   - Alternative: Add "romantic interest" to the set of labels that `reject_unfounded_familial_labels` validates against text evidence. Currently that method only checks familial labels.
   - Impact: Removes 2 wrong relationships → Profiles +0.5

### HIGH

2. **Co-occurrence enrichment not firing — Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret all still missing** [Profiles]
   - Problem: `add_cooccurrence_relationships()` was added in attempt 10 Fix 2 but appears to have NOT actually run. Zero "associated" relationships were added for major co-occurring pairs.
   - Evidence: Elizabeth has 0 relationships total. Victor has no entry for Elizabeth. These characters share 9+ chapter summaries.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `add_cooccurrence_relationships()` method. Also check `run_all()` to verify the method is actually called.
   - Fix approach: **DEBUG FIRST.** Read `run_all()` to verify `add_cooccurrence_relationships` is in the call chain. If it is, the bug is likely in the name-matching logic (canonical names vs summary text). Try: print/log which pairs are detected and how many shared summaries they have. If the method isn't called, add it to `run_all()`.
   - Impact: Adding Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret as "associated" → Profiles +0.75
   - **Combined with #1:** Profiles 7.0 → 8.0+

### MEDIUM

3. **Henry↔Krempe "acquaintance" — borderline wrong** [Profiles]
   - Henry visits Ingolstadt and meets Victor's professors, so there IS a textual basis. But the label overstates their connection.
   - Low priority — removing this wouldn't significantly change the score.

4. **Alphonse Frankenstein missing — 6th consecutive attempt** [Completeness]
   - Accept as limitation. Do NOT attempt to fix.

5. **Caroline Beaufort regressed from attempt 9** [Completeness]
   - Non-deterministic F6 extraction. Low ROI to chase.

6. **Shared "De Lacey" alias between Felix and old man** [Alias Grouping]
   - Same issue as before. Low priority.

### LOW

7. Ernest and Margaret lack full canonical names.
8. Physical descriptions: 6/20 — acceptable given source text.
9. Victor→monster: "associated" — weak label but not wrong.
10. Missing De Lacey→Felix/Agatha "father" relationships.
11. Missing Felix→Safie "romantic interest" relationship.

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
  - **DID NOT WORK** — Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret all still missing. Method may not be in `run_all()` call chain, or name matching against summaries has a bug.

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

**Recurring patterns:**
- `post_corrections.py` (attempts 6-10): Five consecutive attempts. Enrichment has been added, removed, and re-added with different implementations. The current `add_cooccurrence_relationships()` method appears to not be executing.
- Profiles are the LAST remaining blocker. All other categories pass. One focused fix (debug enrichment + remove "romantic interest") can close this.

## Priority Fix Guidance for Attempt 11

### Fix Priority 1: Debug and fix `add_cooccurrence_relationships()` (CRITICAL #1 + HIGH #2 combined)

This is the highest-ROI fix. If the enrichment actually fires, it adds Victor↔Elizabeth, Victor↔Henry, Walton↔Margaret as "associated" — massive profile improvement.

**Step 1: Verify the method is called in `run_all()`.**
Read `src/pipeline/character_profiling/post_corrections.py` and check if `add_cooccurrence_relationships()` is in the `run_all()` method. If not, add it (after `extract_relationships_from_evidence`, before `verify_relationships_from_text`).

**Step 2: If it IS in `run_all()`, debug the name matching.**
The method needs to match character canonical names and aliases against chapter summary text. Possible bugs:
- Case sensitivity (summaries might say "elizabeth" or "Elizabeth")
- Matching against `canonical_name` vs aliases (summaries may use "Elizabeth" not "Elizabeth Lavenza")
- The 3-summary threshold might be too high if the matching is strict

**Step 3: Add temporary logging** to see which pairs are detected and their shared summary count. Remove logging after debugging.

### Fix Priority 2: Remove De Lacey↔monster "romantic interest" (CRITICAL #1)

**Approach:** In `post_corrections.py`, expand `reject_unfounded_familial_labels` (or add a new method) to also validate "romantic interest" labels. Check if the chapter summaries for shared chapters between the pair contain any romantic language (love, beloved, marry, kiss, wedding, courtship, etc.). If not, downgrade to "associated" or remove.

**IMPORTANT:** This validation must be GENERIC — no character-specific logic. Just check for romantic keywords in shared text.

**Expected combined impact:** Fix #1 adds ~3 correct "associated" relationships. Fix #2 removes 2 wrong "romantic interest" labels. Net: Profiles 7.0 → 8.0+.

### Do NOT attempt in attempt 11:
- Alphonse missing — 6th consecutive absence. Accept as limitation.
- Caroline Beaufort regressed — non-deterministic extraction. Accept.
- Henry↔Krempe "acquaintance" — borderline, text basis exists.
- Ernest/Margaret full names — low priority.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- No configuration changes recommended

## Next Action
Run PROMPT_fix.md to debug co-occurrence enrichment and remove "romantic interest" hallucination.
