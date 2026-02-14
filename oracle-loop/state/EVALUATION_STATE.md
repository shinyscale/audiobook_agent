# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

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

Unchanged. Two sections with null titles for a continuous short story. "American, Sir" has no explicit chapter divisions — it's a continuous short story. Splitting into 2 sections is workable but 1 section would be more accurate. Both titles null → displays as "Chapter 1" and "Chapter 2" in HTML.

Score: 7/10 — functional but not ideal for a text with no structural markers.

### 2.2 Character Extraction: 7/10 ✗ (UNCHANGED from attempt 7)

**Summary disambiguation FIX WORKED:**
- Ch1 now shows `["the narrator", "John (the son)"]` ✓
- Ch2 now shows `["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]` ✓
- NO "John Donaldson (the uncle)" — prompt clarification succeeded ✓

**BUT Step 5.10.7 STILL DID NOT PRODUCE A SPLIT:**
- Still a single "John" entry (supporting_0) with 30 mentions conflating father and son
- Canonical name still just "John" — less informative than full "John Donaldson"

**ROOT CAUSE IDENTIFIED (NEW):**
The `_split_disambiguated_same_name_characters()` method at `characters.py:1365-1370` extracts `base_name` from the character's `canonical_name`:
```python
base_name = re.sub(r'\s*\([^)]+\)\s*$', '', char.canonical_name).strip()
# char.canonical_name = "John" → base_name = "John"
```
Then at line 1404-1408, it matches summary refs against this base_name:
```python
match = re.match(r'^' + re.escape(base_name) + r'\s*\(([^)]+)\)\s*$', char_ref)
# Pattern: ^John\s*\(([^)]+)\)$
# Summary refs: "John Donaldson (the father)", "John Donaldson (the son)"
# DOES NOT MATCH because "Donaldson" appears between "John" and "("
```

**The fix needs to also try matching against aliases.** The character has alias "John Donaldson", so when checking summary refs, the method should try BOTH canonical_name ("John") AND all aliases ("John Donaldson") as potential base_names.

**What works:**
- Uncle Bill correctly identified as sole narrator ✓
- Margaret Donaldson present as main_cast_3 ✓
- Ted Frith with alias "Ted" and 5 mentions ✓
- Joe Barron present ✓
- No hallucinated characters ✓
- Summary disambiguation now produces correct upstream data ✓

**Issues remaining:**
1. Father/son John Donaldson still NOT split — regex mismatch (see root cause above)
2. Canonical name "John" is less informative than "John Donaldson"
3. "John Donaldson's" as alias — possessive form shouldn't be an alias
4. John tagged as "minor" in HTML despite 30 mentions — should be major
5. Relationship "The Narrator (Uncle Bill): acquaintance" — should be "cousin/guardian" or "family"

Score: 7/10 — upstream data now correct, but downstream split logic has a regex bug.

### 2.3 Character Profiles: 7.5/10 ✗

**John's profile (HTML):**
- Appearance: "A grizzled, middle-aged American man of striking physical presence" — describes the FATHER accurately ✓
- Features: "very olive skin, thickset and long lashes, dark eyes, shabby clothes with an air like a duke" — accurate for father ✓
- Personality: "morally ambiguous man who committed theft and abandonment but redeemed himself through selfless, courageous service" — accurate for father ✓
- Voice guidance: Excellent — "A voice worn by guilt and years of exile, but lifting with sudden pride when speaking of his American identity" ✓
- Dialect: "English with a foreign twist, likely Italian-influenced accent" — appropriate ✓
- Quotes: "American, sir!" and "Took money. Very unjustifiable." — correctly father's words ✓
- BUT: Still conflates father and son into one profile (because they aren't split)

**Uncle Bill's profile (HTML):**
- Appearance: "elderly man with a stern, reserved demeanor" — reasonable ✓
- Personality: "quiet, reluctant acts of compassion and unwavering loyalty" — accurate ✓
- Voice guidance: "A low, measured, gravelly voice with long pauses" — excellent ✓
- Quote: "Dear John: I will come to your commencement and bring you back with me" — correctly Uncle Bill's letter ✓ (IMPROVED from attempt 7 which had misattributed son's quote)
- Relationships: "John Donaldson (the son) (mentor)", "John Donaldson (the father) (ally)" — correctly distinguishes them ✓ (IMPROVED)

**Margaret Donaldson (supporting table):**
- Listed in supporting characters table

Score: 7.5/10 — good voice guidance and descriptions. Quote attribution IMPROVED (Uncle Bill's quote now correct). Father/son conflation in John's profile remains the main issue.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Good quality. `characters_present` now shows `["the narrator", "John (the son)"]` — IMPROVED from just "the narrator" in attempt 7. BUT "the narrator" should say "Uncle Bill" for consistency.

**Section 2 summary:** Comprehensive and well-structured. Captures the fishing trip, WWI, reunion, and deathbed reveal. Character disambiguation IMPROVED — `characters_present` correctly shows father/son without Uncle Bill mislabeled. **PERSISTENT factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. This has persisted across ALL 8 attempts.

**Plot summary (overview):** Excellent. Detailed, accurate, captures all major plot points. Correctly describes the cousin relationship in the first paragraph. Themes (identity, ambition, loss) are appropriate. Narrative style correctly identified as "first-person retrospective."

Score: 7.5/10 — improved disambiguation in characters_present. Ch2 "sister" hallucination persists.

### 2.5 Pronunciation Guide: 6.5/10 ✗ (UNCHANGED)

27 entries. All categories null.

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~12):** Donaldson, Donaldson's, Barron, Margaret, Johnny, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" `/bəˈrɒn/` — wrong stress pattern (suggests French "baron" not English surname "Barron")
- "was" `/wʌz/` — common word, shouldn't be flagged at all
- "orderlies" `/ˈɔːr.dər.laɪz/` — IPA WRONG (should end in `-lɪz` not `-laɪz`)

Score: 6.5/10 — good Italian/French term coverage, but ~12 false positives including common English words. Categories all null. Some IPA errors remain.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation. Character profiles rendered with rich appearance/personality/voice sections. Uncle Bill correctly tagged as sole narrator ✓. Uncle Bill's relationships correctly distinguish father/son John Donaldson. Plot summary is comprehensive and accurate.

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
- No JSON parse failures (good)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 2` (Margaret Donaldson + Uncle Bill)
- `supporting_cast_count: 3` (John, Joe Barron, Ted Frith)
- Character Profiles was bottleneck at 551s (9m 11s)
- Pronunciation categories all null (regression persists)
- 2 high-confidence, 3 medium-confidence characters — suggests extraction borderline

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson still NOT split — regex mismatch in Step 5.10.7**
   - Problem: One "John" entry (supporting_0, 30 mentions) conflating the father (~55, embezzler/stretcher-bearer who died in Italy) and the son (~23, ambulance driver who survived the war)
   - **ROOT CAUSE (CONFIRMED):** `_split_disambiguated_same_name_characters()` at `characters.py:1365-1370` extracts base_name from `char.canonical_name` → "John". The regex at line 1404-1408 builds pattern `^John\s*\(([^)]+)\)$` which does NOT match summary refs like "John Donaldson (the father)" because "Donaldson" sits between "John" and the parenthetical.
   - **The upstream data is now CORRECT** — Ch2 `characters_present` has "John Donaldson (the son)" and "John Donaldson (the father)" with no Uncle Bill mislabeling.
   - **Fix:** In `_split_disambiguated_same_name_characters()`, try matching summary refs against BOTH the canonical_name AND all aliases as potential base names. The character's alias "John Donaldson" would match "John Donaldson (the father)" correctly.
   - Location: `src/agents/characters.py` lines 1365-1411
   - Specific code change:
     ```python
     # CURRENT (broken):
     base_name = re.sub(r'\s*\([^)]+\)\s*$', '', char.canonical_name).strip()
     name_groups[base_name].append(char)

     # FIX: Also try aliases as base names
     # After grouping by canonical base_name, also check if any alias
     # matches the base of a summary ref. For example:
     # canonical_name="John", aliases=["John Donaldson", ...]
     # summary ref "John Donaldson (the father)" → base "John Donaldson"
     # → matches alias → should split this character
     ```
   - Impact: +1.5 Character Extraction, +0.5 Profiles, ~+0.6 overall

### HIGH

2. **Pronunciation false positives (~12 of 27)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Donaldson's, Barron, Margaret, Johnny
   - Additionally: Barron IPA wrong `/bəˈrɒn/`, orderlies IPA wrong `/ˈɔːr.dər.laɪz/`
   - All pronunciation categories are null
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt needs stronger instruction NOT to flag standard English vocabulary
   - Fix: Two-pronged approach:
     (a) Improve LLM prompt: "Do NOT flag standard English words, common English surnames, or common English first names. Only flag words a native English speaker would genuinely need pronunciation guidance for."
     (b) Post-filter: Expand CMU derivation checking for -ness, -less, -ful, -ly, -ies suffixes and common surnames
   - Impact: Would raise Pronunciation from 6.5 to ~8.5

3. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son
   - Persisted across ALL 8 attempts — LLM consistently hallucinates "sister" for Ch2
   - Ch1 summary CORRECTLY says "beloved cousin" — summaries contradict each other
   - The plot summary in overview ALSO correctly says "his late cousin John"
   - Location: Summary generation — likely the Ch2 text chunk doesn't include the "cousin" reference directly
   - Fix: May need cross-chapter context or post-summary consistency check
   - Impact: Would raise Summaries from 7.5 to ~8.5

### MEDIUM

4. **Canonical name regression: "John" instead of "John Donaldson"**
   - Will be fixed automatically when father/son split is resolved (split creates "John Donaldson (the father)" and "John Donaldson (the son)")

5. **"John Donaldson's" as alias — possessive form**
   - Possessive form shouldn't be an alias entry
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — alias extraction
   - Fix: Strip trailing `'s` from alias candidates

6. **Chapter 1 `characters_present` says "the narrator" instead of "Uncle Bill"**
   - Should use the character's name, not "the narrator"
   - Ch2 correctly says "Uncle Bill"

### LOW

7. **Ted Frith missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured. Same issue since attempt 3.

8. **John tagged as "minor" despite 30 mentions**
   - Role assignment should consider mention count — 30 mentions is not minor

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

**⚠️ FATHER/SON JOHN DONALDSON — 8 ATTEMPTS:**
- Upstream data is now CORRECT: summaries properly disambiguate father/son
- The ONLY remaining issue is a regex bug in `_split_disambiguated_same_name_characters()` — it only tries the canonical_name as base_name, not aliases
- Fix is surgical: add alias-based matching in the method

**⚠️ PRONUNCIATION STUCK:** 8 attempts, false positives remain at ~12 of 27. Need stronger LLM prompt filtering AND expanded post-filtering.

## Priority Fix Order for Attempt 9

**Focus on two fixes:**

1. **Fix regex mismatch in `_split_disambiguated_same_name_characters()` (CRITICAL #1)**
   - At `characters.py:1365-1411`, the method only tries canonical_name as base_name
   - Need to also try each alias as a potential base_name
   - When character has canonical_name "John" and alias "John Donaldson", the method should:
     1. Try base_name "John" → check for "John (the father)", "John (the son)" in summaries
     2. Try base_name "John Donaldson" → check for "John Donaldson (the father)", "John Donaldson (the son)" in summaries
     3. If #2 matches, use "John Donaldson" as the base for split names
   - This is a SMALL, TARGETED code change (add ~10 lines to the name_groups loop)
   - Impact: +1.5 Character Extraction, +0.5 Profiles, ~+0.6 overall

2. **Pronunciation false positive reduction (HIGH #2)**
   - Improve LLM prompt: "Do NOT flag: standard English words, common English surnames, or common English first names. Only flag words a native English speaker would genuinely need pronunciation guidance for."
   - Expand CMU suffix filter for -ness, -less, -ful, -ly, -ies, -er derivations
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

## Next Action
Run PROMPT_fix.md to fix regex mismatch in `_split_disambiguated_same_name_characters()` (add alias-based matching) and reduce pronunciation false positives.
