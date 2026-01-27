# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.65
- **Competitive Mode:** single

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Pipeline Notes (Attempt 2)
- Analysis completed in 16m 57s
- CRITICAL ISSUE: "the monkey's paw" still appears as character despite fix
- Mrs. White profile had low confidence (0.30)
- Some alias blocking warnings (BLOCKED alias messages)
- Competitive consensus enabled for all stages (characters, structure, summaries)

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Object "the monkey's paw" incorrectly classified as character** - FIXED
   - Root cause: MAIN_CAST_PROMPT in main_cast.py:39-118 had no guidance to exclude inanimate objects
   - Fix applied: Added Rule 2 with explicit guidance that only sentient beings can be characters
   - Smoke test: PASS - Rule 2 found, monkey's paw WRONG example included, sentience test included

### HIGH
2. **Herbert White profile incomplete (LOW confidence)** - FIXED
   - Root cause: LLM JSON parsing failed twice (max_attempts=2), all recovery attempts failed
   - Fix applied: Increased max_attempts from 2 to 3 in analyzer.py:2550
   - Smoke test: PASS - max_attempts set to 3

### MEDIUM
3. **Chapter titles showing as null**
   - Deferred: Minor issue, doesn't block 8.0 threshold

## Fix History

### Attempt 1 → Attempt 2
**Fixed Issues:**
1. CRITICAL: Monkey's paw object misclassified as character
   - Root cause: ../src/pipeline/character_extraction_v2/main_cast.py - MAIN_CAST_PROMPT lacked object exclusion guidance
   - Fix: Added Rule 2 "ONLY SENTIENT BEINGS CAN BE CHARACTERS" with explicit examples
   - Updated rule numbering (old 3-16 → new 4-17) and reminder section
   - Smoke test: PASS

2. HIGH: Herbert White profile incomplete
   - Root cause: ../src/analyzer.py:2550 - Profile generation retry count (2) insufficient, JSON parse failures not recovered
   - Fix: Increased max_attempts from 2 to 3 for profile generation
   - Smoke test: PASS

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Baseline: 7.65 |
| 2 | Monkey's paw as character | src/pipeline/character_extraction_v2/main_cast.py | Smoke test PASS |
| 2 | Herbert profile incomplete | src/analyzer.py | Smoke test PASS |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.65 | - | Baseline: Object as character, Herbert profile incomplete |
| 2 | TBD | TBD | Fixes applied, awaiting analysis |

## Next Action
Re-run analysis to verify fixes:
- Monkey's paw should NOT appear in character list
- Herbert White should have complete profile (or higher confidence with retries)
