# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 13
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 12)
- Analysis completed in 30m 47s
- Competitive consensus enabled (3 temperatures: 0.5, 0.7, 0.9)
- **Characters found:** 4 (John Donaldson (the son), Uncle Bill, Joe Barron, Ted Frith)
- **REGRESSION:** Only `main_cast_1_split_1` (son) exists — `split_0` (father) is MISSING
- **REGRESSION:** The son's character has the FATHER's profile (appearance, personality, quotes)
- **REGRESSION:** The son's aliases include "the father" and "John Donaldson (the father)"
- **REGRESSION:** Margaret Donaldson is completely MISSING (was present in attempt 11)
- **IMPROVEMENT:** Uncle Bill is now `is_narrator: true` and `role: "protagonist"` ✓
- Structure: 2 chapters detected
- Pronunciation: 24 entries flagged (all categories null)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4.5/10 ✗ (MAJOR REGRESSION from 5.5)
- Character Profiles: 5/10 ✗ (REGRESSION from 7.5)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 6.5/10 ✗ (REGRESSION from 8)
- **Overall: 6.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate.

Score: 7/10

### 2.2 Character Extraction: 4.5/10 ✗ (MAJOR REGRESSION from 5.5)

The merge-protection fix in Step 3.5 worked (split characters are no longer re-merged), but a **new critical problem** emerged: only `split_1` (the son) exists. The father character (`split_0`) is completely missing from the output. Even worse, the son's character contains the father's data:

**Current character list (4 total — was 5 in attempt 11):**
- `main_cast_1_split_1`: "John Donaldson (the son)" — has FATHER's profile data
  - Aliases: ["John Donaldson", "the father", "John", "John Donaldson (the father)"] ✗ WRONG — "the father" and "John Donaldson (the father)" should not be aliases of the son
  - Appearance: "middle-aged man", "fifty-five or over", "olive skin" — this is the FATHER's appearance ✗
  - Personality: "committed theft and abandonment" — this is the FATHER's personality ✗
  - Voice: father's quotes ("American, sir", "Took money...") ✗
  - Relationships: self-referential — "John Donaldson (the son): parent" ✗
  - 58 mentions (combined father+son mentions)
- `supporting_1`: Uncle Bill (18 mentions, `is_narrator: true`, `role: "protagonist"`) ✓ FIXED
- `supporting_2`: Joe Barron (3 mentions) ✓
- `supporting_3`: Ted Frith (5 mentions, alias "Ted") ✓

**Issues:**
1. **FATHER CHARACTER MISSING**: `main_cast_1_split_0` doesn't exist in output. The split appears to have created both children, but only `split_1` survived. The father may have been filtered out or merged into the son in a downstream step.
2. **SON HAS FATHER'S DATA**: All profile data on the son character actually describes the father. The son should be: young, 12 years old initially, later 18, ambulance driver, brave and dutiful. Instead he has: "middle-aged", "fifty-five or over", "committed theft".
3. **WRONG ALIASES ON SON**: "the father" and "John Donaldson (the father)" are listed as aliases of the son — these should belong to a separate father character.
4. **MARGARET DONALDSON MISSING**: Was `main_cast_3` in attempt 11 with 2 mentions. Now completely absent.
5. **SELF-REFERENTIAL RELATIONSHIP**: The son's relationships include "John Donaldson (the son): parent" — a character lists itself as its own parent.

**What went right:**
- Uncle Bill narrator assignment is FIXED ✓
- Uncle Bill role is now "protagonist" ✓ (was "minor")
- Joe Barron and Ted Frith correct ✓

Score: 4.5/10 — the father character vanishing and the son inheriting the father's identity is worse than the previous false merge.

### 2.3 Character Profiles: 5/10 ✗ (REGRESSION from 7.5)

The "son" character has an excellent profile — but it's the FATHER's profile attached to the wrong character:
- Appearance describes the father (middle-aged, olive skin, fifty-five) — WRONG for the son
- Personality describes the father (theft, abandonment, dishonor) — WRONG for the son
- Voice guidance has the father's quotes — WRONG for the son
- No actual son profile exists anywhere

Uncle Bill's profile is good and improved:
- Appearance: "elderly man", "thin hair", "sits by fire with cigar" ✓
- Personality: "crusty exterior conceals compassion" ✓
- Voice guidance: "low, gravelly, measured tone" ✓
- Verbal tics include "Uncle Bill" (how others address him, not his tic) — minor issue
- Relationship "family" with "John Donaldson (the father)" — references a character that doesn't exist ✗

No father character means no father profile. No son profile exists (the son only has the father's profile).

Score: 5/10 — Uncle Bill's profile is good, but the complete misattribution of the father's profile to the son character is a major error. No actual son profile or father profile exists correctly.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 summary:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, Margaret's dignity. `characters_present: ["the narrator", "John (the son)"]` — uses "the narrator" instead of "Uncle Bill" (minor inconsistency).

**Chapter 2 summary:** Comprehensive. **PERSISTENT factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 12 attempts. The LLM consistently hallucinates "sister" from the uncle-nephew relationship. Everything else in Ch2 is accurate — war service, Caporetto, discovery of the father, reconciliation, death scene.

**Ch2 characters_present:** `["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` — correctly disambiguated ✓

Score: 7.5/10 — the "sister" hallucination is the primary issue.

### 2.5 Pronunciation Guide: 6.5/10 ✗

24 entries, all categories null.

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~10):** Donaldson, Barron, Frith, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "orderlies" still `/ˈɔːr.dər.laɪz/` — wrong (should be `/ˈɔːr.dər.liz/`)
- "was" `/wɒz/` — common word, shouldn't be flagged at all
- All categories null — no categorization

Score: 6.5/10 — good Italian/French geographic coverage but ~10 false positives and all categories null.

### 2.6 HTML Presentation: 6.5/10 ✗ (REGRESSION from 8)

The HTML is well-organized with functional navigation and tabs. However the character data errors severely impact usability for a narrator:

- **"John Donaldson (the son)" shown as main character with father's profile** — deeply confusing. A narrator would read that the "son" is "middle-aged, fifty-five or over" and has "committed theft and abandonment"
- **Aliases show "the father" under the son** — nonsensical to a narrator
- **Self-referential relationship** — "John Donaldson (the son): parent" — the character is listed as its own parent
- **References non-existent character** — Uncle Bill's relationships reference "John Donaldson (the father)" who doesn't exist in the character list
- **No father character at all** — a narrator preparing this story would have no guidance for voicing the father
- **Margaret Donaldson missing** — no entry for her at all

The structural and functional elements of the HTML are fine, but the data quality makes it misleading.

Score: 6.5/10 — functional layout degraded by severely incorrect character data.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4.5 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (6.5 × 0.10)
        = 1.40 + 1.125 + 0.75 + 1.50 + 0.65 + 0.65
        = 6.075
```

**Overall: 6.10/10** (rounded)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents
- `main_cast_count: 2` — but Margaret disappeared, so effectively main cast has only 1 (the merged son/father)
- `supporting_count: 3` (Uncle Bill, Joe, Ted)
- Only one split character survived (`main_cast_1_split_1`) — `split_0` missing
- All pronunciation categories null
- `physical_description` null for all characters (data is in `appearance` field)

## Current Issues (Priority Order)

### CRITICAL

1. **FATHER CHARACTER (`split_0`) MISSING FROM OUTPUT**
   - Problem: The split in Step 1.6 should create both `main_cast_1_split_0` (father) and `main_cast_1_split_1` (son). In attempt 11, only `split_0` survived and absorbed the son. Now in attempt 12 (after the merge-protection fix), only `split_1` survives. The father character has vanished entirely.
   - Evidence: `jq '.characters[] | .id' analysis.json` shows `main_cast_1_split_1` but no `split_0`. The son's aliases include "the father" and "John Donaldson (the father)" — the father's identity was absorbed into the son.
   - Root cause: The Step 3.5 merge-protection fix prevented the re-merge in Pass 2, but there may be ANOTHER merge point that absorbs `split_0` into `split_1`, OR the split itself may be only creating one child. The split logic in `_split_disambiguated_same_name_characters()` needs investigation — it may be assigning ALL aliases (including the father's disambiguated label) to the son, then the father has no aliases/mentions and gets filtered out by a minimum-mention threshold.
   - Location: `src/agents/characters.py` — `_split_disambiguated_same_name_characters()` (split creation logic) and any downstream filtering that removes characters with 0 mentions
   - Fix:
     1. Investigate what happens to `split_0` — does it get created? Does it get filtered?
     2. Ensure each split child gets ONLY its own aliases (son gets "the son" variants, father gets "the father" variants, shared aliases like "John Donaldson" and "John" go to BOTH)
     3. Ensure the split properly distributes mentions (not 58 to one, 0 to the other)
   - Impact: Would raise Character Extraction from 4.5 to ~7+ and Profiles from 5 to ~7+

2. **SON CHARACTER HAS FATHER'S PROFILE AND ALIASES**
   - Problem: The son's profile describes the father (middle-aged, olive skin, committed theft). The son's aliases include "the father". This is a direct consequence of Issue #1 — all data was assigned to the son instead of being split.
   - Evidence: `characters[0].appearance.details.age = "fifty-five or over"` but this character is "John Donaldson (the son)" who is 12-18 years old
   - This will be fixed by fixing Issue #1

### HIGH

3. **Margaret Donaldson MISSING**
   - Problem: Margaret was `main_cast_3` in attempt 11 (2 mentions). Now completely absent from output.
   - Evidence: Margaret is the wife of the father/cousin John. She writes the letter informing Uncle Bill of John's death. She is a named, speaking character.
   - Root cause: May be related to the split changes or a different main cast extraction result in this run.
   - Location: Check if the main cast pipeline produced Margaret in this run or if she was lost.
   - Fix: This may be an LLM variance issue (competitive consensus dropped her) rather than a code bug. Monitor.

4. **Pronunciation false positives (~10 of 24)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums. Common names: Donaldson, Barron, Frith
   - All pronunciation categories are null
   - "orderlies" IPA still wrong (`/laɪz/` instead of `/liz/`)
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve filtering of common English words and names; populate categories

5. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 12 attempts — LLM consistently hallucinates "sister" for Ch2
   - Location: Summary generation — the "cousin" context from Ch1 may not be in Ch2's overlap
   - Fix: Increase summary chunk overlap to ensure the "cousin" relationship from Ch1 is visible in Ch2's context

### MEDIUM

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate for a text with no structural markers

7. **Ch1 characters_present says "the narrator" instead of "Uncle Bill"**
   - Minor inconsistency with Ch2 which correctly uses "Uncle Bill"

8. **Self-referential relationship on son character**
   - "John Donaldson (the son): parent" — the character references itself
   - Will be fixed by fixing the split (Issue #1)

### LOW

9. **Ted Frith still missing "Teddy" alias**
    - Text uses "Teddy" 2x but not captured

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
| 12 | Son re-merged into father | `characters.py:1904-1923` (split character merge protection) | **PARTIAL** — merge protection works, but `split_0` (father) now MISSING. Son has father's data. |
| 13 | Father character missing | `characters.py:1450-1505` (alias partitioning in split logic) | **TESTING** — partitions aliases between split children to prevent mention absorption |

**PATTERN DETECTED:** `characters.py` has been modified in 11 of 13 attempts for the father/son split issue. The split logic (`_split_disambiguated_same_name_characters`) is the core problem area. Each fix addresses one symptom but exposes another:
- Attempt 10: Split works but chars are empty shells
- Attempt 11: Aliases propagated but all go to one child → re-merge
- Attempt 12: Merge protection works but alias distribution is wrong → one child has everything, other has nothing and gets filtered

**ROOT CAUSE:** The alias distribution in `_split_disambiguated_same_name_characters()` gives ALL original aliases to EACH split child. The child whose disambiguated label comes first in the `characters_present` data absorbs all mentions, leaving the other child with 0 mentions and likely getting filtered. The fix must PARTITION aliases between split children, not copy all to both.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. |
| 6 | 7.33 | +0.73 | Narrator flag FIXED (partially). Father/son split still didn't fire (upstream data lacking). |
| 7 | 7.33 | +0.73 | Summary disambiguation PARTIAL — data now in characters_present but Uncle Bill mislabeled + Step 1.6 no split. |
| 8 | 7.33 | +0.73 | Summary fix WORKED (no more Uncle Bill mislabeling). Step 5.10.7 didn't split due to regex mismatch with aliases. |
| 9 | 7.08 | +0.48 | Alias fallback added but wrong condition. Margaret regression. |
| 10 | 7.25 | +0.65 | **Father/son split SUCCESS!** Margaret restored. But split chars have 0 mentions, no profiles. |
| 11 | 6.85 | +0.25 | Father profiled (29 mentions). **REGRESSION: son merged as alias of father. Narrator on wrong character.** |
| 12 | 6.10 | -0.50 | Merge protection works. **NEW REGRESSION: father (`split_0`) missing entirely. Son has father's data. Margaret missing.** |

## Fix History (continued)

### Attempt 13 - Fix 1: Partition aliases between split children
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1)
- **Root cause:** `src/agents/characters.py:1463` - Split logic copied ALL aliases to EACH child, causing one child to absorb all mentions while the other had 0 mentions and got filtered
- **Fix:** Modified `_split_disambiguated_same_name_characters()` (lines 1450-1505) to PARTITION aliases:
  - Label-specific aliases (e.g., "the father", "John Donaldson (the father)") → assigned to that specific split child only
  - Shared aliases (e.g., "John Donaldson", "John") → assigned to ALL split children
  - Each child now gets only relevant aliases, preventing mention-absorption by one child
- **Smoke test:** Verified alias partitioning logic with test case - father gets father-specific + shared, son gets son-specific + shared
- **Modified:** `src/agents/characters.py` (lines 1450-1505)

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify:
1. Both `split_0` (father) and `split_1` (son) survive with non-zero mentions
2. Each character has correct profile data (father = middle-aged, son = young)
3. Margaret Donaldson appears in output (monitor for LLM variance)
