# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_031042/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 7/10
  - Alias Grouping: 6/10
- Character Profiles: 5.5/10 ✗ ← REGRESSION from 6.5
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 7.5/10 ✗
- **Overall: 7.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 6.5, Profiles 5.5, Presentation 7.5)

## What Improved from Attempt 5

- **Fix 1 (dæmon/monster false split) WORKED:** No separate "the dæmon" entry. F6 ligature normalization (æ→ae) correctly matched dæmon to the daemon synonym group. ✓
- **Fix 2 (Turk/old man false merge) WORKED:** "the Turk" is now a separate character (0a5ef5ac589f, 9 mentions). The canonical_base stripping of parenthetical in verify_aliases worked. ✓
- **Fix 4 (Pronunciation false positives) WORKED:** sympathised, sympathise, sympathising, slothful, than — all gone from pronunciation list. 0 false positives from previous attempt remain. ✓
- **Pronunciation improved: 8.0/10** (up from 7.5/10). Now passes threshold. ✓

## What Regressed or Failed

- **REGRESSION: Character Profiles dropped 6.5→5.5.** Fix 3 (`remove_contradictory_relationships`) over-fired. It removes ALL pairs where A→B and B→A share the same label, including valid symmetric relationships like "romantic interest"↔"romantic interest" and "sibling"↔"sibling". This stripped Victor↔Elizabeth, Walton↔Margaret, and likely other valid pairs.
- **NEW: Victor→creature labeled "romantic interest"** — a hallucination. Victor is the creature's CREATOR. This is prominently displayed in the relationship grid.
- **REGRESSION: Alphonse Frankenstein MISSING** — was present in attempts 4-5 (F6 reconciliation). Now gone. Summaries still mention "Alphonse" but F6 didn't extract him this time.
- **NEW: "I" extracted as a character** (dd7536794b63, 3157 mentions) — the first-person pronoun, not a character. F6 reconciliation noise.
- **PERSISTENT: "De Lacey" is a false alias of "the creature"** — De Lacey is the old man's surname. The creature is NOT De Lacey. Felix De Lacey also claims "De Lacey" as alias — Rule 3 should block the duplicate but isn't firing.
- **PERSISTENT: "Professor Krempe" is a false alias of M. Waldman** — Krempe exists as a separate character (split_m_krempe). These are two different professors at Ingolstadt.
- **PERSISTENT: Felix→Agatha: "father" — WRONG** (siblings). Same error as attempt 5.
- **PERSISTENT: William→Victor: "father" — WRONG** (Victor is William's brother, not father).
- **Caroline Beaufort/Frankenstein still missing** (persistent since attempt 1).

## Current Issues (Priority Order)

### CRITICAL

1. **REGRESSION: `remove_contradictory_relationships` over-fires on symmetric labels** [Profiles]
   - Problem: The post-correction removes ALL bidirectional pairs where A→B and B→A share the same label. But symmetric relationships (sibling, romantic interest, colleague, friend, associated) are VALID when both directions have the same label. Only asymmetric labels (parent, creator, mentor, master) are contradictory when bidirectional.
   - Evidence: Victor→Elizabeth "romantic interest" was removed (both had it). Walton→Margaret "sibling" was removed. Felix→Agatha "sibling" was removed. But Waldman↔Krempe "associated" survived (suggesting the check may be partially broken or label-dependent).
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `remove_contradictory_relationships()`
   - Fix: Define SYMMETRIC_LABELS = {"sibling", "romantic interest", "colleague", "friend", "associated", "rival", "enemy", "ally", "neighbor"}. Only remove pairs where the shared label is NOT in SYMMETRIC_LABELS. Labels like "father", "parent", "creator", "mentor", "master", "child" are asymmetric and SHOULD be removed when bidirectional.
   - Impact: Fixing this alone could raise Profiles from 5.5 to ~7.0 (recovering removed valid relationships).

2. **Victor→creature: "romantic interest" is a hallucination** [Profiles]
   - Problem: The LLM labeled Victor's relationship to the creature as "romantic interest". Victor is the creature's CREATOR. This is displayed prominently in the Key Relationships section of the HTML.
   - Evidence: Every other profile element correctly identifies Victor as creator and the creature as creation. This is a one-off LLM hallucination.
   - Location: `src/pipeline/character_profiling/post_corrections.py` or `src/analyzer.py` (profile generation)
   - Fix: Add a post-processing check for implausible relationship labels. If character A is described as "creator" of B elsewhere in profiles, override "romantic interest" with "creator". OR: add "romantic interest" validation — only allow between characters who are textually described as romantic partners.
   - Note: This may be partially solved by Fix #1 (if "creator"↔"creation" was the original pair that got mangled).

### HIGH

3. **"De Lacey" as false alias of the creature** [Alias Grouping]
   - Problem: `main_cast_2` (the creature) has aliases ["the monster", "the wretch", "the being", "De Lacey"]. "De Lacey" is the surname of the old man, Felix, and Agatha — NOT the creature.
   - Evidence: Felix De Lacey (main_cast_8) also has "De Lacey" as an alias. Rule 3 should block duplicate aliases across characters, but it didn't fire here.
   - Root cause: Processing order issue — when the creature's aliases are verified, Felix may not yet be in the profile_names set. OR: "De Lacey" matches Felix's alias but Rule 3 compares exact canonical names, not aliases of other characters.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()` Rule 3
   - Fix: Ensure profile_names is built from ALL characters' canonical names AND aliases BEFORE verify_aliases runs on any character. Currently it may be built incrementally during processing.

4. **"Professor Krempe" as false alias of M. Waldman** [Alias Grouping, Identity Resolution]
   - Problem: M. Waldman (main_cast_12) has "Professor Krempe" as an alias, but M. Krempe (split_m_krempe) is a separate character. Waldman is the benevolent chemistry professor; Krempe is the dismissive natural philosophy professor. They are completely different people.
   - Evidence: Both appear in the same chapters (Victor's time at Ingolstadt). The LLM confused them because they're both professors mentioned together.
   - Location: Same as #3 — `verify_aliases()` should block "Professor Krempe" since "M. Krempe" / "Krempe" exists as another character's name.
   - Fix: Same as #3 — ensure Rule 3 profile_names includes all characters and their name fragments.

5. **Alphonse Frankenstein MISSING — regression from attempts 4-5** [Completeness]
   - Problem: Victor's father Alphonse is a major character (appears in multiple chapters, mentioned by name in summaries). He was present in attempts 4-5 via F6 reconciliation but disappeared in attempt 6.
   - Evidence: HTML tags show "Alphonse Frankenstein" in chapter summary tags (line 1243) and profile text mentions "Victor's father, Alphonse" (line 1980). But he's not in the 21-character list.
   - Root cause: F6 reconciliation may have matched "Alphonse" to an existing character and merged rather than creating a new entry. OR: the threshold for creating a new F6 character changed.
   - Location: `src/analyzer.py` — F6 reconciliation logic
   - Fix: Investigate why F6 didn't create an Alphonse entry. May need to lower matching threshold or add logic to prevent merging a named character into a generic descriptor.

6. **Wrong relationship labels persist: Felix→Agatha "father", William→Victor "father"** [Profiles]
   - Problem: Felix and Agatha are siblings (their father is the old man De Lacey). William is Victor's younger brother (their father is Alphonse). Both are labeled "father" incorrectly.
   - Evidence: These errors have persisted across attempts 5-6. The contradictory check (Fix 3) didn't help because only one direction has the label.
   - Location: `src/analyzer.py` — `_generate_character_profile()` or `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add a consistency check: if A→B is "father" but B→A is NOT "child"/"son"/"daughter", flag as suspicious. Cross-reference with other characters' relationships — if the old man is already identified as father of Felix/Agatha, then Felix cannot also be Agatha's father.

### MEDIUM

7. **"I" extracted as a character (dd7536794b63, 3157 mentions)** [Completeness]
   - Problem: The first-person pronoun "I" was extracted as a character by F6 reconciliation. 3157 mentions confirms it's the pronoun, not a name.
   - Location: `src/analyzer.py` — F6 reconciliation should filter single-letter words and common pronouns
   - Fix: Add a filter in F6 reconciliation: reject candidates where canonical_name is a single letter or a common pronoun (I, he, she, they, we, it).

8. **Creature missing key aliases: "the dæmon"/"the daemon", "the fiend"** [Alias Grouping]
   - Problem: The creature has ["the monster", "the wretch", "the being", "De Lacey"] but missing "the dæmon", "the daemon", "the fiend" — all commonly used in the text.
   - Fix 1 prevented "the dæmon" from being a false split, but the alias wasn't added to the creature's alias list. The F6 matching correctly identified the duplicate but didn't transfer the alias.
   - Location: `src/analyzer.py` — F6 reconciliation merge logic should add the matched name as an alias.

9. **Book title displays as "Contents"** [Presentation]
   - Problem: HTML header shows "Contents" instead of "Frankenstein". Title extracted from table-of-contents page.
   - Location: `src/ingestion/` or title extraction logic

10. **Letter 1 missing from Prologue Materials** [Presentation]
    - Problem: Prologue section starts at "Prologue 1: Letter 2". Letter 1 (null title) is excluded.
    - Location: HTML template — prologue section filters elements with null titles

11. **Supporting characters lack full canonical names** [Alias Grouping]
    - "William" → should be "William Frankenstein"
    - "Ernest" → should be "Ernest Frankenstein"
    - "Margaret" → should be "Margaret Saville"
    - Location: `src/pipeline/character_extraction_v2/supporting.py`

12. **Caroline Beaufort/Frankenstein still missing** [Completeness]
    - Victor's mother appears by name in summaries but has never been extracted as a character across 6 attempts. May require pre-seeding or lowered F6 threshold.

### LOW

13. **"the old man" canonical name is vague** — Should be "De Lacey" or "Old De Lacey"
14. **Cornelius Agrippa and Werter as character entries** — Historical/literary references, not narrative characters
15. **Physical descriptions sparse: 6/21** — Down from 8/21 in attempt 5

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED into Creature aliases. Alphonse still missing (3rd attempt). |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk re-separated ✓. Profiles (5/10) now primary blocker. |
| 5 | 7.38 | +1.18 | Profiles improved 5→6.5. Chapter titles fixed. Creature aliases cleaned. BUT Turk REGRESSED again into old man. Monster/dæmon false split. |
| 6 | 7.40 | +1.20 | Turk separated ✓. Dæmon merged ✓. Pronunciation fixed ✓. BUT Profiles REGRESSED 6.5→5.5 due to over-firing contradictory relationship removal. |

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
  - Result: Blocked Turk variants ✓. Did NOT block "De Lacey", "the blind father (De Lacey)", "shepherd" — these enter through different paths.

- Attempt 4 (Fix 2): Upstream summarizer fix for Alphonse — changed prompt from "use relationship terms only" to "use proper names when stated in text"
  - Modified: `src/pipeline/chapter_summary/summarizer.py`
  - Result: Alphonse now appears in summaries by name → F6 picked him up ✓

- Attempt 5 (Fix 1): Profile relationships — changed prompt to require EXPLICIT textual evidence for relationships; removed "acquaintance"/"unknown" fallback labels; removed "MUST use these exact names" obligation from character_names_text; updated summary evidence instructions.
  - Modified: `src/analyzer.py` (lines ~2764-2868)
  - Result: PARTIAL — many relationships now correct (Victor→monster, Alphonse family, Kirwin, dæmon entries). But ~10 wrong relationships remain and ~5 key ones missing. Over-corrected: some characters now have zero relationships.

- Attempt 5 (Fix 2): Creature false aliases "De Lacey" and "the blind father (De Lacey)"
  - Fix A: Extend `profile_names` to include surname-only fragments
  - Fix B: New Rule 3b — block aliases whose parenthetical content references another character
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - Result: Target aliases blocked ✓. But Turk aliases now appear on old man entry (different issue).

- Attempt 5 (Fix 3): Chapter titles null for Arabic-numbered chapters
  - Modified: `src/pipeline/chapter_detection/consensus.py`
  - Result: Chapters 1-24 now have numeric titles ✓

- Attempt 6 (Fix 1): Monster/dæmon false split — F6 ligature normalization
  - Modified: `src/analyzer.py` (_normalize_descriptor: add æ→ae, œ→oe normalization)
  - Result: WORKED ✓ — no separate dæmon entry

- Attempt 6 (Fix 2): Turkish merchant/old man false merge — canonical base form in co-occurrence check
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py` (verify_aliases: compute canonical_base by stripping parenthetical before summary search)
  - Result: WORKED ✓ — Turk is separate character

- Attempt 6 (Fix 3): Profile relationships — contradictory bidirectional removal
  - Modified: `src/pipeline/character_profiling/post_corrections.py` (new remove_contradictory_relationships method)
  - Result: OVER-FIRED — removed valid symmetric relationships (romantic interest, sibling, colleague). Caused profile score REGRESSION 6.5→5.5.

- Attempt 6 (Fix 4): Pronunciation false positives — British -ise/-ised forms, -ful suffix, "than"
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
  - Result: WORKED ✓ — all false positives eliminated

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Creature/Turkish merchant merge | `main_cast.py`, `characters.py` | Fixed ✓ |
| 3 | Victor/Frankenstein split | `config.py`, `cli.py`, `characters.py` | Fixed ✓ |
| 3 | Alphonse missing | `characters.py` (grounding threshold) | No change — grounding wasn't root cause |
| 3 | Creature De Lacey alias | `characters.py` (_merge_surname) | No change — aliases enter via different path |
| 3 | (Side effect) Turk regression | Unknown | Regression |
| 4 | Creature Turk aliases | `main_cast.py` (verify_aliases rules) | Fixed ✓ — Turk variants blocked |
| 4 | Creature De Lacey/shepherd aliases | `main_cast.py` (verify_aliases rules) | Partial — "De Lacey" still present (Rule 3 timing issue) |
| 4 | Alphonse missing | `summarizer.py` (upstream prompt fix) | Fixed ✓ — escalation to upstream succeeded |
| 5 | Profile relationships | `analyzer.py` (profile prompt) | Partial — many correct, ~10 still wrong, ~5 missing |
| 5 | Creature De Lacey/shepherd aliases | `main_cast.py` (surname fragments + Rule 3b) | Fixed ✓ — target aliases blocked |
| 5 | Chapter titles | `consensus.py` (_clean_title) | Fixed ✓ |
| 5 | Turk merged with old man | (not targeted) | REGRESSION — Turk aliases now on old man instead of Creature |
| 5 | Monster/dæmon split | (not targeted) | NEW — F6 extracted "the dæmon" as separate character |
| 6 | Monster/dæmon false split | `analyzer.py` (F6 _normalize_descriptor) | Fixed ✓ |
| 6 | Turk/old man false merge | `main_cast.py` (verify_aliases canonical_base) | Fixed ✓ |
| 6 | Contradictory relationships | `post_corrections.py` (remove_contradictory_relationships) | OVER-FIRED — removed valid symmetric relationships → regression |
| 6 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 6 | "De Lacey" false alias on creature | (not targeted — Rule 3 timing issue) | PERSISTENT |
| 6 | "Professor Krempe" false alias on Waldman | (not targeted) | PERSISTENT |
| 6 | Alphonse missing | (was fixed in attempt 4, regressed) | REGRESSION |

**Recurring patterns:**
- `post_corrections.py` (attempt 6): Over-broad matching → needs to distinguish symmetric vs asymmetric labels
- `main_cast.py` verify_aliases Rule 3: Profile_names may not contain all characters' aliases at time of checking → needs pre-built complete set
- F6 reconciliation (`analyzer.py`): Inconsistent across runs — Alphonse appeared in attempts 4-5 but disappeared in 6

## Priority Fix Guidance for Attempt 7

### Fix Priority 1: Narrow `remove_contradictory_relationships` (CRITICAL #1) — Profiles +1.5 expected

This is the single highest-impact fix. The method should ONLY remove bidirectional pairs with ASYMMETRIC labels.

**Symmetric labels (KEEP both directions):** sibling, romantic interest, colleague, friend, associated, rival, enemy, ally, neighbor, acquaintance
**Asymmetric labels (REMOVE both when bidirectional):** father, mother, parent, child, son, daughter, creator, creation, mentor, protégé, master, servant, employer, employee

**Location:** `src/pipeline/character_profiling/post_corrections.py`

### Fix Priority 2: Block "De Lacey" alias on creature + "Professor Krempe" alias on Waldman (HIGH #3, #4) — Characters +0.5 expected

Rule 3 in verify_aliases should block these. The issue is that profile_names may not be fully populated when a character's aliases are being checked. Fix: pre-build profile_names from ALL characters' canonical names AND aliases BEFORE running verify_aliases on any character.

**Location:** `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()` and its caller

### Fix Priority 3: Filter "I" from F6 reconciliation (MEDIUM #7) — Characters +0.25 expected

Add a filter: reject F6 candidates with single-character names or common pronouns.

**Location:** `src/analyzer.py` — F6 reconciliation

### Do NOT attempt to fix in attempt 7:
- Caroline missing — persistent across 6 attempts, likely needs upstream summarizer changes; low impact on score
- Alphonse missing — inconsistent F6 behavior; may self-resolve with next analysis run
- Book title "Contents" — presentation-only; won't cross 8.0 threshold without character/profile fixes first
- Felix→Agatha "father", William→Victor "father" — LLM judgment errors; may partially resolve when Fix #1 restores correct symmetric relationships

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- Chapter Summaries: 0 LLM calls (cached from previous run)
- character_llm_chunk_chars: 5000 — relatively small but 0 retries suggests it's working

## Attempt 7 Fixes Applied

### Fix 1 (CRITICAL — Profiles regression): Symmetric relationships restored
- **Root cause:** `_SYMMETRIC_RELATIONSHIPS` was missing "sibling", "romantic interest", "colleague", "associated", "partner", "twin", etc. — so bidirectional pairs with these valid labels were being deleted.
- **Fix:** Added the missing labels to `_SYMMETRIC_RELATIONSHIPS`.
- **Location:** `src/pipeline/character_profiling/post_corrections.py`
- **Expected impact:** Profiles +1.5 (restores removed valid relationships like Victor↔Elizabeth, Walton↔Margaret, Felix↔Agatha)

### Fix 2 (HIGH — De Lacey alias on creature): Alias surname fragments in profile_names
- **Root cause:** `profile_names` only extracted suffix fragments from *canonical names*, not from *aliases*. If Felix's canonical was just "Felix" (single word) with alias "Felix De Lacey", then "de lacey" would NOT be in `other_aliases`, so Rule 3 never fired.
- **Fix:** Rewrote profile_names building to extract suffix fragments from BOTH canonical names AND aliases, iterating over `[canonical] + aliases` uniformly.
- **Location:** `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()`
- **Expected impact:** Characters Alias Grouping +0.5 (blocks De Lacey from creature)

### Fix 3 (HIGH — Professor Krempe alias on Waldman): Extended title pattern
- **Root cause:** `_are_different_titled_people` used regex `^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+(.+)$` — "Professor" was not recognized as a title, so "Professor Krempe" vs "M. Waldman" didn't trigger the different-surname check.
- **Fix:** Added "Professor", "Prof.", "Captain", "Sergeant", "Colonel", "General", "Lord", "Lady", "Baron", "Count", "Countess", "Sir" to the title pattern.
- **Location:** `src/pipeline/character_extraction_v2/main_cast.py` — `_are_different_titled_people()`
- **Expected impact:** Characters Alias Grouping +0.25 (blocks Professor Krempe from Waldman)

### Fix 4 (MEDIUM — "I" as a character): F6 pronoun filter
- **Root cause:** F6 reconciliation had no filter for single-letter names or common pronouns. A first-person narrator's "I" appears in `active_characters` of summaries and creates a spurious character.
- **Fix:** Added filter at top of F6 loop: skip names with len ≤ 1 or names in a common-pronoun set {i, he, she, they, we, it, him, her, them, us, his, hers, theirs, its, ours}.
- **Location:** `src/analyzer.py` — F6 reconciliation loop
- **Expected impact:** Characters Completeness +0.25 (removes "I" character with 3157 fake mentions)

## Next Action
Run PROMPT_analyze.md to re-run the pipeline and verify fixes.
