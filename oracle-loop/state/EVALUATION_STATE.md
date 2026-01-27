# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_fix
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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Baseline: 7.65 |
| 2 | Monkey's paw as character | src/pipeline/character_extraction_v2/main_cast.py | **FIX INEFFECTIVE - Prompt ignored** |
| 2 | Herbert profile incomplete | src/analyzer.py | Partial success |

**⚠️ ESCALATION TRIGGERED:** main_cast.py has been modified for the monkey's paw issue in attempt 2 without success. The fix phase MUST use a different approach (post-processing filter, validation layer, or schema change) rather than additional prompt modifications to the same file.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.65 | - | Baseline: Object as character, Herbert profile incomplete |
| 2 | 8.05 | +0.40 | Prompt fix ineffective for paw, profiles slightly improved |

## Next Action
Run PROMPT_fix.md to implement post-extraction filter for non-sentient entities (Critical #1). The fix must NOT rely solely on additional prompt text to main_cast.py - a code-level filter or validation is required.
