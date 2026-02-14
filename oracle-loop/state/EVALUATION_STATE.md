# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 20
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7.5/10 ✗
- Character Profiles: 5.5/10 ✗ (FAILING)
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 6.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (all 6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). Both structure elements have null start/end lines. For a continuous text with no structural markers, 1 section would be more accurate, but 2 is workable.

### 2.2 Character Extraction: 7.5/10 ✗

**MAJOR IMPROVEMENT from attempt 19 (was 5/10).** The attempt 20 disambiguation label guidance fix WORKED — both father AND son now exist as separate characters.

**What's correct:**
- John Donaldson (the father): 28 mentions, `main_cast_1_split_0` ✓
- John Donaldson (the son): 28 mentions, `main_cast_1_split_1` ✓
- Uncle Bill: 18 mentions, correctly identified as narrator with protagonist role ✓
- Margaret Donaldson: 2 mentions ✓
- Joe Barron: 3 mentions ✓
- Ted Frith with alias "Ted": 5 mentions ✓

**Remaining issues:**
1. **"John Donaldson's" (supporting_2)** — This is a malformed character with a possessive in the name and 4 mentions. It should not exist as a separate character. This is likely a possessive form ("John Donaldson's son" or "John Donaldson's widow") incorrectly extracted as a character name. Its alias is "Johnny" — which could be a legitimate alias for the son, but "John Donaldson's" is not a real character.
2. **Uncle Bill classified as `supporting_0`** — Uncle Bill is the narrator and protagonist but has a `supporting_` ID prefix, suggesting he came from the supporting cast pipeline rather than main cast. This is a classification oddity but doesn't affect the output quality significantly.
3. **Father and son both have role "supporting"** — Both should arguably be "protagonist" or at minimum the father should have a distinct role. The son is arguably the deuteragonist.
4. **Ted Frith still missing "Teddy" alias** — minor.

**Why 7.5/10:** The critical father/son split is now working correctly for the first time in many attempts. The "John Donaldson's" spurious character and role classification issues prevent a higher score.

### 2.3 Character Profiles: 5.5/10 ✗ (CRITICAL ISSUE)

**The son's profile is a COPY of the father's profile.** This is the most serious remaining issue.

**Father's profile: CORRECT and RICH** ✓
- Appearance: "striking physical resemblance to his son, with dark olive skin and blue eyes, bearing an air of quiet dignity despite his shabby appearance" — accurate description of the elder John as seen at the field hospital
- Personality: "morally ambiguous man who committed financial theft and abandoned his family for two decades, yet found redemption through selfless service" — accurate
- Voice: "low, weary, and carefully controlled, with moments of unexpected warmth and pride" — excellent narrator guidance
- Example quotes: "American, sir!", "Took money... Very unjustifiable.", "I'll finish--clean. To--my son." — all correctly attributed to the father
- Relationships: son (parent), Margaret (spouse), Uncle Bill (acquaintance) — relationship types partially correct

**Son's profile: CONTAMINATED — describes the FATHER** ✗✗✗
- Personality: "Morally ambiguous man who committed financial fraud and abandoned his family" — this describes the FATHER, not the son. The son is the young man who enlisted as an ambulance driver, met his father at the front, and brought the story home.
- Voice: "weary but precise, carrying the weight of hidden shame" — this is the father's voice, not the son's
- Example quotes: "American, Sir!", "Took money... Very unjustifiable." — these are the FATHER's lines. The son never says these.
- Appearance: "middle-aged man with a dark, olive complexion" — the son is a young man returning from war, not middle-aged
- Relationships: lists "John Donaldson (the son): parent" — the son lists HIMSELF as his own parent, which is nonsensical. This is a copy of the father's relationship data.

**The son should have:**
- Appearance: young man, recently returned from war, with striking blue eyes (inherited from father)
- Personality: brave, compassionate, reverent of duty and family, emotionally open
- Voice: youthful, earnest, with quiet intensity when recounting the meeting with his father
- Key quotes: dialogue about meeting the volunteer, discovering his father's identity
- Relationships: father (child), Uncle Bill (nephew/ward), Margaret Donaldson (mother)

**Uncle Bill's profile: CORRECT and RICH** ✓
- Personality: "stoic but deeply compassionate protagonist" — excellent
- Voice: "Low, gravelly, and measured" — great narrator guidance
- Relationships: lists "John Donaldson (nephew): mentor", "John Donaldson (father): ally", "Cousin John (deceased): acquaintance" — the multiple John entries are confusing and relationship types are wrong (Uncle Bill is the father's COUSIN, not acquaintance)

**Ted Frith's profile: GOOD** ✓
- Personality and voice guidance are accurate
- Relationships: lists "Ted Frith: ally" (self-referential — minor bug)

**Why 5.5/10:** The son's entire profile is a copy of the father's, making it actively misleading for a narrator. A narrator reading this would voice the son identically to the father, which is completely wrong. The father and Uncle Bill profiles are genuinely high quality, which prevents a lower score. Physical descriptions are present in the appearance sections of the profile body but `physical_description` field is null for all characters (minor structural issue).

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** Good quality. Captures the letter from John, Uncle Bill's initial anger, memories of his bond with John's father, the financial scandal, the death, and Margaret's letter. `characters_present: ["the narrator", "John (the boy)"]` — mostly correct, though "the narrator" should use "Uncle Bill".

**Chapter 2:** Comprehensive and well-structured. Covers taking in the boy, pier meeting, WWI service, Caporetto encounter, deathbed confession, redemption. `characters_present` correctly lists Uncle Bill, son, and father as disambiguated names. ✓

**Book overview:** Excellent — accurately captures the full narrative arc, themes of identity/loss/redemption, first-person retrospective structure. ✓

**PERSISTENT factual error (20th consecutive attempt):** Ch2 says "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "my cousin John". This is a deeply persistent LLM hallucination.

**Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"** — should use actual character name for narrator linking.

### 2.5 Pronunciation Guide: 6.5/10 ✗

27 entries, 22 with IPA. Quality breakdown:
- **Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms a narrator needs
- **Acceptable homographs (4):** live, minute, read, close, moderate — context-dependent pronunciation (but "moderate" is borderline)
- **False positives (~15):** Donaldson, Barron, Frith, Margaret, Johnny, Donaldson's, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — common English words/standard names
  - "was" is particularly egregious — the most common English word
  - "Margaret", "Johnny" are standard English names — no pronunciation help needed
  - "orderlies" IPA shown as "/ˈɔːr.dər.laɪz/" which is incorrect — should be "/ˈɔːr.dər.liz/"

### 2.6 HTML Presentation: 7/10 ✗

**Improvements from attempt 19:**
- Both father and son now present in "Main Characters" section ✓
- Father has rich, accurate profile with appearance, personality, voice guidance ✓
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓

**Remaining issues:**
1. **Son's profile shows father's data** — actively misleading (see Profiles section)
2. **"John Donaldson's" in supporting characters table** — malformed character name with possessive
3. **Son's relationship section lists himself as his own parent** — "John Donaldson (the son) (parent)" is nonsensical
4. **Father's role tag says "supporting"** — misleading for a central character
5. **Navigation, formatting, and overall layout all functional** ✓

**What works well:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Character profiles beautifully rendered with sections ✓
- Chapter summaries well-formatted with character tags ✓
- Pronunciation section organized ✓

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7.5 × 0.25) + (5.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (7 × 0.10)
        = 1.40 + 1.875 + 0.825 + 1.50 + 0.65 + 0.70
        = 6.95
```

**Overall: 6.95/10** (up from 6.50 in attempt 19 — +0.45 improvement)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: ~33m
- Character extraction: 7 items processed, main_cast_count=3, supporting_cast_count=4
- 0 merge decisions recorded
- 1 JSON parse failure in Pronunciation Guide stage (not blocking)
- Profile pipeline produced 4 profiles (items_processed=4) — all high confidence
- No config changes recommended at this time — the bottleneck is profile disambiguation

## Current Issues (Priority Order)

### CRITICAL

1. **Son's profile is a complete copy of the father's profile (PROFILE CONTAMINATION)**
   - Problem: The son (John Donaldson (the son)) has the father's personality, voice guidance, appearance, evidence quotes, and relationships. ALL profile fields describe the father, not the son.
   - Evidence:
     - Son's personality: "committed financial fraud and abandoned his family" — this is the father's story
     - Son's example quotes: "American, Sir!", "Took money... Very unjustifiable." — these are the father's lines
     - Son's appearance: "middle-aged man" — the son is a young man
     - Son's relationship: "John Donaldson (the son): parent" — lists himself as his own parent
   - Root cause: The name disambiguator cannot distinguish between father and son passages because both share the name "John Donaldson" and the same aliases. When the profiling pipeline gathers passages for the son, it picks up father's passages (and vice versa), and the LLM generates a profile from the wrong passages.
   - Location: `src/pipeline/character_profiling/name_disambiguator.py` — the disambiguation signals (Signal 0 for split labels, relationship markers, temporal markers) are either not firing or not strong enough to partition passages correctly between father and son.
   - Fix approach: The split label signal (Signal 0, confidence 0.99) was added in attempt 15 but caused a regression. The issue is that both characters have the SAME aliases (`["John Donaldson", "John"]`), so the passage gatherer collects the same passages for both. The fix must either:
     1. **Pre-partition passages before profiling** — when profiling a split character, only provide passages from chapters where that specific split label appears in `characters_present` (father appears in Ch2 field hospital scenes; son appears in both chapters)
     2. **Use the split label in the profiling prompt** — tell the LLM explicitly "This character is THE SON, a young ambulance driver. Exclude information about the father's crimes, confession, and deathbed."
     3. **Post-filter evidence** — after profile generation, validate that evidence quotes are actually spoken by or about the correct split character

### HIGH

2. **"John Donaldson's" (supporting_2) is a spurious character**
   - Problem: A character named "John Donaldson's" (with possessive apostrophe-s) exists with 4 mentions and alias "Johnny"
   - Evidence: This is likely extracted from possessive phrases like "John Donaldson's son" or "John Donaldson's widow" in the text
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — the NER or text extraction is treating possessive forms as character names
   - Fix: Add name cleaning to strip trailing possessive markers (`'s`) from extracted character names, or improve the NER filtering to reject possessive forms

3. **Chapter 2 summary factual error: "sister" instead of "cousin" (20th consecutive attempt)**
   - Problem: "his deceased sister's son" — should be "his cousin's son" or "his cousin"
   - Evidence: The text says "my cousin John" — Uncle Bill and John Sr. are cousins, not siblings
   - Location: Summary generation LLM — persistent hallucination across 20 runs
   - Fix: This has resisted 20 attempts of LLM-only fixes. Consider a post-processing text correction that searches for "sister's son" in summaries and cross-references actual relationship data from the character extraction.

4. **Relationship data inconsistent across characters**
   - Problem: Father lists Uncle Bill as "acquaintance"; Uncle Bill lists father as "ally". Neither is accurate — they are cousins. Son lists himself as his own parent.
   - Evidence: Text says "my cousin John"
   - Location: `src/pipeline/character_profiling/` — relationship extraction
   - Fix: Will partially improve when son's profile is correctly disambiguated

### MEDIUM

5. **Pronunciation false positives (~15 of 27)**
   - Common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset, dum-dums, mayn't) and standard names (Donaldson, Donaldson's, Barron, Frith, Margaret, Johnny) flagged unnecessarily
   - "was" is particularly egregious
   - "orderlies" IPA is incorrect (/ˈɔːr.dər.laɪz/ → should be /ˈɔːr.dər.liz/)
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve common-word filtering; extend CMU dictionary check to standard names

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles and null start/end lines
   - Location: `src/pipeline/chapter_detection/`

7. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Should use the character's actual name for narrator linking
   - Location: Summary prompt or post-processing

8. **Uncle Bill classified as supporting_0 instead of main_cast**
   - The narrator/protagonist has a supporting_ prefix ID, suggesting misclassification in the extraction pipeline
   - Location: `src/pipeline/character_extraction_v2/` — narrator should be promoted to main_cast

### LOW

9. **Ted Frith still missing "Teddy" alias** — text uses "Teddy" once or twice
10. **Margaret Donaldson promoted to main_cast (main_cast_3)** — she has only 2 mentions. Supporting would be more accurate.
11. **Ted Frith's relationships list "Ted Frith: ally"** — self-referential relationship entry
12. **`physical_description` field null for all characters** — appearance info exists in profile body but not in the top-level field

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
- **Fix:** Copy original character's aliases to each split child
- **Result:** **PARTIAL SUCCESS / NEW REGRESSION** — Father now has 29 mentions and rich profile. BUT: only ONE split child created (father). The son was absorbed as an alias of the father instead of becoming a separate character.
- **Modified:** `src/agents/characters.py` (lines 1459-1470)

### Attempt 12 - Fix 1: Prevent re-merge of split characters in Step 3.5
- **Issue addressed:** Son absorbed as alias of father (CRITICAL #1 regression from attempt 11)
- **Fix:** Added SAFETY CHECK 2 in Pass 2 to skip merge if both characters come from the same split operation
- **Result:** **PARTIAL SUCCESS / NEW PROBLEM** — Merge protection worked but `split_0` (father) MISSING while `split_1` (son) survives.
- **Modified:** `src/agents/characters.py` (lines 1904-1923)

### Attempt 13 - Fix 1: Partition aliases between split children
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1)
- **Fix:** Modified `_split_disambiguated_same_name_characters()` to PARTITION aliases
- **Result:** **NO EFFECT** — father still missing
- **Modified:** `src/agents/characters.py` (lines 1450-1505)

### Attempt 14 - Diagnostic Fix: Add comprehensive logging to trace split character flow
- **Issue addressed:** Father character (`split_0`) missing (CRITICAL #1)
- **Fix:** Added DEBUG logging at all critical pipeline stages
- **Result:** **SUCCESS** — Both `split_0` (father) AND `split_1` (son) now exist! NEW: Son has father's profile (cross-contamination).
- **Modified:** `src/agents/characters.py` (6 diagnostic logging blocks)

### Attempt 15 - Fix: Split character label-based disambiguation
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 14)
- **Fix:** Added Signal 0 (confidence 0.99) for split character label detection in `name_disambiguator.py`
- **Result:** **REGRESSION** — Son absorbed as alias of father. LLM nondeterminism.
- **Modified:** `src/pipeline/character_profiling/name_disambiguator.py`

### Attempt 16 - Fix: LLM Nondeterminism Defenses
- **Issue addressed:** Son absorbed, Uncle Bill lost narrator flag (CRITICAL #1, #2 from attempt 15)
- **Fix:** Three defensive protections: post-split validation, narrator promotion, narrator exclusivity
- **Result:** **SUCCESS** — Both father and son exist. Uncle Bill correctly narrates.
- **Modified:** `src/agents/characters.py` (lines 383-410, 600-631, 731-757)

### Attempt 17 - Fix: Add split character labels as standalone aliases
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 16)
- **Fix:** Add label itself as alias during split character creation
- **Result:** **REGRESSION** — Father absorbed into son.
- **Modified:** `src/agents/characters.py` (lines 1632-1634)

### Attempt 18 - Fix: Revert attempt 17 changes
- **Issue addressed:** Father absorbed into son (CRITICAL #1 from attempt 17)
- **Fix:** Removed lines 1631-1634. Restores attempt 16 stable extraction state.
- **Result:** **DID NOT RESTORE** — Son absorbed into father. LLM nondeterminism.
- **Modified:** `src/agents/characters.py` (removed lines 1631-1634)

### Attempt 19 - Fix: Universal split sibling merge protection
- **Issue addressed:** Son character absorbed despite attempt 12 safety check
- **Fix:** Added safety checks to ALL 5 merge passes in `_merge_within_main_cast()`
- **Result:** **NO EFFECT** — Son still absorbed. This PROVES absorption happens OUTSIDE `_merge_within_main_cast()`. The merge passes were never the problem.
- **Modified:** `src/agents/characters.py` (4 new safety checks in Passes 0,1,3,4)

### Attempt 20 - Fix: Disambiguation label guidance in Pass 2
- **Issue addressed:** Son character absorbed in Pass 2 consolidated alias resolution (CRITICAL #1)
- **Root cause:** `CONSOLIDATED_ALIAS_PROMPT` lacked guidance about characters with disambiguation labels in parentheses. LLM saw "John Donaldson (the father)" and "John Donaldson (the son)" and produced `merge_into` directive merging them, which was applied in `_process_consolidated_pass2()` BEFORE Step 1.6 split could run.
- **Fix:** Added explicit rule to Merge Rules section: "CRITICAL: Characters with disambiguation labels in parentheses are DIFFERENT people" with examples
- **Result:** **SUCCESS** — Both father AND son now exist as separate characters with 28 mentions each. NEW ISSUE: Son's profile is a copy of father's (profile contamination persists from attempt 14).
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` (line 197)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6) | No change — wrong data source |
| 3 | Red Cross organization | `supporting.py` | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` | Partial fix |
| 4 | Father/son conflation | `characters.py` (data source fix) | **REGRESSION** |
| 4 | Pronunciation false positives | `character_proposer.py` | Partial fix |
| 5 | Main cast regression | `characters.py` (remove Step 1.6) | Fixed |
| 6 | Father/son conflation | `characters.py` (re-enable Step 1.6) | DID NOT FIRE |
| 6 | Narrator flag | `characters.py` (fallback matching) | Partial fix |
| 7 | Father/son conflation | `summarizer.py` (upstream prompt) | Partial |
| 8 | Father/son conflation | `summarizer.py` + `characters.py` | Partial |
| 9 | Father/son conflation | `characters.py` (alias fallback) | DID NOT WORK |
| 10 | Father/son conflation | `characters.py:1421` (fix condition) | SUCCESS (but 0 mentions) |
| 11 | Split chars empty | `characters.py` (alias propagation) | Partial |
| 12 | Son re-merged | `characters.py` (merge protection) | Partial |
| 13 | Father missing | `characters.py` (alias partitioning) | NO EFFECT |
| 14 | Diagnostic logging | `characters.py` (6 logging blocks) | SUCCESS |
| 15 | Son profile contamination | `name_disambiguator.py` | REGRESSION |
| 16 | LLM nondeterminism | `characters.py` (3 defenses) | SUCCESS |
| 17 | Son profile contamination | `characters.py` (label aliases) | REGRESSION |
| 18 | Revert attempt 17 | `characters.py` (revert) | DID NOT RESTORE |
| 19 | Universal merge protection | `characters.py` (5 safety checks) | **NO EFFECT — proves absorption is OUTSIDE merge passes** |
| 20 | Disambiguation label guidance | `main_cast.py` (Pass 2 prompt) | **SUCCESS — both characters exist! Profile contamination persists.** |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved |
| 4 | 6.68 | +0.08 | REGRESSION: 0 main cast characters |
| 5 | 7.13 | +0.53 | Main cast restored |
| 6 | 7.33 | +0.73 | Narrator flag partially fixed |
| 7 | 7.33 | +0.73 | Summary disambiguation partial |
| 8 | 7.33 | +0.73 | Summary fix worked, regex mismatch |
| 9 | 7.08 | +0.48 | Alias fallback wrong condition |
| 10 | 7.25 | +0.65 | Father/son split success (0 mentions) |
| 11 | 6.85 | +0.25 | Father profiled, son re-merged |
| 12 | 6.10 | -0.50 | Merge protection, father missing |
| 13 | 5.93 | -0.67 | Alias partitioning no effect |
| 14 | 6.83 | +0.23 | Both chars exist! Son profile contaminated |
| 15 | 5.90 | -0.70 | REGRESSION: son absorbed, narrator lost |
| 16 | 7.28 | +0.68 | RECOVERY: LLM defenses worked |
| 17 | 6.33 | -0.27 | REGRESSION: father absorbed into son |
| 18 | 6.50 | -0.10 | Revert did not restore |
| 19 | 6.50 | -0.10 | Universal merge protection NO EFFECT |
| 20 | 6.95 | +0.35 | Both chars exist! Son profile contaminated |

## Next Action

**Phase:** awaiting_fix

**Priority focus for attempt 21:** Fix the son's profile contamination (CRITICAL #1). The passage gatherer/name disambiguator must correctly partition passages between father and son when both share the same name and aliases. The most promising approach is to use chapter-level `characters_present` data to pre-filter passages — the father only appears in Ch2 field hospital scenes, while the son appears across both chapters. Adding explicit split-label context to the profiling prompt for split characters would also help.

**Secondary:** Fix "John Donaldson's" spurious character (HIGH #2) — strip possessive markers from character names during extraction.
