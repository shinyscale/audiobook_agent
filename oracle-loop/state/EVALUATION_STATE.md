# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 15
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260302_051901/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.0/10 ✗ (FAILING — "friend" misapplied to antagonistic relationships; De Lacey father→children labeled "sibling"; 69% "associated")
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.20/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles)

## What Changed from Attempt 14

### Fixes Verified
- **Fix 1 (Extended text verification for non-family terms):** PARTIALLY WORKED.
  - ✓ Victor↔Henry Clerval: "associated" → "close friend" (9 occurrences of "friend" in co-mention windows)
  - ✓ Victor→Waldman/Krempe: "protégé"; Waldman/Krempe→Victor: "mentor"
  - ✓ Krempe↔Henry/Waldman: "colleague"
  - ✗ Victor↔Creature: "associated" → "friend" — WRONG. "friend" keyword appears contextually near both (Victor discusses wanting a "friend", Creature discusses companionship) but they are creator/creation, not friends.
  - ✗ William→Creature: "associated" → "friend" — WRONG. Creature murders William.
  - ✗ Creature→Justine: "associated" → "friend" — WRONG. Creature frames Justine.
  - ✗ Creature→Victor: "associated" → "friend" — WRONG.
  - Net: 6 correct upgrades, 4 wrong upgrades. Keyword "friend" too broadly applied.

- **Fix 2 (Parenthesis handling in _surnames()):** PARTIALLY WORKED.
  - ✓ "the old man (De Lacey)" now correctly shares "lacey" surname with Felix/Agatha De Lacey.
  - ✗ But this caused ALL De Lacey family relationships to become "sibling" (including father→children) via `fix_bidirectional_parent_labels`. The text verification found "father" in both directions → bidirectional parent → shared surname → "sibling".

- **Fix 3 (Hallucinated label downgrade for non-co-occurring):** WORKED ✓.
  - ✓ Felix→Victor "creator" hallucination is gone (no longer in relationships at all).

### Net Effect on Profiles
- Improved: Victor↔Henry "close friend" ✓ (+major — key relationship for narrator)
- Improved: Professor relationships mentor/protégé/colleague ✓ (+moderate)
- Improved: Felix→Victor "creator" removed ✓ (+minor)
- Regressed: Victor↔Creature "friend" ✗ (was "associated" — now actively wrong on central relationship)
- Regressed: William→Creature, Creature→Justine "friend" ✗ (actively wrong)
- Regressed: De Lacey family all "sibling" including father↔children ✗ (was "associated", now wrong)
- "associated" rate: 80% → 69% (improvement, but some upgrades went wrong)
- Net: Profiles 7.5 → 7.0 (correct upgrades offset by wrong "friend" labels and De Lacey regression)

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
| 5 | 7.38 | +1.18 | Profiles improved 5→6.5. BUT Turk REGRESSED again. Monster/dæmon false split. |
| 6 | 7.40 | +1.20 | Turk separated ✓. Dæmon merged ✓. BUT Profiles REGRESSED 6.5→5.5. |
| 7 | 7.80 | +1.60 | De Lacey alias ✓. Krempe separated ✓. "I" removed ✓. Profiles 5.5→6.5. |
| 8 | 7.83 | +1.63 | Title ✓. Letter 1 ✓. Presentation 7.5→8.5. BUT Profiles REGRESSED 6.5→6.0 (wrong enrichment labels). |
| 9 | 8.05 | +1.85 | Bidirectional sibling FIX ✓. Enrichment removed ✓. Caroline found! Profiles 6.0→7.5 (+1.5). Characters still 7.5 (creature zero aliases). |
| 10 | 8.23 | +2.03 | Creature aliases FIXED ✓ (Characters 7.5→8.5). BUT co-occurrence enrichment DID NOT FIRE. New De Lacey↔monster "romantic interest" hallucination. Profiles 7.5→7.0. |
| 11 | 7.50 | +1.30 | **REGRESSION: Ollama crashed during profiles.** Only 4/19 profiles generated. Co-occurrence enrichment still not producing output despite bug fix. New dæmon alias regression. Profiles 7.0→3.0. |
| 12 | 8.33 | +2.13 | **BEST SCORE.** Ollama stable (20/20 profiles). Co-occurrence enrichment WORKING (20/20 relationships). Dæmon fix ✓. Alphonse back ✓. But Profiles 7/10 — relationship label errors (Victor-Alphonse "sibling", Safie-Beaufort "parent"). |
| 13 | 8.28 | +2.08 | Fix 2 (Safie-Beaufort) WORKED ✓. Fix 1 (bidir parent) caused Felix-Agatha regression. Fix 3 (propagate reverses) did NOT fire. Profiles 7→7.5 (net +0.5). Alphonse missing (LLM variability). |
| 14 | 8.28 | +2.08 | Fix 1 (surname-aware sibling) WORKED ✓ — Felix↔Agatha restored. Fix 2 (propagate ordering) INCONCLUSIVE (no label to propagate). Profiles still 7.5/10 — 80% "associated" label epidemic is remaining blocker. |
| 15 | 8.20 | +2.00 | Text verification upgrades: Victor↔Henry "close friend" ✓, professors mentor/protégé ✓. BUT "friend" misapplied to Victor↔Creature, Creature→Justine/William. De Lacey father→children all "sibling". Profiles 7.5→7.0 (regressions offset gains). |

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

- Attempt 14 (Fix 1): Surname-aware `fix_bidirectional_parent_labels`
  - Root cause: Method always converted bidirectional parent labels to "associated", even for siblings sharing a surname.
  - Fix: Add `_surnames()` helper. If both characters share a surname component → "sibling"; otherwise → "associated".
  - Smoke test: PASS — Felix↔Agatha → "sibling", Safie↔Beaufort → "associated"
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **WORKED ✓** — Felix↔Agatha "sibling" restored

- Attempt 14 (Fix 2): Move `_propagate_missing_reverses` to be absolute last step in `run_all()`
  - Root cause: `_propagate_missing_reverses` ran BEFORE `enforce_gender_consistency`. When it added "sister" to Walton (male), `enforce_gender_consistency` changed it to "unknown", then `clean_unknown_relationships` deleted it.
  - Fix: Swap order — `enforce_gender_consistency` + `clean_unknown_relationships` first, then `_propagate_missing_reverses` last.
  - Smoke test: PASS — Walton→Margaret "sister" now propagated correctly
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **INCONCLUSIVE** — LLM didn't generate "sister" label in either direction this run, so nothing to propagate

- Attempt 15 (Fix 1): Extended `verify_relationships_from_text()` to detect non-family relationship terms
  - Root cause: `_rel_phrase_re` only matched FAMILY_TERMS; "friend", "betrothed", "rival", "mentor", etc. were invisible to the method.
  - Fix: Added `_all_rel_phrase_re` combining FAMILY_TERMS + non-family terms ("friend", "companion", "betrothed", "beloved", "rival", "enemy", "mentor", "creator", etc.) with extended prefix pattern ("my best friend", "my old friend", "my dearest friend")
  - Upgrade logic: family evidence → override any label (preserves "brother"→"cousin" override); generic labels ("associated") → upgrade to any detected term; specific non-family labels → NOT overridden by non-family evidence (prevents spurious "creation"→"friend")
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **PARTIALLY WORKED** — Victor↔Henry "close friend" ✓, professors mentor/protégé ✓. BUT "friend" misapplied to Victor↔Creature, Creature→William, Creature→Justine (keyword too broadly detected).

- Attempt 15 (Fix 2): Fixed `_surnames()` parenthesis handling in two locations
  - Root cause: `_surnames("the old man (De Lacey)")` returned `{"old", "man", "(de", "lacey)"}` — the closing parenthesis on "lacey)" caused no match with Felix De Lacey's "lacey". So old man↔Felix/Agatha failed the shared-surname check in `reject_unfounded_familial_labels()` and family labels were downgraded.
  - Fix: Changed `rstrip(".,")` to `strip("().,")` and used `len(p.strip("().,")) > 2` in both `_surnames()` functions.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **PARTIALLY WORKED** — Surname matching now works, but text verification assigns "father" in BOTH directions, triggering bidirectional parent → "sibling" conversion. Father→children relationship lost.

- Attempt 15 (Fix 3): Added hallucinated specific-label downgrade for non-co-occurring characters
  - Root cause: LLM profile generated "creator" for Felix→Victor (hallucination). Existing code had no mechanism to remove non-family specific labels for characters who barely share the text.
  - Fix: In `verify_relationships_from_text()`, added check: if specific non-family label AND detected evidence doesn't corroborate the label AND very low co-occurrence → downgrade to "associated".
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - **WORKED ✓** — Felix→Victor "creator" correctly removed.

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
| 14 | Bidirectional parent → surname-aware sibling/associated | `post_corrections.py` | Fixed ✓ |
| 14 | _propagate_missing_reverses ordering (run truly last) | `post_corrections.py` | Inconclusive |
| 15 | Non-family term text verification | `post_corrections.py` | Partial — "friend" too aggressive |
| 15 | _surnames() parenthesis handling | `post_corrections.py` | Partial — surnames match but bidir parent→sibling |
| 15 | Hallucinated non-co-occurring label downgrade | `post_corrections.py` | Fixed ✓ |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-15): TEN consecutive attempts modifying relationship post-corrections.
- The "friend" keyword scan is now the primary regression source — it correctly upgraded Victor↔Henry but incorrectly upgraded 4 other pairs.
- The bidirectional parent → sibling conversion works for ACTUAL siblings (Felix↔Agatha) but incorrectly converts parent↔child to sibling (Old Man↔Felix/Agatha).
- The core tension: text keyword matching is inherently direction-unaware and context-unaware. It detects keywords but can't determine WHO is the parent vs. WHO is the child, or whether "friend" describes the actual relationship vs. a contextual desire.

## Priority Fix Guidance for Attempt 16

### Fix Priority 1: Add minimum evidence threshold for "friend" upgrades (HIGH #1)

The "friend" keyword is too common in literary texts. It appears contextually (characters discussing friendship, seeking friends) without describing actual relationships. This causes false upgrades from "associated" to "friend".

**Root cause:** In `verify_relationships_from_text()`, any non-zero count of a relationship term in co-mention windows triggers an upgrade from "associated" to that term. For "friend", even 1-2 contextual hits are enough to trigger the upgrade.

**Fix:** Add a minimum evidence count threshold specifically for common/ambiguous terms like "friend", "companion", "beloved":
- If the detected term is "friend" or "companion", require at least 5 co-mention hits to upgrade (Victor↔Henry had 9 hits — genuine; Victor↔Creature likely had 2-3 — noise)
- For other terms (father, mother, sibling, mentor, creator, enemy), the current threshold (any evidence) is fine because these are rarely used contextually
- Location: `src/pipeline/character_profiling/post_corrections.py` — in the upgrade logic of `verify_relationships_from_text()`
- Alternatively, add a blocklist: never upgrade to "friend" when one character is the Creature and the other is a victim. But this is too novel-specific. The threshold approach is more generic.

**Expected outcome:**
- Victor↔Henry: "close friend" PRESERVED (9 hits > threshold)
- Victor↔Creature: remains "associated" (2-3 hits < threshold)
- William↔Creature: remains "associated" (low hits < threshold)
- Creature↔Justine: remains "associated" (low hits < threshold)

### Fix Priority 2: Direction-aware parent/child labeling in bidirectional parent fix (HIGH #2)

When `fix_bidirectional_parent_labels()` detects bidirectional parent labels with shared surnames, it currently converts both to "sibling". This is wrong when one character is clearly the parent (e.g., "the Old Man" is Felix's father).

**Fix:** In `fix_bidirectional_parent_labels()`, when shared surname is detected and bidirectional parent labels exist, add a heuristic to determine directionality:
1. Check if either character's canonical name contains age indicators: "old man", "elder", "senior", "père"
2. If one character has age indicators → assign that character as "parent" and the other as "child"
3. If neither has age indicators → keep "sibling" (default for same-generation shared surname)

This is a simple heuristic that handles the De Lacey case (canonical name literally contains "Old Man") without novel-specific hardcoding.

**Expected outcome:**
- Old Man (De Lacey)→Felix: "parent" (name contains "old man")
- Old Man (De Lacey)→Agatha: "parent" (name contains "old man")
- Felix→Old Man: "child"
- Agatha→Old Man: "child"
- Felix↔Agatha: "sibling" (neither has age indicator, no bidirectional parent)

### Do NOT attempt in attempt 16:
- Alphonse missing — LLM variability, not a code issue
- Victor's misattributed quotes — LLM limitation
- Victor/Creature physical descriptions — LLM limitation
- Ernest/Margaret canonical names — low impact
- "associated" epidemic broadly — fix #1 and #2 should bring Profiles to ~8.0; further "associated" reduction is polish

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all 5 stages ✓
- 0 parse failures ✓
- Ollama stable throughout entire run ✓
- 340 LLM calls, 610K tokens; 120m 53s total runtime ✓
- Summaries served from cache ✓

## Next Action
Run PROMPT_fix.md to address "friend" threshold (HIGH #1) and direction-aware parent labeling (HIGH #2)
