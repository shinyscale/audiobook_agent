# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗ (REGRESSION)
- Character Profiles: 6.5/10 ✗ (REGRESSION)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 6.73/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold — REGRESSION from attempt 3)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from attempt 3. Two sections with null titles for a continuous short story. Workable but not ideal — 1 section would be more accurate for a text with no structural markers.

### 2.2 Character Extraction: 5/10 ✗ (REGRESSION from 7)

**CRITICAL REGRESSION: Main cast pipeline produced ZERO characters.** All 4 characters have `supporting_*` IDs (`pipeline_metadata.main_cast_count: 0, supporting_cast_count: 4`). In attempts 1-3, John Donaldson and Uncle Bill came from `main_cast_*`. This means:

1. **Father/son split STILL did not fire** — Step 1.6 `_split_disambiguated_same_name_characters()` is in the CharacterAgent which processes main_cast output, but since main_cast produced 0 characters, the split code had nothing to work with. There is still only one "John" entry (supporting_0, 30 mentions) conflating father and son.

2. **Margaret Donaldson is MISSING** — Was present in attempts 1-3 as a supporting character. Now gone entirely. She is mentioned in the text as John Sr.'s widow who wrote Uncle Bill a letter. Her disappearance is unexplained.

3. **Canonical name "John" instead of "John Donaldson"** — The canonical name is just "John" with "John Donaldson" as an alias. This is backwards — the full name should be canonical.

4. **"John Donaldson's" listed as alias** — A possessive form is not a valid alias. This is noise.

5. **Uncle Bill relationship: "enemy"** — The JSON shows `"Uncle Bill": "enemy"` in John's relationships. Uncle Bill was John Sr.'s benefactor and guardian of his son — the opposite of an enemy.

**What works:**
- Uncle Bill correctly identified as protagonist and first-person narrator
- Joe Barron and Ted Frith present with correct mention counts
- No hallucinated characters
- "Johnny" alias correctly captured for John

Score dropped from 7→5 due to: main cast pipeline failure (entire pipeline path broken), Margaret missing, worse canonical naming, wrong relationship labels.

### 2.3 Character Profiles: 6.5/10 ✗ (REGRESSION from 8)

**JSON `profile` field is null for ALL 4 characters.** This is a direct consequence of the main_cast pipeline failure — supporting cast characters apparently don't go through full profiling or their profiles aren't stored in the JSON `profile` field.

**However**, the HTML report DOES render rich profiles for John and Uncle Bill:

**John's profile (in HTML, conflated father+son):**
- Appearance: "middle-aged man with dark complexion and striking blue eyes" — accurate for the father
- Personality: "morally ambiguous man who committed profound betrayal" — accurate for the father
- Voice: "American, sir!" quote, "Took money" quote — accurate father quotes
- Relationships: `Uncle Bill (enemy)` — WRONG, should be cousin/benefactor

**Uncle Bill's profile (in HTML):**
- Appearance: "elderly man of refined but unassuming presence" — acceptable
- Personality: "stoic but deeply principled man" — accurate
- Voice guidance: good tone description, appropriate formality
- Example quote misattribution: "I want you to know that I'll be prouder all my life than words can say that I've had you for a father" — this is the SON speaking to his dying father, NOT Uncle Bill
- Relationships: only `John Donaldson (mentor)` — incomplete, missing cousin relationship to John Sr.

**Issues vs attempt 3:**
- JSON profiles all null (were populated before)
- Relationship label "enemy" for Uncle Bill is worse than attempt 3's "victimizer" (both wrong, but enemy is more wrong)
- Quote misattribution (new issue)
- Son has no profile at all since conflated with father

Score 6.5/10 — profiles exist in HTML but JSON is empty, relationship labels are wrong, key quote is misattributed.

### 2.4 Chapter Summaries: 7.5/10 ✗

Unchanged from attempt 3 evaluation.

**Section 1 summary:** Mostly accurate. Captures the backstory well. Issue: `characters_present` only lists "Narrator" — should include Uncle Bill, John Donaldson, Margaret Donaldson.

**Section 2 summary:** Still contains the persistent factual error: "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN (text explicitly says "a cousin, who had come to be this lad's father"), NOT his sister's son. This is an LLM hallucination that has persisted across all 4 attempts.

Otherwise both summaries are detailed, comprehensive, and useful for narrator preparation.

### 2.5 Pronunciation Guide: 6.5/10 ✗ (SLIGHT IMPROVEMENT)

26 entries (down from 29 in attempt 3). The CMU dictionary filter successfully removed common short names:
- ✅ Removed: Bill, Ted, Joe, Margaret (were false positives in attempt 3)

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**Remaining false positives (~11):** Donaldson, Donaldson's (duplicate), Barron, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" given as `/bəˈrɒn/` (buh-RON) — should be `/ˈbær.ən/` (BARE-un), stress on first syllable
- "orderlies" IPA `/ˈɔːr.dər.lɪz/` — now correct (fixed from attempt 3)
- "was" `/wɒz/` — common word, shouldn't be flagged at all

Score 6.5/10 (up from 6) — common short names removed successfully, but still ~11 false positives including common English vocabulary (was, whippersnapper, manliness, thriftless, thickset, orderlies, dum-dums).

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation, character profiles rendered with appearance/personality/voice sections, pronunciation guide. Both section titles show "Chapter 1" and "Chapter 2" (no null display). Minor: sections lack meaningful titles since text has no chapter divisions.

Score unchanged.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (6.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (9 × 0.10)
        = 1.40 + 1.25 + 0.975 + 1.50 + 0.65 + 0.90
        = 6.675 ≈ 6.68
```

**Overall: 6.68/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- 1 JSON parse failure in pronunciation (minor, same as before)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 0` — **THIS IS THE ROOT CAUSE** of most regressions
- Character Profiles was the bottleneck at 534s (largest stage)
- Only 3 characters profiled (not 4) — Joe Barron likely skipped due to low mentions

## Current Issues (Priority Order)

### CRITICAL

1. **Main cast pipeline produced ZERO characters — all characters came from supporting cast**
   - Problem: `pipeline_metadata.main_cast_count: 0, supporting_cast_count: 4`. In attempts 1-3, John Donaldson and Uncle Bill came from main_cast. Now the main cast pipeline is completely silent.
   - Impact: This causes cascading failures: (a) Step 1.6 father/son split can't fire since it operates on main_cast output, (b) JSON profiles are null since supporting cast path may skip full profiling, (c) canonical names are worse ("John" instead of "John Donaldson")
   - Root cause: Unknown — need to investigate why main cast extraction returned 0 results. Possible causes: (1) the Step 1.6 fix in `characters.py` broke something upstream, (2) the pronunciation fix inadvertently affected character extraction, (3) model/prompt interaction changed
   - Location: `src/agents/characters.py` (main cast orchestration), `src/pipeline/character_extraction_v2/main_cast.py` (main cast pipeline)
   - Fix: **INVESTIGATE FIRST** — check the changes made in attempt 4 Fix 1 (`characters.py` lines 161-165, 1285-1360). Look for any change that could prevent main cast from running or could cause it to return 0 results. Run main cast extraction in isolation to verify.

2. **Father/son John Donaldson still NOT split**
   - Problem: Still one "John" entry (supporting_0, 30 mentions) conflating father (~55, embezzler, died as stretcher-bearer) and son (~23, ambulance driver)
   - Root cause: Step 1.6 operates on main_cast output, but main cast produced 0 characters (see Critical #1). The split code literally has nothing to split.
   - Fix: Fix Critical #1 first. Once main cast pipeline works again, the Step 1.6 data source fix (which smoke-tested successfully) should enable the split.

### HIGH

3. **Margaret Donaldson missing**
   - Problem: Present in attempts 1-3, now absent. She is John Sr.'s widow who wrote Uncle Bill a letter — a named, mentioned character.
   - Root cause: Likely related to main cast pipeline failure (Critical #1). She may have been extracted by main cast previously, or a supporting cast change inadvertently excluded her.
   - Location: Check supporting cast extraction and any filtering changes

4. **Pronunciation false positives still excessive (11 of 26)**
   - Problem: Common English words still flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Johnny, Donaldson, Donaldson's, Barron
   - The CMU filter worked for short common names (Bill, Ted, Joe, Margaret removed), but doesn't catch longer common words
   - Location: `src/pipeline/pronunciation_guide/` — needs broader filtering beyond just short names
   - Fix: The pronunciation prompt should instruct the LLM to NOT flag: (1) standard English vocabulary found in any dictionary (whippersnapper, thriftless, manliness, orderlies, thickset), (2) common English words (was), (3) possessive forms of already-flagged words (Donaldson's when Donaldson is already listed), (4) common English nicknames (Johnny). The "Barron" IPA is also wrong (buh-RON instead of BARE-un).

5. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across all 4 attempts — LLM hallucination
   - Hard to fix generically

### MEDIUM

6. **JSON `profile` field null for all characters**
   - Problem: HTML has rich profiles but JSON `profile`, `physical_description`, `speech_patterns` all null
   - Root cause: Likely connected to main cast failure — profiles may only be stored in JSON for main_cast characters, or the profile-to-JSON export path is broken for supporting cast
   - Impact: API consumers expecting profile data won't find it

7. **Relationship labels wrong**
   - Problem: "Uncle Bill (enemy)" — should be cousin/benefactor. Uncle Bill's quote misattributed (son's words given to Uncle Bill)
   - Location: Character profiling — LLM-generated relationship labels

8. **Chapter 1 `characters_present` only lists "Narrator"**
   - Problem: Should include Uncle Bill, John Donaldson, Margaret Donaldson
   - Characters discussed/referenced should be included

### LOW

9. **"Donaldson's" listed as both alias and pronunciation entry**
   - Problem: Possessive form shouldn't be a separate alias or pronunciation entry
   - Location: Alias extraction and pronunciation filtering

10. **Ted Frith missing "Teddy" alias**
    - Problem: Text uses "Teddy" 2x but not captured
    - Same issue as attempt 3

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
- **Smoke test:** PASS — but full pipeline FAILED because main cast produced 0 characters
- **Result:** **REGRESSION** — main cast pipeline now produces 0 characters. The Step 1.6 fix may have broken upstream main cast processing, or the fix changed the CharacterAgent.run() method in a way that disrupted the flow.
- **Modified:** `src/agents/characters.py` (lines 164, 1285-1360)

### Attempt 4 - Fix 2: Pronunciation common name filtering
- **Issue addressed:** Excessive pronunciation false positives — common names flagged
- **Fix:** Added CMU dictionary check for <=4 char names
- **Result:** PARTIAL SUCCESS — Bill, Ted, Joe, Margaret removed, but many longer false positives remain
- **Modified:** `src/pipeline/pronunciation_guide/proposers/character_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | No change — reads wrong data source |
| 3 | Red Cross organization | `supporting.py` (org filter) | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Partial fix |
| 4 | Father/son conflation | `characters.py` (Step 1.6 data source fix) | **REGRESSION — main cast now produces 0 characters** |
| 4 | Pronunciation false positives | `character_proposer.py` (CMU filter for short names) | Partial fix (short names removed, long words remain) |

**⚠️ STUCK PATTERN DETECTED:** `characters.py` has been modified 3 times (attempts 3, 3, 4) targeting the father/son split, and each time either failed or caused regression. The attempt 4 change is the prime suspect for the main_cast_count=0 regression.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. Pronunciation slightly improved. |

## Priority Fix Order for Attempt 5

**CRITICAL: Investigate and fix the main cast pipeline failure FIRST.** This is a regression caused by attempt 4 changes to `characters.py`. The fix phase must:

1. **Investigate `characters.py` changes from attempt 4** — Compare the current code to the pre-attempt-4 version (commit `8aa406c`). Identify what in the Step 1.6 data source fix broke the main cast pipeline. The most likely cause: a change to `CharacterAgent.run()` or its helper methods that prevents main cast from executing or causes it to return empty.

2. **Fix without re-breaking Step 1.6** — The Step 1.6 data source fix (reading from summary objects instead of chapters) smoke-tested correctly. The goal is to preserve that fix while restoring main cast pipeline functionality. This may require reverting only the parts that broke main cast while keeping the Step 1.6 data source change.

3. **Pronunciation prompt improvement** — After character extraction is fixed, improve the pronunciation LLM prompt to not flag standard English dictionary words. The CMU short-name filter works for names like Bill/Ted/Joe but doesn't help with whippersnapper/thriftless/manliness/orderlies/was.

## Next Action
**Phase:** awaiting_fix

Run PROMPT_fix.md. Priority: investigate and fix the main_cast_count=0 regression in `characters.py`, then address pronunciation false positives.
