# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 3)
- ✅ Analysis completed successfully
- ✅ Red Cross organization filtered (Fix 2 worked)
- ✅ Ted Frith now has alias "Ted" and 5 mentions (up from 2) (Fix 3 partially worked)
- ❌ Father/son John Donaldson split DID NOT FIRE (Fix 1 failed — code exists but reads wrong data source)
- ⚠️ "Teddy" still missing as alias for Ted Frith
- ⚠️ Step 1.6 reads `chapters` (StructuralElement from `_get_chapters`) which has empty `characters_present` at CharacterAgent runtime. The `characters_present` data is only in the summary objects, not the chapter map's structural elements.
- Pipeline used qwen3-next:80b-a3b-instruct-q8_0 for all agents

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
- Character Profiles: 8/10 ✓
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

"American, Sir!" is a continuous short story (~5000 words) with NO chapter divisions, headings, or section breaks. The tool detected 2 sections (both with `title: null`). This is the same result as attempts 1 and 2.

**Assessment:** A 2-section split is workable for narrator prep (the story has a natural shift from backstory to wartime narrative), but:
- Both sections have null titles — not useful for navigation
- For a text this short with no structural markers, 1 section would be more accurate
- The split point is somewhat arbitrary

Score unchanged from attempt 2 — no structure fixes were attempted.

### 2.2 Character Extraction: 7/10 ✗

**Improvements from attempt 2:**
- ✅ Red Cross filtered out (was listed as supporting character, now removed)
- ✅ Ted Frith has alias "Ted" (was missing) and 5 mentions (was 2)
- Total characters: 5 (down from 6 — Red Cross removed)

**Still broken:**

1. **Father/son John Donaldson NOT split (CRITICAL — Fix 1 failed).** There is still only ONE "John Donaldson" entry (main_cast_1) conflating two distinct characters:
   - The FATHER: 55+ years old, embezzler who faked his death, lived in Italy 20 years, died as stretcher-bearer
   - The SON: ~23 years old, Uncle Bill's ward, Yale student, ambulance driver, narrator of war story

   **Root cause identified:** Step 1.6 (`_split_disambiguated_same_name_characters`) reads `characters_present` from `chapters` parameter (StructuralElement objects from `_get_chapters`), but these objects have EMPTY `characters_present` at CharacterAgent runtime. The `characters_present` data is in the *summary objects* (via `context.previous_results["summaries"]`), not in the chapter_map's StructuralElements. The StructuralElements only get `characters_present` populated during final output assembly in `_convert_chapters()` (analyzer.py:2575-2600), which runs AFTER all agents.

2. **"the father" listed as alias of John Donaldson** — Since the split didn't fire, "the father" appears as an alias of the single conflated entry, which is misleading.

3. **John Donaldson marked as narrator: true** — Both characters are tagged as narrators (John as secondary narrator of the war story, which is correct for the son), but since they're conflated, the narrator tag applies ambiguously.

4. **Ted Frith missing "Teddy" alias (MINOR)** — Text uses "Teddy" 2x to refer to Ted Frith but this wasn't captured.

**What works:**
- Uncle Bill correctly identified as protagonist and first-person narrator
- Margaret Donaldson, Joe Barron, Ted Frith all present
- Red Cross correctly filtered
- No hallucinated characters

Score improved from 6→7 (Red Cross removed +0.5, Ted aliases +0.5), but father/son conflation remains the critical blocker.

### 2.3 Character Profiles: 8/10 ✓

**John Donaldson profile (conflated but detailed):**
- Appearance describes the father: "olive complexion, blue eyes with thickset lashes, shabby but dignified bearing" — accurate for the father
- Personality: "morally ambiguous man who committed financial fraud" — accurate for the father
- Voice guidance: "repeats 'American, sir' with solemn emphasis" — accurate for the father
- Relationships: "Uncle Bill (victimizer)" — odd label, should be "cousin" or "ward-of"; "John Donaldson (the son) (parent)" — correct; "Margaret Donaldson (spouse)" — correct
- The profile is rich and accurate FOR THE FATHER, but the son's profile is entirely missing since they're conflated

**Uncle Bill profile (good):**
- Appearance: "elderly, grizzled, small man" — accurate
- Personality: "self-sacrificing, emotionally reserved but deeply loyal" — accurate
- Voice guidance: "low, measured, restrained tone" — appropriate
- Relationships: "John (the nephew) (mentor)" — correct; "John Donaldson (the father) (ally)" — should be "cousin"; "Margaret Donaldson (ally)" — acceptable
- Example quotes are accurate and well-chosen

**Issues:**
- Uncle Bill's relationship to John Sr. labeled "ally" — should be "cousin"
- Uncle Bill's relationship to John Sr. labeled "victimizer" in John's profile — very odd characterization. Uncle Bill *helped* John Sr., not victimized him
- The `physical_description` JSON field is still null for all characters (data model issue)

Score: 8/10 — the profiles are rich and mostly accurate, but the relationship labels are sometimes odd and the conflated John Donaldson means the son has no profile.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary — Mostly accurate:**
- Correctly captures: young John's letter, Uncle Bill's emotional response, backstory about John Sr.
- ✅ Correctly uses "cousin" context ("a charismatic Yale classmate whom he once shared a room, ponies, and travels with")
- Issue: `characters_present` only lists "Narrator" — should list Uncle Bill, John Donaldson, Margaret Donaldson, young John

**Section 2 summary — Major factual error persists:**
- Error: "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN (text line 28: "a cousin, who had come to be this lad's father"), NOT his sister's son. This is an LLM hallucination that has persisted across all attempts.
- Otherwise comprehensive and detailed — covers the war service, meeting the father, deathbed reunion
- `characters_present` correctly lists: Uncle Bill, John Donaldson (the son), John Donaldson (the father) — this shows the summary agent CAN distinguish father/son

Score unchanged from attempt 2 — no summary fixes were attempted.

### 2.5 Pronunciation Guide: 6/10 ✗

29 pronunciation entries (down from 30 — "Cross" likely removed with Red Cross filtering).

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate — useful for narrators

**False positives (~14):** Bill, Ted, Joe, Donaldson, Donaldson's (duplicate), Margaret, Barron, was, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies

**IPA issues:**
- "Barron" given as `/bəˈrɒn/` (buh-RON) — should be `/ˈbær.ən/` (BARE-un)
- "orderlies" given as `/ˈɔːr.dər.laɪz/` — should be `/ˈɔːr.dər.liz/`

Score unchanged — pronunciation false positive filtering was not addressed in this attempt.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation, rich character profiles, pronunciation guide. No broken elements.
- Minor: Both chapter sections show "null" for titles

Score unchanged.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (8 × 0.15) + (7.5 × 0.20) + (6 × 0.10) + (9 × 0.10)
        = 1.40 + 1.75 + 1.20 + 1.50 + 0.60 + 0.90
        = 7.35
```

**Overall: 7.35/10**

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson NOT split — Step 1.6 reads wrong data source**
   - Problem: Still only one "John Donaldson" entry (main_cast_1) conflating father (55+, embezzler, died as stretcher-bearer) and son (~23, ambulance driver, narrator of war story).
   - Root cause: `_split_disambiguated_same_name_characters()` (characters.py:1285) reads `characters_present` from `chapters` parameter, but `_get_chapters()` (line 775) creates StructuralElement objects from `context.chapter_map` which do NOT have `characters_present` populated at CharacterAgent runtime. The data is in the summary objects (`context.previous_results["summaries"]`), not the chapter map.
   - Evidence: `jq '.structure[1].characters_present'` shows `["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` in the FINAL output, but that's populated by `_convert_chapters()` (analyzer.py:2575-2600) AFTER all agents finish.
   - Location: `src/agents/characters.py` — `_split_disambiguated_same_name_characters()` (line 1285) and `_get_chapters()` (line 775)
   - Fix: Modify Step 1.6 to read `characters_present` from the summary objects instead of the chapters. The summary data is already available via `self._get_chapter_summaries(context)`. The method signature should take `chapter_summaries` (the summary objects) instead of or in addition to `chapters`, and iterate over their `characters_present` fields.
   - This fix also requires the method to extract `characters_present` correctly from the summary objects (they use `active_characters` field with a `characters_present` property — see `src/pipeline/chapter_summary/models.py:63`).

### HIGH

2. **Excessive pronunciation false positives (14 of 29 entries are common English)**
   - Problem: Common names (Bill, Ted, Joe, Margaret), common words (was), standard vocabulary (whippersnapper, manliness, orderlies, thickset, thriftless, dum-dums) flagged unnecessarily
   - Useful entries: ~10 Italian/French place names + "mayn't" + Frith + 5 homographs
   - Location: `src/pipeline/pronunciation/` or `src/agents/pronunciation_agent.py`
   - Fix: Improve the prompt to focus on GENUINELY unusual words: foreign terms, archaic words, names with non-obvious pronunciation. Exclude common English vocabulary and common given names. The prompt should specify: "Do NOT flag common English first names (Bill, Ted, Joe, Margaret, etc.), common English words found in any standard dictionary (was, orderlies, manliness, etc.), or possessive forms of already-flagged words."
   - Impact: +2 to Pronunciation (6→8)

3. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN (text line 28: "a cousin, who had come to be this lad's father"), NOT his sister
   - Location: Summary generation — LLM hallucination
   - Fix: Difficult to fix generically (LLM-generated content). Could potentially be addressed by lowering summary temperature.

### MEDIUM

4. **Chapter 1 `characters_present` only lists "Narrator"**
   - Problem: Should identify Uncle Bill, John Donaldson, Margaret Donaldson as characters discussed/referenced
   - Location: Summary agent / character presence detection
   - Fix: Characters who are discussed (not just physically present) should be included

5. **Uncle Bill relationship labels inaccurate**
   - Problem: "John Donaldson (the father) (ally)" should be "cousin"; "Uncle Bill (victimizer)" in John's profile is wrong (Uncle Bill helped John Sr.)
   - Location: Character profiling — relationship extraction
   - Fix: LLM-generated labels; hard to fix generically

6. **Structure: 2 null-titled sections for a continuous short story**
   - Problem: No structural markers in text → 2 null-titled sections less useful than 1 titled section
   - Location: Chapter detection — needs threshold for minimum structural evidence
   - Fix: For very short texts with no markers, treat as one section

### LOW

7. **Ted Frith missing "Teddy" alias**
   - Problem: Text uses "Teddy" 2x to refer to Ted Frith but this wasn't captured as alias
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — nickname matching rules
   - Fix: Add nickname variant matching for common diminutives

8. **`physical_description` JSON field null for all characters**
   - Problem: HTML profiles render appearance data but JSON `physical_description` field is null
   - Location: Data model / export — profile data stored differently
   - Impact: API consumers expecting this field won't find it

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
- **Result:** DID NOT FIRE — method reads `characters_present` from `chapters` (StructuralElements from `_get_chapters`), but those objects have empty `characters_present` at CharacterAgent runtime. The data is in the summary objects.
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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | **No change — reads wrong data source** |
| 3 | Red Cross organization | `supporting.py` (org filter) | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Partial fix (Ted alias, 5 mentions, but Teddy missing) |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- 1 JSON parse failure in pronunciation (minor, same as before)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- Character Profiles was the bottleneck at 573s (largest stage)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |

## Priority Fix Order for Attempt 4

Focus on the 4 failing categories. Highest-impact fixes:

1. **Fix Step 1.6 data source (Critical #1)** — Change `_split_disambiguated_same_name_characters()` to read `characters_present` from the summary objects (available via `_get_chapter_summaries(context)`) instead of from the `chapters` StructuralElements. The summary objects have the correct data. (+1 to Character Extraction, +0.5 to Profiles)

2. **Pronunciation false positive filtering (High #2)** — Improve the pronunciation prompt to not flag common English names and standard vocabulary. (+2 to Pronunciation, pushing it from 6→8)

These 2 fixes should push Character Extraction from 7→8+ and Pronunciation from 6→8+, making 4 of 6 categories pass. Structure (7) and Summaries (7.5) remain below threshold but are harder to fix generically. If the father/son split works correctly, the summaries' `characters_present` improvement could push Summaries slightly higher.

## Next Action
Run PROMPT_fix.md to address:
1. Step 1.6 data source fix (Critical #1) — one targeted code change in characters.py
2. Pronunciation false positive filtering (High #2)
