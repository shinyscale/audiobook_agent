# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score:** 7.65
- **Competitive Mode:** single

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Object "the monkey's paw" STILL classified as character despite prompt fix**
   - Problem: "the monkey's paw" appears as main_cast_5 with role "antagonist" and 21 mentions
   - Evidence: `jq '.characters[] | select(.canonical_name | test("monkey"))' analysis.json` shows it present
   - Previous fix: Added Rule 2 to MAIN_CAST_PROMPT in main_cast.py:45-49 with explicit wrong example
   - **Why fix failed:** The LLM is not following the instruction. Prompt changes alone are insufficient.
   - **Escalation required:** Same file (main_cast.py) was modified in attempt 2 without success. Per modification history rules, must escalate upstream to a different approach.

   **Recommended fix approaches (in order of preference):**
   1. **Post-extraction filter** (PREFERRED): Add a validation function after main cast extraction that rejects entries matching object patterns (items ending in "paw", "sword", "ring", "book", etc. that lack human/creature indicators)
   2. **Schema validation**: Add an `is_sentient` boolean field to the extraction schema that forces the LLM to explicitly affirm sentience
   3. **Two-stage extraction**: First extract all named entities, then use a separate LLM call to classify as character vs. object

   - Location for fix: `src/pipeline/character_extraction_v2/main_cast.py` - add `_filter_non_sentient()` function after `_extract_main_cast()`

### HIGH
2. **Mrs. White profile has LOW confidence and sparse data**
   - Problem: Mrs. White's profile shows only a personality paragraph, no structured fields (age, features, traits, tone)
   - Evidence: HTML shows LOW confidence badge; JSON shows `physical_description: null`, `relationships: {}`, `speech_patterns: null`
   - Root cause: Profile generation likely failed or returned minimal data due to JSON parsing issues
   - Location: `src/analyzer.py` profile generation section (around line 2550)
   - Note: The retry increase from 2→3 was applied but may not be sufficient
   - Fix: Consider more robust profile fallback or larger context window for profile generation

### MEDIUM
3. **Chapter titles showing as null** (deferred from attempt 1)
   - Problem: Structure shows `title: null` for all 3 parts
   - Evidence: The original text uses Roman numerals (I, II, III) without descriptive titles
   - Impact: Minor - doesn't affect narrator usability
   - Fix: Could auto-generate "Part I", "Part II", etc. or extract Roman numerals

4. **Missing minor character: Maw and Meggins representative**
   - Problem: The company representative who delivers news of Herbert's death is not in character list
   - Evidence: He has dialogue in Part II and is narratively significant
   - Impact: Minor - he's unnamed and brief
   - Location: Character extraction thresholds or supporting cast detection

## Fix History

### Attempt 1 → Attempt 2
**Fixed Issues:**
1. CRITICAL: Monkey's paw object misclassified as character
   - Root cause: ../src/pipeline/character_extraction_v2/main_cast.py - MAIN_CAST_PROMPT lacked object exclusion guidance
   - Fix: Added Rule 2 "ONLY SENTIENT BEINGS CAN BE CHARACTERS" with explicit examples
   - **Result: FIX INEFFECTIVE** - LLM ignored the instruction

2. HIGH: Herbert White profile incomplete
   - Root cause: ../src/analyzer.py:2550 - Profile generation retry count (2) insufficient
   - Fix: Increased max_attempts from 2 to 3 for profile generation
   - **Result: PARTIAL** - Herbert now has full profile, but Mrs. White still has issues

### Attempt 2 → Attempt 3
**Fixed Issues:**
1. CRITICAL: Monkey's paw object misclassified as character
   - Root cause: src/pipeline/character_extraction_v2/main_cast.py:extract() - LLM returns object despite prompt instructions
   - Data flow trace:
     - Symptom: "the monkey's paw" appears as main_cast_5 with role "antagonist" in analysis.json
     - Originates: LLM extraction in main_cast.py returns it as a character profile
     - Root cause: Prompt-based exclusion insufficient; LLM does not reliably follow "no objects" instruction
   - Fix: Added post-extraction filter `_filter_non_sentient_entities()` that uses keyword pattern matching to reject objects (paw, ring, sword, talisman, etc.)
   - Smoke test: PASS - Filter successfully removes "the monkey's paw" while preserving human characters
   - Modified: src/pipeline/character_extraction_v2/main_cast.py (lines 595-601, 1332-1397)

2. HIGH: Mrs. White profile has incomplete structured fields
   - Root cause: src/analyzer.py:2777 - Fallback restructuring condition too strict, doesn't trigger when fields are empty dicts
   - Data flow trace:
     - Symptom: Mrs. White shows null appearance/personality/voice_guidance in JSON output
     - Stored in: AnalysisResult.characters[].appearance/personality/voice_guidance
     - Generated by: _generate_character_profile()
     - Root cause: JSON parsing fails, producing malformed profile text; fallback restructuring doesn't trigger because condition only checks for None, not empty dicts
   - Fix: Made fallback condition more aggressive - triggers if structured fields are None OR mostly empty (only "unknown" values)
   - Modified: src/analyzer.py (lines 2776-2784)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Baseline: 7.65 |
| 2 | Monkey's paw as character | src/pipeline/character_extraction_v2/main_cast.py (prompt) | **FIX INEFFECTIVE - Prompt ignored** |
| 2 | Herbert profile incomplete | src/analyzer.py (retry count) | Partial success |
| 3 | Monkey's paw as character | src/pipeline/character_extraction_v2/main_cast.py (filter) | **Pending verification** |
| 3 | Mrs. White profile incomplete | src/analyzer.py (fallback condition) | **Pending verification** |

**⚠️ ESCALATION APPLIED:** Attempt 3 implements post-processing filter for monkey's paw issue (escalated from failed prompt-only approach in attempt 2)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.65 | - | Baseline: Object as character, Herbert profile incomplete |
| 2 | 8.05 | +0.40 | Prompt fix ineffective for paw, profiles slightly improved |
| 3 | TBD | TBD | Applied: object filter + profile fallback enhancement |

## Next Action
Re-run analysis to verify fixes for:
1. Object filtering (should remove "the monkey's paw" from character list)
2. Profile generation (should produce complete structured fields for Mrs. White)
