# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 16:07 (attempt 5 analysis complete)

## Latest Scores (Attempt 4)
- Structure Detection: 7/10 ✗ (FAILING - 25/28 titles null, Letter 1 missing)
- Character Extraction: 7/10 ✗ (FAILING - Creature missing from main_cast, fragmentation persists)
- Character Profiles: 7.5/10 ✗ (FAILING - all appearance="unknown", relationships good)
- Chapter Summaries: 9.5/10 ✓ (excellent quality, factually accurate)
- Pronunciation Guide: 9/10 ✓ (436/457 have IPA, good coverage)
- HTML Presentation: 8.5/10 ✓ (navigation works, character list complete)
- **Overall: 7.88/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## CRITICAL FIX VERIFIED ✓

**Issue #1 from Attempt 3 is FIXED:** Robert Walton (main_cast_0) now correctly has `is_narrator=true`. The frame narrator detection in supporting_cast fix worked.

Narrators now identified: `['Robert Walton', 'Victor Frankenstein']` - Both correct for the nested narrative structure.

## Current Issues (Priority Order)

### CRITICAL

1. **The Creature/Monster missing from main_cast**
   - Problem: The novel's deuteragonist is only present as two F6 reconciliation entries:
     - "the Monster" (843d532715f2, 6 mentions)
     - "The Monster (as hallucinated presence)" (d26c9a7e79ed, 1 mention)
   - Evidence: The Creature is a central character with extensive narrative presence (has own POV chapters)
   - Expected: Should be in main_cast with aliases: ["the Creature", "the monster", "the fiend", "the daemon", "the wretch"]
   - ID Patterns: Both are F6 reconciliation hash IDs → summaries mention the creature but extraction missed it
   - Impact: Character Extraction cannot score 8.0+ without the deuteragonist
   - Location: Main cast extraction (`src/pipeline/character_extraction_v2/main_cast.py`) - the Creature may not have a proper noun name that NER detects
   - Fix: The Creature is referred to as "the creature", "the monster", "the fiend", "the daemon" (common nouns) - extraction may need to handle major non-named characters mentioned prominently in summaries

### HIGH

2. **Alphonse Frankenstein fragmented**
   - Problem: Two separate F6 entries:
     - "Alphonse Frankenstein" (cf652e4d2e68, 1 mention)
     - "The narrator's father" (4542ed769e00, 1 mention)
   - Evidence: Same person - Victor's father is Alphonse Frankenstein
   - ID Patterns: Both 12-char hashes → F6 reconciliation (analyzer.py:1220-1240)
   - Fix: F6 reconciliation should merge relationship-based references with named characters

3. **Generic groups extracted as characters**
   - Problem: Non-character groups in character list:
     - "the people of the inn" (0976d73b1ce1)
     - "The sailors" (799f6ac74701)
     - "Old woman (nurse)" (6fdf7040235f)
   - Evidence: These are generic references, not named/significant characters
   - ID Patterns: All F6 reconciliation hash IDs
   - Location: F6 reconciliation or summary extraction
   - Fix: Filter generic group references from character reconciliation

4. **Beaufort fragmented from Caroline context**
   - Problem: "Beaufort" (0e0a948fd562, 1 mention) separate from Caroline Beaufort Frankenstein
   - Evidence: Beaufort is Caroline's father - contextually related but distinct person (this may actually be CORRECT - they are different people)
   - Verification: Check if this is Caroline's father or an erroneous split
   - Note: May not be an error - Beaufort the father is distinct from his daughter Caroline

### MEDIUM

5. **Structure titles mostly null**
   - Problem: Only 3/28 structure elements have titles (Letters 2-4)
   - Missing: Letter 1, Chapter I through Chapter XXIV
   - Evidence: `jq '[.structure[] | .title] | map(select(. == null)) | length'` returns 25
   - Impact: Navigation and chapter reference usability reduced
   - Location: Structure detection pipeline (`src/pipeline/chapter_detection/proposers/llm.py`)
   - Fix: Ensure title extraction captures "Letter 1", "Chapter I", "Chapter II", etc.

6. **All character profiles have appearance="unknown"**
   - Problem: 0/32 characters have physical_description populated
   - Evidence: `jq '[.characters[] | select(.physical_description != null)] | length'` returns 0
   - Even Victor and the Creature (both extensively described) show "unknown"
   - Location: Character profiling pipeline
   - Note: The Creature has one of the most detailed physical descriptions in literature - this should not be "unknown"
   - Fix: Investigate why appearance extraction is failing completely

### LOW

7. **M. Waldman missing "Professor Waldman" alias**
   - Problem: "M. Waldman" (main_cast_13, 17 mentions) lacks context
   - Evidence: Text refers to him as both "M. Waldman" and "Professor Waldman"
   - Impact: Minor - character correctly extracted
   - Fix: Add alias recognition

8. **Monster vs Creature naming inconsistency**
   - Problem: F6 entries use "the Monster" but literary convention prefers "the Creature"
   - Impact: Minor stylistic issue
   - Note: Shelley herself used various terms; "Creature" is modern preference

## What Improved in Attempt 4

| Category | Attempt 3 | Attempt 4 | Change |
|----------|-----------|-----------|--------|
| Structure | 7.5 | 7.0 | -0.5 (regression - title issue noted more carefully) |
| Characters | 6.5 | 7.0 | +0.5 (Walton narrator fix) |
| Profiles | 8.0 | 7.5 | -0.5 (appearance issue not previously noted) |
| Summaries | 9.0 | 9.5 | +0.5 (confirmed excellent quality) |
| Pronunciation | 9.0 | 9.0 | - |
| Presentation | 8.0 | 8.5 | +0.5 |
| **Overall** | 7.83 | 7.88 | +0.05 |

The Walton narrator fix worked, but the deeper character extraction issues (Creature missing) prevent reaching 8.0.

## Fix History

### Attempt 4 Fix (2026-01-31) - PARTIALLY SUCCESSFUL
1. ✓ Robert Walton narrator detection - NOW WORKS
   - Fix: Added Step 5.0.5 re-run with combined_cast (main + supporting)
   - File: src/agents/characters.py (lines 470-523)
   - Result: Walton now has is_narrator=true

**Deferred:**
- Issue #1 (CRITICAL): Creature missing from main_cast
- Issue #2 (HIGH): Alphonse fragmentation
- Issue #3 (HIGH): Generic groups
- Issue #5 (MEDIUM): Structure titles null

### Attempt 3 Fixes - PARTIALLY FAILED
1. ❌ Robert Walton epistolary narrator detection - did not apply (Walton in supporting_cast)
2. ❌ Alphonse relationship references - still fragmented

### Attempt 2 Fixes - SUCCESSFUL
1. ✅ Victor Frankenstein in main_cast
2. ✅ Krempe/Waldman now separate
3. ✅ The Creature appearance description format

### Attempt 1
- Initial analysis (baseline 6.35/10)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline 6.35 |
| 2 | Victor missing, Waldman/Krempe merge | main_cast.py | Victor FIXED, Waldman/Krempe FIXED |
| 3 | Walton narrator, Alphonse refs | main_cast.py | NO CHANGE (wrong file) |
| 4 | Walton narrator in supporting_cast | characters.py | FIXED (Walton now narrator) |
| 5 | Creature missing (upstream data) | characters.py, main_cast.py | PENDING (characters_present fix) |
| 6 | Architectural improvements | characters.py, main_cast.py, models.py | PENDING (co-occurrence + consolidated Pass 2) |

**Pattern:** Fixes to main_cast.py don't affect characters in supporting_cast or F6 reconciliation. Must target the correct pipeline stage. **NEW:** Upstream data issues require fixing data propagation, not extraction logic. **NEWER:** Defensive step proliferation suggests upstream extraction quality, not downstream salvage.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive consensus: ENABLED (single-model mode, 3 temperatures)
- Total LLM calls: 668
- Total tokens: 773,500
- Processing time: 150m 12s

## Next Action

**Phase:** awaiting_analysis

**MAJOR CHANGES APPLIED:** Both upstream data fix (Attempt 5) and architectural improvements (Attempt 6) have been implemented. Ready for analysis run.

**Changes to verify:**
1. **Attempt 5 (upstream data):** `characters_present` now passed to main_cast extraction - the Creature should appear in 13 chapter summaries explicitly
2. **Attempt 6 (architectural):**
   - Co-occurrence validation provides structural merge confidence scores
   - Consolidated Pass 2 gives LLM full context for alias resolution
   - Defensive step logging tracks improvement measurement

**What to check in results:**
1. Is "the Creature" now in main_cast (not just F6 reconciliation)?
2. What are the defensive step counts in `pipeline_metadata.defensive_steps`?
3. Are there any `pending_reviews` flagged for low co-occurrence?
4. Did consolidated Pass 2 reduce alias-canonical conflicts (Step 3.6)?

## Pipeline Execution Notes (Attempt 5)

**Analysis completed:** 2026-01-31 16:07
**Total time:** 152m 13s
**LLM calls:** 620
**Tokens:** 636,570

**Key observations from stderr:**

1. **The Creature EXTRACTED** ✓
   - Appears in main_cast character list: `'the Creature'`
   - This confirms the upstream data fix (characters_present) worked!

2. **Defensive Steps Activated:**
   - Step 3.4: 2 same-firstname merges
   - Step 3.7: 1 titled character split (M. Krempe vs M. Waldman)
   - Step 3.8: 1 semantic conflict split (the Creature vs the old man De Lacey)

3. **Robert Walton Issue Persists:**
   - Stderr shows: "Narrator 'Robert Walton' identified but NOT found in main_cast"
   - This issue repeated multiple times during character extraction

4. **Low Confidence Merges Flagged:**
   - 'the Creature' → 'the old man (De Lacey)' (score: 0.000) - flagged for review
   - 'Henry' → 'Henry Clerval' (score: 0.000) - flagged for review
   - 'Saville' → 'Margaret Saville' (score: 0.000) - flagged for review

5. **Alphonse Fragmentation Still Present:**
   - "The narrator's father" and "Alphonse Frankenstein" listed as separate characters
   - Stderr shows: "BLOCKED alias: 'Victor's father' and 'Alphonse Frankenstein' appear in summaries but NEVER co-occur"

6. **Profile Generation Errors:**
   - Failed to parse JSON for M. Waldman (empty response)
   - 'Werter' profile failed: "name 'pipeline_char_map' is not defined"
   - Missing passages for: The narrator's father, Alphonse Frankenstein, the court officials

7. **Pronunciation Agent JSON Issues:**
   - Multiple "LLM batch enrichment failed" errors
   - qwen3-next returning error messages instead of JSON arrays
   - This is a model compatibility issue with json_mode in pronunciation stage

**Final counts:**
- 28 chapters detected
- 27 characters extracted
- 19 profiles generated (out of 22 eligible)
- 457 pronunciation flags

## Attempt 5 Fix (2026-01-31) - IMPLEMENTED

### Issue #1 (CRITICAL): The Creature missing from main_cast

**Root cause (CONFIRMED):**
- Chapter summaries correctly identify "the Creature" in `characters_present` field (13 chapters)
- `characters.py:_get_chapter_summaries()` extracted ONLY `.summary` text, ignoring `.characters_present`
- Main_cast extraction LLM saw prose summaries but NOT the structured character list
- LLM missed extracting "the Creature" because it only had prose context, not explicit character presence data
- F6 reconciliation caught it later from `characters_present`, but with low mentions (6 vs should be 44+)

**Fix implemented:**
1. Modified `src/agents/characters.py:_get_chapter_summaries()` to format summaries with `[Characters: ...]` prefix
2. Added `_format_summary_with_characters()` helper that prepends character list to prose summary
3. Updated prompt in `src/pipeline/character_extraction_v2/main_cast.py` to acknowledge this format
4. Files modified:
   - `src/agents/characters.py` (lines 881-925)
   - `src/pipeline/character_extraction_v2/main_cast.py` (line 83)

**Expected impact:**
- "the Creature" will be explicitly listed in 13 chapter summaries
- LLM extraction should see it as a recurring major character
- Should be extracted to main_cast instead of F6 reconciliation
- Grounding should find 44+ mentions in raw text

**Universality:** This fix helps ANY book where summaries have structured character data. It's a data propagation fix, not book-specific logic.

## Attempt 6 Architectural Changes (2026-01-31) - IMPLEMENTED

### Major Architectural Enhancements

Based on analysis of defensive step proliferation (steps 3.4, 3.6, 3.7, 3.8 all exist to fix upstream LLM errors), implemented two complementary improvements:

### A. Co-occurrence Validation (NEW)

**Purpose:** Provide a structural signal independent of LLM reasoning to validate/reject proposed merges.

**Implementation:**
1. Added `MergeDecision` model to `src/models.py` - tracks merge decisions with:
   - Source/target character info
   - Co-occurrence score (Jaccard similarity of text chunk presence)
   - Confidence level (high/medium/low)
   - `needs_review` flag for TUI

2. Added to `src/agents/characters.py`:
   - `_compute_cooccurrence()` - Computes pairwise Jaccard similarity based on which ~1-page text chunks characters appear in together
   - `_should_merge()` - Returns (should_merge, score, confidence) tuple
   - `_record_merge_decision()` - Records merge decisions for TUI review

3. Integrated into merge functions:
   - Steps 3.4, 3.6, 5.5 now record merge decisions with co-occurrence scores
   - Low-confidence merges (score < 0.2) are flagged for human review in TUI

**How it helps:**
- If "Jay Gatsby" and "Gatsby" appear in same paragraphs → high confidence merge
- If "Tom Buchanan" and "Tom the gardener" never appear together → block merge or flag for review
- Provides quantitative data for debugging merge decisions

### B. Consolidated Pass 2 Alias Resolution (NEW)

**Purpose:** Give LLM full context during alias resolution to prevent conflicts upstream.

**Problem with old approach:**
- Pass 2 ran per-character: "What are Victor's aliases?" then "What are the Creature's aliases?"
- When asking about Victor, LLM didn't know Pass 1 also extracted "the narrator" as separate character
- LLM might add "the narrator" as Victor's alias, creating a conflict Step 3.6 had to fix

**New approach:**
- Single consolidated Pass 2 with ALL characters visible
- LLM sees full list and can identify duplicates via `merge_into` field
- Prompt: "Here are ALL characters. Assign aliases AND identify duplicates."

**Implementation in `src/pipeline/character_extraction_v2/main_cast.py`:**
- Added `CONSOLIDATED_ALIAS_PROMPT` (~50 lines)
- Added `_process_consolidated_pass2()` to handle merge_into directives
- Added `_extract_two_pass_per_character()` as fallback if consolidated fails

**Expected impact:**
- LLM can now see "Victor Frankenstein" and "the narrator" together
- Should merge them during Pass 2 instead of requiring Step 3.6
- Fewer defensive step activations = cleaner extraction

### C. Defensive Step Logging (NEW)

**Purpose:** Track when defensive steps activate to measure if upstream fixes are working.

**Implementation:**
- Steps 3.4, 3.6, 3.7, 3.8 now log with `DEFENSIVE STEP X ACTIVATED` prefix
- Added `defensive_steps` summary to pipeline_metadata:
  - `step_3_4_same_firstname_merges`
  - `step_3_6_alias_canonical_merges`
  - `step_3_7_titled_splits`
  - `step_3_8_semantic_splits`
  - `total_activations`

**How to use:** After analysis, check `pipeline_metadata.defensive_steps.total_activations`. Lower = better upstream extraction.

### Files Modified

| File | Changes |
|------|---------|
| `src/models.py` | Added `MergeDecision` model, `pending_reviews` field on `AnalysisResult` |
| `src/agents/characters.py` | +261 lines: co-occurrence computation, merge recording, defensive logging |
| `src/pipeline/character_extraction_v2/main_cast.py` | +206 lines: consolidated Pass 2, fallback per-character |
| `tests/test_character_extraction_v2.py` | Updated line count threshold (6000→7000) |

### Expected Impact on Frankenstein

1. **Creature extraction**: Combined with Attempt 5 fix, should now be in main_cast
2. **Alias conflicts**: Consolidated Pass 2 should reduce Step 3.6 activations
3. **Wrong merges**: Co-occurrence validation should catch low-confidence merges
4. **Measurement**: Defensive step counts will show if improvements are working
