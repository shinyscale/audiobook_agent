# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 12
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5.5/10 ✗ (REGRESSION from 7.5)
- Character Profiles: 7.5/10 ✗ (IMPROVEMENT from 6.5)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.90/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

Score: 7/10

### 2.2 Character Extraction: 5.5/10 ✗ (MAJOR REGRESSION from 7.5)

**CRITICAL REGRESSION: John Donaldson (the son) is MISSING as a separate character.**

Attempt 10 had 6 characters with father and son as separate entries. Attempt 11 has only 5 characters — the son has been absorbed as an ALIAS of the father:

```
"John Donaldson (the father)" aliases: ["John Donaldson", "the father", "John Donaldson (the son)", "John"]
```

Having "John Donaldson (the son)" as an alias of the father is a **false merge** — these are two different people (father and son, different ages, different roles in the story).

Characters found (5 total — was 6):
- `main_cast_1_split_0`: John Donaldson (the father) (mentions=29, role=protagonist, narrator=TRUE) ✗ WRONG
- `main_cast_3`: Margaret Donaldson (mentions=2, role=supporting) ✓
- `supporting_1`: Uncle Bill (mentions=18, role=minor, narrator=FALSE) ✗ WRONG — Uncle Bill IS the narrator
- `supporting_2`: Joe Barron (mentions=3, role=minor) ✓
- `supporting_3`: Ted Frith (mentions=5, aliases=["Ted"], role=minor) ✓

**Issues:**
1. **FALSE MERGE (son into father):** The son character ("John Donaldson (the son)") from attempt 10 has been absorbed as an alias of the father. This is a critical error — the entire story hinges on these being two separate people.
2. **NARRATOR REGRESSION:** Uncle Bill is marked `is_narrator: false`, while the father is marked `is_narrator: true`. Uncle Bill is definitively the first-person narrator of this story. The father never narrates — he is narrated about.
3. **ROLE INVERSION:** Uncle Bill is demoted to "minor" while the father is "protagonist". Uncle Bill should be the protagonist/narrator. The father is a major character but not the narrator.
4. **Only one split child created:** The split produced `main_cast_1_split_0` (father) but no `split_1` (son). The split logic created only the father and merged the son into it as an alias.

Score: 5.5/10 — major regression from 7.5. The false merge of son into father, narrator misassignment, and role inversion are all critical errors.

### 2.3 Character Profiles: 7.5/10 ✗ (IMPROVEMENT from 6.5)

**Major improvement:** The father now has a rich, detailed profile (appearance, personality, voice guidance) thanks to the alias propagation fix enabling mention search and profiling.

**John Donaldson (the father) profile:**
- Appearance: "middle-aged man with a dark, olive complexion" — accurate ✓
- Details: "big, athletic, grizzled" — matches text ✓
- Personality: "morally ambiguous man who committed financial fraud" — accurate ✓
- Voice guidance: "begins weary and rough... softens into quiet dignity" — excellent ✓
- Speech patterns: "formal, uses restrained language" — accurate ✓
- Quotes: All correctly attributed to the father ✓
- Relationships: spouse=Margaret, parent=son, victimizer=Uncle Bill — "victimizer" is odd (Uncle Bill was not his victim; if anything the father victimized his family through embezzlement)

**Uncle Bill profile:**
- Appearance: "elderly man with reserved presence" — reasonable ✓
- Personality: "emotionally reserved but capable of deep loyalty" — accurate ✓
- Voice guidance: "low, measured baritone with deliberate pauses" — excellent ✓
- Quotes: "You know, Uncle Bill..." — this is actually someone ELSE addressing Uncle Bill, not Uncle Bill's speech. Misattribution ✗
- Verbal tics: "I am not soft-hearted", "You know, Uncle Bill...", "Sincerely, Uncle Bill" — the first is good, second is how others address him, third is his sign-off ✓ mostly
- Relationships: "victimizer" for father (wrong label — should be "cousin" or "guardian")

**Ted Frith profile:**
- Has appearance, personality, and voice guidance — good for a minor character ✓
- "heroic protagonist" — not a protagonist, just a brave soldier. Overblown but not critically wrong.

**Missing:** No profile for John Donaldson (the son) since he doesn't exist as a separate character. This is a direct consequence of the false merge in Character Extraction.

Score: 7.5/10 — significant improvement from 6.5 because the father and Uncle Bill now have rich profiles. But the missing son profile and some relationship mislabeling hold it back.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, Margaret's dignity. `characters_present: ["the narrator", "John (the boy)"]` — uses "the narrator" instead of "Uncle Bill" (minor inconsistency).

**Section 2 summary:** Comprehensive and well-written. **PERSISTENT factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has now persisted across ALL 11 attempts. The LLM consistently hallucinates "sister" from the uncle-nephew relationship. Everything else in Ch2 is accurate — war service, Caporetto, discovery of the father, reconciliation, death scene.

**Ch2 characters_present:** `["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` — correctly disambiguated ✓ (even though the character extraction didn't preserve this split).

Score: 7.5/10 — the "sister" hallucination is the primary issue.

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries, all categories null.

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~11):** Donaldson, Barron, Frith, Margaret, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" now `/ˈbærən/` — FIXED from previous wrong stress ✓
- "orderlies" still `/ˈɔːr.dər.laɪz/` — wrong (should be `/ˈɔːr.dər.liz/`) ✗
- "was" `/wɒz/` — common word, shouldn't be flagged at all
- All categories null — no categorization (foreign, homograph, etc.)

Score: 6.5/10 — good Italian/French geographic coverage but ~11 false positives and all categories null.

### 2.6 HTML Presentation: 8/10 ✓

Well-organized report with functional navigation, tabs, character profiles with appearance/personality/voice sections. The father's profile is now rich and detailed.

**Issues:**
- Father's aliases show "John Donaldson (the son)" — confusing to a narrator reading the report, since the son is listed as the father's alias
- Uncle Bill shown as "minor" role — misleading for the narrator/protagonist
- Father shown as narrator — wrong

Score: 8/10 — functional and well-organized, but the character data issues bleed through into misleading presentation.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5.5 × 0.25) + (7.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (8 × 0.10)
        = 1.40 + 1.375 + 1.125 + 1.50 + 0.65 + 0.80
        = 6.85
```

**Overall: 6.85/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents
- `main_cast_count: 2` (father and Margaret) — Margaret should not be main cast with only 2 mentions
- `supporting_count: 3` (Uncle Bill, Joe, Ted)
- Only one split character created (`main_cast_1_split_0`) — split_1 missing
- All pronunciation categories null
- `physical_description` null for all 5 characters (rich data is in `appearance` field instead)

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE MERGE: Son absorbed as alias of father**
   - Problem: "John Donaldson (the son)" appears as an ALIAS of "John Donaldson (the father)" instead of being a separate character. Only `main_cast_1_split_0` (father) was created; no `split_1` (son) exists.
   - Evidence: `characters[0].aliases = ["John Donaldson", "the father", "John Donaldson (the son)", "John"]` — "the son" should never be an alias of the father
   - Root cause: The split logic in `_split_disambiguated_same_name_characters()` likely created both split children, but then the alias propagation or downstream merge logic incorrectly combined them. OR the split only created one child and assigned the son's label as an alias.
   - Location: `src/agents/characters.py` — `_split_disambiguated_same_name_characters()` method. Need to trace why only one split character was created and why the son's disambiguated label ended up as a father alias.
   - Fix: Ensure the split creates TWO separate Character objects (one per disambiguated label found in `characters_present`). The son's label should become the son's canonical name, NOT an alias of the father. Check that downstream merge/dedup logic doesn't re-merge split characters.
   - Impact: Would raise Character Extraction from 5.5 to ~7.5+

2. **NARRATOR MISASSIGNMENT: Father is narrator, Uncle Bill is not**
   - Problem: `is_narrator: true` on father, `is_narrator: false` on Uncle Bill. Uncle Bill is definitively the first-person narrator.
   - Evidence: The story opens with Uncle Bill's internal monologue and all events are told from his perspective. The father is a character narrated about.
   - Root cause: The alias propagation may have caused the narrator flag to transfer to the father (since "John" was originally tagged as narrator in some earlier pipeline step, and now the father inherits all of John's attributes including narrator status).
   - Location: `src/agents/characters.py` — narrator assignment logic. Check if the split character inherits `is_narrator` from the pre-split character that may have been incorrectly tagged.
   - Fix: After split, re-evaluate narrator assignment. The narrator flag should be on the character whose canonical name matches the narrator detection output (Uncle Bill), not on a split character.
   - Impact: Would raise Character Extraction by ~0.5 points

### HIGH

3. **Uncle Bill demoted to "minor" role**
   - Problem: Uncle Bill has `role: "minor"` despite being the first-person narrator and protagonist with 18 mentions
   - Evidence: He narrates the entire story, drives the plot, and is the emotional center
   - Location: Role assignment in character pipeline — supporting cast defaults to "minor"
   - Fix: Narrator should automatically get "protagonist" role, or at minimum "supporting"

4. **Pronunciation false positives (~11 of 25)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums. Common names: Donaldson, Barron, Frith, Margaret
   - All pronunciation categories are null
   - "orderlies" IPA still wrong (`/laɪz/` instead of `/liz/`)
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve filtering of common English words and names; populate categories

5. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 11 attempts — LLM consistently hallucinates "sister" for Ch2
   - Location: Summary generation — the "cousin" context from Ch1 may not be included in Ch2's overlap
   - Fix: Increase summary chunk overlap to ensure the "cousin" relationship from Ch1 is visible in Ch2's context

### MEDIUM

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate for a text with no structural markers

7. **Father-Uncle Bill relationship labeled "victimizer"**
   - The father is labeled as Uncle Bill's "victimizer" — Uncle Bill was not victimized by the father. The father victimized his own family. "cousin" or "ward's father" would be more accurate.

8. **Uncle Bill's verbal tics include others' speech**
   - "You know, Uncle Bill..." is how the SON addresses Uncle Bill, not Uncle Bill's verbal tic

9. **Ch1 characters_present says "the narrator" instead of "Uncle Bill"**
   - Minor inconsistency with Ch2 which correctly uses "Uncle Bill"

### LOW

10. **Ted Frith still missing "Teddy" alias**
    - Text uses "Teddy" 2x but not captured

11. **Margaret in main_cast with only 2 mentions**
    - Should be supporting cast, not main cast

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

### Attempt 12 - Fix 1: Prevent re-merge of split characters
- **Issue addressed:** Son absorbed as alias of father (CRITICAL #1 regression from attempt 11)
- **Root cause:** `src/agents/characters.py:1905-1945` - Step 3.5 `_merge_within_main_cast()` Pass 2 (spelling variants) uses fuzzy matching that re-merges split characters
- **Data investigation:**
  - Character IDs show only `main_cast_1_split_0` (father) exists, no `split_1` (son)
  - Father's aliases include "John Donaldson (the son)" which should be a separate character
  - Split created both father and son correctly in Step 1.6, but Step 3.5 fuzzy matching (~85% similarity) merged them back together
- **Fix:** Add SAFETY CHECK 2 in Pass 2 to skip merge if both characters come from the same split operation (check if `_split_` in ID and same base ID before `_split_` suffix)
- **Universality check:** YES - this prevents re-merging any same-name disambiguated characters (father/son, Sr./Jr., elder/younger, etc.)
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
| 12 | Son re-merged into father | `characters.py:1904-1923` (split character merge protection) | **PENDING VERIFICATION** |

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

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify fix:
- Split characters (father and son) should both exist as separate characters
- Narrator assignment should be re-evaluated (may self-correct with proper split)
