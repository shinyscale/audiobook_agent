# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 14
- **Phase:** awaiting_analysis
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260302_024636/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING — 70/87 relationships are "associated"; one hallucinated relationship)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.28/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles)

## What Changed from Attempt 13

### Fixes Verified
- **Fix 1 (Surname-aware bidirectional parent):** WORKED ✓. Felix↔Agatha now correctly "sibling" (both share "De Lacey" surname). Regression from attempt 13 is reversed.
- **Fix 2 (_propagate_missing_reverses ordering):** INCONCLUSIVE. Walton→Margaret and Margaret→Walton both show "associated". The LLM did not generate "sister"/"brother" for either direction this run, so there was nothing to propagate. The fix may be correct but untestable this attempt.

### Net Effect on Profiles
- Restored: Felix↔Agatha "sibling" ✓ (+0.25 from attempt 13's regression)
- Unchanged: Walton↔Margaret still "associated" (LLM didn't generate a family label to propagate)
- Unchanged: 70/87 relationships are "associated" (systemic issue)
- New: Felix→Victor "creator" hallucination (was not present in attempt 13)
- Net: Profiles 7.5/10 (same as attempt 13 — sibling fix balanced by new hallucination)

## Current Issues (Priority Order)

### CRITICAL

*(none)*

### HIGH

1. **"associated" label epidemic — 80% of all relationships** [Profiles - Relationships]
   - Problem: 70 out of 87 relationship entries are labeled "associated". This is technically correct but useless for narrator preparation. A narrator needs to know "Victor and Elizabeth are engaged" not "Victor and Elizabeth are associated."
   - Key missing labels:
     - Victor↔Elizabeth: "associated" → should be "fiancée" or "romantic interest"
     - Victor↔Henry Clerval: "associated" → should be "friend" (best friend)
     - Victor↔Ernest: "associated" → should be "sibling" (brother)
     - Victor↔Caroline Beaufort: "associated" → should be "child"/"parent" (she's his mother)
     - Old man De Lacey↔Felix/Agatha: "associated" → should be "parent"/"child" (father/children)
     - Walton↔Margaret: "associated" → should be "sibling" (brother/sister)
   - Root cause: The LLM profiler generates "associated" as a safe default, AND `reject_unfounded_familial_labels` downgrades specific labels to "associated" when surname evidence is weak. The combination floods the output with generic labels.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `reject_unfounded_familial_labels()` is too aggressive. Also, the LLM prompt in `src/analyzer.py` `_generate_character_profile()` may need to encourage more specific labels.
   - Impact: This is the PRIMARY blocker preventing Profiles from reaching 8.0.
   - Suggested approach: Two-pronged fix:
     1. In `reject_unfounded_familial_labels()`: Relax the surname requirement — allow "sibling"/"parent"/"child" when characters co-occur frequently AND the LLM originally chose a family label (the LLM saw the text; trust its label more)
     2. OR add a new post-correction step `upgrade_known_relationships()` that upgrades "associated" to more specific labels for character pairs that co-occur in many chapters, using summary text as evidence (e.g., if summaries mention "friend", "father", "fiancée" near both names)

2. **Felix→Victor "creator" — hallucinated relationship** [Profiles - Accuracy]
   - Problem: Felix De Lacey has a "creator" relationship with Victor Frankenstein. Felix and Victor never interact in the novel. This appears to be an LLM confusion — the "creator" label belongs to monster→Victor, not Felix→Victor.
   - Evidence: Felix's chapters (11-16) are in the creature's embedded narrative. Victor doesn't appear in the De Lacey scenes.
   - Location: LLM profiler output, not caught by post-corrections.
   - Fix: Add validation that rejects relationship labels between characters who never co-occur in any chapter. If char_a and char_b appear in zero shared chapters, their relationship is suspect and should be removed or downgraded.

### MEDIUM

3. **Elizabeth alias "more than sister"** [Character Extraction - Alias Grouping]
   - Problem: Elizabeth Lavenza has alias "more than sister" which is a descriptive phrase Victor uses, not an actual name/alias.
   - Evidence: Victor describes Elizabeth as "more than sister" in his narrative, but nobody addresses her by this phrase.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias extraction
   - Impact: Minor — doesn't cause confusion but looks wrong in output.

4. **Alphonse Frankenstein absent (LLM variability)** [Character Extraction - Completeness]
   - Problem: Alphonse (Victor's father) was present in attempt 12 with 10 mentions, now absent. No code changes to character extraction were made.
   - Evidence: 20 characters extracted, Alphonse not among them. He appears in chapters 1, 2, 6, 7, 22, and his death is a plot point.
   - Location: LLM variability in `src/pipeline/character_extraction_v2/` — not a code bug.
   - Impact: Characters 8.0 (still passing). Do NOT attempt a code fix.

5. **Victor's misattributed example quotes (2/3 wrong)** [Profiles - Voice Guidance]
   - Problem: Victor's voice_guidance.example_quotes include Walton's "I have no friend, Margaret" and possibly other misattributed lines.
   - Accept as LLM limitation. Do NOT attempt to fix.

6. **De Lacey family relationships all "associated"** [Profiles - Relationships]
   - Problem: Old man De Lacey↔Felix and De Lacey↔Agatha are "associated" instead of "parent"/"father".
   - Subsumed by HIGH #1 — the "associated" epidemic fix should address this.

7. **Elizabeth→Caroline "favorite" — odd label** [Profiles - Relationships]
   - Problem: "favorite" is an unusual relationship label. Caroline was Elizabeth's adoptive mother.
   - Minor — "favorite" is not wrong (Caroline did especially favor Elizabeth) but it's not the primary relationship.

### LOW

8. Ernest and Margaret lack full canonical names (Ernest Frankenstein, Margaret Walton Saville).
9. Letter 1 title null in JSON (displayed correctly as "Prologue 1" in HTML).
10. Creature role "antagonist" — debatable; is also narrator and protagonist of own embedded narrative.
11. Victor's verbal_tics includes empty string "".
12. Monster's physical_description very sparse ("Miserable deformity; fiend's grasp") — text describes 8-foot tall, yellow watery eyes, black lips in detail.
13. 6 pronunciation entries missing IPA (desert, lead, produce, and 3 others).

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

**Recurring patterns:**
- `post_corrections.py` (attempts 6-14): NINE consecutive attempts modifying relationship post-corrections.
- The "associated" epidemic has persisted since co-occurrence enrichment was added in attempt 10. The enrichment adds "associated" → post-corrections fail to upgrade → output is flooded.
- The LLM profiler prompt (in `analyzer.py`) was last modified in attempt 5. The prompt may need revisiting.

## Priority Fix Guidance for Attempt 15

### Fix Priority 1: Reduce "associated" label prevalence (HIGH #1)

The core problem is that 80% of relationships are "associated". Two approaches (choose based on investigation):

**Approach A — Relax `reject_unfounded_familial_labels()`:**
Currently, this method downgrades family labels to "associated" when characters don't share a surname. But many genuine family relationships don't share surnames (Victor↔Caroline Beaufort, Old man De Lacey↔Felix when name parsing is imprecise). Consider:
- Trust the LLM's original label when character pair co-occurs in 3+ chapters
- Only reject family labels when co-occurrence is very low (0-1 chapters)

**Approach B — Add `upgrade_associated_from_summaries()` post-correction:**
After all rejections are done, scan chapter summaries for relationship evidence between "associated" pairs. If summaries contain "friend", "father", "mother", "fiancée", "brother", "sister", etc. near both character names, upgrade "associated" to the detected relationship.

**Approach C — Improve LLM profiler prompt:**
In `src/analyzer.py` `_generate_character_profile()`, the prompt may be generating "associated" too freely. Instruct it to use specific labels: "friend", "sibling", "parent", "child", "romantic interest", "mentor", "rival", "employer", "servant", etc. Make "associated" a last resort, not a default.

**Location:** `src/pipeline/character_profiling/post_corrections.py` and/or `src/analyzer.py`

**Expected outcome:** Victor↔Elizabeth → "fiancée"/"romantic interest", Victor↔Henry → "friend", Victor↔Ernest → "sibling", De Lacey↔Felix/Agatha → "parent"/"child"

### Fix Priority 2: Remove Felix→Victor "creator" hallucination (HIGH #2)

Felix De Lacey has no interaction with Victor Frankenstein in the novel. The "creator" label is clearly confused from monster→Victor.

Fix: Add a co-occurrence check in post-corrections. If two characters never appear in the same chapter (zero co-occurrence), remove or downgrade suspicious labels. "associated" from co-occurrence enrichment is fine (it's explicitly co-occurrence-based), but specific labels like "creator", "mentor", "sibling" etc. should require at least 1 shared chapter.

**Location:** `src/pipeline/character_profiling/post_corrections.py` — new method `reject_non_cooccurring_specific_labels()`

### Do NOT attempt in attempt 15:
- Alphonse missing — LLM variability, not a code issue
- Victor's misattributed quotes — LLM limitation
- Elizabeth "more than sister" alias — minor, non-blocking
- Creature role "antagonist" — low impact
- Monster's sparse physical description — LLM limitation

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all 5 stages ✓
- 0 parse failures ✓
- Ollama stable throughout entire run ✓
- 364 LLM calls total, 682K tokens
- 128m 33s total runtime
- Summaries served from cache ✓

## Pipeline Notes (Attempt 14)
- 28 chapters detected ✓
- 20 character profiles generated for 20 eligible characters ✓
- NOTABLE: Many creature aliases BLOCKED — "the fiend", "the wretch", "the demon", "the daemon", "the being", etc. blocked as not found in summaries
- NOTABLE: Elizabeth Lavenza has alias "more than sister" (odd, likely hallucination)
- Output directory: output/Frankenstein_ebook_20260302_024636/
- 0 Ollama crashes ✓

## Fix History (Attempt 15 additions)

- Attempt 15 (Fix 1): Extended `verify_relationships_from_text()` to detect non-family relationship terms
  - Root cause: `_rel_phrase_re` only matched FAMILY_TERMS; "friend", "betrothed", "rival", "mentor", etc. were invisible to the method.
  - Fix: Added `_all_rel_phrase_re` combining FAMILY_TERMS + non-family terms ("friend", "companion", "betrothed", "beloved", "rival", "enemy", "mentor", "creator", etc.) with extended prefix pattern ("my best friend", "my old friend", "my dearest friend")
  - Upgrade logic: family evidence → override any label (preserves "brother"→"cousin" override); generic labels ("associated") → upgrade to any detected term; specific non-family labels → NOT overridden by non-family evidence (prevents spurious "creation"→"friend")
  - Smoke test: PASS — Victor→Henry detects "friend" (9 occurrences dominate); old man→Felix detects "father" (10 occurrences); Victor→monster "creation" preserved; Felix→Victor "creator" downgraded
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

- Attempt 15 (Fix 2): Fixed `_surnames()` parenthesis handling in two locations
  - Root cause: `_surnames("the old man (De Lacey)")` returned `{"old", "man", "(de", "lacey)"}` — the closing parenthesis on "lacey)" caused no match with Felix De Lacey's "lacey". So old man↔Felix/Agatha failed the shared-surname check in `reject_unfounded_familial_labels()` and family labels were downgraded.
  - Fix: Changed `rstrip(".,")` to `strip("().,")` and used `len(p.strip("().,")) > 2` in both `_surnames()` functions (in `fix_bidirectional_parent_labels()` and `reject_unfounded_familial_labels()`).
  - Smoke test: PASS — "the old man (De Lacey)" now shares "lacey" surname with "Felix De Lacey" and "Agatha De Lacey"
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

- Attempt 15 (Fix 3): Added hallucinated specific-label downgrade for non-co-occurring characters
  - Root cause: LLM profile generated "creator" for Felix→Victor (hallucination). Existing code had no mechanism to remove non-family specific labels for characters who barely share the text.
  - Fix: In `verify_relationships_from_text()`, added check: if specific non-family label AND detected evidence doesn't corroborate the label (`found.get(cur_lower, 0) == 0`) AND very low co-occurrence (`comention_count <= 1`) → downgrade to "associated". Also added zero co-occurrence downgrade for the empty-evidence case.
  - Smoke test: PASS — Felix→Victor "creator" correctly downgraded to "associated" (1 co-mention, "creator" never appears in that window; corroborating label count = 0). Victor→monster "creation" preserved (creator: 2 in windows).
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

### Expected outcomes of attempt 15 fixes:
- Victor→Henry Clerval / Henry→Victor: "associated" → "friend" ✓
- Old man (De Lacey) → Felix/Agatha: "associated" → "father" ✓ (preserved by shared "lacey" surname)
- Felix/Agatha → old man (De Lacey): "associated" → "son"/"daughter" (from reverse text evidence)
- Felix→Victor "creator": "creator" → "associated" ✓ (hallucination removed)
- Victor→Elizabeth: likely still "associated" (window contamination from "my father Alphonse" in co-mention scenes)
- Walton→Margaret: likely still "associated" (first-person letter narration prevents direct name co-mention near "sister")

## Next Action
Set phase to awaiting_analysis
