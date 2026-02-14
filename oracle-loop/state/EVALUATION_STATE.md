# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 10
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 10)
- **MAJOR SUCCESS:** Father/son split WORKED! Output shows "John Donaldson (the father)" and "John Donaldson (the son)" as separate characters
- Character count: 6 (up from 4 in attempt 9)
- Margaret Donaldson appears (regression from attempt 9 is FIXED)
- Main cast count: 1 (Uncle Bill) — restored from 0
- Supporting cast: 5 (Margaret, father, son, Joe Barron, Ted Frith)
- Father/son split characters have 0 mentions and no aliases — original ~30 mentions not distributed
- Father/son have NO profiles (no appearance, personality, voice guidance in HTML)
- Some warnings about ungrounded evidence quotes for Uncle Bill (2) and Ted Frith (3)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7.5/10 ✗
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.20/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from attempt 9. "American, Sir" is a continuous short story with no explicit chapter divisions. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers. The two sections are at least reasonable narrative divisions.

Score: 7/10

### 2.2 Character Extraction: 7.5/10 ✗ (IMPROVEMENT from 6.5/10)

**MAJOR WIN: Father/son split WORKED!**

Characters found (6 total):
- main_cast_3: Margaret Donaldson (mentions=2, role=supporting) ✓ RESTORED
- supporting_0_split_0: John Donaldson (the father) (mentions=0, role=minor) ✓ SPLIT WORKED
- supporting_0_split_1: John Donaldson (the son) (mentions=0, role=minor) ✓ SPLIT WORKED
- supporting_1: Uncle Bill (mentions=17, narrator=true, role=protagonist) ✓
- supporting_2: Joe Barron (mentions=3, role=minor) ✓
- supporting_3: Ted Frith (mentions=5, aliases=["Ted"], role=minor) ✓

**Remaining issues:**
1. Father (supporting_0_split_0) has 0 mentions — the original ~30 mentions from the pre-split "John" were not distributed to the split children
2. Son (supporting_0_split_1) has 0 mentions — same issue
3. Neither father nor son has aliases — the original aliases ["John Donaldson", "Johnny"] were not distributed
4. Father and son roles are "minor" — father is central to the plot (should be at least "supporting"), son is a major character
5. Ch1 `characters_present` still says "the narrator" instead of "Uncle Bill" — minor inconsistency

**What's working well:**
- Uncle Bill correctly identified as protagonist and narrator ✓
- Margaret Donaldson back as main_cast ✓
- Ted Frith has "Ted" alias ✓
- All 6 expected characters present (Uncle Bill, father, son, Margaret, Joe Barron, Ted Frith) ✓

Score: 7.5/10 — improved from 6.5 due to successful split and Margaret restoration, but 0 mentions on split characters and missing aliases hold it back

### 2.3 Character Profiles: 6.5/10 ✗ (REGRESSION from 7/10)

**Uncle Bill profile (main cast — in HTML):**
- Appearance: "elderly man with a reserved, unassuming physical presence" — reasonable ✓
- Features: "thin hair" — not strongly supported by text, but not wrong
- Personality: "heroic protagonist whose transformative acts of compassion, sacrifice, and emotional courage..." — overblown; Uncle Bill is more of a gruff, reluctant guardian who grows to care. "Crabbed and selfish demeanor" is mentioned but only as initial state. Description is too hagiographic.
- Voice guidance: "measured, gravelly baritone with restrained emotion" — excellent ✓
- Quotes: First quote (letter) is Uncle Bill's ✓. Second quote ("God arranged it...") is actually JOHN THE SON's words to Uncle Bill, misattributed ✓→✗
- Relationships: "John Donaldson (mentor)", "John Donaldson (father) (ally)" — reasonable but doesn't clearly distinguish which John is which. "mentor" should specify mentor to the son.

**Father profile:** NO PROFILE AT ALL — just appears in supporting character table with 0 mentions, no description. This is a major gap: the father (John Donaldson Sr.) is the central dramatic figure — embezzler, fugitive, war hero, redeemed in death. A narrator NEEDS voice/personality guidance for him.

**Son profile:** NO PROFILE AT ALL — same issue. The son is a major character who drives the entire second half. Narrator needs voice guidance.

**Margaret Donaldson:** Has a brief description in the supporting table: "John Donaldson (the father)'s widow, who informs the narrator of his death and assures him they need no financial aid" — accurate ✓

**Ted Frith:** Has description: "heroic figure whose actions reveal unwavering courage and selflessness under fire" — accurate ✓

**Overall:** All `physical_description` fields are null in JSON. Only Uncle Bill gets a full profile with appearance/personality/voice sections. The two Johns — arguably the most important characters for narrator preparation — have NO profiles at all. This is a significant gap.

Score: 6.5/10 — regression from 7/10 because the father/son split created two entries with NO profiles. Previously the single "John" entry at least had a profile covering the father's attributes. Now neither split character has any profile content.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, Margaret's dignity. `characters_present` shows `["the narrator", "John (the boy)", "Margaret Donaldson"]` — good father/son disambiguation, but uses "the narrator" instead of "Uncle Bill". Factual accuracy is strong — correctly identifies John as Uncle Bill's cousin.

**Section 2 summary:** Comprehensive. **PERSISTENT factual error:** "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 10 attempts. The plot summary correctly says "his late cousin John" in the overview section. Everything else in the Ch2 summary is accurate — war service, Caporetto, the reunion, the father's confession, death scene.

**Plot summary (overview):** Excellent. Detailed, accurate, captures all major plot points including the cousin relationship correctly. Three paragraphs, well-structured for narrator preparation.

Score: 7.5/10 — Ch2 "sister" hallucination persists

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries (down from 26). All categories still null.

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~11):** Donaldson, Barron, Frith, Margaret, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA improvements from attempt 9:**
- "orderlies" IPA is now `/ˈɔːr.dər.lɪz/` — FIXED from previous wrong `-laɪz` ✓
- "Barron" still `/bəˈrɒn/` — wrong stress for English surname (should be `/ˈbæɹ.ən/`)
- "was" `/wɒz/` — common word, shouldn't be flagged at all
- "Margaret" — common English name, shouldn't be flagged

Score: 6.5/10 — good Italian/French coverage, but ~11 false positives remain. All categories null.

### 2.6 HTML Presentation: 8.5/10 ✓

Well-organized HTML report with functional navigation. Character profiles rendered with rich appearance/personality/voice sections for Uncle Bill. Father/son correctly split into separate entries. Tab-based navigation works. Plot summary is comprehensive and well-rendered. Pronunciation guide has search and filtering.

Minor issues:
- Father/son entries in supporting table show 0 mentions — looks like extraction failure to a narrator
- Father/son have no profile details — just names in the table
- "Verbal tics: Uncle Bill" in Uncle Bill's profile is meaningless/wrong

Score: 8.5/10

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7.5 × 0.25) + (6.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (8.5 × 0.10)
        = 1.40 + 1.875 + 0.975 + 1.50 + 0.65 + 0.85
        = 7.25
```

**Overall: 7.25/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 1` (Uncle Bill) — RESTORED from 0 in attempt 9
- `supporting_cast_count: 5` — includes the 2 split Johns, Margaret, Joe, Ted
- Father/son split characters from `supporting_0_split_*` — split logic worked correctly
- All pronunciation categories null
- `physical_description` null for all 6 characters

## Current Issues (Priority Order)

### CRITICAL

1. **Split characters have 0 mentions and no aliases**
   - Problem: After splitting "John" (supporting_0) into father/son, both split characters have `mention_count: 0` and `aliases: []`. The original ~30 mentions and aliases ["John Donaldson", "Johnny"] were not distributed to the split children.
   - Evidence: `supporting_0_split_0` (father) has 0 mentions, `supporting_0_split_1` (son) has 0 mentions
   - Location: `src/agents/characters.py` — `_split_disambiguated_same_name_characters()` method. When creating split characters, the method needs to:
     (a) Copy over the original character's aliases to both split children (both can be referred to as "John Donaldson")
     (b) Set a reasonable mention count — either split proportionally or copy the total to each
   - Fix: After creating the split Character objects, copy `original_char.aliases` to each split child, and set `mention_count` to at least `original_char.mention_count // 2` or use the actual mention count from summary data
   - Impact: Would raise Character Extraction from 7.5 to ~8.0+ (proper mention counts + aliases)

2. **Split characters have NO profiles (appearance, personality, voice guidance)**
   - Problem: Father and son John Donaldson have NO profile content — no appearance, personality, voice guidance, or quotes. They appear as empty entries in the supporting character table. The father is the central dramatic figure; a narrator NEEDS voice/personality guidance for him.
   - Evidence: In HTML, father and son entries only show name and "0 mentions" — no profile sections
   - Root cause: The profiling pipeline runs BEFORE the split, so the pre-split "John" gets profiled, but the post-split children don't inherit the profile. OR the profiling runs AFTER but the split characters are new and have no text passages to profile.
   - Location: `src/agents/characters.py` — the split method needs to either:
     (a) Trigger re-profiling for split characters, OR
     (b) Copy relevant profile fields from the original character to the appropriate split child
   - Fix approach: When splitting, copy the original character's profile to the father split (since the pre-split profile was dominated by father attributes in previous attempts). For the son, at minimum copy voice guidance with a note. Alternatively, re-run profiling on split characters only.
   - Impact: Would raise Character Profiles from 6.5 to ~8.0+ (two major characters gain profiles)

### HIGH

3. **Pronunciation false positives (~11 of 25)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums. Common names flagged: Donaldson, Barron, Frith, Margaret
   - "Barron" IPA `/bəˈrɒn/` still wrong (French-style stress)
   - "was" — common word, no narrator would need pronunciation help
   - All pronunciation categories are null
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt needs stronger filtering
   - Fix: Two-pronged approach:
     (a) Improve LLM prompt: "Do NOT flag standard English words, common English surnames, or common English first names unless they have genuinely ambiguous pronunciation"
     (b) Post-filter: Expand CMU derivation checking for common suffixes (-ness, -less, -ful, -set, -ies)
   - Impact: Would raise Pronunciation from 6.5 to ~8.0+

4. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 10 attempts — LLM consistently hallucinates "sister" for Ch2
   - The plot summary CORRECTLY says "his late cousin John"
   - Location: Summary generation — the Ch2 text chunk may not include the "cousin" reference, or the LLM is pattern-matching "uncle" → "sister's son"
   - Fix options:
     (a) Add post-summary consistency check against plot_summary
     (b) Ensure the "cousin" context from Ch1 is included in Ch2's summary prompt overlap
     (c) Add explicit guidance in summary prompt: "Do not infer family relationships not stated in the text"
   - Impact: Would raise Summaries from 7.5 to ~8.5

### MEDIUM

5. **Structure: 2 sections for a continuous short story**
   - "American, Sir" has no chapter markers. 2 sections is workable but 1 would be more accurate.
   - This is a difficult edge case for structure detection and may not be worth fixing for this text alone.
   - Score impact: ~0.5 points on Structure (7→7.5 at best with 1 section)

6. **Uncle Bill profile quote misattribution**
   - "God arranged it, Uncle Bill" is the SON's quote, not Uncle Bill's. This is in Uncle Bill's voice guidance section.
   - Location: Character profiling pipeline — quote attribution

7. **Uncle Bill "Verbal tics: Uncle Bill"**
   - The verbal tics field contains "Uncle Bill" which is meaningless — this is his own name, not a verbal tic.

8. **Ch1 characters_present says "the narrator" instead of "Uncle Bill"**
   - Minor inconsistency with Ch2 which correctly uses "Uncle Bill"

### LOW

9. **Ted Frith still missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured

10. **Father/son roles are "minor"**
    - Father is central to the plot (should be at least "supporting")
    - Son is a major character (should be at least "supporting")
    - This will partly be addressed by fixing mention counts (CRITICAL #1)

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

## Priority Fix Order for Attempt 11

**Focus on THREE fixes (all in the same area):**

1. **Propagate mentions/aliases to split characters (CRITICAL #1)**
   - In `_split_disambiguated_same_name_characters()`, after creating split Character objects:
     - Copy `original_char.aliases` to each split child
     - Set `mention_count` to at least `original_char.mention_count // 2` per child
     - Copy `original_char.role` or set to "supporting" (not "minor")
   - Location: `src/agents/characters.py` — the split method

2. **Propagate profiles to split characters (CRITICAL #2)**
   - When creating split characters, copy the original character's profile fields to the appropriate split child
   - The pre-split "John" profile described the FATHER (grizzled, embezzler, stretcher-bearer) — copy to father split
   - For the son, at minimum set a basic description
   - OR: re-trigger profiling for split characters
   - Location: `src/agents/characters.py` — the split method

3. **Pronunciation false positive reduction (HIGH #3)**
   - Improve LLM prompt filtering for common English words and names
   - Expand post-filter for common suffixes
   - Location: `src/pipeline/pronunciation_guide/`

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

## Next Action
Run PROMPT_fix.md to address split character data propagation (mentions, aliases, profiles) and pronunciation false positives.

**Expected impact:**
- Propagating mentions/aliases: Character Extraction 7.5 → 8.0+
- Propagating profiles: Character Profiles 6.5 → 8.0+
- Pronunciation filtering: Pronunciation 6.5 → 8.0+
- Overall: 7.25 → ~8.0+
