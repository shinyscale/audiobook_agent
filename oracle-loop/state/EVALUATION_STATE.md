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

## Pipeline Notes (Attempt 14)
- Analysis completed in 38m 33s with diagnostic logging enabled
- **BREAKTHROUGH:** Both father AND son characters now exist as separate entities!
- **Characters found:** 7 total
  - `main_cast_0_split_0`: John Donaldson (the father) - 29 mentions ✓ RESTORED
  - `main_cast_0_split_1`: John Donaldson (the son) - 28 mentions ✓ EXISTS
  - `main_cast_2`: Uncle Bill - 18 mentions, is_narrator=true ✓ RESTORED
  - `main_cast_4`: Margaret Donaldson - 2 mentions ✓ RESTORED
  - `supporting_1`: Joe Barron - 3 mentions ✓
  - `supporting_2`: "John Donaldson's" - 4 mentions ✗ SPURIOUS (possessive form)
  - `supporting_3`: Ted Frith - 5 mentions, alias "Ted" ✓

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6.5/10 ✗
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 7.5/10 ✗
- **Overall: 6.83/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

Score: 7/10

### 2.2 Character Extraction: 6.5/10 ✗ (IMPROVEMENT from 4/10)

**Major progress this attempt:** The father/son split finally works — both `split_0` and `split_1` exist as separate characters. Margaret Donaldson is restored. Uncle Bill's narrator flag is restored.

**Current character list (7 total):**
- `main_cast_0_split_0`: "John Donaldson (the father)" — 29 mentions, aliases: ["the father", "John Donaldson", "John"], is_narrator: false, role: protagonist ✓ CORRECT
- `main_cast_0_split_1`: "John Donaldson (the son)" — 28 mentions, aliases: ["John Donaldson", "John"], is_narrator: true, role: supporting ✗ ISSUES (see below)
- `main_cast_2`: Uncle Bill — 18 mentions, alias "Bill", is_narrator: true, role: protagonist ✓ CORRECT
- `main_cast_4`: Margaret Donaldson — 2 mentions, no aliases ✓ CORRECT
- `supporting_1`: Joe Barron — 3 mentions ✓ CORRECT
- `supporting_2`: "John Donaldson's" — 4 mentions, alias "Johnny" ✗ SPURIOUS — this is a possessive form extracted as a character name. "Johnny" is likely Ted Frith's nickname for the son and should be an alias of the son, not a separate character.
- `supporting_3`: Ted Frith — 5 mentions, alias "Ted" ✓ CORRECT

**Issues:**
1. **Spurious character "John Donaldson's"**: A possessive form extracted as a character. This is a supporting cast extraction error — the apostrophe-s was treated as part of the name.
2. **Son marked as narrator (partially defensible)**: The son does tell the embedded wartime story in Ch2, so "secondary narrator (nested narrative)" is partially correct. However, he's primarily a character, not a narrator — he recounts events to Uncle Bill who is the actual first-person narrator.
3. **Son's role is "supporting"**: Should be "protagonist" or "major" — the son is a central character whose story drives the entire narrative.
4. **"Johnny" alias misassigned**: "Johnny" is used by Ted Frith to address the son ("That you, Johnny?"). It should be an alias of the son, not of the spurious "John Donaldson's" character.

**What went right (MAJOR):**
- Father character fully restored with correct ID, aliases, and mention count ✓
- Uncle Bill narrator flag restored ✓
- Margaret Donaldson restored ✓
- Father has "the father" as alias, son does not — alias partitioning partially working ✓
- Father role is "protagonist" ✓

Score: 6.5/10 — huge improvement from 4/10. Spurious possessive character and misassigned alias prevent higher score.

### 2.3 Character Profiles: 6/10 ✗

**Father's profile (split_0): GOOD** ✓
- Appearance: "fifty-five or over", "big and athletic", "grizzled", "olive skin", "blue eyes" — all correct for the father
- Personality: "morally ambiguous", "committed grave betrayals by embezzling and faking his death, yet sought redemption" — accurate
- Speech: "'Took money,' he said", "'American, sir,' he said proudly" — correct father quotes
- Relationships: son=parent ✓, Margaret=spouse ✓, Uncle Bill=acquaintance (should be "cousin" — medium issue)

**Son's profile (split_1): WRONG — contains father's profile data** ✗
- Appearance: "fifty-five or over", "big and athletic", "dark olive skin", "grizzled" — this is the FATHER's appearance. The son is 12 years old initially, 18 during the war.
- Personality: "morally ambiguous man who committed theft and abandoned his family" — this is the FATHER's story. The son is brave, dutiful, serves as ambulance driver.
- Voice quotes: "'Took money,' he said", "'American, sir'" — these are the FATHER's lines, not the son's.
- Relationships: self-referential — "John Donaldson (the son): parent" (lists itself as its own parent), "Margaret Donaldson: spouse" (Margaret is his MOTHER, not spouse)
- The appearance summary even says "A man of striking physical resemblance to his son" — describing a father's resemblance to his son, when this IS the son character. Completely backwards.

**Uncle Bill's profile: GOOD** ✓
- Appearance: "elderly, grizzled, small man, grim and unexhilarating" — accurate
- Personality: "self-sacrificing", "loyal", "crabbed and prejudiced" — accurate, drawn from text
- Speech: "formal", "reserved", "uses understatement" — appropriate
- Relationships: father=ally (should be "cousin"), son=mentor ✓, Margaret=acquaintance ✓

**Ted Frith's profile: MIXED**
- Appearance: "natural eyes" — minimal but text-grounded
- Personality: "heroic", "self-sacrificing", "courageous" — appropriate for the stretcher-bearer character
- Voice: "'That you, Johnny?' he shouted" — correct quote
- But some traits seem borrowed from the father ("selfless hero", "pride in serving under the American flag")

**Margaret Donaldson: NO PROFILE** — expected for a 2-mention character

**Root cause of son's profile contamination:** The split creates two characters but the profiling stage doesn't differentiate — it gathers evidence for "John Donaldson" and assigns the same passages to both split children. The father's more dramatic profile (embezzlement, deathbed confession) dominates, so both characters get the father's profile.

Score: 6/10 — father's and Uncle Bill's profiles are good, but the son having the father's complete profile is deeply misleading for a narrator.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 summary:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, the scandal, the inheritance split. `characters_present: ["John (the boy)"]` — uses the boy's name only, doesn't mention Uncle Bill by name (says "the narrator" in the summary text instead).

**Chapter 2 summary:** Comprehensive and well-structured. Covers the decade of guardianship, WWI enlistment, Caporetto deployment, discovery of the father, deathbed confession. `characters_present: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` — correctly disambiguated ✓

**PERSISTENT factual error in Ch2:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 14 attempts. The LLM consistently hallucinates "sister" from the uncle-nephew relationship.

**Book summary (overview section):** Well-written, comprehensive, captures the full arc of the story. No factual errors in the overview.

Score: 7.5/10 — the "sister" hallucination is the primary issue, preventing 8.0.

### 2.5 Pronunciation Guide: 6.5/10 ✗

27 entries, all categories null. 22 have IPA (improvement).

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 4):** live, minute, read, close, moderate

**False positives (~9):** Donaldson, Barron, Frith, Margaret, Johnny, Donaldson's, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "orderlies" IPA `/ˈɔːr.dər.laɪz/` — the "laɪz" ending is incorrect (should be /lɪz/)
- "was" `/wɒz/` — common word, shouldn't be flagged
- "Barron" `/ˈbærən/` — IPA corrected from attempt 13 ✓
- All categories null — no categorization

Score: 6.5/10 — good Italian/French geographic coverage but ~9 false positives and all categories null.

### 2.6 HTML Presentation: 7.5/10 ✗ (IMPROVEMENT from 6.5)

The HTML is well-organized with functional navigation and tabs. Major improvements from attempt 13:
- **Father AND son both displayed** — separate profile cards with distinct information ✓
- **Uncle Bill correctly shown as "First-Person narrator"** ✓
- **Son shown as "Secondary narrator (nested narrative)"** — partially correct
- **Father has "the father" alias displayed** ✓
- **Margaret Donaldson displayed in supporting cast** ✓
- **Book overview/summary well-written and prominent** ✓

**Remaining presentation issues:**
- Son's profile card shows father's data (appearance: "fifty-five or over", personality: "committed theft") — deeply confusing for a narrator
- Son shows "parent" relationship to himself
- Son shows "spouse" to Margaret (his mother)
- Spurious "John Donaldson's" character in supporting cast table
- Ch1 characters_present shows only "John (the boy)" — inconsistent naming with the main character list
- Son tagged as "supporting" role — should be higher

Score: 7.5/10 — functional layout with correct structure, significantly improved from 6.5 by having all characters present. Profile data errors on the son prevent higher score.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6.5 × 0.25) + (6 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (7.5 × 0.10)
        = 1.40 + 1.625 + 0.90 + 1.50 + 0.65 + 0.75
        = 6.825
```

**Overall: 6.83/10** (improvement from 5.93)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents
- Both split children survived: `main_cast_0_split_0` AND `main_cast_0_split_1` ✓
- Margaret Donaldson restored as `main_cast_4` ✓
- Spurious "John Donaldson's" in supporting cast — possessive form parsing issue
- All pronunciation categories null
- `physical_description` null for all characters (data is in `appearance` field)

## Current Issues (Priority Order)

### CRITICAL

1. **Son's profile is entirely the father's profile (cross-contamination)**
   - Problem: `main_cast_0_split_1` (the son) has the father's appearance ("fifty-five or over", "big and athletic", "grizzled"), personality ("committed theft and abandoned his family"), voice quotes ("'Took money,' he said", "'American, sir'"), and relationships (parent to himself, spouse to his mother Margaret)
   - Evidence: The son is 12 years old initially, 18 during the war. His actual traits: brave, dutiful, enlists as ambulance driver, physically resembles his father but younger. His actual quotes: "'No--no. It's covered over--wiped out--with service and honor'" and "'That sounds nice,' he said"
   - Root cause: The profiling stage gathers evidence for "John Donaldson" and assigns identical passages to both split children. Since the father's dramatic story dominates the text, both characters get the father's profile. The profiler needs to differentiate between split characters during passage gathering.
   - Location: `src/pipeline/character_profiling/` — specifically `passage_gatherer.py` which collects evidence, and/or `name_disambiguator.py` which resolves ambiguous mentions
   - Fix approach: When profiling split characters (identifiable by `_split_` in their ID), the passage gatherer should use the disambiguated label (e.g., "the father" vs "the son") to filter passages. Passages containing "the father", "fifty-five", "grizzled" should go to split_0, while passages about the boy, the ambulance driver, the young man should go to split_1.

### HIGH

2. **Spurious character "John Donaldson's" (possessive form)**
   - Problem: `supporting_2` has canonical_name "John Donaldson's" (with apostrophe-s) and alias "Johnny". This is a possessive form extracted as a character name.
   - Evidence: "John Donaldson's physical beauty" is a possessive construction, not a character name. "Johnny" is Ted Frith's nickname for the son.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — the NER or LLM extraction is capturing possessive forms as names
   - Fix: Strip trailing "'s" from extracted character names before creating character entries. Also, "Johnny" should be an alias of the son character (`split_1`), not a separate character.

3. **Son's role is "supporting" — should be "protagonist" or "major"**
   - Problem: The son drives the entire narrative arc but is labeled "supporting"
   - Evidence: The story follows the son from age 12 through WWI and his discovery of his father. He's central to both chapters.
   - Location: Role assignment in character extraction pipeline
   - Fix: This may resolve if the profile contamination (Issue #1) is fixed, since the son currently has the father's data and the father is already "protagonist"

4. **Chapter 2 summary factual error: "sister" instead of "cousin" (14th consecutive attempt)**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 14 attempts — LLM consistently hallucinates "sister"
   - Location: Summary generation — the "cousin" context from Ch1 may not carry into Ch2's context window
   - Fix: Increase summary chunk overlap or cross-chapter context to ensure Ch1's relationship information ("my cousin") is available when summarizing Ch2

### MEDIUM

5. **Father's relationship to Uncle Bill is "acquaintance"** — should be "cousin"
   - The text explicitly states they are cousins ("my cousin John")
   - Uncle Bill's relationship to father is "ally" — also should be "cousin"
   - Location: Relationship extraction in profiling pipeline

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate for a text with no structural markers

7. **Pronunciation false positives (~9 of 27)**
   - Common English words: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums
   - Common names: Donaldson, Barron, Frith, Margaret, Johnny, Donaldson's
   - All categories null — no categorization

8. **Ch1 characters_present shows only "John (the boy)"**
   - Inconsistent naming with the main character list (which uses "John Donaldson (the son)")
   - Uncle Bill should also be listed as characters_present for Ch1 since he's the narrator and active character

### LOW

9. **Ted Frith still missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured

10. **"orderlies" IPA wrong**
    - `/ˈɔːr.dər.laɪz/` should be `/ˈɔːr.dər.lɪz/`

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
- **Issue addressed:** Son's profile cross-contamination (CRITICAL #1)
- **Root cause:** `name_disambiguator.py` line 355-364 — Disambiguator couldn't distinguish split characters with shared aliases ("John Donaldson", "John"). Both have same word count, so relationship markers couldn't use elder/younger heuristics. Label-specific aliases like "the father" weren't recognized as strong signals.
- **Fix:** Added Signal 0 (confidence 0.99) for split character label detection:
  1. Enhanced `NameAmbiguityMap._build_ambiguity_map()` to detect exact alias duplicates (lines 96-122)
  2. Added `_check_split_character_labels()` method (lines 449-517)
  3. Passages containing label-specific aliases now strongly assigned to that character
- **Smoke test:** `test_split_label_fix.py` — 3/3 tests PASS (father passages assigned correctly, son passages rejected, neutral passages use other signals)
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
| 15 | Son's profile contamination | `name_disambiguator.py` (split label detection) | Split character label disambiguation to prevent cross-contamination |

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

## Next Action
**Phase:** awaiting_analysis

**Fix Applied (Attempt 15):**
- **Split character label-based disambiguation** — Added Signal 0 (confidence 0.99) to detect label-specific aliases in passages, preventing profile cross-contamination between split characters. Smoke test confirms correct behavior.

**Expected Impact:**
- Son's profile should now contain son-specific passages (brave, dutiful, ambulance driver) instead of father's passages (embezzlement, deathbed confession)
- Profile contamination score impact: +1 to +2 points (currently 6/10, expect 7-8/10)
- HTML presentation should improve as son's profile becomes accurate

**Next Issues to Address (if score still below threshold):**
1. **HIGH: Spurious "John Donaldson's" character** — possessive form extraction
2. **HIGH: Ch2 summary "sister" → "cousin" hallucination** (14 consecutive attempts)
3. **MEDIUM: Pronunciation false positives** (~9 of 27 entries)
