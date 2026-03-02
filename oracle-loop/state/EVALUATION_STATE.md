# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 12
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_220344/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING — relationship label errors)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles)

## What Improved from Attempt 11

Massive improvements:
- **Ollama stable:** 20/20 profiles generated (19 high, 1 low) vs 4/19 in attempt 11
- **Co-occurrence enrichment WORKING:** 20/20 characters have relationships (vs 4/19)
- **Dæmon alias FIX CONFIRMED:** "the dæmon" correctly on creature, removed from De Lacey
- **Alphonse Frankenstein FOUND:** Back after 7 consecutive absences (10 mentions)
- **Personality + voice guidance:** All 20 characters have personality data + voice guidance (excellent quality)
- **All zero-retry pipeline run:** 349 LLM calls, 0 retries, 0 JSON parse failures

## What Still Needs Fixing (Profiles Only)

The ONLY failing category is Profiles (7/10). The profile generation itself is excellent — personality, voice guidance, speech patterns are all high quality. The issue is **relationship label accuracy**.

### Relationship Errors Found

1. **Victor↔Alphonse: "sibling"** — WRONG. Alphonse is Victor's FATHER.
   - Victor→Alphonse: "sibling" (should be "child")
   - Alphonse→Victor: "sibling" (should be "parent")
   - Root cause: `fix_bidirectional_parent_labels` converts bidirectional "parent" claims to "sibling". The LLM incorrectly said both are parents of each other → post-correction converted to "sibling" → `reject_unfounded_familial_labels` preserved it because they share surname "Frankenstein".

2. **Safie↔Beaufort: "parent"/"child"** — WRONG. Beaufort is Caroline Beaufort's father (Victor's maternal grandfather), NOT Safie's parent. Safie's father is the Turkish merchant.
   - Safie→Beaufort: "parent"
   - Beaufort→Safie: "child"
   - Root cause: LLM profiler hallucinated this relationship. `reject_unfounded_familial_labels` (with attempt 12 fix) should have downgraded to "associated" since they don't share a surname, but didn't. Possible bug in the downgrade logic.

3. **Walton→Margaret: missing** — Walton's relationships only contain `{"Victor Frankenstein": "associated"}`. Margaret→Walton correctly has "sister", but Walton doesn't have the reciprocal.
   - Root cause: Co-occurrence enrichment added Victor (from shared letter chapters) but missed Margaret. Or: the LLM profiler only generated one relationship for Walton and co-occurrence didn't add Margaret because Walton's letters are addressed TO Margaret (she's not mentioned BY NAME in summaries?).

4. **Victor's example_quotes: 2/3 misattributed**
   - "You wish to eat me and tear me to pieces. You are an ogre." — This is William Frankenstein's line (child speaking to creature in Ch. 16)
   - "Farewell, Frankenstein! If thou wert yet alive..." — This is the creature's final soliloquy
   - Only "I, not in deed, but in effect, was the true murderer." is actually Victor's
   - Root cause: LLM profiler misattributed quotes from narrated speech to the narrator

5. **De Lacey family "associated"** — Felix→De Lacey, Agatha→De Lacey, De Lacey→Felix, De Lacey→Agatha are all "associated" instead of parent/child. Only Felix↔Agatha correctly shows "sibling".

## Current Issues (Priority Order)

### CRITICAL

1. **`fix_bidirectional_parent_labels` converts parent/child to "sibling" incorrectly** [Profiles - Relationships]
   - Problem: When LLM labels both directions as "parent" (which is wrong), the fix converts both to "sibling". For Victor↔Alphonse, this creates a factually wrong "sibling" label. The LLM was wrong to say both are parents, but the correction is ALSO wrong.
   - Evidence: Victor→Alphonse: "sibling", Alphonse→Victor: "sibling". Should be parent/child.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `fix_bidirectional_parent_labels()`
   - Fix: Change the method to downgrade bidirectional "parent" claims to "associated" instead of "sibling". This prevents the wrong label. The narrator sees "associated" (neutral) rather than "sibling" (wrong). Alternatively: when converting, check summaries for "father"/"mother"/"son"/"daughter" keywords near both names to determine the correct direction.
   - Impact: Profiles 7/10 → 7.5/10 (removes most egregious error)

### HIGH

2. **`reject_unfounded_familial_labels` not catching Safie↔Beaufort "parent"** [Profiles - Relationships]
   - Problem: Safie and Beaufort don't share a surname. The attempt 12 fix should downgrade non-sibling familial labels without shared surname to "associated". But "parent"/"child" between Safie and Beaufort survived.
   - Evidence: Safie→Beaufort: "parent", Beaufort→Safie: "child". Should be no relationship or "associated".
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `reject_unfounded_familial_labels()`
   - Fix: Debug why the method didn't catch "parent"/"child" labels between Safie and Beaufort. The downgrade logic may only handle specific labels (e.g., "wife"/"husband") and not "parent"/"child". Ensure ALL familial labels are covered.
   - Impact: Profiles +0.25 (removes hallucinated relationship)

3. **Walton missing Margaret relationship** [Profiles - Relationships]
   - Problem: Walton has only `{"Victor Frankenstein": "associated"}`. Margaret→Walton is "sister" but the reciprocal doesn't exist.
   - Evidence: Robert Walton writes ALL letters to Margaret, she's his sister. This should be the most prominent relationship.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — likely a gap in the bidirectional relationship enforcement
   - Fix: The `fix_bidirectional_parent_labels` or a new method should ensure that if A→B has a familial label, B→A also gets the reciprocal. Margaret→Walton "sister" should create Walton→Margaret "sibling".
   - Impact: Profiles +0.25

### MEDIUM

4. **Victor's misattributed example quotes (2/3 wrong)** [Profiles - Voice Guidance]
   - Problem: LLM profiler attributed William's and creature's quotes to Victor. Hard to fix generically.
   - Accept as LLM limitation. Do NOT attempt to fix in attempt 13.

5. **De Lacey family all "associated" instead of parent/children** [Profiles - Relationships]
   - Problem: Felix, Agatha, and De Lacey senior are all "associated" with each other (except Felix↔Agatha "sibling"). The parent/child relationships are missing.
   - Root cause: Co-occurrence added "associated", LLM didn't provide specific labels for this family.
   - Accept for now — "associated" is not wrong, just generic. Fixing CRITICAL #1 is more impactful.

6. **Creature role "supporting" instead of "main"** [Character Extraction]
   - Recurring issue. The creature is a narrator and protagonist. Role should be "main".
   - Low impact on overall score. Accept.

### LOW

7. Ernest and Margaret lack full canonical names (Ernest Frankenstein, Margaret Walton Saville).
8. Letter 1 title null in JSON (displayed correctly as "Prologue 1" in HTML).
9. Elizabeth's voice guidance has incomplete quote: `"I wish,"` — truncated.
10. Elizabeth Lavenza profile flagged as low confidence ("lacks evidence").

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

**Recurring patterns:**
- `post_corrections.py` (attempts 6-12): SEVEN consecutive attempts. The method ordering and interaction effects are the core challenge.
- The relationship post-correction chain has complex interactions: co-occurrence → verify → reject → bidirectional fix. Each fix in one step can be undone by another step.

## Priority Fix Guidance for Attempt 13

### Fix Priority 1: Change `fix_bidirectional_parent_labels` to downgrade to "associated" (CRITICAL #1)

Instead of converting bidirectional "parent" claims to "sibling", downgrade to "associated". This prevents the Victor↔Alphonse error. "Associated" is neutral and correct; "sibling" is wrong.

**Location:** `src/pipeline/character_profiling/post_corrections.py` — `fix_bidirectional_parent_labels()`

### Fix Priority 2: Debug `reject_unfounded_familial_labels` for "parent"/"child" (HIGH #2)

Verify the method handles ALL familial labels including "parent" and "child", not just "wife"/"husband" or "sibling". If the label list is incomplete, add "parent" and "child" to the checks. Safie↔Beaufort "parent"/"child" should be downgraded to "associated" (no shared surname).

**Location:** `src/pipeline/character_profiling/post_corrections.py` — `reject_unfounded_familial_labels()`

### Fix Priority 3: Ensure bidirectional familial labels (HIGH #3)

If Margaret→Walton has "sister", ensure Walton→Margaret gets "sibling" reciprocal. This might already be handled by `fix_bidirectional_parent_labels` or another method, but the current output shows it's not working for this pair.

**Location:** `src/pipeline/character_profiling/post_corrections.py`

### Do NOT attempt in attempt 13:
- Victor's misattributed quotes — LLM profiler limitation, hard to fix generically
- De Lacey family "associated" labels — "associated" is not wrong, just generic
- Creature "supporting" role — low impact
- Ernest/Margaret full names — low priority

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- 0 JSON parse failures ✓
- Ollama stable throughout entire run (197m54s)
- Bottleneck: Chapter Summaries (34% of time — cached from previous run)
- 1 quality concern: Elizabeth Lavenza low-confidence profile

## Next Action
Run PROMPT_fix.md to address relationship label errors in post_corrections.py (Fixes 1-3)
