# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 10
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6.5/10 ✗
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from attempt 8. "American, Sir" is a continuous short story with no explicit chapter divisions. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers.

Score: 7/10

### 2.2 Character Extraction: 6.5/10 ✗ (REGRESSION from 7/10)

**The alias-based split fix DID NOT WORK due to a logic bug:**

The code at `characters.py:1416-1447` has:
```python
if not labels_found and hasattr(char, 'aliases') and char.aliases:
```
But `labels_found` is NOT empty — it contains `{'the son'}` from Chapter 1's `"John (the son)"` matching canonical base_name "John". Since `labels_found` has 1 element (truthy), the alias fallback is skipped entirely. The code needs `if len(labels_found) < 2` instead of `if not labels_found`.

**Regression: Margaret Donaldson MISSING**
- In attempt 8: Margaret present as main_cast_3
- In attempt 9: Margaret completely absent from output
- This is a regression — main_cast_count dropped from 2 to 0 (all 4 characters are now supporting_cast)

**Characters found (4 total, all supporting):**
- supporting_0: John (mentions=30, aliases=["John Donaldson", "John Donaldson's", "Johnny"]) — father/son STILL conflated
- supporting_1: Uncle Bill (mentions=18, narrator=true, aliases=["Bill"]) ✓
- supporting_2: Joe Barron (mentions=3) ✓
- supporting_3: Ted Frith (mentions=5, aliases=["Ted"]) ✓

**Issues:**
1. Father/son John Donaldson STILL NOT SPLIT (logic bug — see CRITICAL #1)
2. Margaret Donaldson MISSING (regression)
3. Canonical name "John" less informative than "John Donaldson"
4. "John Donaldson's" possessive alias
5. John tagged as "minor" despite 30 mentions
6. main_cast_count = 0 (all from supporting cast)

Score: 6.5/10 — regression from 7/10 due to Margaret loss

### 2.3 Character Profiles: 7/10 ✗

**John's profile (HTML):**
- Appearance: "A grizzled, middle-aged American man" — describes the FATHER accurately ✓
- Features: "dark skin, thickset and long lashes, grizzled appearance" — accurate for father ✓
- Personality: "morally ambiguous man who committed grave betrayals" — accurate for father ✓
- Voice guidance: Excellent — tone, dialect, formality all well-crafted ✓
- Quotes: "American, sir!" and others — correctly father's words ✓
- Relationships: "John Donaldson (the son) (father)", "Margaret Donaldson (spouse)" — CORRECTLY disambiguated in relationships ✓
- BUT: Still conflates father and son into one profile (because they aren't split)

**Uncle Bill's profile (HTML):**
- Appearance: "elderly man with a stern, reserved presence" — reasonable ✓
- Personality: "quiet, gruff exterior conceals profound compassion" — accurate ✓
- Voice guidance: "A low, measured, gravelly tone" — excellent ✓
- Quote: "Dear John: I will come to your commencement and bring you back with me" — correctly Uncle Bill's letter ✓
- Relationships: "John Donaldson (the son) (mentor)", "John Donaldson (the father) (family)" — correctly distinguishes them ✓
- physical_description field: null in JSON (0/4 characters have it) — though descriptions appear in HTML under "Appearance" sections

**Margaret Donaldson:** MISSING (regression) — no profile at all

Score: 7/10 — reduced from 7.5 due to Margaret's absence and father/son conflation

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Good quality. `characters_present` shows `["the narrator", "John (the son)"]` — good disambiguation. Summary captures key events: the letter, Uncle Bill's conflicted reaction, memories of the elder John, the cousin bond, the mysterious death, Margaret's cold note. One note: `characters_present` says "the narrator" instead of "Uncle Bill" — inconsistent with Ch2.

**Section 2 summary:** Comprehensive and well-structured. **PERSISTENT factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 9 attempts. The plot summary correctly says "his late cousin John" in the overview section. Characters_present correctly shows father/son disambiguation.

**Plot summary (overview):** Excellent. Detailed, accurate, captures all major plot points including cousin relationship correctly.

Score: 7.5/10 — Ch2 "sister" hallucination persists

### 2.5 Pronunciation Guide: 6.5/10 ✗

26 entries (down from 27 in attempt 8). All categories still null.

**Genuinely useful entries (~9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~12):** Donaldson, Donaldson's, Barron, Frith, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" `/bəˈrɒn/` — wrong stress (suggests French "baron" not English surname "Barron")
- "orderlies" `/ˈɔːr.dər.laɪz/` — IPA WRONG (should be `-lɪz` not `-laɪz`)
- "was" `/wɒz/` — common word, shouldn't be flagged at all

Score: 6.5/10 — good Italian/French coverage, but ~12 false positives. All categories null.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation. Character profiles rendered with rich appearance/personality/voice sections. Uncle Bill correctly tagged as sole narrator. Relationships correctly distinguish father/son John Donaldson. Plot summary is comprehensive. Tab-based navigation works.

Score: 9/10

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (9 × 0.10)
        = 1.40 + 1.625 + 1.05 + 1.50 + 0.65 + 0.90
        = 7.125 ≈ 7.08
```

**Overall: 7.08/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- No JSON parse failures (good)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 0` (REGRESSION from 2 in attempt 8)
- `supporting_cast_count: 4` (John, Uncle Bill, Joe Barron, Ted Frith)
- Character Profiles was bottleneck at 541s (9m)
- Pronunciation categories all null
- All 4 character confidences: medium → profiled to high

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson STILL NOT SPLIT — logic bug in alias fallback condition**
   - Problem: Single "John" entry (supporting_0, 30 mentions) conflating father (~55, embezzler/stretcher-bearer) and son (~23, ambulance driver)
   - **ROOT CAUSE (NEW — CONFIRMED VIA SIMULATION):** The fallback condition at `characters.py:1420` checks `if not labels_found`, but `labels_found` is NOT empty. Chapter 1's `characters_present` has `"John (the son)"` which matches canonical base_name "John", giving `labels_found = {'the son'}` (1 label). Since this is truthy, the alias fallback is SKIPPED. The code finds only 1 label from canonical matching, which isn't enough for a split (needs ≥ 2), but never tries aliases because the set isn't empty.
   - **Fix:** Change line 1420 from `if not labels_found` to `if len(labels_found) < 2`. This way, when canonical matching finds only 1 label, it still tries aliases which would find both "the father" and "the son" via "John Donaldson".
   - Location: `src/agents/characters.py` line 1420
   - **Exact code change:**
     ```python
     # CURRENT (broken):
     if not labels_found and hasattr(char, 'aliases') and char.aliases:

     # FIX:
     if len(labels_found) < 2 and hasattr(char, 'aliases') and char.aliases:
     ```
   - **NOTE:** When alias matching finds labels, it should REPLACE (not extend) the canonical labels, since the alias provides the correct base_name. The current code already does this correctly with `labels_found = alias_labels` on line 1441.
   - Impact: +1.5 Character Extraction, +0.5 Profiles, ~+0.6 overall

### HIGH

2. **Margaret Donaldson MISSING (regression from attempt 8)**
   - Problem: Margaret was present as main_cast_3 in attempt 8 but is completely absent in attempt 9
   - Evidence: Only 4 characters in output, all supporting_cast. main_cast_count = 0.
   - Likely cause: The main cast extraction produced 0 characters this run (LLM variability), and Margaret didn't appear in supporting cast extraction either
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `supporting.py`
   - Fix: This may be LLM stochasticity — re-running analysis after the split fix may restore Margaret. If not, investigate why main_cast extraction fails intermittently.
   - Impact: -0.5 Character Extraction

3. **Pronunciation false positives (~12 of 26)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Donaldson's, Barron, Frith, Johnny
   - Additionally: Barron IPA wrong `/bəˈrɒn/`, orderlies IPA wrong `/ˈɔːr.dər.laɪz/`
   - All pronunciation categories are null
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt needs stronger filtering
   - Fix: Two-pronged approach:
     (a) Improve LLM prompt: "Do NOT flag standard English words, common English surnames, or common English first names"
     (b) Post-filter: Expand CMU derivation checking for common suffixes
   - Impact: Would raise Pronunciation from 6.5 to ~8.5

4. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 9 attempts — LLM consistently hallucinates "sister" for Ch2
   - The plot summary CORRECTLY says "his late cousin John"
   - Location: Summary generation — the Ch2 text chunk may not include the "cousin" reference
   - Fix: May need cross-chapter context or a post-summary consistency check
   - Impact: Would raise Summaries from 7.5 to ~8.5

### MEDIUM

5. **Canonical name "John" instead of "John Donaldson"**
   - Will be fixed automatically when father/son split is resolved (split creates "John Donaldson (the father)" and "John Donaldson (the son)")

6. **"John Donaldson's" as alias — possessive form**
   - Possessive form shouldn't be an alias entry
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Strip trailing `'s` from alias candidates

7. **Chapter 1 `characters_present` says "the narrator" instead of "Uncle Bill"**
   - Should use the character's name for consistency with Ch2

### LOW

8. **Ted Frith missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured

9. **John tagged as "minor" despite 30 mentions**
   - Role assignment should consider mention count

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
- **Result:** Summary fix WORKED (no more Uncle Bill mislabeling), but split STILL DID NOT FIRE due to regex mismatch:
  - Character canonical_name = "John" → base_name = "John"
  - Summary refs = "John Donaldson (the father)", "John Donaldson (the son)"
  - Regex `^John\s*\(...)$` does NOT match "John Donaldson (the father)"
  - Need to also check aliases (character has alias "John Donaldson")
- **Modified:**
  - `src/pipeline/chapter_summary/summarizer.py` (prompt clarification)
  - `src/agents/characters.py` (Step 5.10.7)

### Attempt 9 - Fix 1: Alias-based regex matching in _split_disambiguated_same_name_characters()
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — downstream fix
- **Fix:** Added fallback logic to try each alias as potential base_name when canonical doesn't match
- **Result:** **DID NOT WORK** — the alias fallback condition `if not labels_found` is wrong. Chapter 1 has "John (the son)" which matches canonical "John", setting `labels_found = {'the son'}`. Since set is truthy, alias fallback is never reached. Only 1 label found (need ≥2 for split).
- **Root cause:** Condition should be `if len(labels_found) < 2` not `if not labels_found`
- **Modified:** `src/agents/characters.py` (lines 1400-1467)

### Attempt 10 - Fix 1: Correct alias fallback condition in _split_disambiguated_same_name_characters()
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — final fix
- **Root cause:** `src/agents/characters.py:1421` - condition `if not labels_found` is wrong
  - Ch1 has "John (the son)" → canonical "John" matches → `labels_found = {'the son'}` (1 label)
  - Set is truthy → alias fallback SKIPPED
  - Only 1 label found → split doesn't trigger (need ≥ 2)
- **Fix:** Changed line 1421 from `if not labels_found` to `if len(labels_found) < 2`
  - Now: when canonical finds only 1 label, alias fallback runs
  - Alias "John Donaldson" matches Ch2 refs → finds 2 labels ("the father", "the son")
  - Split triggers correctly
- **Smoke test:** PASS - Logic verified against actual data:
  - Ch1: `"John (the son)"` matches canonical → 1 label found
  - Ch2: `"John Donaldson (the father)"`, `"John Donaldson (the son)"` match alias → 2 labels found
  - New condition triggers alias fallback → split should fire
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
| 9 | Father/son conflation | `characters.py` (alias fallback — wrong condition) | **DID NOT WORK** — `if not labels_found` should be `if len(labels_found) < 2` |
| 10 | Father/son conflation | `characters.py:1421` (fix condition) | **APPLIED** — one-line fix: `if len(labels_found) < 2` |

**⚠️ FATHER/SON JOHN DONALDSON — 9 ATTEMPTS:**
- Upstream data is CORRECT (attempts 7-9): summaries properly disambiguate father/son
- Regex matching was correct (attempt 9) BUT the fallback condition was wrong
- FIX: Change `if not labels_found` → `if len(labels_found) < 2` at characters.py:1420
- This is a ONE-LINE FIX

**⚠️ PRONUNCIATION STUCK:** 9 attempts, false positives remain at ~12 of 26. Need stronger LLM prompt filtering AND expanded post-filtering.

## Priority Fix Order for Attempt 10

**Focus on TWO fixes:**

1. **Fix the alias fallback condition (CRITICAL #1) — ONE LINE CHANGE**
   - At `characters.py:1420`, change `if not labels_found` to `if len(labels_found) < 2`
   - This is the ONLY remaining blocker for the father/son split
   - Verified via simulation: canonical "John" finds 1 label ("the son"), then alias "John Donaldson" would find 2 labels ("the father", "the son") → split triggered

2. **Pronunciation false positive reduction (HIGH #3)**
   - Improve LLM prompt: "Do NOT flag standard English words, common surnames, or common first names"
   - Expand post-filter for common suffixes (-ness, -less, -ful, -ly, -ies, -er)
   - Fix: `src/pipeline/pronunciation_guide/`
   - Impact: Would raise Pronunciation from 6.5 to ~8.5

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. Narrator flag inverted. |
| 6 | 7.33 | +0.73 | Narrator flag FIXED (partially). Father/son split still didn't fire (upstream data lacking). |
| 7 | 7.33 | +0.73 | Summary disambiguation PARTIAL — data now in characters_present but Uncle Bill mislabeled + Step 1.6 no split. |
| 8 | 7.33 | +0.73 | Summary fix WORKED (no more Uncle Bill mislabeling). Step 5.10.7 didn't split due to regex mismatch with aliases. |
| 9 | 7.08 | +0.48 | Alias fallback added but wrong condition (`not labels_found` vs `len < 2`). Margaret regression. |

## Next Action
Run PROMPT_analyze.md to re-run analysis with corrected alias fallback condition.

**Expected impact:**
- Father/son John Donaldson should split into 2 characters ✓
- Margaret Donaldson may reappear (LLM stochasticity)
- Character Extraction: 6.5 → 8.0+ (father/son split + better canonical names)
- Character Profiles: 7.0 → 8.0+ (no more conflation)
- Overall: 7.08 → ~7.8+
