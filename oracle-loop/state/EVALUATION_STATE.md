# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Last modified: 2026-01-31 08:32 (attempt 4 analysis complete)

## Latest Scores (Attempt 3)
- Structure Detection: 7.5/10 ✗ (FAILING - most chapter titles null)
- Character Extraction: 6.5/10 ✗ (FAILING - Walton not narrator, Alphonse fragmented, generic groups)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.83/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **Robert Walton NOT marked as narrator**
   - Problem: Walton is the FRAME narrator of Frankenstein (entire novel is his letters to Margaret) but `is_narrator=false`
   - Evidence: "Walton" (supporting_5, 8 mentions, is_narrator=false) - should be the primary frame narrator
   - Impact: Fundamentally misrepresents the novel's narrative structure for audiobook preparation
   - Location: The epistolary narrator detection fix in attempt 3 was applied to main_cast.py but Walton ended up in supporting_cast, not main_cast
   - ID Pattern: supporting_5 → supporting cast pipeline
   - Fix: Either (a) promote Walton to main_cast with is_narrator=true, or (b) ensure supporting cast can also detect frame narrators

2. **Robert Walton fragmented: "Walton" vs "R.W."**
   - Problem: "Walton" (supporting_5, 8 mentions) and "R.W." (f1b39c083608, 1 mention) are separate entries
   - Evidence: R.W. is Walton's signature on Letter 3 - same person
   - ID Patterns: supporting_5 (supporting cast) + f1b39c083608 (F6 reconciliation)
   - Location: Cross-pipeline merge needed - F6 reconciliation should merge "R.W." with "Walton"
   - Fix: Add alias recognition for initials → full name in F6 reconciliation (analyzer.py:1220-1240)

### HIGH

3. **Alphonse Frankenstein fragmented into two F6 entries**
   - Problem: "Alphonse Frankenstein" (cf652e4d2e68, 1 mention) and "The narrator's father" (4542ed769e00, 1 mention) are separate
   - Evidence: Same person - Victor's father is Alphonse Frankenstein
   - ID Patterns: Both are 12-char hashes → both from F6 reconciliation
   - The attempt 3 relationship-based reference guidance did NOT work
   - Location: F6 reconciliation (analyzer.py:1220-1240)
   - Fix: F6 reconciliation needs to merge relationship-based references ("The narrator's father") with named characters when context makes them equivalent

4. **Generic groups extracted as characters**
   - Problem: "the court officials", "Witnesses (fishermen, women)", "the people of the inn" are not characters
   - Evidence: These are generic group references, not named/significant characters
   - ID Patterns: All F6 reconciliation (12-char hashes)
   - Location: F6 reconciliation (analyzer.py:1220-1240) or summary extraction that created them
   - Fix: Filter out generic group references ("the [noun]s", "witnesses", etc.) from character reconciliation

5. **Caroline Beaufort fragmented**
   - Problem: "Caroline Beaufort Frankenstein" (main_cast_7, 10 mentions) and "Caroline Beaufort" (1b0ca2c5dd62, 1 mention) separate
   - Evidence: Same person - Caroline Beaufort is her maiden name, Caroline Beaufort Frankenstein after marriage
   - ID Patterns: main_cast_7 (main cast) + 1b0ca2c5dd62 (F6 reconciliation)
   - Location: F6 reconciliation should merge with existing main_cast entry
   - Fix: Name-shape matching in F6 to recognize maiden name as alias of married name

### MEDIUM

6. **Chapter titles mostly null**
   - Problem: Only Letters 2-4 have titles; Letter 1 and all 24 chapters show `title: null`
   - Evidence: 24/28 structure elements have null titles
   - Impact: Navigation and chapter reference usability reduced
   - Location: Structure detection pipeline (chapter_detection/proposers/llm.py or consensus logic)
   - Fix: Ensure chapter title extraction captures "Letter 1", "Chapter I", "Chapter II", etc.

7. **Victor Frankenstein has "unknown" appearance**
   - Problem: Main protagonist lacks physical description in profile
   - Evidence: `appearance.summary: "unknown"` for main_cast_1
   - Location: Character profiling pipeline
   - Fix: May be limited by source text (Victor doesn't describe himself much), but some details exist

### LOW

8. **M. Waldman not merged with Professor Waldman context**
   - Problem: "M. Waldman" (supporting_4, 9 mentions) lacks full context
   - Evidence: Text refers to him as both "M. Waldman" and "Professor Waldman"
   - Impact: Minor - character is correctly extracted, just missing alias
   - Fix: Add "Professor Waldman" as alias

## Pipeline Notes (Attempt 4 - 2026-01-31 08:32)

**Analysis completed successfully in 150m 12s**

Key observations:
- ✅ Narrator detection: "Robert Walton (epistolary)" detected from summaries
- ✅ M. Krempe and M. Waldman correctly split (not merged)
- ⚠️ Character profiling errors: `name 'pipeline_char_map' is not defined` for some characters
- ⚠️ Pronunciation LLM errors: qwen3-next returning error objects instead of JSON arrays
- ⚠️ Structure: 27 chapters detected vs 28 expected (TOC enforcement warning)

**Pipeline Metrics:**
- Total time: 150m 12s
- LLM calls: 668
- Tokens: 773,500
- Characters found: 32 (24 from extraction + 8 from summary reconciliation)
- Profiles generated: 20/25 eligible characters

**Warnings to investigate in evaluation:**
1. Character profiling failures (pipeline_char_map undefined)
2. Pronunciation JSON parsing failures (model compatibility issue)
3. TOC mismatch (27 detected vs 31 expected from TOC)

## Fix History

### Attempt 4 Fix (2026-01-31) - ANALYSIS COMPLETE, AWAITING EVALUATION

**Fixed:**
1. ✓ Robert Walton narrator detection (CRITICAL issue #1)
   - Root cause: Narrator detection (Step 4) ran BEFORE supporting cast extraction (Step 5)
   - Frame narrators with few name mentions get extracted to supporting_cast, not main_cast
   - Previous fallback (Step 5.0.5) only ran if main_cast was EMPTY (wrong condition)
   - Fix: Added Step 5.0.5 re-run with combined_cast (main + supporting)
   - Now checks narrator against ALL characters, not just main_cast
   - If narrator found in supporting_cast, marks them as is_narrator=true
   - File modified: src/agents/characters.py (lines 470-523)

**Smoke test:** Code logic verified - re-runs narrator detection with combined cast after supporting extraction

**Deferred for next iteration:**
- Issue #2 (CRITICAL): Walton "R.W." fragmentation - F6 reconciliation (analyzer.py)
- Issue #3 (HIGH): Alphonse fragmentation - F6 reconciliation (analyzer.py)
- Issue #4 (HIGH): Generic groups - F6 reconciliation (analyzer.py)
- Issue #5 (HIGH): Caroline maiden name - F6 reconciliation (analyzer.py)
- Issue #6 (MEDIUM): Chapter titles null - Structure detection

### Attempt 3 Fixes (2026-01-31) - PARTIALLY FAILED

**Intended fixes:**
1. ❌ Robert Walton epistolary narrator detection - FIX DID NOT WORK
   - Added epistolary guidance to CHARACTER_IDENTIFICATION_PROMPT
   - But Walton ended up in supporting_cast (not main_cast), so the guidance didn't apply
   - Walton still NOT marked as narrator

2. ❌ Alphonse Frankenstein relationship-based references - FIX DID NOT WORK
   - Added relationship-based reference guidance to CHARACTER_IDENTIFICATION_PROMPT
   - But Alphonse still fragmented into two F6 reconciliation entries
   - Neither entry is in main_cast

**Root cause analysis:**
- The fixes were applied to main_cast.py but the characters are being created in OTHER pipelines (supporting_cast, F6 reconciliation)
- The LLM did not extract Walton or Alphonse into main_cast, so the main_cast.py guidance never applied
- Attempt 4 correctly targets src/agents/characters.py where narrator detection runs

### Attempt 2 Fixes (2026-01-31)

**Fixes that WORKED:**
1. ✅ Victor Frankenstein now in main_cast (main_cast_1, 55 mentions, is_narrator=true)
2. ✅ Professor Krempe and M. Waldman are NOW SEPARATE - false merge FIXED
3. ✅ The Creature has proper appearance description in structured format
4. ✅ Victor and Creature correctly marked as narrators

**Character Extraction improved from 4/10 to 7/10**
**Character Profiles improved from 5/10 to 8/10**

### Attempt 1
- Initial analysis (baseline 6.35/10)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline score 6.35 |
| 2 | Victor missing, Walton missing, Waldman/Krempe merge | src/pipeline/character_extraction_v2/main_cast.py | Victor FIXED, Walton still failing, Waldman/Krempe now separate |
| 3 | Walton epistolary narrator, Alphonse relationship refs | src/pipeline/character_extraction_v2/main_cast.py | NO CHANGE - Walton/Alphonse not in main_cast, fixes didn't apply |
| 4 | Walton narrator detection in supporting_cast | src/agents/characters.py | AWAITING VERIFICATION - re-runs narrator detection with combined cast |

**Pattern evolution:** Attempt 4 correctly targets characters.py (where narrator detection orchestration happens) instead of main_cast.py (where LLM extraction happens). This addresses the architectural issue of narrator detection timing.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive consensus: ENABLED (single-model mode, 3 temperatures: 0.5, 0.7, 0.9)
- Competitive stages: characters, structure, summaries (all enabled via --competitive-all)

## Next Action

Re-run analysis to verify fix for:
1. **CRITICAL:** Walton narrator detection - should now detect narrators in supporting_cast

Expected impact:
- Walton should now have is_narrator=true
- Character Extraction score should improve (6.5 → 7.0+)

If fix works, remaining issues for subsequent iterations:
- Issue #2 (CRITICAL): Walton "R.W." fragmentation
- Issues #3-5 (HIGH): F6 reconciliation improvements
- Issue #6 (MEDIUM): Chapter titles
