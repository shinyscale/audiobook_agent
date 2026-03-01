# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 8
- **Phase:** awaiting_analysis
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_081841/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗ ← primary blocker (REGRESSION from 6.5)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓ (improved from 7.5)
- **Overall: 7.83/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Changed from Attempt 7

### Fixes that WORKED
- **Fix 3 (Book title "Contents" → "Frankenstein ebook") WORKED:** HTML title now reads "Frankenstein ebook" derived from filename. ✓
- **Fix 4 (Letter 1 prologue classification) WORKED:** Letter 1 (null title) now appears as "Prologue 1" in Prologue Materials section. All 4 letters grouped as prologue. ✓
- Presentation improved: 7.5 → 8.5 (+1.0)

### Fixes that PARTIALLY WORKED
- **Fix 1 (summary-based relationship enrichment) PARTIALLY WORKED:** Added relationships for 5 previously-empty characters (Walton, Elizabeth, William, Margaret, Safie — Ernest still empty). However, many added relationships have WRONG labels:
  - Walton→Margaret: "sister" ✓ (correct)
  - Margaret→Walton: "sister" ✓ (correct)
  - Walton→Beaufort: "father" ✗ (WRONG — no family connection)
  - Victor→William: "father" ✗ (WRONG — they are BROTHERS)
  - William→Victor: "father" ✗ (WRONG — brothers)
  - Elizabeth→Beaufort: "associated" ✗ (WRONG — no direct relationship)
  - Justine→Beaufort: "associated" ✗ (persistent from attempt 7)
  - Beaufort→Walton: "son" ✗ (WRONG — reverse of wrong Walton→Beaufort)
  - Net effect: more relationships exist but many are WRONG → slight profiles regression

### Fixes that DID NOT WORK
- **Fix 2 (bidirectional parent → sibling) DID NOT WORK:** Felix↔Agatha still has bidirectional "father" (should be "sibling"). Victor↔William also has bidirectional "father" (should be "brother/sibling"). The fix either didn't execute, didn't match the conditions, or ran before the LLM profiler regenerated these labels. This is the most critical fix failure.

### New Regressions
- **Creature canonical name changed:** "the monster" (attempt 7) → "the fiend" (attempt 8, id: `split_the_fiend`). "the monster" is now COMPLETELY ABSENT from both canonical name and aliases. This is the most widely-recognized term for the creature.
- **Safie's relationships all "father":** Safie→Felix: "father", Safie→Agatha: "father", Safie→De Lacey: "father", Safie→the fiend: "father". All four are wrong. This appears to be a systematic LLM profiler failure.
- **Wrong De Lacey family labels persist:** Felix→Safie: "son", Agatha→Safie: "son", De Lacey→Safie: "son" — all wrong. Felix→Agatha: "father" — wrong (siblings).
- **Profiles REGRESSED:** 6.5 → 6.0. Wrong relationships are worse than missing relationships for narrator preparation. A narrator relying on these profiles would be misinformed about character relationships.

## What's Still Failing

### Profiles (6/10) — Primary Blocker

**Relationship label accuracy is severely broken.** Of ~37 total relationship entries, ~17 are correct/acceptable and ~20 are WRONG. Key problems:

1. **Bidirectional "father" unfixed (Fix 2 failure):**
   - Felix↔Agatha: both "father" (should be "sibling")
   - Victor↔William: both "father" (should be "brother/sibling")

2. **Safie has all "father" labels (LLM bug):**
   - Safie→Felix: "father" (should be "romantic interest")
   - Safie→Agatha: "father" (should be "friend/housemate")
   - Safie→De Lacey: "father" (should be "host/father figure")
   - Safie→the fiend: "father" (should be absent or "observer")

3. **Enrichment-generated wrong relationships:**
   - Walton→Beaufort: "father" — WRONG. The enrichment likely found "father" in summary text near both names but the "father" referred to Victor's father (Alphonse), not a Walton-Beaufort relationship.
   - Victor→William: "father" — WRONG. Same pattern — "father" found near both names in summary refers to their shared father Alphonse.
   - Elizabeth→Beaufort: "associated" — WRONG. No meaningful direct connection.

4. **Missing critical relationships:**
   - Victor↔Elizabeth: romantic/fiancée/wife — THE central romance. STILL ABSENT.
   - Victor↔Henry: friendship — Victor's closest friend. STILL ABSENT.
   - De Lacey→Felix/Agatha: father-son/father-daughter — MISLABELED as other things.
   - Felix→Safie: romantic interest — LABELED "son" instead.

5. **Physical descriptions: 7/19, Speech patterns: 0/19**

### Characters (7.5/10) — Close to Passing

1. **Alphonse Frankenstein STILL MISSING** — 4th consecutive attempt without him. Victor's father is referenced by name in chapter summaries. This has been inconsistent (appeared in attempts 4-5 but not since).

2. **"the monster" completely absent** — was the canonical name in attempt 7, now neither canonical nor alias. The creature is `split_the_fiend` with aliases "the wretch", "the creature". Missing: "the monster" (most common reference), "the daemon/dæmon".

3. **Caroline Beaufort/Frankenstein still missing** — persistent across all 8 attempts.

## Current Issues (Priority Order)

### CRITICAL

1. **Fix 2 (bidirectional parent → sibling) DID NOT EXECUTE** [Profiles]
   - Problem: Felix↔Agatha and Victor↔William still have bidirectional "father" labels. The `fix_bidirectional_parent_labels` method from attempt 8 either didn't run, didn't match conditions, or was overwritten by later pipeline steps.
   - Evidence: 4 character pairs have A→B: "father" AND B→A: "father", which is logically impossible.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `fix_bidirectional_parent_labels()`
   - Debug approach: Add logging to confirm the method executes and matches the expected patterns. Check if it runs AFTER the LLM profiler and AFTER the enrichment (which may be re-introducing "father" labels). Check method signature — is it being called in `run_all()`?
   - Impact: Fixing this alone could convert ~4 wrong "father" pairs to correct "sibling" labels (+0.5 on Profiles).

2. **Summary enrichment assigns wrong relationship labels** [Profiles]
   - Problem: `enrich_zero_relationships_from_summaries` uses `_rel_phrase_re` to find family terms near character name co-occurrences. But when summary text says "his father Alphonse" near mentions of Victor and William, the regex matches "father" and assigns it to Victor→William — which is WRONG (they're brothers; "father" refers to their shared parent Alphonse).
   - Evidence: Walton→Beaufort: "father", Victor→William: "father", Elizabeth→Beaufort: "associated" — all wrong enrichment outputs.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enrich_zero_relationships_from_summaries()`
   - Fix approaches:
     A) **Remove or disable enrichment** — it's causing more harm than good. The 2 correct additions (Walton↔Margaret) don't outweigh ~6 wrong ones.
     B) **Fix label extraction** — instead of regex-matching the first family term found between two names, require the family term to syntactically refer to one of the two characters (e.g., "his sister Margaret" → the "sister" refers to Margaret relative to Walton).
     C) **Restrict to high-confidence patterns only** — only enrich when the summary explicitly states "X's [label] Y" or "X, Y's [label]" patterns.
   - Impact: Removing wrong enrichment could raise Profiles from 6.0 to ~6.5-7.0.

### HIGH

3. **Victor↔Elizabeth relationship STILL missing** [Profiles]
   - Problem: The central romantic relationship of the novel is absent. Elizabeth has 92 mentions. The enrichment was supposed to catch this but assigned her a wrong Beaufort relationship instead.
   - Evidence: Elizabeth is Victor's fiancée/adopted sister/wife. They appear together in many chapters.
   - Location: `src/pipeline/character_profiling/post_corrections.py` or `src/analyzer.py`
   - Fix: If enrichment is fixed to use better patterns, "Victor" and "Elizabeth" co-occurring with marriage/bride/wife language should produce the correct relationship.
   - Impact: +0.25 on Profiles.

4. **Safie has all "father" labels — LLM systematic failure** [Profiles]
   - Problem: The LLM profiler assigned "father" to all 4 of Safie's relationships. Felix→Safie is "son", Agatha→Safie is "son", De Lacey→Safie is "son" — all wrong.
   - Evidence: Safie is Felix's romantic interest who comes to the De Lacey cottage. She is NOT their child.
   - Root cause: The LLM is confusing the De Lacey family structure. Since De Lacey IS the father of Felix and Agatha, the profiler may be generalizing "father" to all relationships in that household.
   - Location: LLM profiler prompt or post-corrections
   - Fix: Post-correction validation — if a character has 4+ relationships ALL with the same label, and that label is asymmetric ("father", "son"), flag as suspicious and remove or replace with "associated".
   - Impact: +0.25 on Profiles.

5. **"the monster" completely absent from creature entry** [Alias Grouping]
   - Problem: The creature's canonical name changed from "the monster" (attempt 7) to "the fiend" (attempt 8). "the monster" is not even an alias. This is the most widely-recognized reference.
   - Evidence: The novel uses "monster" extensively — Victor calls his creation "the monster" repeatedly.
   - Location: Creature entry is `split_the_fiend` — came from semantic split pipeline. The split key determined the canonical name.
   - Fix: Ensure "the monster" appears at minimum as an alias on the creature entry. The semantic split may need to include commonly-used descriptors that were blocked or consumed during main cast extraction.

### MEDIUM

6. **Henry Clerval→M. Krempe: "associated" — persistent wrong relationship** [Profiles]
   - Henry and Krempe have no direct narrative connection. Henry is Victor's friend; Krempe is Victor's professor.
   - Location: LLM profiler or post-corrections
   - Fix: Add co-occurrence validation — if two characters never appear in the same chapter summary, remove their relationship.

7. **Alphonse Frankenstein missing — 4th consecutive attempt** [Completeness]
   - Victor's father, referenced by name in summaries. F6 reconciliation found him in attempts 4-5 but not since.
   - Location: `src/analyzer.py` — F6 reconciliation
   - This issue has been attempted 3 times across different files without lasting fix. May need escalation.

8. **Supporting characters lack full canonical names** [Alias Grouping]
   - Ernest → should be "Ernest Frankenstein"
   - Margaret → should be "Margaret Saville"

9. **Wrong De Lacey family labels: Felix→Safie "son", Agatha→Safie "son"** [Profiles]
   - These are wrong — Safie is not their child. Felix is her romantic interest.
   - Partially overlaps with issue #4 (Safie's "father" labels are the reverse of these "son" labels).

### LOW

10. **Physical descriptions: 7/19** — many major characters (Victor, Henry, Walton) lack physical descriptions, though this partly reflects the source text.
11. **Speech patterns: 0/19** — no speech_pattern fields populated.
12. **Caroline Beaufort/Frankenstein still missing** — persistent 8 attempts.
13. **Cornelius Agrippa and Werter as character entries** — historical/literary figures, not harmful.

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
  - PARTIALLY WORKED — added Walton↔Margaret "sister" ✓ but also added ~6 wrong relationships (Walton→Beaufort "father", Victor→William "father", etc.) ✗

- Attempt 8 (Fix 2): Bidirectional parent label → sibling conversion
  - New method `fix_bidirectional_parent_labels` in `OutputCharacterCorrector`
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - DID NOT WORK — Felix↔Agatha and Victor↔William still bidirectional "father"

- Attempt 8 (Fix 3): Book title "Contents" fallback to filename
  - Modified: `src/ingestion/txt.py`
  - WORKED ✓

- Attempt 8 (Fix 4): Letter 1 null title → prologue classification
  - Modified: `src/export/html_report.py`
  - WORKED ✓

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
| 8 | Bidirectional parent→sibling | `post_corrections.py` | DID NOT WORK |
| 8 | Book title "Contents" | `txt.py` | Fixed ✓ |
| 8 | Letter 1 prologue classification | `html_report.py` | Fixed ✓ |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-8): Relationship corrections have been fragile. Three consecutive attempts at fixing relationship labels: contradictory removal over-fired (attempt 6), symmetric labels partial (attempt 7), enrichment added wrong labels + bidirectional fix didn't work (attempt 8). **This file needs careful debugging, not new methods.**
- Profile generation is the persistent primary blocker since attempt 4. The LLM consistently fails to generate correct relationship labels for the De Lacey family and for characters like Safie.

## Priority Fix Guidance for Attempt 9

### Fix Priority 1: Debug and fix `fix_bidirectional_parent_labels` (CRITICAL #1) — Profiles +0.5 expected

This is the highest-ROI fix because the method was already written but didn't execute properly. Steps:
1. Read the method in `post_corrections.py` — verify the logic
2. Check if it's called in `run_all()` — verify execution order
3. Add a print/log statement to confirm it runs during analysis
4. Verify it runs AFTER both the LLM profiler AND the enrichment (otherwise the enrichment may re-introduce "father" labels after the fix runs)
5. Check if the method matches on the relationship dict structure correctly (key names vs character objects)

If the method runs but doesn't match: fix the matching logic.
If the method doesn't run: wire it into `run_all()`.

### Fix Priority 2: Fix or remove `enrich_zero_relationships_from_summaries` (CRITICAL #2) — Profiles +0.5 expected

The enrichment is causing more harm than good. Options:
A) **REMOVE IT** — simplest. The 2 correct relationships (Walton↔Margaret) aren't worth the ~6 wrong ones.
B) **Fix the label extraction** — the regex is matching family terms that refer to a THIRD character (e.g., "his father Alphonse" near Victor and William → assigns "father" to Victor→William). Fix by requiring the family term to syntactically describe one of the two characters, not a third.
C) **Restrict to symmetric-only enrichment** — only add "sibling"/"associated" labels (never asymmetric ones like "father"/"son") since these are lower risk.

Recommendation: Option A (remove). The enrichment approach is fundamentally flawed — regex-based label extraction from summaries cannot reliably determine WHICH character the family term describes. The LLM profiler should be the source of relationship labels, and post-corrections should only clean/validate them, not invent new ones.

### Fix Priority 3: Fix wrong De Lacey/Safie relationship labels (HIGH #4) — Profiles +0.25 expected

Add a post-correction rule: if a character has 3+ relationships ALL with the same asymmetric label (e.g., all "father" or all "son"), replace with "associated" since the labels are clearly wrong. No real character has the same relationship type with 3+ other characters.

### Do NOT attempt in attempt 9:
- Alphonse missing — 4 attempts without lasting fix. Low ROI.
- "the monster" missing from creature — varies across runs. Low ROI vs profile fixes.
- Caroline missing — persistent 8 attempts. Accept as limitation.
- Victor↔Elizabeth — focus on fixing existing wrong relationships first. If enrichment is removed, this stays missing but won't be WRONG.
- Henry→Krempe "associated" — low impact compared to profile fixes.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- No configuration changes recommended — profile post-corrections are the primary issue, not model config

## Attempt 9 Fixes Applied

### Fix 1: Move `fix_bidirectional_parent_labels` to after text verification
- **Root cause:** `verify_relationships_from_text` (line 723) ran AFTER `fix_bidirectional_parent_labels` (line 720) and overrode "sibling" back to "father". The source text contains "father" near co-mentioned siblings (e.g., De Lacey is their father, so "father" appears near Felix and Agatha) — the regex matched the wrong "father".
- **Fix:** Move `fix_bidirectional_parent_labels` call to after BOTH `verify_relationships_from_text` AND `reject_unfounded_familial_labels`.
- **Modified:** `src/pipeline/character_profiling/post_corrections.py` — `run_all()` order
- **Expected impact:** Felix↔Agatha and Victor↔William bidirectional "father" → "sibling" (+0.5 Profiles)

### Fix 2: Remove `enrich_zero_relationships_from_summaries` from `run_all`
- **Root cause:** The enrichment used regex to find family terms near character co-occurrences in summaries, but the regex matched "father" that referred to a THIRD character (Alphonse near Victor+William, De Lacey near Safie+Felix). Additionally, `reject_unfounded_familial_labels` correctly removed Safie's wrong "father" labels, but the enrichment ran LAST and re-added them since Safie became zero-relationship.
- **Fix:** Remove `enrich_zero_relationships_from_summaries` from `run_all`. The 2 correct relationships it added (Walton↔Margaret "sister") don't outweigh the ~6 wrong ones it introduced. The method code is preserved in case it's needed later.
- **Modified:** `src/pipeline/character_profiling/post_corrections.py` — `run_all()` order
- **Expected impact:** Removes Walton→Beaufort:"father", Beaufort→Walton:"son", Elizabeth→Beaufort:"associated", Justine→Beaufort:"associated", and prevents Safie's all-"father" labels from being re-added after `reject_unfounded_familial_labels` removes them (+0.5 Profiles)

## Next Action
Re-run analysis to verify fix.
