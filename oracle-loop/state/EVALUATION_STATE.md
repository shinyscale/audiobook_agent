# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 17
- **Phase:** running_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 16)
- Analysis completed in 33m 39s
- **KEY SUCCESS:** LLM nondeterminism defenses WORKED:
  - Both father (`main_cast_0_split_0`, 28 mentions) AND son (`main_cast_0_split_1`, 28 mentions) exist as separate characters
  - Uncle Bill correctly identified as narrator (`is_narrator: true`, role: protagonist)
  - Narrator exclusivity defense cleared `is_narrator` from all non-narrator characters
  - Narrator promotion defense promoted Uncle Bill from supporting to main cast
- **REMAINING:** Son's profile is contaminated with father's data (profiling pipeline issue)
- Total characters: 7 (1 spurious: "John Donaldson's")
- Character profiles generated for top 4 characters via HTML profiling pipeline

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7.5/10 ✗
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.28/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

### 2.2 Character Extraction: 7.5/10 ✗

**Major recovery from attempt 15 (4/10).** The three nondeterminism defenses all worked correctly:

**What's correct now (recovered from attempt 15 regression):**
- Father (`main_cast_0_split_0`) and son (`main_cast_0_split_1`) both present — 28 mentions each ✓
- Uncle Bill correctly identified as first-person narrator with protagonist role ✓
- No alias cross-contamination between father and son ✓
- Margaret Donaldson present (2 mentions) ✓
- Ted Frith with alias "Ted" (5 mentions) ✓
- Joe Barron (3 mentions) ✓

**Remaining issues:**
1. Spurious `supporting_2` "John Donaldson's" (possessive form) with alias "Johnny" — "Johnny" should be on the son
2. Son has self-referential relationship: `"John Donaldson (the son)": "parent"` — should be `"John Donaldson (the father)": "parent"`
3. Son has `"Margaret Donaldson": "spouse"` — Margaret is the father's wife, not the son's
4. Both father and son have role "supporting" — son could be argued as higher

### 2.3 Character Profiles: 7/10 ✗

**Major recovery from attempt 15 (5/10).** Uncle Bill's profile is no longer contaminated:

**Uncle Bill: EXCELLENT** ✓
- Appearance: "elderly, grizzled, small man" — correct
- Personality: "deeply principled and self-sacrificing" with "crabbed exterior" — correct
- Voice: Uncle Bill's own quotes — correct

**Father: EXCELLENT** ✓
- Appearance: "dark olive skin and intense blue eyes" — correct
- Personality: "morally ambiguous man who stole and fled" — correct
- Voice: "American, sir" — correct

**Son: CONTAMINATED WITH FATHER'S DATA** ✗
- Appearance: "dark-complexioned, blue eyes, grizzled, shabby clothes" — this is the FATHER
- Personality: "committed theft and deception" — this is the FATHER's arc; the son is innocent and brave
- Voice: "American, Sir!" — the FATHER's quote
- The son's profile is essentially a duplicate of the father's profile

**Root cause:** The `name_disambiguator.py` cannot distinguish which "John Donaldson" passages belong to the father vs. the son, because both split characters share the same aliases (`["John Donaldson", "John"]`). The profiling pipeline gathers passages for "John Donaldson" and assigns them to whichever character matches — but both match equally. The father's profile is correct because his distinctive actions (theft, flight, deathbed) are more salient. The son's profile gets the remaining father-descriptive passages.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** Good quality. Captures letter, Uncle Bill's reaction, memories, scandal, inheritance split. `characters_present: ["John (the boy)"]` — acceptable but should also include "Uncle Bill" / "the narrator".

**Chapter 2:** Comprehensive. Covers guardianship, WWI, Caporetto, father discovery, deathbed. `characters_present` correctly lists all three key characters.

**PERSISTENT factual error (16th consecutive attempt):** Ch2 says "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son.

**Book overview:** Excellent — accurate, comprehensive, well-written.

### 2.5 Pronunciation Guide: 6.5/10 ✗

27 entries, 22 with IPA. Unchanged from prior attempts.
- ~9 genuinely useful (Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't)
- ~5 acceptable homographs (live, minute, read, close, moderate)
- ~13 false positives (Donaldson, Barron, Donaldson's, Frith, Margaret, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was)
- "orderlies" IPA now correct: `/ˈɔːr.dər.lɪz/` ✓ (was wrong in attempt 15)

### 2.6 HTML Presentation: 8/10 ✓

**Major recovery from attempt 15 (6/10):**
- Uncle Bill correctly shown with narrator badge and "protagonist" tag ✓
- Father and son BOTH have separate profile cards ✓
- Navigation tabs functional ✓
- Book overview prominent and accurate ✓
- Father's profile card content correct ✓
- Uncle Bill's profile card content correct (no contamination) ✓

**Minor issues:**
- Son's profile card shows father's data (contamination from profiling, not presentation)
- Spurious "John Donaldson's" visible in supporting cast
- Generic chapter titles ("Chapter 1", "Chapter 2")

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (8 × 0.10)
        = 1.40 + 1.875 + 1.05 + 1.50 + 0.65 + 0.80
        = 7.275 → 7.28
```

**Overall: 7.28/10** (recovery from 5.90 in attempt 15, approaching attempt 3 high of 7.35)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: 33m 39s
- Character extraction: 7 items, main_cast_count=4, supporting_cast_count=3
- Split characters `main_cast_0_split_0` and `main_cast_0_split_1` both survived pipeline ✓
- Uncle Bill promoted from supporting to main cast by narrator promotion defense ✓
- 1 merge decision (high confidence)

## Current Issues (Priority Order)

### CRITICAL

1. **Son's profile is entirely the father's profile (profiling cross-contamination)**
   - Problem: Son's appearance ("grizzled, shabby clothes"), personality ("committed theft"), and voice ("American, Sir!") all describe the father. The son is a young, brave American soldier — none of this appears.
   - Evidence: Compare father (line 946) and son (line 1049) profile cards in report.html — nearly identical content.
   - Root cause: `name_disambiguator.py` cannot distinguish father vs. son passages because both share aliases `["John Donaldson", "John"]`. The profiling pipeline assigns father-descriptive passages to both characters.
   - Location: `src/pipeline/character_profiling/name_disambiguator.py` — the disambiguation signals (name-shape, temporal, relationship markers) are not sufficient when both characters share identical name forms.
   - Fix approach: The disambiguator needs to use the split label itself — "John Donaldson (the father)" vs "John Donaldson (the son)" — to route passages. The attempt 15 fix (Signal 0 for split labels) was on the right track but caused a regression in extraction. The key difference now: extraction is STABLE (defenses protect it), so a profiling-only fix to `name_disambiguator.py` should be safe. Add logic: for split characters, extract the label (e.g., "the father", "the son") and use it as a high-confidence disambiguation signal to assign generational/role-specific passages correctly.

### HIGH

2. **Spurious character "John Donaldson's" (possessive form) — 16th consecutive attempt**
   - Problem: `supporting_2` has canonical_name "John Donaldson's" with alias "Johnny"
   - Evidence: This is a possessive form artifact, not a real character
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Strip trailing "'s" from extracted character names during supporting cast extraction. Merge "Johnny" as alias of the son character.

3. **Chapter 2 summary factual error: "sister" instead of "cousin" (16th consecutive attempt)**
   - Problem: "his deceased sister's son" — should be "his cousin's son" or "his cousin"
   - Evidence: The text says "my cousin John" — Uncle Bill and John Sr. are cousins, not siblings
   - Location: Summary generation LLM — the model consistently hallucinates "sister"
   - Fix: Add a fact-checking pass or increase summary chunk overlap to carry Ch1 relationship information into Ch2. Alternatively, add explicit guidance to the summary prompt: "Preserve exact relationship terms used in the text (cousin, uncle, etc.) — do not substitute similar terms."

4. **Son's relationships are incorrect**
   - Problem: Son has `"John Donaldson (the son)": "parent"` (self-referential) and `"Margaret Donaldson": "spouse"` (Margaret is father's wife)
   - Root cause: Profiling cross-contamination — the son received the father's relationship data
   - Location: `src/pipeline/character_profiling/` — relationship extraction
   - Fix: Will likely resolve when CRITICAL #1 (profile contamination) is fixed

### MEDIUM

5. **Pronunciation false positives (~13 of 27)**
   - Common English words (was, orderlies, manliness) and standard names (Donaldson, Barron, Margaret, Johnny) flagged unnecessarily
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve common-word filtering; extend CMU dictionary check to longer names

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles
   - Location: `src/pipeline/chapter_detection/`
   - Fix: Could add a "no chapters detected" fallback that produces a single section

7. **Ch1 characters_present missing Uncle Bill**
   - `characters_present: ["John (the boy)"]` — Uncle Bill/the narrator should be included
   - Location: Summary prompt or character extraction from summaries

### LOW

8. **Ted Frith still missing "Teddy" alias**
9. **Father and son both have role "supporting"** — son could be argued as higher importance

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
- **Issue addressed:** Son's profile cross-contamination (CRITICAL #1 from attempt 14)
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

## Fix History (continued)

### Attempt 17 - Fix: Add split character labels as standalone aliases
- **Issue addressed:** Son's profile contamination (CRITICAL #1)
- **Root cause:** `src/agents/characters.py:1623-1630` - Split characters created with labels in canonical name (e.g., "John Donaldson (the father)") but labels NOT added as standalone aliases. The `_check_split_character_labels()` method in `name_disambiguator.py` looks for "the father"/"the son" in text but never finds them because they're not in the alias list.
- **Fix:** Add label itself as alias during split character creation (line 1632-1634)
  - Father aliases: `["John Donaldson", "John", "John Donaldson (the father)", "the father"]`
  - Son aliases: `["John Donaldson", "John", "John Donaldson (the son)", "the son"]`
- **Expected result:** `name_disambiguator._check_split_character_labels()` will now find label-specific aliases ("the father", "the son") in text passages and correctly route father-descriptive passages to father and son-descriptive passages to son.
- **Modified:** `src/agents/characters.py` (lines 1632-1634)
- **Status:** RUNNING - Analysis started at $(date +%H:%M) on attempt 17

## Next Action
Wait for analysis completion (estimated 30-40 minutes)
