# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 13
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260302_002421/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING — relationships too generic, sibling regression)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.28/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles)

## What Changed from Attempt 12

### Fixes Verified
- **Fix 1 (bidirectional parent → "associated"):** WORKED but caused side-effect. Victor↔Alphonse "sibling" issue is now moot (Alphonse absent). But Felix↔Agatha REGRESSED from "sibling" to "associated" — the old "sibling" was correct for them.
- **Fix 2 (parent/child in FAMILY_TERMS):** WORKED ✓. Safie↔Beaufort hallucinated "parent"/"child" is GONE. They no longer share a relationship entry.
- **Fix 3 (_propagate_missing_reverses):** DID NOT WORK. Walton→Margaret still missing despite Margaret→Walton having "sister". The smoke test passed but the real pipeline didn't propagate. Likely cause: "sister" not in RELATIONSHIP_REVERSES, or method execution error.

### Regressions
- **Alphonse Frankenstein missing** — Was present in attempt 12 (10 mentions), now absent. No character extraction code was changed; this is LLM run-to-run variability. Characters drops from 8.5 to 8.0 (still passing).
- **Felix↔Agatha "sibling" → "associated"** — Direct side-effect of Fix 1. When the LLM labels both as "parent" of each other, the old code converted to "sibling" (correct for siblings), new code converts to "associated" (neutral but less useful).

### Net Effect on Profiles
- Removed: Safie↔Beaufort hallucinated "parent" ✓ (+0.25)
- Regressed: Felix↔Agatha "sibling" → "associated" (−0.25)
- Unchanged: Walton→Margaret still missing, Victor's quotes still misattributed
- Net: Profiles 7/10 → 7.5/10 (+0.5, from removing worst errors)

## Current Issues (Priority Order)

### CRITICAL

1. **`fix_bidirectional_parent_labels` too blunt — converts real siblings to "associated"** [Profiles - Relationships]
   - Problem: When both characters claim "parent" of each other (common LLM error), the method now converts both to "associated". This is correct for actual parent/child pairs (where one direction is wrong) but incorrect for siblings (where both "parent" claims should map to "sibling").
   - Evidence: Felix↔Agatha were "sibling" in attempt 12, now "associated". They share surname "De Lacey" and are siblings in the text.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `fix_bidirectional_parent_labels()`
   - Fix: Add surname-sharing heuristic. If both characters share a surname fragment, convert bidirectional "parent" to "sibling" (more likely siblings than both being parents of each other). If they don't share a surname, convert to "associated" (can't determine direction). This restores Felix↔Agatha while keeping Safie↔unrelated-character cases neutral.
   - Impact: Profiles 7.5 → 8.0 (restores sibling labels for surname-sharing pairs: Felix↔Agatha, and would also correctly label Victor↔William, Victor↔Ernest if LLM generates "parent" for them)

### HIGH

2. **`_propagate_missing_reverses` not firing for Margaret→Walton "sister"** [Profiles - Relationships]
   - Problem: Margaret→Walton has "sister" but Walton→Margaret has no entry. The new `_propagate_missing_reverses` method was added but didn't produce results in the actual pipeline run.
   - Evidence: Walton's relationships: `{"Victor Frankenstein": "associated", "the creature": "associated"}` — Margaret not present.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses()`
   - Fix: Debug the method. Check: (a) Is "sister" in `RELATIONSHIP_REVERSES`? (b) Does the method correctly iterate through all characters? (c) Is it actually being called in `run_all()`? The smoke test passed, so it may be a data-shape issue in real pipeline output vs test fixture.
   - Impact: Profiles +0.25

### MEDIUM

3. **Alphonse Frankenstein absent (LLM variability regression)** [Character Extraction - Completeness]
   - Problem: Alphonse (Victor's father) was present in attempt 12 with 10 mentions, now absent. No code changes to character extraction were made.
   - Evidence: 20 characters extracted, Alphonse not among them. He appears in chapters 1, 2, 6, 7, 22, and his death is a plot point.
   - Location: LLM variability in `src/pipeline/character_extraction_v2/` — not a code bug.
   - Impact: Characters 8.5 → 8.0 (still passing). Do NOT attempt a code fix — this is LLM non-determinism. Will likely resolve on re-run.

4. **Victor's misattributed example quotes (2-3/4 wrong)** [Profiles - Voice Guidance]
   - Problem: Victor's voice_guidance.example_quotes include Walton's "I have no friend, Margaret" and the creature's "I am thy creature, and I will be even mild and docile..."
   - Accept as LLM limitation. Do NOT attempt to fix in attempt 14.

5. **De Lacey family mostly "associated"** [Profiles - Relationships]
   - Problem: Felix→De Lacey (the old man) and Agatha→De Lacey (the old man) are "associated" instead of "child"/"parent".
   - The surname-sharing heuristic in CRITICAL #1 will help for sibling pairs but not for parent/child direction between De Lacey members.
   - Accept for now — "associated" is not wrong, just generic.

### LOW

6. Ernest and Margaret lack full canonical names (Ernest Frankenstein, Margaret Walton Saville).
7. Letter 1 title null in JSON (displayed correctly as "Prologue 1" in HTML).
8. Creature role "antagonist" — debatable; is also narrator and protagonist of own embedded narrative.
9. Victor's verbal_tics includes empty string "".

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
| 12 | 8.33 | +2.13 | **BEST SCORE.** Ollama stable (20/20 profiles). Co-occurrence enrichment WORKING (20/20 relationships). Dæmon fix ✓. Alphonse back ✓. But Profiles 7/10 — relationship label errors (Victor-Alphonse "sibling", Safie-Beaufort "parent"). |
| 13 | 8.28 | +2.08 | Fix 2 (Safie-Beaufort) WORKED ✓. Fix 1 (bidir parent) caused Felix-Agatha regression. Fix 3 (propagate reverses) did NOT fire. Profiles 7→7.5 (net +0.5). Alphonse missing (LLM variability). |

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
  - **NOW WORKING ✓** — All 20 characters have relationships

- Attempt 11 (Fix 2): Romantic label validation — new `reject_unfounded_romantic_labels()` method
  - Root cause: LLM profiler generated "romantic interest" for De Lacey↔monster. No post-correction validated romantic labels against text evidence.
  - Fix: New method checks for strong romantic evidence in co-mention windows. Downgrades to "associated" if no evidence found.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

- Attempt 12 (Fix 1): Co-occurrence enrichment pipeline chain — `reject_unfounded_familial_labels()` downgrade
  - Root cause: `add_cooccurrence_relationships()` adds "associated" → `verify_relationships_from_text()` upgrades to family term → `reject_unfounded_familial_labels()` DELETES non-sibling family without shared surname.
  - Fix: Changed `reject_unfounded_familial_labels()` to downgrade to "associated" instead of deleting.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **PARTIALLY WORKING** — co-occurrence chain preserved but "parent" labels between Safie-Beaufort not downgraded (possible bug)

- Attempt 12 (Fix 2): "the dæmon" alias transfer from De Lacey to creature
  - Fix: When a creature synonym is claimed by a non-creature character, transfer it to the creature.
  - Modified: `src/agents/characters.py`
  - **WORKED ✓** — "the dæmon" on creature, removed from De Lacey

- Attempt 13 (Fix 1): `fix_bidirectional_parent_labels` downgrade to "associated" instead of "sibling"
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **PARTIALLY WORKED** — Removed wrong "sibling" labels but also regressed correct sibling labels (Felix↔Agatha)

- Attempt 13 (Fix 2): Added "parent" and "child" to `FAMILY_TERMS`
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **WORKED ✓** — Safie↔Beaufort "parent"/"child" now correctly handled

- Attempt 13 (Fix 3): Added `_propagate_missing_reverses` to `OutputCharacterCorrector.run_all()`
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **DID NOT WORK** — Walton→Margaret still missing despite smoke test passing

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
| 11 | Co-occurrence temp dict bug | `post_corrections.py` | NOW WORKING ✓ |
| 11 | Romantic label validation | `post_corrections.py` | Working (untestable in att 11) |
| 12 | Co-occurrence chain (downgrade familial) | `post_corrections.py` | Partial (parent not downgraded) |
| 12 | Dæmon alias transfer | `characters.py` | Fixed ✓ |
| 13 | Bidirectional parent → "associated" | `post_corrections.py` | Partial — regressed siblings |
| 13 | parent/child in FAMILY_TERMS | `post_corrections.py` | Fixed ✓ |
| 13 | _propagate_missing_reverses | `post_corrections.py` | DID NOT WORK |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-13): EIGHT consecutive attempts. The relationship post-correction chain continues to be the core challenge.
- The bidirectional parent fix has gone through 3 iterations: "sibling" (att 9) → "associated" (att 13) → needs surname heuristic (att 14).

## Priority Fix Guidance for Attempt 14

### Fix Priority 1: Surname-aware bidirectional parent resolution (CRITICAL #1)

In `fix_bidirectional_parent_labels()`, instead of always converting bidirectional "parent" to "associated":
- Extract surname fragments from both characters' canonical names
- If they share a surname → convert to "sibling" (correct for same-generation family members like Felix↔Agatha)
- If they don't share a surname → convert to "associated" (neutral fallback)

Surname extraction: take the last word of canonical name (e.g., "Felix De Lacey" → "De Lacey" or "Lacey", "Victor Frankenstein" → "Frankenstein"). For multi-word surnames like "De Lacey", consider the last 2+ words.

**Location:** `src/pipeline/character_profiling/post_corrections.py` — `fix_bidirectional_parent_labels()`

**Expected outcome:** Felix↔Agatha → "sibling" (share "De Lacey"), Agatha↔De Lacey (the old man) → "sibling" if both labeled "parent", unrelated pairs → "associated"

### Fix Priority 2: Debug `_propagate_missing_reverses` (HIGH #2)

The method was added but didn't produce results. Steps to debug:
1. Check if "sister" is in `RELATIONSHIP_REVERSES` dict
2. Check if the method is actually called in `run_all()` (log or print statement)
3. Check if it correctly iterates `self.characters` and accesses `char.relationships`
4. The smoke test passed, so the issue may be in how the real pipeline data is structured vs the test fixture

**Location:** `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses()` and `RELATIONSHIP_REVERSES`

### Do NOT attempt in attempt 14:
- Alphonse missing — LLM variability, not a code issue
- Victor's misattributed quotes — LLM limitation
- De Lacey parent/child direction — "associated" is acceptable
- Creature role "antagonist" — low impact

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all 5 stages ✓
- 0 JSON parse failures ✓
- Ollama stable throughout entire run
- 358 LLM calls total, summaries served from cache
- 125m14s total runtime

## Next Action
Run PROMPT_fix.md to address surname-aware bidirectional parent resolution (Critical #1) and debug _propagate_missing_reverses (High #2)
