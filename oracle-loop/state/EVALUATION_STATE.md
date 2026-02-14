# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 15
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4/10 ✗ (REGRESSION from 6.5 in attempt 14)
- Character Profiles: 5/10 ✗ (REGRESSION from 6 in attempt 14)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 6/10 ✗ (REGRESSION from 7.5 in attempt 14)
- **Overall: 5.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold) — REGRESSION from attempt 14

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

Score: 7/10

### 2.2 Character Extraction: 4/10 ✗ (CRITICAL REGRESSION from 6.5/10)

**MAJOR REGRESSION: Son character completely missing.** The attempt 15 fix (split label-based disambiguation in `name_disambiguator.py`) appears to have destabilized the split mechanism itself. Only `split_0` (father) exists; `split_1` (son) has been absorbed as an alias of the father.

**Current character list (6 total):**
- `main_cast_1_split_0`: "John Donaldson (the father)" — 56 mentions (combined father+son count!), aliases: ["John Donaldson", "John", "John Donaldson (the son)"], is_narrator: true ✗, role: supporting ✗
- `main_cast_3`: Margaret Donaldson — 2 mentions ✓ CORRECT
- `supporting_0`: Uncle Bill — 18 mentions, alias "Bill", is_narrator: false ✗, role: minor ✗
- `supporting_1`: Joe Barron — 3 mentions ✓ CORRECT
- `supporting_2`: "John Donaldson's" — 4 mentions, alias "Johnny" ✗ SPURIOUS
- `supporting_3`: Ted Frith — 5 mentions, alias "Ted" ✓ CORRECT

**Critical regressions from attempt 14:**
1. **Son character (`split_1`) is MISSING** — absorbed as an alias of the father. "John Donaldson (the son)" appears as an alias of `main_cast_1_split_0` (the father). Father's mention count is 56 (= 29 + 28, combined).
2. **Uncle Bill lost narrator flag** — `is_narrator: false` (was `true` in attempt 14). Also demoted from `main_cast` to `supporting_0` with role "minor" (was "protagonist").
3. **Father incorrectly marked as narrator** — `is_narrator: true` (was `false` in attempt 14).
4. **Father's role is "supporting"** — was "protagonist" in attempt 14.
5. **ID changed from `main_cast_0_split_0` to `main_cast_1_split_0`** — split index shifted, suggesting the underlying main cast extraction also changed.

**Persistent issues:**
6. Spurious "John Donaldson's" (possessive form) still present.
7. "Johnny" alias misassigned to spurious character instead of son.

Score: 4/10 — this is worse than attempt 14 (6.5/10). The son is gone, narrator flag inverted, Uncle Bill demoted.

### 2.3 Character Profiles: 5/10 ✗ (REGRESSION from 6/10)

**Father's profile (`main_cast_1_split_0`): MOSTLY CORRECT for the father character**
- Appearance: "middle-aged American man with dark olive skin and striking blue eyes" — correct for father ✓
- Personality: "committed financial fraud and abandoned his responsibilities, yet sought redemption" — correct for father ✓
- Voice: "American, sir", "Took money" — correct father quotes ✓
- Relationships: son=parent ✓, Margaret=spouse ✓, Uncle Bill="brother-in-law" (should be "cousin") ✗

**Uncle Bill's profile: SEVERELY CONTAMINATED with father's data** ✗
- Appearance: "A middle-aged man of dark complexion with striking blue eyes and thick lashes, bearing the physical resemblance of his son" — this describes the FATHER, not Uncle Bill. Uncle Bill is "elderly, grizzled, small man, grim and unexhilarating" per the text.
- Personality: "profound betrayal of family through theft and abandonment" — this is the FATHER's story. Uncle Bill is the narrator, characterized as "crabbed and prejudiced and critical" and "thoroughly selfish."
- Voice: "'Took money,' he said" — this is the FATHER's quote, not Uncle Bill's.
- Evidence quotes: Uncle Bill's "I am not soft-hearted" quote is present (correct), but mixed with father's quotes.
- Relationships: "John Donaldson (son): victimizer", "John Donaldson (nephew): mentor" — confused. Uncle Bill is a mentor/guardian to the son.

**Ted Frith's profile: CONTAMINATED with father's data** ✗
- Personality: "heroic protagonist whose selfless actions under fire" — partially applicable to Ted, but "serving under the American flag" is the FATHER's motivation, not Ted's
- Appearance: "elderly man with natural eyes, American uniform, tin derby hat" — mixed (tin derby is correct for Ted, but age is wrong)
- Voice quotes include "'Ah, but you are--my superior officer'" — this is actually the FATHER speaking TO Ted/the son, not Ted himself
- Relationships: "Ted Frith: ally" — self-referential relationship ✗

**Son has NO profile** because the son character doesn't exist — complete loss.

**Root cause:** The `name_disambiguator.py` fix (Signal 0 for split labels) may have changed how passages are distributed, but the deeper problem is that `split_1` (son) was re-absorbed into `split_0` (father) during the extraction pipeline. Profile contamination between Uncle Bill and the father suggests the disambiguator is now assigning father-specific passages to Uncle Bill as well.

Score: 5/10 — father's own profile is accurate, but Uncle Bill and Ted Frith are contaminated with father's data, and son has no profile at all.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 summary:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, the scandal, the inheritance split. `characters_present: ["the narrator", "John (the son)"]` — uses "the narrator" for Uncle Bill (acceptable).

**Chapter 2 summary:** Comprehensive. Covers guardianship, WWI, Caporetto, father discovery, deathbed scene. `characters_present: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` — correctly disambiguated ✓

**PERSISTENT factual error in Ch2 (15th consecutive attempt):** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The LLM consistently hallucinates "sister."

**Book overview/plot summary:** Well-written, comprehensive, captures the full arc. No factual errors in the overview.

Score: 7.5/10 — the "sister" hallucination remains the primary issue.

### 2.5 Pronunciation Guide: 6.5/10 ✗

27 entries, 22 with IPA. Unchanged from attempt 14.

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~13):** Donaldson, Barron, Donaldson's, Frith, Margaret, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "orderlies" IPA `/ˈɔːr.dər.laɪz/` — the "laɪz" ending is incorrect (should be /lɪz/)
- "was" `/wɒz/` — common word, shouldn't be flagged
- All categories null — no categorization

Score: 6.5/10 — pronunciation unchanged from prior attempts.

### 2.6 HTML Presentation: 6/10 ✗ (REGRESSION from 7.5)

**Regressions from attempt 14:**
- **Son character entirely missing** — no profile card for the son. "John Donaldson (the son)" appears only as an alias of the father.
- **Uncle Bill NOT marked as narrator** — no narrator badge displayed
- **Uncle Bill demoted to "Main Characters" section but tagged as "minor"** — contradictory
- **Father incorrectly shown as "Secondary narrator (nested narrative)"** — father is not a narrator at all
- **Father tagged as "supporting"** — should be protagonist

**Still working:**
- Navigation tabs functional ✓
- Book overview/plot summary well-written and prominent ✓
- Father's profile card content is accurate (for the father) ✓
- Margaret Donaldson in supporting cast ✓
- Ted Frith and Joe Barron present ✓

**Confusing for a narrator:**
- Uncle Bill's profile shows father's personality/appearance — a narrator would think Uncle Bill embezzled money
- Father's alias list shows "John Donaldson (the son)" — implies father IS the son
- No son character profile available at all

Score: 6/10 — functional layout but critical data errors make it misleading for narrators.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (6 × 0.10)
        = 1.40 + 1.00 + 0.75 + 1.50 + 0.65 + 0.60
        = 5.90
```

**Overall: 5.90/10** (REGRESSION from 6.83 in attempt 14)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: 32m 38s
- Character extraction: 7 items processed, 3 high / 4 medium confidence
- `main_cast_1_split_0` — ID index changed from 0 to 1, suggesting main cast extraction changed
- Only split_0 exists — split_1 was created but absorbed downstream
- Uncle Bill moved from main_cast to supporting_0

## Current Issues (Priority Order)

### CRITICAL

1. **REGRESSION: Son character (`split_1`) absorbed as alias of father**
   - Problem: `main_cast_1_split_0` (father) has "John Donaldson (the son)" as an alias, and mention_count=56 (combined father+son). The son has no separate character entry.
   - Evidence: In attempt 14, both `main_cast_0_split_0` (father, 29 mentions) and `main_cast_0_split_1` (son, 28 mentions) existed as separate characters.
   - Root cause: The attempt 15 fix to `name_disambiguator.py` (Signal 0 for split labels) was supposed to fix PROFILING, but the son character was re-absorbed during CHARACTER EXTRACTION (upstream of profiling). The fix was applied to the wrong pipeline stage — or the name_disambiguator changes had an unintended side effect on the split mechanism in `characters.py`.
   - **KEY DIAGNOSTIC: ID changed from `main_cast_0_*` to `main_cast_1_*`** — the underlying main cast extraction produced different results this run. This is likely LLM nondeterminism in character extraction, not caused by the name_disambiguator fix (which only affects profiling).
   - Location: `src/agents/characters.py` — the split mechanism in `_split_disambiguated_same_name_characters()` and/or the merge logic in `_merge_within_main_cast()`
   - Fix approach: **REVERT the attempt 15 changes to `name_disambiguator.py`** — the fix was targeting profiling but may have introduced instability. The split mechanism itself is fragile and depends on the LLM producing consistent character extraction results. Need to investigate why split_1 was absorbed. Add protection: if a split character has another split sibling's canonical name as an alias, that alias MUST be removed and the sibling character preserved.

2. **REGRESSION: Uncle Bill lost narrator flag and demoted to supporting cast**
   - Problem: Uncle Bill is `supporting_0` with `is_narrator: false` and role "minor". In attempt 14, Uncle Bill was `main_cast_2` with `is_narrator: true` and role "protagonist".
   - Evidence: Uncle Bill is unambiguously the first-person narrator of the story ("I am not soft-hearted. I am crabbed and prejudiced...").
   - Root cause: The main cast extraction produced a different set of characters this run (LLM nondeterminism). Uncle Bill may not have been identified by the LLM as a main cast member, so he fell to supporting cast where narrator detection doesn't apply as strongly.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` and `src/agents/characters.py` (narrator assignment)
   - Fix approach: Narrator detection should be more robust — if a character is identified as first-person narrator by the narrator detection pipeline, they should be promoted to main cast regardless of LLM extraction results.

3. **Father incorrectly marked as narrator**
   - Problem: `main_cast_1_split_0` (father) has `is_narrator: true`. The father is not a narrator.
   - Evidence: The father speaks dialogue in the story but does not narrate. Uncle Bill is the first-person narrator.
   - Root cause: Same as #2 — when Uncle Bill fell to supporting cast, the narrator flag may have been assigned to the remaining main cast character.
   - Location: `src/agents/characters.py` — narrator flag assignment
   - Fix approach: Will likely resolve when #2 is fixed.

### HIGH

4. **Profile contamination: Uncle Bill has father's profile data**
   - Problem: Uncle Bill's appearance, personality, and voice all describe the father (embezzlement, dark olive skin, etc.)
   - Evidence: Uncle Bill is "elderly, grizzled, small man" who is "crabbed and prejudiced and critical" — none of this appears in his current profile
   - Root cause: The `name_disambiguator.py` changes may have affected how passages for "John Donaldson" are distributed across characters. Since the son is now an alias of the father, more passages are attributed to "John Donaldson" which then bleed into Uncle Bill's profile (since Uncle Bill discusses John extensively as first-person narrator).
   - Location: `src/pipeline/character_profiling/name_disambiguator.py` and `passage_gatherer.py`
   - Fix approach: May resolve when the son is restored as a separate character (Critical #1)

5. **Spurious character "John Donaldson's" (possessive form) — 15th consecutive attempt**
   - Problem: `supporting_2` has canonical_name "John Donaldson's" with alias "Johnny"
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Strip trailing "'s" from extracted character names. Merge "Johnny" as alias of the son.

6. **Chapter 2 summary factual error: "sister" instead of "cousin" (15th consecutive attempt)**
   - Problem: "his deceased sister's twelve-year-old son" — should be "his cousin's"
   - Location: Summary generation — cross-chapter context
   - Fix: Increase summary chunk overlap to carry Ch1 relationship info into Ch2

### MEDIUM

7. **Father's relationship to Uncle Bill is "brother-in-law"** — should be "cousin"
   - The text explicitly states they are cousins ("my cousin John")

8. **Pronunciation false positives (~13 of 27)**
   - Common English words and standard names flagged unnecessarily

9. **Structure: 2 sections for a continuous short story** — 1 section more accurate

### LOW

10. **Ted Frith still missing "Teddy" alias**
11. **"orderlies" IPA wrong** — `/ˈɔːr.dər.laɪz/` should be `/ˈɔːr.dər.lɪz/`

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
| 14 | Diagnostic logging for split character flow | `characters.py` (6 diagnostic logging blocks) | **SUCCESS** — both split chars now exist! New issue: son profile contaminated with father's data |
| 15 | Son's profile contamination | `name_disambiguator.py` (split label detection) | **REGRESSION** — son absorbed as alias of father. Uncle Bill lost narrator flag. LLM nondeterminism likely primary cause. |

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

### Attempt 16 - Fix: LLM Nondeterminism Defenses (awaiting_analysis)
- **Issue addressed:** Son absorbed as alias of father, Uncle Bill lost narrator flag (CRITICAL #1, #2)
- **Root cause:** LLM nondeterminism in main cast extraction caused unstable results. The attempt 15 fix was in profiling (downstream), but regression was in extraction (upstream).
- **Fix:** Added three defensive protections to make the pipeline resilient against LLM nondeterminism:
  1. **Post-split validation** (`characters.py:1600-1631`): After split operation, scans all split siblings and removes any sibling canonical names that appear as aliases. Prevents "John Donaldson (the son)" from being an alias of the father character.
  2. **Narrator promotion** (`characters.py:383-410`): If a first-person narrator is found in supporting cast, automatically promotes them to main cast with protagonist role. Defends against main cast extraction missing the narrator.
  3. **Narrator exclusivity** (`characters.py:731-757`): After all merge/filter steps, enforces that ONLY the identified narrator has `is_narrator=True`. Clears the flag from all other characters.
- **Smoke test:** Full test suite PASS (297 passed, 10 skipped)
- **Modified:**
  - `src/agents/characters.py` (lines 383-410, 600-631, 731-757)
  - `tests/test_character_extraction_v2.py` (line 1137 - updated line limit to 7050)

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify the defensive protections stabilize the split mechanism and narrator assignment against LLM nondeterminism.
