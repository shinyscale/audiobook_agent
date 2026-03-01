# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_053706/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗ ← primary blocker
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 7.5/10 ✗
- **Overall: 7.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Improved from Attempt 6

- **Fix 2 (De Lacey alias on creature) WORKED:** "De Lacey" no longer appears in the creature's aliases. The creature is now "the monster" with alias "the creature" only. ✓
- **Fix 3 (Professor Krempe alias on Waldman) WORKED:** M. Krempe (supporting_4) is a separate character. M. Waldman (supporting_3) has no false aliases. ✓
- **Fix 4 ("I" as character) WORKED:** The pronoun "I" is no longer in the character list. ✓
- **Fix 1 (symmetric relationships) PARTIALLY WORKED:** Victor→creature is now "creation" (no longer "romantic interest" hallucination). However, key symmetric relationships (Victor↔Elizabeth, Walton↔Margaret, Felix↔Agatha "sibling") are still absent — the LLM simply didn't generate them this run, so the symmetric fix had nothing to preserve.
- **Overall score improved:** 7.40 → 7.80 (+0.40)
- **Profiles improved:** 5.5 → 6.5 (romantic interest hallucination gone)
- **Characters improved:** 6.5 → 7.5 (De Lacey, Krempe, "I" all fixed)

## What's Still Failing

### Profiles (6.5/10) — Primary Blocker

**Missing relationships for major characters:**
- Robert Walton (narrator, 9 mentions): ZERO relationships. Should have: Victor (confidant), Margaret (sister).
- Elizabeth Lavenza (92 mentions): ZERO relationships. Should have: Victor (fiancée/wife), William (family), Justine (friend/household member).
- the old man De Lacey (63 mentions): ZERO relationships. Should have: Felix (son), Agatha (daughter), the monster (brief encounter).
- William (25 mentions): ZERO relationships. Should have: Victor (brother), Elizabeth (family).
- Ernest (13 mentions): ZERO relationships. Should have: Victor (brother).
- Margaret (10 mentions): ZERO relationships. Should have: Walton (brother).

**Wrong relationship labels:**
- Felix→Agatha: "father" — WRONG. They are siblings. Their father is the old man De Lacey. PERSISTENT across attempts 5-7.
- Agatha→Felix: "father" — WRONG. Same error in both directions.
- Henry Clerval→M. Krempe: "colleague" — WRONG. Henry is Victor's best friend, not Krempe's colleague.
- Justine Moritz→Beaufort: "associated" — WRONG. No direct connection between them.
- Cornelius Agrippa→M. Waldman: "associated" — WRONG/QUESTIONABLE. Historical figure, not narratively connected.

**Missing critical relationships:**
- Victor↔Elizabeth romantic/family (the central love relationship)
- Victor↔Henry friendship (Victor's closest friend)
- Victor↔Walton frame narrator relationship
- Monster→Victor creator relationship (only Victor→monster "creation" exists, not reverse)
- Felix↔Safie romantic interest
- De Lacey↔Felix/Agatha parent-child

**Physical descriptions:** 8/19 — decent for major characters. No speech patterns at all (0/19).

### Characters (7.5/10) — Close to Passing

**Alphonse Frankenstein STILL MISSING** (regression from attempts 4-5). Victor's father appears by name in chapter summaries ("his father Alphonse" in Ch. 7 summary) but F6 reconciliation didn't create an entry. This is the 3rd consecutive attempt where Alphonse was missing after appearing in attempts 4-5.

**Creature aliases still sparse:** "the monster" has only alias "the creature". Missing: "the wretch", "the being", "the fiend", "the daemon"/"the dæmon". The analysis log noted "the dæmon BLOCKED from creature aliases — already claimed by another character" — suggesting a regression where Rule 3 is over-blocking.

**Caroline Beaufort/Frankenstein still missing** — persistent across all 7 attempts.

### Presentation (7.5/10) — Close to Passing

- Book title displays as "Contents" instead of "Frankenstein"
- Letter 1 missing from Prologue Materials (null title filtered out)

## Current Issues (Priority Order)

### CRITICAL

1. **Major characters have ZERO relationships** [Profiles]
   - Problem: 6 of 19 characters have no relationships at all, including Elizabeth Lavenza (92 mentions — second-most mentioned character), Robert Walton (frame narrator), and the old man De Lacey (63 mentions). The LLM profile generator is failing to produce relationships for these characters.
   - Evidence: Victor→Elizabeth is absent despite Elizabeth being Victor's fiancée and later wife, the emotional center of the novel. Walton→Margaret is absent despite every letter being addressed to her.
   - Location: `src/analyzer.py` — `_generate_character_profile()` or `src/pipeline/character_profiling/`
   - Root cause hypothesis: The profile generation prompt may not be providing sufficient context about these characters' co-occurrences, or the LLM is only producing relationships for characters that appear together in explicit textual passages provided as evidence.
   - Fix approach:
     A) Check if the co-occurrence/evidence passages being fed to the profiler include enough context for these characters. If Elizabeth appears in 92 mentions across many chapters but the profiler only gets a small excerpt, it may miss her relationships.
     B) Add a post-processing enrichment step: if character A mentions character B by name in their profile text but has no relationship entry for B, add a default "associated" relationship.
     C) Consider adding a "must include" hint for characters with high mention counts that share chapters.
   - Impact: Fixing this alone could raise Profiles from 6.5 to ~8.0.

2. **Felix→Agatha labeled "father" (should be "sibling")** [Profiles]
   - Problem: Felix De Lacey→Agatha De Lacey: "father" and Agatha→Felix: "father". They are SIBLINGS. The old man De Lacey is their father.
   - Evidence: Persistent across 3 attempts. The LLM consistently mislabels this relationship.
   - Location: `src/pipeline/character_profiling/post_corrections.py` or profile generation prompt
   - Fix approach: Add a post-correction rule: if two characters share a surname AND a third character with that surname is labeled as "old man"/"father"/"parent", then the shared-surname pair are likely siblings, not parent-child. OR: if A→B is "father" and B→A is also "father" (bidirectional "father"), convert both to "sibling" (two people cannot each be each other's father).
   - Impact: +0.25 on Profiles

### HIGH

3. **Alphonse Frankenstein missing — 3rd consecutive absence** [Completeness]
   - Problem: Victor's father appears by name in summaries ("his father Alphonse" in Ch. 7) but is not in the character list. F6 reconciliation found him in attempts 4-5 but not since.
   - Evidence: Summaries reference "Alphonse" explicitly. The character has significant narrative presence (multiple chapters).
   - Location: `src/analyzer.py` — F6 reconciliation loop
   - Root cause: F6 may be matching "Alphonse" to an existing character (e.g., Victor Frankenstein as "Frankenstein") and merging rather than creating a new entry. OR: the matching threshold changed.
   - Fix: Debug F6 reconciliation for "Alphonse" — add logging to see if it's being matched/merged. If threshold is the issue, adjust matching logic to treat given names as distinct from surnames.

4. **Creature missing key aliases: "the wretch", "the fiend", "the daemon"** [Alias Grouping]
   - Problem: "the monster" has only alias "the creature". The text extensively uses "the wretch", "the being", "the fiend", "the daemon"/"the dæmon". Analysis log shows "the dæmon BLOCKED — already claimed by another character."
   - Evidence: These descriptors are used throughout the novel for the same entity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias detection, or `src/analyzer.py` — F6 reconciliation
   - Root cause: Rule 3 may be over-blocking. The dæmon→daemon normalization (Fix 1 from attempt 6) prevented a false split, but the alias was then claimed by another entry, causing Rule 3 to block it from the creature.
   - Fix: Investigate which character "claimed" the dæmon alias. If it's a phantom entry that got filtered, the alias should be freed. Consider a priority system: if an alias is claimed by a character with <5 mentions but the candidate has >20 mentions, prefer the higher-mention character.

5. **Wrong relationships: Henry→Krempe "colleague", Justine→Beaufort "associated"** [Profiles]
   - Problem: Henry Clerval has no relationship to Krempe; Justine has no connection to Beaufort. These are LLM hallucinations.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add validation — if a relationship label seems implausible (e.g., "colleague" between characters that never share a scene), filter it. OR: cross-reference with co-occurrence data — if characters never appear in the same chapter, their relationship should be flagged as suspect.

### MEDIUM

6. **Book title "Contents" instead of "Frankenstein"** [Presentation]
   - Problem: HTML header shows "Contents" — extracted from table-of-contents page.
   - Location: `src/ingestion/` or title extraction logic
   - Fix: Skip pages whose text is primarily "Contents" / table-of-contents structure when extracting title. Or use filename as fallback.

7. **Letter 1 missing from Prologue Materials** [Presentation]
   - Problem: Letter 1 (null title) excluded from prologue section in HTML.
   - Location: HTML template — prologue section likely filters elements with null titles.
   - Fix: Assign a default title like "Letter 1" when the structure element has a null title and is the first element.

8. **Supporting characters lack full canonical names** [Alias Grouping]
   - "William" → should be "William Frankenstein"
   - "Ernest" → should be "Ernest Frankenstein"
   - "Margaret" → should be "Margaret Saville"
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

9. **Cornelius Agrippa and Werter as character entries** [Completeness]
   - These are a historical figure and a literary character (from a book the creature reads), not narrative characters. Their inclusion is not harmful but not ideal.
   - LOW priority — does not significantly impact scoring.

10. **Caroline Beaufort/Frankenstein still missing** [Completeness]
    - Victor's mother, mentioned by name in text and summaries. Persistent across all 7 attempts.
    - May require upstream summarizer changes or lowered F6 threshold.

### LOW

11. **"the old man (De Lacey)" canonical name is vague** — Should be "De Lacey" or "Old De Lacey"
12. **Physical descriptions sparse: 8/19** — Many major characters (Victor, Henry, Walton) lack physical descriptions, though this partly reflects the source text.
13. **Zero speech patterns detected** — 0/19 characters have speech_pattern field populated.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED into Creature aliases. Alphonse still missing (3rd attempt). |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk re-separated ✓. Profiles (5/10) now primary blocker. |
| 5 | 7.38 | +1.18 | Profiles improved 5→6.5. Chapter titles fixed. Creature aliases cleaned. BUT Turk REGRESSED again into old man. Monster/dæmon false split. |
| 6 | 7.40 | +1.20 | Turk separated ✓. Dæmon merged ✓. Pronunciation fixed ✓. BUT Profiles REGRESSED 6.5→5.5 due to over-firing contradictory relationship removal. |
| 7 | 7.80 | +1.60 | De Lacey alias fixed ✓. Krempe separated ✓. "I" removed ✓. Romantic interest gone ✓. BUT profiles still failing (6.5) — major chars have ZERO relationships. |

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
  - PARTIAL — prevented removal but LLM didn't regenerate the key relationships

- Attempt 7 (Fix 2): Alias surname fragments — rewrote profile_names to include fragments from BOTH canonical names and aliases
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - WORKED ✓ — De Lacey blocked from creature

- Attempt 7 (Fix 3): Title pattern expansion — added Professor, Captain, Lord, etc. to _are_different_titled_people
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - WORKED ✓ — Professor Krempe recognized as different from M. Waldman

- Attempt 7 (Fix 4): F6 pronoun filter — reject single-letter names and common pronouns
  - Modified: `src/analyzer.py`
  - WORKED ✓ — "I" no longer extracted

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
| 6 | Contradictory relationships | `post_corrections.py` (remove_contradictory_relationships) | OVER-FIRED → regression |
| 6 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 7 | Symmetric relationship labels | `post_corrections.py` | Partial — fix correct but LLM didn't regenerate the relationships |
| 7 | De Lacey alias on creature | `main_cast.py` (profile_names from aliases) | Fixed ✓ |
| 7 | Professor Krempe alias on Waldman | `main_cast.py` (_are_different_titled_people) | Fixed ✓ |
| 7 | "I" pronoun as character | `analyzer.py` (F6 pronoun filter) | Fixed ✓ |

**Recurring patterns:**
- `post_corrections.py` (attempts 6-7): Relationship corrections have been fragile. The symmetric fix worked but the underlying LLM isn't producing relationships for 6 major characters.
- `analyzer.py` F6 reconciliation: Alphonse appeared in attempts 4-5 but has been missing for attempts 6-7. Inconsistent behavior.
- Profile generation is now the primary blocker — the LLM simply isn't generating relationships for many major characters.

## Priority Fix Guidance for Attempt 8

### Fix Priority 1: Relationship enrichment for characters with ZERO relationships (CRITICAL #1) — Profiles +1.5 expected

This is the highest-impact fix. 6 major characters (Elizabeth, Walton, De Lacey, William, Ernest, Margaret) have NO relationships at all. The LLM profiler isn't generating them.

**Approach A (Recommended): Post-processing relationship enrichment based on summary co-occurrence**
- After profiles are generated, check for characters with zero relationships.
- For each, scan chapter summaries for co-occurring character names.
- If character A and character B appear in the same chapter summary and A has a relationship to B but B doesn't have one to A, add a reciprocal.
- If neither has one, check the text for relationship indicators (family terms near both names).

**Approach B: Improve profile prompt to explicitly handle high-mention characters**
- The current prompt may not provide enough co-occurrence evidence for characters like Elizabeth (92 mentions).
- Ensure the profiler receives evidence passages where Elizabeth and Victor appear together.

**Location:** `src/pipeline/character_profiling/post_corrections.py` (Approach A) or `src/analyzer.py` `_generate_character_profile()` (Approach B)

### Fix Priority 2: Felix↔Agatha "father" → "sibling" (CRITICAL #2) — Profiles +0.25 expected

Bidirectional "father" between same-surname characters is logically impossible. Add post-correction:
- If A→B is "father" AND B→A is "father", convert both to "sibling" (or "family").
- More generally: "father" is asymmetric. If the reverse should be "child"/"son"/"daughter" but instead is also "father", both labels are wrong.

**Location:** `src/pipeline/character_profiling/post_corrections.py`

### Fix Priority 3: Fix wrong relationships (Henry→Krempe, Justine→Beaufort) (HIGH #5) — Profiles +0.25 expected

Add a post-correction that validates relationships against chapter co-occurrence:
- If character A and character B never appear in the same chapter summary, flag their relationship as suspect.
- Remove or downgrade relationships with no textual co-occurrence evidence.

**Location:** `src/pipeline/character_profiling/post_corrections.py`

### Fix Priority 4: Book title "Contents" (MEDIUM #6) — Presentation +0.25 expected

**Location:** `src/ingestion/` — title extraction. Use filename as fallback when extracted title matches common TOC patterns.

### Fix Priority 5: Letter 1 null title (MEDIUM #7) — Presentation +0.25 expected

**Location:** HTML template or structure post-processing — assign "Letter 1" when first element has null title.

### Do NOT attempt to fix in attempt 8:
- Alphonse missing — F6 reconciliation is inconsistent; may self-resolve. 3 files already modified for this issue without lasting fix.
- Caroline missing — persistent 7 attempts; low relative impact.
- Creature aliases sparse — lower priority than profiles; risk of over-blocking regression.
- Supporting character full names — minor; won't cross threshold.
- Cornelius Agrippa/Werter as characters — cosmetic.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- Chapter Summaries: cached from previous run
- character_llm_chunk_chars: 5000 — relatively small but 0 retries suggests it's working
- No configuration changes recommended — the primary issue is profile generation quality, not config parameters

## Next Action
Run PROMPT_fix.md to address profile relationship gaps (Critical #1, #2) and presentation issues (Medium #6, #7).
