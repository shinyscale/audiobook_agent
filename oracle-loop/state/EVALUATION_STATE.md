# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 17
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 8/10 (unchanged)
- Character Extraction: 7/10 ← REGRESSED from 8/10 in attempt 15
- Character Profiles: 7/10 (unchanged)
- Chapter Summaries: 9/10 (unchanged)
- Pronunciation Guide: 7/10 ← IMPROVED from 6/10
- HTML Presentation: 9/10 (unchanged)
- **Overall: 7.80/10** (threshold: 8.0)

## Score Calculation

```
Overall = (8 × 0.20) + (7 × 0.25) + (7 × 0.15) + (9 × 0.20) + (7 × 0.10) + (9 × 0.10)
        = 1.60 + 1.75 + 1.05 + 1.80 + 0.70 + 0.90
        = 7.80/10
```

## Evaluation Details

### Attempt 16 Results - PRONUNCIATION FIX WORKED BUT CHARACTER REGRESSION

**What Attempt 16 Fixed:**
1. ✅ **Project Gutenberg boilerplate stripped** - No more GutenbergTM, eBooks, PGLAF, MERCHANTABILITY in pronunciation
2. ✅ **Pronunciation count reduced** from 73 to 53 (cleaner list)
3. ✅ **All summaries remain excellent**

**What Attempt 16 Regressed:**
1. ❌ **Morris character split** - "Morris" (3 mentions) and "Sergeant-Major Morris" (1 mention) are separate entries, should be merged
2. ❌ **Missing aliases from attempt 15:**
   - Mr. White missing "the old man" alias
   - Herbert White missing "the son" alias
   - "the monkey's paw" character with aliases "the talisman", "the paw" is GONE entirely
3. ❌ **Character quality down** from 8/10 to 7/10

**Current Character List (6 characters):**
1. Mr. White (10 mentions) - NO aliases (had "the old man" in attempt 15)
2. Mrs. White (10 mentions) - NO aliases (expected)
3. Herbert White (14 mentions) with alias "Herbert" only (had "the son" in attempt 15)
4. Morris (3 mentions) - NO aliases ← SHOULD BE MERGED
5. Sergeant-Major Morris (1 mention) ← SHOULD BE MERGED WITH ABOVE
6. Stranger from Maw and Meggins (1 mention) - OK

**Missing from attempt 15:**
- "the monkey's paw" character (14 mentions) with aliases "the talisman", "the paw"

**Pronunciation Guide (53 entries):**
- ✅ Gutenberg terms eliminated
- ✅ Legitimate unusual words: fakirs, rubicund, Laburnam, antimacassar, condoling, bibulous
- Valid homographs present: live, minute, object, present, separate

## Current Issues (Priority Order)

### CRITICAL

1. **Character regression: Morris split and aliases lost**
   - Problem: This attempt regressed from attempt 15's character quality
   - Evidence:
     - Morris now split into two entries instead of one
     - "the old man" alias for Mr. White is gone
     - "the son" alias for Herbert is gone
     - "the monkey's paw" character entirely missing
   - Location: The V2 character extraction pipeline may have LLM variance or the Gutenberg stripping affected character context
   - Root cause: Likely LLM non-determinism in the summary-driven extraction, or the text change from removing boilerplate caused different results
   - Impact: -1 point (8→7), blocks passing

### HIGH

2. **Morris should be merged with Sergeant-Major Morris**
   - Problem: Same person listed twice
   - Evidence: "Morris" and "Sergeant-Major Morris" are the same character - the story introduces him as "Sergeant-Major Morris" then refers to him as just "Morris" throughout
   - Location: `src/pipeline/character_extraction_v2/` - alias resolution
   - Fix: The LLM consolidation should recognize "Morris" = "Sergeant-Major Morris"

### MEDIUM

3. **Chapter titles showing as "null"**
   - Problem: All three chapters have `title: null` instead of "Part I", "Part II", "Part III"
   - Location: `src/pipeline/chapter_detection/` - title extraction
   - Impact: Would improve Structure from 8 to 9

4. **Missing epithet aliases ("the old man", "the son")**
   - Problem: The F6 filter from attempt 15 added epithet aliases, but they're not present now
   - Evidence: Mr. White should have "the old man", Herbert should have "the son"
   - Location: May be LLM variance or the F6 filter didn't run
   - Impact: Polish, minor

## Root Cause Analysis

The regression appears to be due to **LLM non-determinism** in the V2 character extraction pipeline. Even with the same code, re-running the analysis produced different (worse) results:

| Aspect | Attempt 15 | Attempt 16 |
|--------|-----------|-----------|
| Characters | 6 | 6 |
| Morris entries | 1 (merged) | 2 (split) |
| Mr. White alias "the old man" | ✅ Present | ❌ Missing |
| Herbert alias "the son" | ✅ Present | ❌ Missing |
| "the monkey's paw" character | ✅ Present | ❌ Missing |
| Gutenberg terms in pron | ❌ Present | ✅ Gone |

**Possible causes:**
1. The Gutenberg text removal changed the input sufficiently that the LLM produced different results
2. The F6 epithet filter may have a bug or didn't execute
3. Temperature/sampling variance in the LLM

## Fix History

| Attempt | Fix | Score | Delta |
|---------|-----|-------|-------|
| 5 | First successful run | 6.275 | baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 | +0.775 |
| 10 | Case sensitivity fix | 7.05 | +0.775 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | 6.70 | Regression |
| 12 | Added ambiguity check to `_validate_merge()` in LLM path | 7.00 | +0.725 |
| 13 | Gender conflict detection in epithet resolution | 7.00 | Fix didn't execute |
| 14 | **V2 character extraction (summary-driven)** | **7.60** | **+1.325** |
| 15 | F6 epithet filtering + pronunciation stopwords | **7.95** | **+1.675** |
| 16 | Strip Project Gutenberg boilerplate | **7.80** | **Regression** |
| 17 | Deterministic title-variant merge (Morris fix) | **TBD** | **TBD** |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix |
| 11 | 6.70 | +0.425 | Regression |
| 12 | 7.00 | +0.725 | Partial fix |
| 13 | 7.00 | +0.725 | Cache issue |
| 14 | 7.60 | +1.325 | V2 working! |
| 15 | 7.95 | +1.675 | Nearly passing! |
| **16** | **7.80** | **+1.525** | **Pron fixed, chars regressed** |

## Path to 8.0

**Current: 7.80**
**Needed: +0.20 points**

The fix strategy needs to address the character regression while preserving the pronunciation improvement:

1. **Fix Morris split** (Character 7→8, +0.25 weighted) = 8.05 overall
   - Ensure "Morris" and "Sergeant-Major Morris" are merged as aliases
   - Either in the prompt or post-processing

2. **Alternative: Improve structure titles** (Structure 8→9, +0.20 weighted) = 8.00 overall
   - Detect "Part I", "Part II", "Part III" as chapter titles
   - Easier fix, less risky

**Recommended approach:** Fix the Morris split via deterministic post-processing (not LLM) to avoid further variance.

## Configuration Audit

- Model: qwen3-next:80b-a3b-instruct-q8_0 for character extraction
- V2 character extraction (summary-driven)
- LLM calls: 13 total (down from 30 in attempt 15)
- Character Extraction: 27.2s (efficient)
- Gutenberg removal: 19,050 chars (46.4%) removed successfully

## Notes for Attempt 17

**Fix Applied:** Added deterministic title-variant character merging in `src/agents/characters_v2.py`

**Root Cause:**
- **File:** `src/pipeline/character_extraction_v2/main_cast.py`
- **Function:** `MainCastExtractor.extract()` lines 94-145
- **Issue:** LLM non-determinism - different input (Gutenberg stripping changed summaries) caused different character extraction results
- **Confidence:** HIGH - same code, different input text

**Implementation:**
- Added `_merge_title_variants()` method in `CharacterAgentV2` (lines 363-425)
- Runs after step 1 (main cast extraction), before step 2 (mention search)
- Merges characters where one canonical name contains another as a word (e.g., "Sergeant-Major Morris" contains "Morris")
- Word-boundary aware to avoid false merges (e.g., "White" won't merge "Whitehouse")

**Smoke Test Results:** ✅ PASS
- Correctly merges "Sergeant-Major Morris" + "Morris" → 1 character with alias
- Correctly keeps "Mr. White", "Mrs. White", "Herbert White" separate (different first names)

**Full Test Suite:** ✅ PASS (193 passed, 3 skipped in 6.36s)

**Expected Impact:**
- Should fix Morris split (Character 7→8, +0.25 weighted = 8.05 overall)
- Will NOT restore missing aliases ("the old man", "the son") - those are LLM variance
- Will NOT restore "the monkey's paw" character - also LLM variance

## Analysis Results (Attempt 17)

**Output Files:**
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

**Pipeline Performance:**
- Total time: 11m 56s
- Total LLM calls: 25 (down from 27 in attempt 16)
- Total tokens: 50,662
- Bottleneck: Chapter Summaries (44.9% of time)

**Key Observations:**
- ✅ 7 characters extracted (6 in previous attempts + 1 from chapter summaries)
- ✅ "Sergeant-Major Morris" now appears as single character with "Morris" alias (MERGE FIX WORKED!)
- ✅ Mr. White has "the old man" alias restored
- ✅ Herbert White has "Herbert" and "the son" aliases restored
- ✅ "the stranger" character extracted
- ✅ "the monkey's paw" character present with 6 mentions
- ✅ Pronunciation guide: 55 entries (clean, no Gutenberg terms)
- ⚠️ Some LLM warnings: profile generation had issues for some characters ("No passages provided")

**Pipeline Warnings:**
- LLM identity detection failed (500 error from Ollama) - non-critical
- Low confidence profile for "the stranger" (0.30) - expected for minor character

**Next Step:** Evaluation phase to verify scores and check if Morris fix pushed us to 8.0+
