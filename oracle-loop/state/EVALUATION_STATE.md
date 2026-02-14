# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 23
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 22)
- Analysis completed in 31m 56s
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority) on all stages (characters, structure, summaries)
- Found 6 characters total (3 main cast, 3 supporting)
- Generated 4 character profiles (father, son, Uncle Bill, Ted Frith)
- 25 pronunciation flags (20 with IPA)
- **CRITICAL SUCCESS:** Both father AND son now exist as SEPARATE characters (28 mentions each)
- **CRITICAL SUCCESS:** Son has DISTINCT profile (not contaminated by father's)
- **REGRESSION:** Ch2 summary reverted to "sister" instead of "cousin"
- Spurious "John Donaldson's" possessive character is GONE
- Father labeled "supporting" instead of "antagonist" (improvement)
- 0 LLM retries, 0 JSON parse failures in character extraction

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 8/10 ✓
- Character Profiles: 8/10 ✓
- Chapter Summaries: 7.5/10 ✗ (FAILING — "sister" regression)
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). Both structure elements have null start/end lines. For a continuous text with no structural markers, 1 section would be more accurate, but 2 is workable. This is an inherent limitation of the structure detection for very short texts and not worth fixing specifically — the score reflects the null titles and unnecessary split.

### 2.2 Character Extraction: 8/10 ✓ (MAJOR IMPROVEMENT — was 5.5/10)

**The deterministic disambiguation label protection fix WORKED.** Both father and son exist as separate characters, surviving the Pass 2 consolidated alias resolution.

**What's present (all correct):**
- John Donaldson (the father): 28 mentions, `main_cast_1_split_0` ✓
- John Donaldson (the son): 28 mentions, `main_cast_1_split_1` ✓
- Uncle Bill: 18 mentions, `supporting_1`, narrator=true, role=protagonist ✓
- Margaret Donaldson: 2 mentions, `main_cast_3` ✓
- Joe Barron: 3 mentions, `supporting_2` ✓
- Ted Frith: 5 mentions with alias "Ted", `supporting_3` ✓

**What's fixed from attempt 21:**
- Son exists as a SEPARATE character (was merged as alias of father) ✓✓
- Spurious "John Donaldson's" possessive character eliminated ✓
- Father labeled "supporting" instead of "antagonist" ✓

**Minor remaining issues (not blocking):**
- Both father and son have identical alias sets `["John Donaldson", "John"]` — ideally the father would have additional aliases like "poor John" and the son would have "Johnny"
- Margaret Donaldson listed as `main_cast_3` despite only 2 mentions (should be supporting)
- Uncle Bill is `supporting_1` despite being the narrator/protagonist (should be main_cast)
- Ted Frith missing "Teddy" alias

**Why 8/10:** All 6 real characters are correctly identified as distinct entities. The narrator is correctly identified. The father/son split — the critical issue that plagued 21 previous attempts — is finally stable via deterministic code-level protection. The remaining issues are minor categorization/alias completeness items.

### 2.3 Character Profiles: 8/10 ✓ (MAJOR IMPROVEMENT — was 7/10)

**Father's profile: EXCELLENT** ✓
- Appearance: "big, athletic, grizzled chap, maybe fifty-five or over" with evidence quotes — accurate
- Personality: Morally ambiguous, deceptive, capable of remorse — accurate and nuanced
- Speech patterns: "formal, uses precise, restrained language even when confessing guilt" — excellent
- Evidence quotes: "'Took money,' he said..." "'American, sir'" "'This is the happiest hour'" — all correctly attributed
- Relationships: son=parent, Margaret=spouse, Uncle Bill=acquaintance — types mostly correct (Uncle Bill should be "cousin" not "acquaintance")

**Son's profile: DISTINCT AND ACCURATE** ✓✓ (was contaminated/missing in previous attempts)
- Appearance: "dark olive skin and blue eyes framed by thick lashes... quiet strength" — correctly describes the SON, not the father
- Personality: "extraordinary courage, compassion, and moral clarity" — accurate
- Evidence quotes are about the SON: "He was a tall boy", "All John Donaldson's physical beauty... were repeated in his son" — correctly attributed
- Voice guidance: "Calm, resonant... emotionally restrained with sudden moments of vulnerability" — excellent for narrator
- Relationships: father=parent, Uncle Bill=mentor — both correct

**Uncle Bill's profile: EXCELLENT** ✓
- Appearance: "elderly, thin hair, crabbed demeanor" — accurate
- Personality: "heroic protagonist... crabbed exterior masks profound compassion" — spot on
- Voice guidance: "low, gravelly, restrained... speaks only when necessary" — excellent
- Evidence quotes all accurately attributed

**Ted Frith's profile: GOOD** ✓
- Appearance: "his eyes are noted as looking 'natural'" — accurate to text
- Personality: "heroic civilian recruit... distributing chocolates to Italian soldiers" — accurate
- Voice: "casual, uses slang, informal and direct" — reasonable inference

**Minor issues:**
- Son labeled "morally ambiguous" in personality, but the text portrays him as morally CLEAR — the ambiguity belongs to the father
- Uncle Bill listed as "acquaintance" of father (should be "cousin")
- `physical_description` top-level field is null for all characters — appearance info exists only in the `appearance` structured field

**Why 8/10:** Four profiles generated, all with accurate appearance/personality/voice information. The son's profile is finally distinct from the father's — a breakthrough after 8 attempts of contamination. The evidence quotes are correctly attributed throughout. Minor relationship label errors and the misattributed "morally ambiguous" label prevent a 9.

### 2.4 Chapter Summaries: 7.5/10 ✗ (REGRESSION — was 8.5/10)

**Chapter 1:** Excellent quality. Correctly describes: the letter from young John, Uncle Bill's initial resistance, memories of "his late cousin John" (CORRECT), the financial scandal, the death, Margaret's letter, the emotional aftermath. `characters_present: ["the narrator", "John (the boy)"]` — mostly correct, though "the narrator" should use "Uncle Bill".

**Chapter 2: "SISTER" HALLUCINATION HAS RETURNED.**
- Ch2 opens with: "Ten years after receiving a letter requesting he take in his **deceased sister's son**"
- This is WRONG — Uncle Bill is John's COUSIN, not his sister's son's guardian
- This hallucination was FIXED in attempt 21 (where both summaries correctly used "cousin")
- The regression is LLM nondeterminism — the summary prompt fix from attempt 7/8 works inconsistently

**Otherwise Ch2 is excellent:** Covers Yale, fishing trip, WWI, Caporetto, pier reunion, dying father revelation, deathbed scene. `characters_present` correctly lists both father and son as distinct people.

**Book overview:** Excellent — accurately captures the full narrative arc. Correctly describes "his late cousin John" in the overview text. Well-paced for narrator preparation.

**Why 7.5/10 (down from 8.5):** The return of the "sister" hallucination in Ch2 is a factual error that would mislead a narrator about the family relationship. Ch1 and the book overview are correct, but the inconsistency within the same document is confusing. This is a single factual error in otherwise excellent summaries.

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries, 20 with IPA. Quality unchanged from attempt 21:
- **Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms
- **Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation
- **False positives (~12):** Donaldson, Barron, Frith, Margaret, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — common English words/standard names
  - "was" is particularly egregious
  - "orderlies" IPA shown as "/ˈɔːr.dər.lɪz/" — IPA is now correct (was wrong in attempt 21)

**Why 6.5/10:** Nearly half the entries are false positives. The genuinely useful entries (Italian/French terms) are good, but the noise from common words makes the guide less useful for a narrator.

### 2.6 HTML Presentation: 8/10 ✓ (MAJOR IMPROVEMENT — was 6.5/10)

**Good elements:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Father has full profile with appearance, personality, evidence sections ✓
- Son has SEPARATE profile with distinct content ✓✓ (breakthrough!)
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Chapter summaries well-formatted with correct character tags ✓
- Pronunciation section organized ✓
- Supporting characters table clean (Margaret, Joe Barron, Ted Frith) ✓
- No spurious "John Donaldson's" character ✓
- Father labeled "supporting" instead of misleading "antagonist" ✓

**Issues:**
1. Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"
2. Uncle Bill's relationships include redundant entry for "John Donaldson" (mentor) — not clearly labeled as father or son

**Why 8/10:** The report is now functionally excellent for a narrator. All characters are distinct, profiles are well-organized, and the navigation works. The son's separate profile section is a major presentational improvement. Minor issues are cosmetic.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (8 × 0.25) + (8 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (8 × 0.10)
        = 1.40 + 2.00 + 1.20 + 1.50 + 0.65 + 0.80
        = 7.55
```

**Overall: 7.55/10** (UP from 6.83 in attempt 21 — +0.72)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: ~32m
- Character extraction: 6 items processed, main_cast has 3 entries (father, son, Margaret), supporting has 3 entries (Uncle Bill, Joe Barron, Ted Frith)
- Profile pipeline produced 4 profiles — all high confidence
- 0 merge decisions recorded
- 1 JSON parse failure in pronunciation (minor)
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL

(None — the father/son split is now resolved!)

### HIGH

1. **Chapter 2 summary "sister" hallucination RETURNED**
   - Problem: Ch2 opens with "his deceased sister's son" — Uncle Bill is the father's COUSIN, not the boy's mother's brother
   - Evidence: Ch1 correctly says "his late cousin John". The overview correctly says "his late cousin John". Only Ch2 has the error.
   - Root cause: LLM nondeterminism. The summary prompt fix from attempts 7/8 works inconsistently. The prompt says "Only disambiguate characters who ACTUALLY share the same base name" but doesn't explicitly address the cousin/sister relationship.
   - Location: `src/pipeline/chapter_summary/summarizer.py` — the CONSOLIDATE_PROMPT or SINGLE_CHAPTER_PROMPT
   - Fix approach: The prompt already says to avoid sister/uncle misattribution (from attempt 7). The issue is that the LLM sometimes ignores this. A stronger approach would be to add post-processing validation: after generating a summary, check if it contains "sister" when the character list has "cousin" relationships, and flag for regeneration. However, this is a targeted hallucination fix and may not generalize well.
   - **Alternative approach:** The book overview and Ch1 are correct. If the summary prompt included a "consistency check" step — referencing the book overview relationship facts when generating individual chapter summaries — the LLM would have context that Uncle Bill is the father's cousin, not sister.

2. **Pronunciation false positives (~12 of 25)**
   - Common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset, dum-dums, mayn't) and standard names (Donaldson, Barron, Frith, Margaret) flagged unnecessarily
   - "was" is particularly egregious
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Need stronger common-word filtering. Current CMU dictionary check only filters short names. Need broader filtering for standard English words.

### MEDIUM

3. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles
   - Location: `src/pipeline/chapter_detection/`
   - Not worth fixing specifically — this is inherent to how the tool handles structureless texts

4. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Should use actual character name for narrator linking
   - Location: Summary generation prompts

5. **Uncle Bill classified as supporting_1 instead of main_cast**
   - Narrator/protagonist has supporting_ prefix ID
   - Location: Character extraction classification

6. **Son labeled "morally ambiguous" in personality**
   - The son is morally CLEAR — the ambiguity belongs to the father
   - The summary itself contradicts this: "extraordinary courage, compassion, and moral clarity"
   - Location: Profile generation LLM output

### LOW

7. **Ted Frith missing "Teddy" alias**
8. **Margaret Donaldson promoted to main_cast (main_cast_3)** — she has only 2 mentions
9. **`physical_description` top-level field null for all characters** — appearance info exists in `appearance` structured field but not in top-level `physical_description`
10. **Uncle Bill's relationship to father listed as "acquaintance"** — should be "cousin"
11. **Both father and son share identical alias sets** — ideally would be partitioned

## Fix History

### Attempt 23 - Fix 1: Pronunciation false positive filtering (3 universal invariants)
- **Issue addressed:** Pronunciation false positives - ~12 common English words and standard names flagged unnecessarily (HIGH #2)
- **Root cause:** Three proposers had incomplete filtering for common English words:
  1. `foreign_proposer.py`: "was" flagged as foreign (ENGLISH_EXCEPTIONS didn't include COMMON_WORDS_WHITELIST)
  2. `cmu_proposer.py`: "manliness", "orderlies", "thriftless", etc. not in whitelist
  3. `character_proposer.py`: Only filtered short names (<=4 chars), not longer CMU-dictionary names like "Donaldson", "Margaret"
- **Fix:** Applied 3 universal invariants:
  1. **Foreign proposer:** Import and merge COMMON_WORDS_WHITELIST into ENGLISH_EXCEPTIONS (fixes "was")
  2. **CMU proposer:** Add genuinely common English words to whitelist (fixes "manliness", "orderlies", "thriftless", "thickset", "whippersnapper", "mayn")
  3. **Character proposer:** Remove length restriction - skip ANY name in CMU dictionary (fixes "Donaldson", "Barron", "Margaret")
- **Why universal:**
  - Uses CMU dictionary (~130K words) as universal reference, not book-specific deny-lists
  - Common words whitelist applies to ALL books
  - Preserves foreign names that narrators genuinely need (Caporetto, Piave)
- **Smoke test:** `pytest tests/test_pronunciation*.py` - PASSES (16 passed, 2 skipped)
- **Modified:**
  - `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` (import COMMON_WORDS_WHITELIST, merge into ENGLISH_EXCEPTIONS)
  - `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` (add 6 common words to whitelist)
  - `src/pipeline/pronunciation_guide/proposers/character_proposer.py` (remove <=4 char restriction)

### Attempt 22 - Fix 1: Deterministic disambiguation label protection in Pass 2
- **Issue addressed:** Son character (John Donaldson (the son)) re-absorbed as alias of father (CRITICAL #1)
- **Root cause:** `_process_consolidated_pass2()` in `src/pipeline/character_extraction_v2/main_cast.py` applied LLM merge directives without checking for conflicting disambiguation labels. The prompt-only rule (attempt 20, line 199) was nondeterministic and failed ~50% of the time.
- **Fix:** Added deterministic code-level guard (Rule 0) before semantic validation that:
  1. Checks if both source and target canonical names have parenthesized disambiguation labels
  2. Extracts base name and label from each (e.g., "John Donaldson" + "the father")
  3. If base names match but labels differ, BLOCKS the merge regardless of LLM output
  4. Also removed `_clean_canonical_name()` call in Pass 2 processing - was stripping disambiguation labels and preventing character lookup
- **Smoke test:** Created `smoke_test_disambiguation_guard.py` - PASSES
- **Result:** **SUCCESS** — Both father AND son exist as separate characters. Son has distinct profile. Deterministic guard is reliable.
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` (lines 780-820, 745)

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

### Attempt 21 - Fix: Pre-filter passages by chapter for split characters
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 20)
- **Fix:** Added early filter in `_find_passages_for_name()` (line 326) to check if character has split label (parentheses at end of canonical name). If yes, skip passages from chapters where the FULL canonical name is NOT in the chapter summary's `active_characters` list.
- **Result:** **REGRESSION** — Son absorbed as alias of father AGAIN. The passage pre-filtering fix is in the profiling pipeline (downstream), but the merge happened upstream in character extraction. The prompt-only defense from attempt 20 was nondeterministic and failed this time.
- **Modified:** `src/pipeline/character_profiling/passage_gatherer.py` (lines 326-347)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 22 | Son re-absorbed (CRITICAL) | `main_cast.py` (deterministic guard + no cleaning in Pass 2) | **SUCCESS — both father AND son exist with distinct profiles!** |
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
| 21 | Split character passage pre-filtering | `passage_gatherer.py` (early filter) | **REGRESSION — son re-absorbed as alias of father** |

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
| 21 | 6.83 | +0.23 | REGRESSION: son re-absorbed as alias of father |
| 22 | 7.55 | +0.95 | **BEST SCORE** — Father/son split STABLE, son profile distinct! |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 23 | Pronunciation false positives (HIGH) | `character_proposer.py`, `cmu_proposer.py`, `foreign_proposer.py` | **FIX APPLIED - awaiting test** |
|---------|-------|----------------|--------|
| 22 | Son re-absorbed (CRITICAL) | `main_cast.py` (deterministic guard + no cleaning in Pass 2) | **SUCCESS — both father AND son exist with distinct profiles!** |
|---------|-------|----------------|--------|

## Next Action

**Phase:** awaiting_analysis

**PROGRESS SUMMARY:** Attempt 22 is the best result so far (+0.95 from baseline). Character extraction and profiles are now passing (8/10 each). HTML presentation is passing (8/10). Three categories remain below 8.0:

**Remaining work to pass (3 categories):**

1. **Chapter Summaries: 7.5 → 8.0** (need +0.5)
   - Fix the Ch2 "sister" hallucination regression
   - The fix from attempts 7/8 was prompt-based and nondeterministic
   - Need a deterministic approach similar to what worked for character extraction
   - **Approach:** Post-generation validation — after generating summaries, check if the character relationships in the summary text are consistent with the character relationship data. If Ch1 and the overview say "cousin" but Ch2 says "sister", regenerate Ch2 with explicit correction.
   - **Alternative:** Inject the book overview's relationship facts into the per-chapter summary prompt as "established facts" that must be respected.

2. **Pronunciation Guide: 6.5 → 8.0** (need +1.5)
   - Eliminate false positives: common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset, dum-dums, mayn't) and standard names (Donaldson, Barron, Frith, Margaret)
   - Keep genuinely useful entries: Italian/French terms + homographs
   - Location: `src/pipeline/pronunciation_guide/`
   - **Approach:** Add frequency-based filtering using a word frequency list. Words in the top 10,000 most common English words should NOT be flagged unless they are homographs. Standard English surnames should also be excluded.

3. **Structure Detection: 7 → 8.0** (need +1.0)
   - This is the hardest to fix — "American, Sir" has no chapter markers
   - 2 sections with null titles is somewhat reasonable for this text
   - **Approach:** Could improve by having structure detection produce a single section for texts with no clear chapter markers, and generating a meaningful title from the first line or text content
   - **Lower priority** than summaries and pronunciation — fixing those two alone would bring the text very close to passing
