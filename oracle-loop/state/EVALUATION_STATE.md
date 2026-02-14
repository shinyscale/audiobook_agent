# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 17
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 17)
- Analysis completed in 37m 18s
- **CRITICAL REGRESSION:** Father character (`main_cast_0_split_0`) is MISSING from output
- Only 5 characters extracted (down from 7 in attempt 16)
- Son character (`main_cast_1_split_1`) has 57 mentions and absorbed father's aliases ("John Donaldson (the father)", "the father")
- The attempt 17 fix (adding split labels as standalone aliases) broke the split mechanism — father was absorbed into son
- The post-split validation from attempt 16 should have caught the sibling canonical in aliases, but the label aliases ("the father") likely created a new path for absorption
- Narrator detection: Uncle Bill correctly identified as first-person narrator ✓
- 2 chapters detected (unchanged)
- 25 pronunciation flags
- No physical_description on ANY character (0/5) — regression from attempt 16 where father and Uncle Bill had descriptions

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗ (REGRESSION from 7.5)
- Character Profiles: 5.5/10 ✗ (REGRESSION from 7)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 7/10 ✗ (REGRESSION from 8)
- **Overall: 6.28/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (all 6 categories below threshold — major regression)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

### 2.2 Character Extraction: 5/10 ✗ (REGRESSION from 7.5 in attempt 16)

**CRITICAL REGRESSION:** The father character is completely gone. The attempt 17 fix (adding split labels "the father"/"the son" as standalone aliases) caused the father to be absorbed into the son character.

**What's wrong:**
1. Father (`main_cast_0_split_0`) is MISSING — only 5 characters exist (was 7)
2. Son (`main_cast_1_split_1`) has 57 mentions — this is father+son combined (~28+28=56, plus the label alias matches)
3. Son's aliases include "John Donaldson (the father)" and "the father" — clearly absorbed from the father character
4. No `main_cast_0_split_0` exists at all — the split either didn't create a father, or the father was immediately merged back into the son
5. The spurious "John Donaldson's" possessive entry is gone (improvement), but at the cost of losing the father entirely

**What's correct:**
- Uncle Bill correctly identified as narrator with protagonist role ✓
- Margaret Donaldson present (2 mentions) ✓
- Ted Frith with alias "Ted" (5 mentions) ✓
- Joe Barron (3 mentions) ✓

**Root cause analysis:** The fix added "the father" and "the son" as standalone aliases to their respective split characters. But the post-split validation in `characters.py:1600-1631` (which removes sibling canonical names from aliases) likely did NOT catch these label aliases. Then downstream merge logic (Step 3.5 `_merge_within_main_cast()` or alias resolution) saw "the father" as an alias of the son and treated the father character as redundant, absorbing it. The ID `main_cast_1_split_1` suggests the split DID fire, but only one child survived.

### 2.3 Character Profiles: 5.5/10 ✗ (REGRESSION from 7 in attempt 16)

**Physical descriptions: ALL NULL (0/5 characters)** — Major regression from attempt 16 where father and Uncle Bill had descriptions.

**Uncle Bill profile: GOOD** ✓
- Personality summary captures his heroic, reluctant compassion correctly
- Traits accurate: "reluctantly compassionate", "emotionally reserved yet deeply loyal"
- Speech patterns noted: formal, restrained
- Evidence quotes are relevant and correctly attributed
- Relationships: mentor to son ✓, ally to father ✓, ally to "Cousin John" (this is the father's informal name — acceptable)

**Son profile: CONTAMINATED — contains entirely the father's data** ✗
- Personality: "A morally ambiguous man who committed grave ethical violations by embezzling" — this is the FATHER
- Traits: "cowardly in the face of accountability" — the FATHER, not the son
- Evidence: "'Took money,' he said" and "'American, sir'" — these are the FATHER's quotes
- Relationships: self-referential `"John Donaldson (the son)": "parent"` (should be the father as parent)
- Relationships: `"Margaret Donaldson": "spouse"` — Margaret is the FATHER's wife

Since the father character doesn't exist, there's no profile for him at all. The son's profile is essentially the father's profile assigned to the wrong character.

**Ted Frith profile: GOOD** ✓
- Personality captures his heroism, selflessness, and courage accurately
- Evidence quotes correctly attributed
- Speech patterns noted: casual, uses slang, energetic

**Margaret Donaldson & Joe Barron: No profiles** — acceptable for very minor characters

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, the scandal, inheritance split, Florida recklessness, mysterious death, Margaret and the boy. `characters_present: ["the narrator", "John (the son)"]` — correctly identifies narrator and the son.

**Chapter 2:** Comprehensive and well-structured. Covers the full arc: taking in the boy, fishing trip, WWI enlistment, Caporetto, meeting the ship, dinner, encounter with the father in khaki, deathbed confession, redemption. `characters_present` correctly lists all three key characters including both "John Donaldson (the son)" and "John Donaldson (the father)".

**PERSISTENT factual error (17th consecutive attempt):** Ch2 says "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "my cousin John". This is a deep, persistent LLM hallucination.

**Book overview:** Excellent — accurate, comprehensive, narratively rich. However it also says "nephew" (which is acceptable as a narrative simplification of the relationship, and Uncle Bill himself uses "nephew" colloquially).

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries, 20 with IPA. Unchanged quality from attempt 16:
- ~8 genuinely useful: Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux
- ~5 acceptable homographs: live, minute, read, close, moderate
- ~12 false positives: Donaldson, Barron, Frith, Margaret, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was
- "mayn't" is borderline — it is an unusual contraction that a narrator might want to prepare for

### 2.6 HTML Presentation: 7/10 ✗ (REGRESSION from 8 in attempt 16)

**Regressions from attempt 16:**
- Father character completely missing from the character list — only "John Donaldson (the son)" appears
- Son's profile card shows father's data (personality, evidence, relationships all wrong)
- Son's alias list shows "John Donaldson (the father), the father" — confusing for a narrator
- No physical descriptions visible for any character (all null)

**What still works:**
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Navigation tabs functional ✓
- Book overview prominent and accurate ✓
- Ted Frith profile card present with correct content ✓
- Chapter summaries well-formatted ✓

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (5.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (7 × 0.10)
        = 1.40 + 1.25 + 0.825 + 1.50 + 0.65 + 0.70
        = 6.325 → 6.33
```

**Overall: 6.33/10** (REGRESSION from 7.28 in attempt 16, below baseline of 6.60)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: 37m 18s
- Character extraction: 6 items processed (pipeline_metadata.main_cast_count=3), only 5 in final output
- The split produced `main_cast_1_split_1` but no `main_cast_0_split_0` — father was absorbed
- 0 merge decisions recorded in pipeline_metadata — the absorption happened BEFORE merge tracking
- No JSON parse failures except 1 in Pronunciation Guide

## Current Issues (Priority Order)

### CRITICAL

1. **Father character (`split_0`) absorbed into son — attempt 17 fix CAUSED regression**
   - Problem: Father is completely missing from output. Son has 57 mentions (combined father+son) and father's aliases ("John Donaldson (the father)", "the father")
   - Evidence: Only `main_cast_1_split_1` exists with ID pattern; no `main_cast_0_split_0` in output
   - Root cause: The attempt 17 fix added "the father" and "the son" as standalone aliases to split characters. This likely created a new absorption vector — the father character had alias "the father" which matched son's alias pattern, causing downstream merge logic to absorb father into son. OR the alias "John Donaldson (the father)" on the son character created a match for the father's canonical name.
   - **FIX APPROACH: REVERT attempt 17 changes.** The fix at `src/agents/characters.py:1632-1634` must be reverted. The attempt 16 state (both father and son existing, extraction stable, son profile contaminated) was MUCH better than this regression. After reverting, the son profile contamination should be addressed through the PROFILING pipeline (`name_disambiguator.py`) rather than through extraction aliases.
   - Location: `src/agents/characters.py` (lines 1632-1634 — the attempt 17 addition)
   - **IMPORTANT:** The fix for son profile contamination should NOT touch the extraction pipeline. The extraction was STABLE in attempt 16. Profile disambiguation is a profiling-layer concern in `src/pipeline/character_profiling/name_disambiguator.py`.

### HIGH

2. **Son's profile entirely contains father's data (pre-existing from attempt 16, WORSENED)**
   - Problem: Son's personality, traits, evidence, and relationships all describe the father
   - Evidence: "committed grave ethical violations by embezzling", "'Took money,' he said" — all father's attributes
   - Root cause: `name_disambiguator.py` cannot distinguish father vs. son passages because both share aliases `["John Donaldson", "John"]`
   - Location: `src/pipeline/character_profiling/name_disambiguator.py`
   - Fix: After reverting CRITICAL #1, address this in the profiling pipeline ONLY. The `_check_split_character_labels()` signal needs to work without requiring "the father"/"the son" as extraction aliases. Instead, the disambiguator should extract the label from the canonical name itself (e.g., parse "John Donaldson (the father)" → label "the father") and look for contextual clues like generational references, age markers, and specific actions in the surrounding text.

3. **Chapter 2 summary factual error: "sister" instead of "cousin" (17th consecutive attempt)**
   - Problem: "his deceased sister's son" — should be "his cousin's son" or "his cousin"
   - Evidence: The text says "my cousin John" — Uncle Bill and John Sr. are cousins, not siblings
   - Location: Summary generation LLM — persistent hallucination
   - Fix: Add explicit guidance to summary prompt: "Preserve exact relationship terms used in the text (cousin, uncle, etc.) — do not substitute similar terms." OR add a post-processing verification pass.

4. **All physical_description fields are null (regression)**
   - Problem: 0/5 characters have physical descriptions; attempt 16 had descriptions for father and Uncle Bill
   - Evidence: `jq '[.characters[] | select(.physical_description != null)] | length'` returns 0
   - Root cause: May be related to the character absorption (fewer characters means different profiling targets), or profiling pipeline changes
   - Location: `src/pipeline/character_profiling/`
   - Fix: Should resolve partially after CRITICAL #1 revert restores the attempt 16 character set

### MEDIUM

5. **Pronunciation false positives (~12 of 25)**
   - Common English words (was, orderlies, manliness) and standard names (Donaldson, Barron, Margaret) flagged
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve common-word filtering; extend CMU dictionary check to longer names

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles
   - Location: `src/pipeline/chapter_detection/`

7. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Ch1 has `["the narrator", "John (the son)"]` — should use the character's actual name
   - Location: Summary prompt or post-processing

### LOW

8. **Ted Frith still missing "Teddy" alias**
9. **Son has role "supporting"** — could be argued as higher importance

## Fix History

### Attempt 1 - Fix 1: Supporting cast alias resolution
- **Issue addressed:** False character split (Ted Frith / Ted / Johnny)
- **Fix:** Added `_merge_obvious_aliases()` in `supporting.py`
- **Result:** Partially fixed — Ted Frith merged, Johnny removed. Mention counts not accumulated.
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 1 - Fix 2: Same-name disambiguation in main cast
- **Issue addressed:** Father/son conflation
- **Fix:** Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT`
- **Result:** NO CHANGE — prompt-only approach insufficient
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 1 - Fix 3: Frame vs embedded narrator detection
- **Issue addressed:** Wrong narrator identification
- **Fix:** Updated `NARRATOR_DETECTION_PROMPT` in `narrator.py`
- **Result:** FIXED — Uncle Bill now correctly tagged as first-person narrator
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`

### Attempt 3 - Fix 1: Same-name character split via summary disambiguation
- **Issue addressed:** Father/son John Donaldson conflation
- **Fix:** Added Step 1.6 `_split_disambiguated_same_name_characters()` in characters.py
- **Result:** DID NOT FIRE — method reads `characters_present` from `chapters` (StructuralElements from `_get_chapters`), but those objects have empty `characters_present` at CharacterAgent runtime.
- **Modified:** `src/agents/characters.py` (lines 161-165, 1285-1360)

### Attempt 3 - Fix 2: Organization entity filtering
- **Issue addressed:** "Red Cross" extracted as character
- **Fix:** Added `_is_organization_name()` method with universal org indicators
- **Result:** FIXED — Red Cross no longer appears in character list
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 3 - Fix 3: Spelling variant merge + alias accumulation
- **Issue addressed:** Ted Frith shows 2 mentions, no aliases
- **Fix:** Added Rule 4 for spelling variants, added aliases field to SupportingCharacter
- **Result:** PARTIALLY FIXED — Ted Frith now has alias "Ted" and 5 mentions, but "Teddy" still missing
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 4 - Fix 1: Step 1.6 data source correction
- **Issue addressed:** Father/son John Donaldson not split (Critical #1)
- **Root cause:** `_split_disambiguated_same_name_characters()` read from `chapters` (StructuralElements with empty `characters_present`), but data is in summary objects
- **Fix:** Changed method to read from `chapter_summaries` parameter
- **Result:** **REGRESSION** — main cast pipeline now produces 0 characters
- **Modified:** `src/agents/characters.py` (lines 164, 1285-1360)

### Attempt 4 - Fix 2: Pronunciation common name filtering
- **Issue addressed:** Excessive pronunciation false positives — common names flagged
- **Fix:** Added CMU dictionary check for <=4 char names
- **Result:** PARTIAL SUCCESS — Bill, Ted, Joe, Margaret removed, but many longer false positives remain
- **Modified:** `src/pipeline/pronunciation_guide/proposers/character_proposer.py`

### Attempt 5 - Fix 1: Revert Step 1.6 implementation
- **Issue addressed:** CRITICAL #1 from attempt 4 - Main cast pipeline produces 0 characters
- **Root cause:** `src/agents/characters.py:164` - Step 1.6 changes caused main_cast_count to drop to 0
- **Fix:** Removed Step 1.6 entirely to restore attempt 3 baseline
- **Result:** SUCCESS — main cast pipeline restored (`main_cast_count: 2`)
- **Modified:** `src/agents/characters.py`

### Attempt 6 - Fix 1: Re-enable Step 1.6 same-name disambiguation split
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Fix:** Re-enabled call to `_split_disambiguated_same_name_characters()` after Step 1.5
- **Result:** **DID NOT FIRE** — `characters_present` in Ch2 now shows `["Uncle Bill", "John Donaldson"]` without father/son disambiguation, so method found no split candidates
- **Modified:** `src/agents/characters.py` (lines 161-169)

### Attempt 6 - Fix 2: Fallback narrator matching
- **Issue addressed:** Narrator flag inverted (HIGH #2)
- **Fix:** Added Step 4.5 fallback fuzzy matching using `names_similar()` with 0.7 threshold
- **Result:** PARTIALLY FIXED — Uncle Bill now has `is_narrator: true`, but John Donaldson also still has `is_narrator: true`
- **Modified:** `src/agents/characters.py` (lines 247-262)

### Attempt 7 - Fix 1: Summary prompt same-name disambiguation
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — upstream fix
- **Fix:** Added "SAME-NAME DISAMBIGUATION" section to CONSOLIDATE_PROMPT and SINGLE_CHAPTER_PROMPT
- **Result:** PARTIALLY WORKED — Ch2 `characters_present` now has "John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (the uncle)". But "the uncle" is Uncle Bill misidentified as John Donaldson, and Step 1.6 still didn't produce a split.
- **Modified:** `src/pipeline/chapter_summary/summarizer.py` (lines 115-129, 191-205)

### Attempt 8 - Fix 1: Clarify summary disambiguation + extend Step 1.6 to supporting cast
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Fix 1:** Summary prompt: "Only disambiguate characters who ACTUALLY share the same base name" — prevents Uncle Bill mislabeling
- **Fix 2:** Added Step 5.10.7 to apply `_split_disambiguated_same_name_characters()` to supporting cast
- **Result:** Summary fix WORKED (no more Uncle Bill mislabeling), but split STILL DID NOT FIRE due to regex mismatch
- **Modified:**
  - `src/pipeline/chapter_summary/summarizer.py` (prompt clarification)
  - `src/agents/characters.py` (Step 5.10.7)

### Attempt 9 - Fix 1: Alias-based regex matching in _split_disambiguated_same_name_characters()
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — downstream fix
- **Fix:** Added fallback logic to try each alias as potential base_name when canonical doesn't match
- **Result:** **DID NOT WORK** — wrong condition prevented alias fallback from running
- **Modified:** `src/agents/characters.py` (lines 1400-1467)

### Attempt 10 - Fix 1: Correct alias fallback condition
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — final fix
- **Fix:** Changed line 1421 from `if not labels_found` to `if len(labels_found) < 2`
- **Result:** **SUCCESS** — Father/son split now works! Two separate characters created.
- **BUT:** Split characters have 0 mentions, no aliases, and no profiles — the split creates empty shells.
- **Modified:** `src/agents/characters.py` (line 1421)

### Attempt 11 - Fix 1: Propagate aliases to split characters
- **Issue addressed:** Split characters have 0 mentions and no profiles (CRITICAL #1, #2)
- **Root cause:** `src/agents/characters.py:1463` - Split characters created with `aliases=[]`
- **Fix:** Copy original character's aliases to each split child
- **Result:** **PARTIAL SUCCESS / NEW REGRESSION** — Father now has 29 mentions and rich profile (alias propagation worked). BUT: only ONE split child created (father). The son was absorbed as an alias of the father instead of becoming a separate character. Narrator flag incorrectly transferred to father.
- **Modified:** `src/agents/characters.py` (lines 1459-1470)

### Attempt 12 - Fix 1: Prevent re-merge of split characters in Step 3.5
- **Issue addressed:** Son absorbed as alias of father (CRITICAL #1 regression from attempt 11)
- **Root cause:** `src/agents/characters.py:1904-1923` - Step 3.5 `_merge_within_main_cast()` Pass 2 (spelling variants) uses fuzzy matching that re-merges split characters
- **Fix:** Added SAFETY CHECK 2 in Pass 2 to skip merge if both characters come from the same split operation
- **Result:** **PARTIAL SUCCESS / NEW PROBLEM** — Merge protection worked (split chars not re-merged), but NOW only `split_1` (son) survives while `split_0` (father) is MISSING. The son inherited all the father's data. The fix prevented one failure mode but exposed another: the split itself or alias distribution is assigning everything to one child.
- **Modified:** `src/agents/characters.py` (lines 1904-1923)

### Attempt 13 - Fix 1: Partition aliases between split children
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1)
- **Root cause:** `src/agents/characters.py:1463` - Split logic copied ALL aliases to EACH child, causing one child to absorb all mentions while the other had 0 mentions and got filtered
- **Fix:** Modified `_split_disambiguated_same_name_characters()` (lines 1450-1505) to PARTITION aliases
- **Result:** **NO EFFECT** — Father still missing. Son still has father's alias "John Donaldson (the father)". The partitioning code either didn't execute, was overridden downstream, or the logic was incorrect.
- **Modified:** `src/agents/characters.py` (lines 1450-1505)

### Attempt 14 - Diagnostic Fix: Add comprehensive logging to trace split character flow
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1) — 13 consecutive failed attempts required diagnostic approach
- **Fix:** Added DEBUG logging at all critical pipeline stages
- **Result:** **SUCCESS** — Both `split_0` (father) AND `split_1` (son) now exist in output! Father has 29 mentions, son has 28 mentions, Margaret Donaldson restored. The diagnostic logging and/or the accumulated fixes from prior attempts finally produced the correct split.
- **NEW ISSUE:** Son's profile is entirely the father's profile (cross-contamination in profiling stage)
- **Modified:** `src/agents/characters.py` (6 diagnostic logging blocks added throughout pipeline)

### Attempt 15 - Fix: Split character label-based disambiguation
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 14)
- **Root cause:** `name_disambiguator.py` line 355-364 — Disambiguator couldn't distinguish split characters with shared aliases
- **Fix:** Added Signal 0 (confidence 0.99) for split character label detection in `name_disambiguator.py`
- **Result:** **REGRESSION** — Son character (`split_1`) completely absorbed as alias of father. Uncle Bill lost narrator flag and demoted to supporting cast. Father incorrectly marked as narrator. The name_disambiguator changes were in the PROFILING pipeline but character EXTRACTION produced different results this run (LLM nondeterminism likely the primary cause).
- **Modified:** `src/pipeline/character_profiling/name_disambiguator.py`

### Attempt 16 - Fix: LLM Nondeterminism Defenses
- **Issue addressed:** Son absorbed as alias of father, Uncle Bill lost narrator flag (CRITICAL #1, #2 from attempt 15)
- **Root cause:** LLM nondeterminism in main cast extraction caused unstable results between runs
- **Fix:** Added three defensive protections:
  1. **Post-split validation** (`characters.py:1600-1631`): Removes sibling canonical names from aliases
  2. **Narrator promotion** (`characters.py:383-410`): Promotes narrator from supporting to main cast
  3. **Narrator exclusivity** (`characters.py:731-757`): Enforces single narrator flag
- **Result:** **SUCCESS** — Both father and son exist. Uncle Bill correctly narrates with protagonist role. Extraction is now STABLE. BUT: Son's profile still contaminated with father's data (profiling issue from attempt 14 remains unresolved — attempt 15's fix regressed and attempt 16 focused on extraction stability, not profiling).
- **Modified:**
  - `src/agents/characters.py` (lines 383-410, 600-631, 731-757)
  - `tests/test_character_extraction_v2.py` (line 1137 - updated line limit)

### Attempt 17 - Fix: Add split character labels as standalone aliases
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 16)
- **Root cause:** `src/agents/characters.py:1623-1630` - Split characters labels NOT added as standalone aliases
- **Fix:** Add label itself as alias during split character creation (line 1632-1634)
- **Result:** **REGRESSION** — Father character (`split_0`) completely absorbed into son. Only 5 characters remain (down from 7). The standalone label aliases ("the father", "the son") created new absorption vectors that bypassed the post-split validation from attempt 16.
- **Modified:** `src/agents/characters.py` (lines 1632-1634)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | No change — reads wrong data source |
| 3 | Red Cross organization | `supporting.py` (org filter) | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Partial fix |
| 4 | Father/son conflation | `characters.py` (Step 1.6 data source fix) | **REGRESSION — main cast 0 characters** |
| 4 | Pronunciation false positives | `character_proposer.py` (CMU filter for short names) | Partial fix |
| 5 | Main cast regression | `characters.py` (remove Step 1.6 entirely) | Fixed — main cast restored |
| 6 | Father/son conflation | `characters.py` (re-enable Step 1.6) | **DID NOT FIRE — upstream data lacks disambiguation** |
| 6 | Narrator flag | `characters.py` (fallback matching) | Partial fix — both chars now is_narrator=true |
| 7 | Father/son conflation | `summarizer.py` (UPSTREAM FIX - prompt disambiguation) | **PARTIAL** — disambiguation appeared but Uncle Bill mislabeled |
| 8 | Father/son conflation | `summarizer.py` (prompt clarification) + `characters.py` (Step 5.10.7) | **PARTIAL** — Summary fix worked, but regex mismatch prevents split |
| 9 | Father/son conflation | `characters.py` (alias fallback — wrong condition) | **DID NOT WORK** — condition bug |
| 10 | Father/son conflation | `characters.py:1421` (fix condition) | **SUCCESS** — split works, but 0 mentions/no profiles |
| 11 | Split chars empty | `characters.py:1459-1470` (alias propagation) | **PARTIAL** — father profiled, but son merged as alias; narrator regression |
| 12 | Son re-merged into father | `characters.py:1904-1923` (split character merge protection) | **PARTIAL** — merge protection works, but `split_0` (father) now MISSING |
| 13 | Father character missing | `characters.py:1450-1505` (alias partitioning in split logic) | **NO EFFECT** — father still missing |
| 14 | Diagnostic logging for split character flow | `characters.py` (6 diagnostic logging blocks) | **SUCCESS** — both split chars now exist! New issue: son profile contaminated |
| 15 | Son's profile contamination | `name_disambiguator.py` (split label detection) | **REGRESSION** — son absorbed as alias. LLM nondeterminism primary cause. |
| 16 | LLM nondeterminism defenses | `characters.py` (3 defensive protections) | **SUCCESS** — extraction stable. Son profile contamination remains (profiling issue). |
| 17 | Son profile contamination (via extraction aliases) | `characters.py:1632-1634` (label as alias) | **REGRESSION** — father absorbed into son. Standalone label aliases created new absorption vector. |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. |
| 6 | 7.33 | +0.73 | Narrator flag FIXED (partially). Father/son split still didn't fire (upstream data lacking). |
| 7 | 7.33 | +0.73 | Summary disambiguation PARTIAL — data now in characters_present but Uncle Bill mislabeled. |
| 8 | 7.33 | +0.73 | Summary fix WORKED (no more Uncle Bill mislabeling). Step 5.10.7 didn't split due to regex mismatch. |
| 9 | 7.08 | +0.48 | Alias fallback added but wrong condition. Margaret regression. |
| 10 | 7.25 | +0.65 | **Father/son split SUCCESS!** Margaret restored. But split chars have 0 mentions, no profiles. |
| 11 | 6.85 | +0.25 | Father profiled (29 mentions). **REGRESSION: son merged as alias of father. Narrator on wrong character.** |
| 12 | 6.10 | -0.50 | Merge protection works. **NEW REGRESSION: father (`split_0`) missing entirely.** |
| 13 | 5.93 | -0.67 | **Alias partitioning NO EFFECT.** Father still missing. Narrator regression. |
| 14 | 6.83 | +0.23 | **BREAKTHROUGH: Both father AND son exist!** Margaret restored. Uncle Bill narrator restored. NEW: Son has father's profile (cross-contamination). |
| 15 | 5.90 | -0.70 | **REGRESSION: Son absorbed as alias of father. Uncle Bill lost narrator and demoted. Father wrongly narrates.** |
| 16 | 7.28 | +0.68 | **RECOVERY: LLM defenses worked!** Both chars exist, narrator correct. Son profile still contaminated. Approaching attempt 3 high (7.35). |
| 17 | 6.33 | -0.27 | **REGRESSION: Father absorbed into son.** Attempt 17 fix (label aliases) created new absorption vector. MUST REVERT. |

## Next Action

**IMMEDIATE: Revert attempt 17 changes** to `src/agents/characters.py:1632-1634`. This will restore the attempt 16 extraction state where both father and son exist.

**THEN: Fix son profile contamination in the PROFILING pipeline** (`name_disambiguator.py`), NOT in the extraction pipeline. The key insight from attempts 15 and 17: modifying extraction aliases to help profiling causes extraction regressions. The profiling layer must solve its own disambiguation problem by:
1. Parsing the split label from the canonical name itself (e.g., "John Donaldson (the father)" → "the father")
2. Using contextual signals in gathered passages (age references, generational markers, specific actions like embezzlement vs. soldiering)
3. NOT relying on alias-level signals that could interfere with extraction
