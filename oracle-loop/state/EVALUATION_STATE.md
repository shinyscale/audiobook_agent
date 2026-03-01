# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260301_003644/

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 7.5/10
  - Identity Resolution: 5/10
  - Alias Grouping: 6/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 7.5/10 ✗
- **Overall: 7.38/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## What Improved from Attempt 4
- **Fix 1 (Profile relationships) PARTIALLY WORKED**: Victor→monster "creation" relationship now present ✓, Alphonse relationships correct ✓, Mr. Kirwin→Victor "magistrate and protector" correct ✓, dæmon→Victor "creator" ✓, dæmon→William/Clerval "murderer" ✓. But still ~10 wrong relationships and ~5 key ones missing.
- **Fix 2 (Creature false aliases) WORKED for target aliases**: "De Lacey" and "the blind father (De Lacey)" are no longer Creature aliases ✓. "shepherd" no longer present ✓.
- **Fix 3 (Chapter titles) WORKED**: Chapters 1-24 now have numeric titles ("1", "2", etc.) ✓.
- **Physical descriptions: 8/21** (up from 7/21 in attempt 4)

## What Regressed or Failed
- **REGRESSION: The Turkish merchant / the Turk falsely merged with old man De Lacey** (main_cast_9). In attempt 4, the Turk was a separate character (0a5ef5ac589f). Now "the Turkish merchant" and "the Turk" appear as aliases of "the old man (De Lacey)". The blind father and Safie's father are completely different people.
- **NEW ISSUE: "the dæmon" is a separate entry (cab8aefa3380, 15 mentions)** — false split from "the monster" (split_the_monster, 25 mentions). These are the same Creature. F6 reconciliation extracted "the dæmon" from summaries but didn't merge it with the existing monster entry.
- **Relationships still wrong**: Felix→Agatha "father" (WRONG: siblings), Elizabeth→Alphonse "acquaintance" (WRONG: adopted daughter), Safie→Beaufort "parent" (WRONG: no relation), Agrippa↔Waldman "associated" (WRONG: centuries apart), Krempe→Clerval "colleague" (WRONG: professor vs student)
- **Key relationships still missing**: Victor→Elizabeth, Victor→Henry Clerval, Victor→Alphonse, Victor→Robert Walton
- **Caroline Beaufort/Frankenstein still missing**

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE SPLIT: "the monster" and "the dæmon" are the same character** [Identity Resolution]
   - Problem: `split_the_monster` (25 mentions, aliases: "the creature") and `cab8aefa3380` (15 mentions, no aliases) are listed as two separate characters. The Creature is referred to as "the monster", "the creature", "the dæmon/daemon", "the fiend", "the wretch" throughout the text — all one being.
   - Evidence: "the dæmon" has relationships {Victor: "creator", William: "murderer", Clerval: "murderer"} — exactly the Creature's actions. Meanwhile "the monster" has {William: "victim of vengeance", Walton: "narrated to"}.
   - Root cause: `cab8aefa3380` is an F6 reconciliation hash ID, meaning "the dæmon" was extracted from summaries and not matched to the existing `split_the_monster` entry. F6's matching logic doesn't recognize "the dæmon" as equivalent to "the monster"/"the creature".
   - Location: `src/analyzer.py` (F6 reconciliation logic, ~line 1220-1240) — the matching function needs to recognize variant descriptors of the same entity.
   - Fix approach: In F6 reconciliation, before adding a summary-only character as new, check if it's a known descriptor/alias variant of an existing character. "the dæmon" should match "the monster"/"the creature" via semantic similarity or a descriptors list.

2. **FALSE MERGE: "the old man (De Lacey)" incorrectly has "the Turkish merchant" and "the Turk" as aliases — REGRESSION** [Identity Resolution, Alias Grouping]
   - Problem: main_cast_9 has aliases ["the old man", "De Lacey", "the Turkish merchant", "the Turk"]. The old man De Lacey is the BLIND FATHER of Felix and Agatha. The Turkish merchant / the Turk is SAFIE'S FATHER — a completely different person imprisoned by the French government.
   - Evidence: In attempt 4, the Turk was correctly a separate character (0a5ef5ac589f, 9 mentions). This is a regression.
   - Root cause: The LLM proposed "the Turkish merchant" and "the Turk" as aliases of "the old man" because both appear in the same chapters (the Creature's narrative about the De Lacey cottage). `verify_aliases()` didn't block them because: (a) no other character claims these aliases (Rule 3 doesn't fire), and (b) the terms appear in summaries (Rule 2a doesn't fire since the Turkish merchant IS mentioned in De Lacey chapters).
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()`
   - Fix approach: Rule 2a (alias must appear in summaries) passes because "the Turkish merchant" appears in De Lacey chapter summaries. Need a new rule or refinement: if an alias refers to a specific person described differently from the canonical character (blind old man ≠ merchant), block it. Alternatively, detect when an alias is a distinct character descriptor (contains "merchant", "soldier", "priest" etc.) that doesn't match the canonical character's descriptor ("old man").

### HIGH

3. **Wrong relationships persist despite Fix 1 — Felix/Agatha sibling relationship incorrect** [Profiles]
   - Problem: Felix→Agatha: "father" and Agatha→Felix: "father" — BOTH WRONG. Felix and Agatha are SIBLINGS. Their father is "the old man (De Lacey)".
   - Additional wrong relationships:
     - Elizabeth→Alphonse: "acquaintance" (she's his adopted daughter/ward)
     - Alphonse→Elizabeth: "acquaintance" (he's her adoptive father)
     - Safie→Beaufort: "parent" (no relationship — Beaufort is Caroline's father, not Safie's)
     - Beaufort→Safie: "child" (fabricated)
     - Cornelius Agrippa↔M. Waldman: "associated" (centuries apart)
     - M. Krempe→Henry Clerval: "colleague" (professor vs student)
   - Root cause: Fix 1 improved the prompt to require "explicit textual evidence" and removed "acquaintance" as fallback — but "acquaintance" still appears (Elizabeth↔Alphonse), and the Felix/Agatha "father" error suggests the LLM is still confused by co-occurrence in the cottage scenes. The prompt fix was partially effective but needs stronger constraints on relationship type accuracy.
   - Location: `src/analyzer.py` — `_generate_character_profile()` relationship extraction
   - Fix: The remaining errors are LLM judgment errors, not systematic prompt failures. May need to add post-processing validation that catches impossible relationships (e.g., if A→B is "father" and B→A is also "father", that's contradictory and both should be removed).

4. **Key relationships MISSING for Victor** [Profiles]
   - Problem: Victor has only 3 relationships {monster: "creation", Krempe: "mentor", Waldman: "mentor"} but is missing the central relationships of the novel:
     - Victor→Elizabeth: fiancée/wife (THE romantic relationship)
     - Victor→Henry Clerval: best friend
     - Victor→Alphonse: father
     - Victor→Robert Walton: friend/confidant (the framing narrative)
   - Henry Clerval has ZERO relationships listed
   - Robert Walton has ZERO relationships listed
   - Root cause: Fix 1 removed the "MUST list all characters" obligation from the prompt, which correctly stopped fabricated relationships. But it over-corrected — now the LLM is too conservative and omits real relationships even when textual evidence exists.
   - Location: `src/analyzer.py` — `_generate_character_profile()`
   - Fix: The prompt may need a middle ground: "Include relationships where the text explicitly describes the nature of the connection (e.g., 'his friend', 'my father', 'his betrothed'). Omit relationships where characters merely appear in the same scene."

5. **Caroline Beaufort/Frankenstein (Victor's mother) still missing** [Completeness]
   - Problem: Victor's mother appears prominently in Chapters 1-3, is mentioned by name "Caroline Beaufort" in summaries, and her death from scarlet fever is a key plot point. Still absent from character list.
   - Location: `src/analyzer.py` (F6 reconciliation) or `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: F6 reconciliation thresholds may require multiple summary mentions. Caroline may appear by name in only 1-2 summaries. Check and lower threshold, or pre-seed her as a candidate.

### MEDIUM

6. **Pronunciation false positives** [Pronunciation]
   - Problem: ~5-6 false positives: "sympathised", "sympathise", "sympathising", "unsympathised" (standard British spellings), "slothful" (straightforward English), "than" (flagged as "foreign" — it's common English)
   - 11 entries lack IPA (homographs like "desert", "lead" are acceptable without IPA since pronunciation is context-dependent)
   - Location: `src/pipeline/pronunciation/` — word filtering
   - Fix: Add British -ise/-ised variants to exclusion list. Remove "slothful" and "than" from flagged words.

7. **Book title displays as "Contents"** [Presentation]
   - Problem: HTML header shows "Contents" instead of "Frankenstein". Title extracted from table-of-contents page.
   - Location: `src/ingestion/` or title extraction logic

8. **Letter 1 missing from Prologue Materials** [Presentation]
   - Problem: Prologue section starts at "Prologue 1: Letter 2". Letter 1 (null title) is excluded, and chapter count shows "25 Chapters" instead of 24.
   - Location: HTML template — prologue section filters elements with null titles

9. **Supporting characters lack full canonical names** [Alias Grouping]
   - "William" → should be "William Frankenstein"
   - "Ernest" → should be "Ernest Frankenstein"
   - "Margaret" → should be "Margaret Saville"
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

### LOW

10. **Creature missing key aliases: "the fiend", "the wretch", "the daemon"** [Alias Grouping]
    - "the monster" entry only has "the creature" as alias. Missing major descriptors used throughout.
    - May be over-blocked by Rule 2a if cached summaries don't contain these terms verbatim.

11. **"the old man" canonical name is vague** [Identity Resolution]
    - "the old man (De Lacey)" could refer to anyone. Should ideally be "De Lacey (father)" or "Old De Lacey".

12. **Cornelius Agrippa and Werter as character entries** [Completeness]
    - Historical/literary references, not narrative characters. Minor noise.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED into Creature aliases. Alphonse still missing (3rd attempt). |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk re-separated ✓. Profiles (5/10) now primary blocker. |
| 5 | 7.38 | +1.18 | Profiles improved 5→6.5. Chapter titles fixed. Creature aliases cleaned. BUT Turk REGRESSED again into old man. Monster/dæmon false split. |

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

**Pattern detected:** The Turkish merchant/Turk alias has been a recurring problem across attempts 1, 3, and 5. It moves between characters (Creature in attempt 1/3, old man in attempt 5) but the core issue persists — the LLM groups it with whoever appears in the De Lacey cottage scenes. Rule-based blocking (Rule 3, Rule 2a) doesn't help because the Turk IS mentioned in those chapter summaries.

**Suggested approach for attempt 6:** Rather than more alias-verification rules, consider a **semantic conflict rule** specifically for aliases that describe a distinct person with a different role/occupation than the canonical character. "the old man (De Lacey)" is described as blind/father; "the Turkish merchant" is a merchant — these are semantically different roles that suggest different people. This is similar to the existing `_split_semantic_conflicts` logic in `characters.py` but applied at the alias-verification stage.

## Priority Fix Guidance for Attempt 6

### Fix Priority 1: Monster/dæmon false split (CRITICAL #1)

The most impactful fix — merges two entries that are clearly the same character, immediately improving Identity Resolution and Alias Grouping.

**Investigation steps:**
1. Look at F6 reconciliation in `src/analyzer.py` (~line 1220-1240)
2. Find the matching logic that decides whether a summary-extracted character matches an existing character
3. "the dæmon" should match "the monster" / "the creature" — they're all descriptors for the same being
4. Add matching logic that recognizes common creature/monster/dæmon/fiend/wretch descriptors as equivalent

**This fix alone could raise Character Extraction by ~0.5-1 point.**

### Fix Priority 2: Old man / Turkish merchant false merge (CRITICAL #2 — REGRESSION)

This has regressed 3 times across attempts. Rule-based alias blocking hasn't permanently solved it because the LLM keeps proposing these aliases and the blocking rules don't fire (terms appear in summaries + no other character claims them).

**Investigation steps:**
1. Look at `verify_aliases()` in `main_cast.py`
2. Consider adding a rule that blocks aliases describing a semantically different person-type than the canonical character:
   - Canonical: "the old man (De Lacey)" — descriptors: old, blind, father
   - Proposed alias: "the Turkish merchant" — descriptor: merchant (different person-type)
   - Proposed alias: "the Turk" — descriptor: ethnic/national designation (different from "old man")
3. This is a variant of semantic conflict detection but at the alias level
4. Alternative: Add "merchant" to the list of occupation titles that trigger a split or alias rejection when the canonical character doesn't share that occupation

**This fix could raise Character Extraction by ~0.5 points and stops the recurring regression.**

### Fix Priority 3: Profile relationship quality (HIGH #3, #4)

Profile relationships improved from 5/10 to 6.5/10 but need to reach 8/10. Two sub-problems:
- **Wrong relationships** (~10): LLM still makes errors like Felix "father" of Agatha
- **Missing key relationships** (~5): Over-correction from Fix 1 — Victor, Henry, Robert Walton all have sparse/empty relationship lists

**Suggested approach:** Add a post-processing validation step that catches impossible relationships (e.g., bidirectional "father" means both are wrong and should be removed). For missing relationships, adjust the prompt to encourage including relationships with explicit textual markers ("his friend", "my father", "his bride") rather than just co-occurrence.

### Do NOT attempt to fix: Chapter Summaries (8.5/10), Structure Detection (8.5/10) — already passing.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- Chapter Summaries: 0 LLM calls (cached from previous run)
- character_llm_chunk_chars: 5000 — relatively small; may miss cross-chunk character references but 0 retries suggests it's working

## Next Action
Run PROMPT_fix.md to address:
1. Monster/dæmon false split (F6 reconciliation in analyzer.py)
2. Old man/Turkish merchant false merge (verify_aliases in main_cast.py)
3. Profile relationship quality (analyzer.py profile prompt refinement)
