# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 7)
- Analysis completed successfully in 37m 9s
- 5 characters extracted: Margaret Donaldson (main_cast), John/Uncle Bill/Joe Barron/Ted Frith (supporting)
- Summary disambiguation fix PARTIALLY WORKED: Ch2 `characters_present` now has "John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (the uncle)"
- BUT "John Donaldson (the uncle)" is Uncle Bill misidentified as a third John — this confused Step 1.6
- Step 1.6 still DID NOT produce a character split — single "John" entry with 30 mentions
- Uncle Bill now sole narrator (fixed from attempt 6's dual-narrator issue)
- Margaret Donaldson now present as main_cast_4 (fixed from attempt 6)
- Canonical name regressed: "John" instead of "John Donaldson"

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. Two sections with null titles for a continuous short story. "American, Sir" by Ben Ames Williams has no explicit chapter divisions — it's a continuous short story. Splitting into 2 sections is workable but 1 section would be more accurate. Both titles are null, which displays as "Chapter 1" and "Chapter 2" in HTML.

Score: 7/10 — functional but not ideal for a text with no structural markers.

### 2.2 Character Extraction: 7/10 ✗ (UNCHANGED from attempt 6)

**Fix 1 (Summary prompt disambiguation) PARTIALLY WORKED:**
- Ch2 `characters_present` now shows `["John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (the uncle)"]` ✓
- BUT "John Donaldson (the uncle)" is Uncle Bill, NOT a third John Donaldson
- This extra entry may have confused Step 1.6's split logic

**Step 1.6 still DID NOT FIRE or DID NOT PRODUCE A SPLIT:**
- Still a single "John" entry (supporting_0) with 30 mentions conflating father and son
- Canonical name regressed to just "John" (was "John Donaldson" in attempt 6)

**What works:**
- Uncle Bill correctly identified as sole narrator ✓ (IMPROVED from attempt 6)
- Margaret Donaldson now present as main_cast_4 ✓ (IMPROVED — was missing in attempt 6)
- Ted Frith with alias "Ted" and 5 mentions ✓
- Joe Barron present ✓
- No hallucinated characters ✓

**Issues remaining:**
1. Father/son John Donaldson still NOT split — single "John" entry with 30 mentions
2. Canonical name "John" is worse than "John Donaldson" — less informative
3. "John Donaldson's" as alias — possessive form shouldn't be an alias
4. Relationship "Narrator (Uncle Bill): enemy" — WRONG. Uncle Bill was John Sr.'s close cousin/friend, not enemy
5. "Italian Red Cross" listed as relationship partner — organization, not character
6. John tagged as "minor" in HTML despite 30 mentions — should be major

Score: 7/10 — narrator fix is good, Margaret Donaldson now present. Father/son conflation remains the primary blocker. Canonical name regression is new.

### 2.3 Character Profiles: 7.5/10 ✗ (UNCHANGED)

**John's profile (HTML):**
- Appearance: "dark olive skin and blue eyes framed by thick lashes" — accurate for the FATHER ✓
- Personality: "committed financial betrayal...redeemed himself through selfless, courageous service" — accurate ✓
- Voice guidance: Excellent — "worn by time and guilt, yet firm with inner conviction" ✓
- Quotes: "American, sir!" and "Took money. Very unjustifiable." — correctly father's words ✓
- BUT: Still conflates father and son into one profile

**Uncle Bill's profile (HTML):**
- Appearance: "elderly man with a stern, reserved presence" — reasonable ✓
- Personality: "gruff exterior conceals profound compassion" — accurate ✓
- Voice guidance: Excellent — "calm, gravelly, restrained voice" ✓
- **Quote MISATTRIBUTED**: "I want you to know that I'll be prouder all my life than words can say that I've had you for a father" — this is the SON's words to his dying father, NOT Uncle Bill's
- Relationships: "John Donaldson (mentor)", "John Donaldson (father) (family)" — internally distinguishes father/son ✓

**Margaret Donaldson (supporting):**
- Description: "The widow of John Donaldson (the father) and mother of John Donaldson (the son)" — correctly disambiguates ✓ (IMPROVED)

Score: 7.5/10 — good voice guidance and descriptions. Quote misattribution and father/son conflation in John's profile remain.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Good quality. Correctly says "his late cousin John" (accurate!). `characters_present` only lists "the narrator" — should include Uncle Bill, John Donaldson, Margaret Donaldson.

**Section 2 summary:** Comprehensive and well-structured. Captures the fishing trip, WWI, reunion, and deathbed reveal. **Persistent factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 7 attempts. Ch1 correctly uses "cousin" but Ch2 hallucinates "sister."

**Ch2 `characters_present` improvement:** Now disambiguated with father/son/uncle qualifiers, but "John Donaldson (the uncle)" is actually Uncle Bill, not a separate John.

Score: 7.5/10 — detailed summaries useful for narrator prep, but Ch2 "sister" hallucination persists and Ch1 `characters_present` is incomplete.

### 2.5 Pronunciation Guide: 6.5/10 ✗ (UNCHANGED)

27 entries. All categories null (regression persists from attempt 5).

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~12):** Donaldson, Donaldson's, Barron, Margaret, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" `/bəˈrɒn/` — wrong stress pattern (suggests "baron" not surname "Barron")
- "was" `/wɒz/` — common word, shouldn't be flagged at all
- "orderlies" `/ˈɔːr.dər.lɪz/` — IPA now correct (fixed from attempt 6's /laɪz/)

Score: 6.5/10 — good Italian/French term coverage, but ~12 false positives including common English words. Categories all null.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation. Character profiles rendered with rich appearance/personality/voice sections. Uncle Bill correctly tagged as sole narrator ✓. Margaret Donaldson's description correctly disambiguates father/son. Supporting characters in table format.

Score: 9/10 — professional presentation.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (7.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (9 × 0.10)
        = 1.40 + 1.75 + 1.125 + 1.50 + 0.65 + 0.90
        = 7.325 ≈ 7.33
```

**Overall: 7.33/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 1` — DOWN from 2 (Margaret Donaldson is now the only main_cast character)
- Character Profiles was bottleneck at 501s
- Pronunciation categories all null (regression persists)
- 4 medium-confidence characters, 1 high-confidence — suggests extraction is borderline

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson still NOT split**
   - Problem: One "John" entry (supporting_0, 30 mentions) conflating the father (~55, embezzler/stretcher-bearer who died in Italy) and the son (~23, ambulance driver who survived the war)
   - What happened: Summary prompt disambiguation PARTIALLY WORKED — Ch2 now shows "John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (the uncle)". But "the uncle" is Uncle Bill, not a third John, which may have confused Step 1.6
   - **NEW DIAGNOSIS:** Need to verify Step 1.6 code actually ran and why it didn't produce a split. The upstream data is now available (disambiguated `characters_present`), so the issue is likely in Step 1.6's matching logic — possibly it requires EXACTLY 2 same-name variants (not 3), or the "(the uncle)" entry confuses it
   - Location: `src/agents/characters.py` — Step 1.6 `_split_disambiguated_same_name_characters()`
   - Fix approach:
     (a) Debug Step 1.6 — add logging to understand why it doesn't fire with the current disambiguated data
     (b) Fix the summary prompt to NOT label Uncle Bill as "John Donaldson (the uncle)" — he should just be "Uncle Bill"
     (c) Make Step 1.6 more robust — filter out entries that don't match the base name pattern, handle 3+ variants

### HIGH

2. **Pronunciation false positives (~12 of 27)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Donaldson's, Barron, Margaret, Johnny
   - Additionally: Barron IPA still wrong `/bəˈrɒn/` (should be `/ˈbærən/`)
   - All pronunciation categories are null (regression from attempt 5)
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt needs stronger instruction NOT to flag standard English vocabulary
   - Fix: Two-pronged approach:
     (a) Improve LLM prompt: "Do NOT flag standard English words, common English surnames, or common English first names. Only flag words a native English speaker would genuinely need pronunciation guidance for."
     (b) Post-filter: Expand CMU derivation checking for -ness, -less, -ful, -ly, -ies suffixes

3. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 7 attempts — LLM consistently hallucinates "sister" for Ch2
   - Ch1 summary CORRECTLY says "his late cousin" — summaries contradict each other
   - Location: Summary generation — likely the Ch2 text chunk doesn't include the "cousin" reference directly, so LLM infers (incorrectly) "sister"
   - Fix: This may require cross-chapter context or post-summary consistency check

### MEDIUM

4. **Canonical name regression: "John" instead of "John Donaldson"**
   - Problem: Canonical name for main character is now just "John" — less informative than "John Donaldson" in attempt 6
   - With aliases "John Donaldson, John Donaldson's, Johnny" — the canonical should be the FULL name
   - Location: Character extraction canonical name selection — `src/pipeline/character_extraction_v2/` or supporting cast logic
   - Fix: Canonical name should prefer the longest/most-complete form

5. **Relationship labels wrong**
   - "Narrator (Uncle Bill): enemy" — WRONG. Uncle Bill was John Sr.'s close cousin/friend who covered up his scandal
   - "Italian Red Cross: ally" — an organization, not a character relationship
   - Uncle Bill's relationships are better: "John Donaldson (mentor)", "John Donaldson (father) (family)"
   - Location: Character profiling LLM — relationship extraction confused by conflated character

6. **Chapter 1 `characters_present` only lists "the narrator"**
   - Should include Uncle Bill, John Donaldson, Margaret Donaldson
   - Ch2 was improved with disambiguation but Ch1 regressed/stayed minimal

7. **Uncle Bill quote misattribution**
   - "I want you to know that I'll be prouder all my life than words can say that I've had you for a father" — this is the SON's words to his dying father, NOT Uncle Bill's
   - Uncle Bill retells the story but the quote itself belongs to John Jr.

### LOW

8. **"John Donaldson's" as alias**
   - Possessive form shouldn't be an alias entry

9. **Ted Frith missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured. Same issue since attempt 3.

10. **JSON `profile` field null for all characters**
    - HTML has rich profiles but JSON export doesn't include them.

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
| 7 | Father/son conflation | `summarizer.py` (UPSTREAM FIX - prompt disambiguation) | **PARTIAL** — disambiguation appeared in characters_present but Uncle Bill misidentified as "John Donaldson (the uncle)"; Step 1.6 still no split |

**⚠️ FATHER/SON JOHN DONALDSON — 7 ATTEMPTS, STILL UNRESOLVED:**
- Attempts 1-6: Downstream fixes in characters.py and main_cast.py — all failed
- Attempt 7: Upstream fix in summarizer.py — PARTIALLY WORKED (data now available but Step 1.6 didn't produce split)
- **ROOT CAUSE NARROWED:** The upstream data is now partially correct. Two remaining issues:
  1. Summary LLM incorrectly labeled Uncle Bill as "John Donaldson (the uncle)" — need to fix prompt to be clearer
  2. Step 1.6 may need debugging to understand why it doesn't split even with 2 valid same-name variants

**⚠️ PRONUNCIATION STUCK:** 7 attempts, false positives remain at ~12 of 27. The CMU filter only works for short names. Need stronger LLM prompt filtering AND expanded post-filtering.

## Priority Fix Order for Attempt 8

**Focus on the two highest-impact fixes:**

1. **Debug and fix Step 1.6 + refine summary disambiguation prompt (CRITICAL #1)**
   - Two sub-fixes:
     (a) Refine the summary disambiguation prompt to NOT relabel Uncle Bill as "John Donaldson (the uncle)". Add guidance: "Only disambiguate characters who actually share the same name. Do not relabel characters who already have distinct names (e.g., if 'Uncle Bill' is a separate character, keep him as 'Uncle Bill')."
     (b) Debug Step 1.6 in `src/agents/characters.py` — add logging or examine the code to understand why it doesn't produce a split when Ch2 has "John Donaldson (the son)" and "John Donaldson (the father)" in `characters_present`. The issue may be:
       - Step 1.6 requires exactly 2 variants (and there are 3 including "the uncle")
       - Step 1.6 doesn't match the base name correctly
       - Step 1.6 runs before summaries are available
   - Impact: +1.5 Character Extraction, +0.5 Profiles, ~+0.6 overall

2. **Pronunciation false positive reduction (HIGH #2)**
   - Improve LLM prompt: "Do NOT flag: standard English words (e.g., 'was', 'manliness', 'thriftless', 'whippersnapper'), common English surnames (e.g., 'Donaldson', 'Barron'), or common English first names (e.g., 'Margaret', 'Johnny'). Only flag words a native English speaker would genuinely need pronunciation guidance for: foreign words, technical terms, archaic terms, or ambiguous homographs."
   - Expand CMU suffix filter for -ness, -less, -ful, -ly, -ies derivations
   - Location: `src/pipeline/pronunciation_guide/`
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
| 7 | 7.33 | +0.73 | Summary disambiguation PARTIAL — data now in characters_present but Step 1.6 still no split. Uncle Bill sole narrator ✓. Margaret Donaldson present ✓. |

## Next Action
**Phase:** awaiting_fix

Run PROMPT_fix.md to address:
1. CRITICAL #1: Debug Step 1.6 + refine summary prompt (both sub-fixes needed)
2. HIGH #2: Pronunciation false positive reduction
