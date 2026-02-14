# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 19
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 19)
- Analysis completed in 33m 7s
- 5 characters extracted: father, Margaret Donaldson, Uncle Bill, Joe Barron, Ted Frith
- **Son character (`main_cast_1_split_1`) STILL MISSING** — universal merge protection did not help
- Father (`main_cast_1_split_0`) has 56 mentions (combined father+son ~28+28)
- Father's aliases include "John Donaldson (the son)" — absorption confirmed
- `pipeline_metadata.main_cast_count: 3` (up from 2 in attempt 18) — Margaret now main_cast, but son still absent
- Margaret Donaldson: 2 mentions (RESTORED — was missing in attempt 18) ✓
- Uncle Bill: 17 mentions, correctly identified as first-person narrator ✓
- 2 chapters detected (unchanged)
- 25 pronunciation flags (20 with IPA)
- Total LLM calls: 81
- Total tokens: ~114K

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 6.5/10 ✗
- **Overall: 6.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (all 6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). Both structure elements have null start/end lines. For a continuous text with no structural markers, 1 section would be more accurate, but 2 is workable.

### 2.2 Character Extraction: 5/10 ✗ (UNCHANGED from attempt 18)

**CRITICAL: Son character still absorbed into father despite universal merge protection.**

The attempt 19 fix added split sibling safety checks to ALL 5 merge passes in `_merge_within_main_cast()`. However, the son is STILL missing, which means **the absorption is NOT happening in `_merge_within_main_cast()`**. The safety checks are guarding the wrong location.

**Evidence:**
1. `main_cast_1_split_0` (father) exists with 56 mentions — combined father+son
2. No `main_cast_1_split_1` (son) in output
3. Father's aliases include "John Donaldson (the son)" — son absorbed as alias
4. `pipeline_metadata.main_cast_count: 3` — the main cast pipeline extracted 3 characters (father, Margaret, and presumably son), but only 2 main cast entries survive in final output
5. 0 merge decisions recorded — absorption is NOT going through the merge tracking system

**KEY INSIGHT FROM THIS ATTEMPT:** The universal merge protection in `_merge_within_main_cast()` did NOT fix the issue. This conclusively proves the absorption happens ELSEWHERE in the pipeline — NOT in the merge passes. Candidate absorption points that must be investigated:
- **Consolidated alias resolution (Pass 2)** in `main_cast.py` — `_process_consolidated_pass2()` may merge son into father via `merge_into` directives
- **Post-split alias cleanup** — some step may re-add "John Donaldson (the son)" as an alias of the father
- **F6 reconciliation** — although no hash IDs are present, reconciliation logic could be merging
- **Grounding/filtering** — son may be filtered as ungrounded if mention count drops to 0

**What's correct:**
- Uncle Bill correctly identified as narrator with protagonist role ✓
- Joe Barron (3 mentions) ✓
- Ted Frith with alias "Ted" (5 mentions) ✓
- Margaret Donaldson restored (2 mentions) ✓
- Father's canonical name uses "(the father)" disambiguation ✓

### 2.3 Character Profiles: 7/10 ✗

Profiles remain high quality for characters that exist. Both father and Uncle Bill have rich structured profiles with appearance, personality, voice_guidance, and evidence quotes.

**Father profile: CORRECT and RICH** ✓
- Appearance: "big, athletic, grizzled chap", "fifty-five or over", "very dark skin", "unmistakable blue eyes" — all accurate
- Personality: "morally ambiguous man who committed theft and deception... found redemption through selfless service" — accurate
- Voice: "worn thin by time and guilt—low, deliberate, and quiet" — excellent narrator guidance
- Example quotes: correctly attributed to the father

**Uncle Bill profile: CORRECT and RICH** ✓
- Appearance: "elderly man of quiet, unassuming presence" — accurate
- Personality: "stoic, initially reluctant guardian" — excellent
- Voice: "low, measured, gravelly baritone" — great narrator guidance

**Issues:**
1. Father's relationship to Uncle Bill listed as "acquaintance" — INACCURATE. They were cousins. Text says "my cousin John". "ally" or "cousin" would be more accurate.
2. Uncle Bill's relationship to father listed as "ally" — inconsistent with father's listing of "acquaintance". Both should say "cousin".
3. No profile for the son (because he doesn't exist as a character) — CRITICAL gap
4. No profile for Margaret Donaldson (only 2 mentions, so reasonable she's below profile threshold)

**Why 7/10:** The profiles that DO exist are genuinely high quality with accurate evidence, useful voice guidance, and good narrator preparation. But the missing son profile is a significant gap.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** Good quality. Captures the letter from John, Uncle Bill's initial anger, memories of his bond with John's father, the financial scandal, the death, and Margaret's letter. `characters_present: ["the narrator", "John (the son)"]` — correctly identifies narrator and the boy.

**Chapter 2:** Comprehensive and well-structured. Covers taking in the boy, pier meeting, WWI service, Caporetto encounter, deathbed confession, redemption. `characters_present` correctly lists Uncle Bill, son, and father as disambiguated names.

**Book overview:** Excellent — accurately captures the full narrative arc, themes of identity/loss/redemption, first-person retrospective structure.

**PERSISTENT factual error (19th consecutive attempt):** Ch2 says "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "my cousin John". This is a deeply persistent LLM hallucination.

**Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"** — should use actual character name for narrator linking.

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries, 20 with IPA. Quality breakdown:
- **Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms a narrator needs
- **Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation
- **False positives (~12):** Donaldson, Barron, Frith, Margaret, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — common English words/standard names
  - "was" is particularly egregious — the most common English word
  - "Margaret" is a standard English name — no pronunciation help needed
  - "orderlies" IPA shown as "/ˈɔːr.dər.laɪz/" which is wrong — should be "/ˈɔːr.dər.liz/"

### 2.6 HTML Presentation: 6.5/10 ✗

**Issues:**
- Son character completely missing from character list — only father and Uncle Bill as "Main Characters"
- Father's alias list shows "John Donaldson (the son)" — actively misleading for a narrator
- Father's relationships section lists "John Donaldson (the son): parent" which is confusing when the son doesn't exist as a separate character
- Margaret Donaldson appears in "Main Characters" section (promoted from supporting) — reasonable

**What works well:**
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Character profiles beautifully rendered with appearance, personality, voice guidance sections ✓
- Ted Frith and Joe Barron in supporting characters table ✓
- Chapter summaries well-formatted with character tags ✓
- Pronunciation section organized ✓

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (6.5 × 0.10)
        = 1.40 + 1.25 + 1.05 + 1.50 + 0.65 + 0.65
        = 6.50
```

**Overall: 6.50/10** (at baseline of 6.60 — effectively flat, within noise)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: ~33m
- Character extraction: 6 items processed, main_cast_count=3, supporting_cast_count=3
- Only 2 main cast characters in final output despite main_cast_count=3 — son absorbed
- 0 merge decisions recorded — absorption happened outside merge tracking
- 1 JSON parse failure in Character Extraction stage (not blocking)
- Profile pipeline produced 3 profiles (items_processed=3) — father, Uncle Bill, and one supporting character
- No config changes recommended at this time — the bottleneck is pipeline logic, not model/config

## Current Issues (Priority Order)

### CRITICAL

1. **Son character (`split_1`) absorbed into father — absorption NOT in `_merge_within_main_cast()`**
   - Problem: Son is completely missing from output. Father has 56 mentions (combined) and "John Donaldson (the son)" as alias.
   - Evidence: Attempt 19 added safety checks to ALL 5 merge passes. Son STILL absorbed. 0 merge decisions recorded. This CONCLUSIVELY PROVES the absorption happens OUTSIDE `_merge_within_main_cast()`.
   - **Root cause hypothesis:** The absorption most likely occurs in one of these locations:
     1. **`_process_consolidated_pass2()` in `main_cast.py`** — The consolidated alias resolution may produce a `merge_into` directive merging the son into the father BEFORE the characters even reach `characters.py`. If the LLM's Pass 2 output says "John Donaldson (the son)" should `merge_into` "John Donaldson (the father)", the son would be absorbed at the main_cast extraction level.
     2. **The split step itself** — `_split_disambiguated_same_name_characters()` may be creating only one child this run (LLM nondeterminism in `characters_present` affecting which labels are found).
     3. **Grounding/mention filtering** — If the son gets 0 text mentions after the split (all mentions assigned to father), the son could be filtered as ungrounded.
   - **FIX APPROACH:** The diagnostic strategy must shift. Instead of adding more protections to `_merge_within_main_cast()`, the fix must:
     1. **Add logging BEFORE and AFTER `_process_consolidated_pass2()`** to see if the son exists as a separate character at that stage
     2. **Add logging BEFORE and AFTER `_split_disambiguated_same_name_characters()`** to see if the split actually creates 2 children
     3. **Add logging at the grounding step** to see if the son is filtered
     4. Once the absorption point is identified, add a HARD BLOCK there
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (consolidated pass 2) AND `src/agents/characters.py` (split + grounding)

### HIGH

2. **Chapter 2 summary factual error: "sister" instead of "cousin" (19th consecutive attempt)**
   - Problem: "his deceased sister's son" — should be "his cousin's son" or "his cousin"
   - Evidence: The text says "my cousin John" — Uncle Bill and John Sr. are cousins, not siblings
   - Location: Summary generation LLM — persistent hallucination across 19 runs
   - Fix: Add post-processing text correction pass to summaries that checks relationship terms against the source text, OR add explicit guidance in summary prompt

3. **Father's relationship to Uncle Bill inconsistent**
   - Problem: Father lists Uncle Bill as "acquaintance"; Uncle Bill lists father as "ally". Neither is accurate — they are cousins.
   - Evidence: Text says "my cousin John"
   - Location: `src/pipeline/character_profiling/` — relationship extraction
   - Fix: May improve when son is properly separated (less noise in father's profile passages)

### MEDIUM

4. **Pronunciation false positives (~12 of 25)**
   - Common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset, dum-dums) and standard names (Donaldson, Barron, Frith, Margaret) flagged unnecessarily
   - "was" is particularly egregious
   - "orderlies" IPA is incorrect (/ˈɔːr.dər.laɪz/ → should be /ˈɔːr.dər.liz/)
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve common-word filtering; extend CMU dictionary check to longer standard names

5. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles and null start/end lines
   - Location: `src/pipeline/chapter_detection/`

6. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Should use the character's actual name for narrator linking
   - Location: Summary prompt or post-processing

### LOW

7. **Ted Frith still missing "Teddy" alias** — text uses "Teddy" once or twice
8. **Margaret Donaldson promoted to main_cast** — she has only 2 mentions. Supporting would be more accurate.

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

## Next Action

**CRITICAL DIAGNOSTIC PIVOT:** After 19 attempts and 19 fixes to `characters.py`, the absorption has been CONCLUSIVELY proven to NOT be in `_merge_within_main_cast()`. The fix phase must now look UPSTREAM:

1. **TRACE `_process_consolidated_pass2()` in `main_cast.py`** — Add logging to see if the consolidated alias resolution (Pass 2) produces a `merge_into` directive that merges the son into the father before the characters ever reach `characters.py`. This is the most likely absorption point because:
   - The LLM in Pass 2 sees both "John Donaldson (the father)" and "John Donaldson (the son)" and may decide they should be merged
   - The `merge_into` mechanism is designed to absorb duplicates — if the LLM treats father/son as duplicates, one gets absorbed

2. **TRACE `_split_disambiguated_same_name_characters()` output** — Verify the split actually creates 2 children this run. If it only creates 1, the absorption is at the split level.

3. **TRACE grounding step** — Check if the son is filtered as ungrounded after the split.

4. **Once absorption point is found, add a split-sibling hard block AT THAT LOCATION** — not in `_merge_within_main_cast()` where we've already proven it's ineffective.
