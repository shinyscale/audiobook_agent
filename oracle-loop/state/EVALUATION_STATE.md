# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Model:** qwen3-next:80b-a3b-instruct-q8_0 (DO NOT CHANGE - see USER_NOTES.md)
- **Competitive Mode:** single

## IMPORTANT: Model Configuration

**DO NOT change the model.** The user has explicitly configured `qwen3-next:80b-a3b-instruct-q8_0`.

If you encounter JSON issues:
1. The prompts use wrapped object format `{"characters": [...]}` which works with this model
2. If fallback is needed, use `nemotron-3-nano:30b` (NOT qwen2.5:32b)
3. See USER_NOTES.md for full details

## Latest Scores (Attempt 2)
- Structure Detection: 10/10
- Character Extraction: 5/10 (FAILING)
- Character Profiles: 4/10 (FAILING)
- Chapter Summaries: 9/10
- Pronunciation Guide: 8/10
- HTML Presentation: 9/10
- **Overall: 7.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Changes for Attempt 3

### Prompt Format Fix (main_cast.py)
Changed JSON output format from raw arrays to wrapped objects for qwen3-next compatibility:

**Before (caused issues with qwen3-next):**
```
Output JSON array:
[{"canonical_name": ..., "role": ...}]
```

**After (works with qwen3-next):**
```
Output format - return a JSON object with a "characters" array:
{"characters": [{"canonical_name": ..., "role": ...}]}
```

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |
| 2 | 7.35 | 0.00 | First scoreable run - character fragmentation + missing profiles |

## Current Issues (Priority Order)

### CRITICAL

1. **Severe character fragmentation: 5 major character pairs split**
   - Problem: First-name-only and full-name entries are not merged
   - Evidence:
     - "Tom" (170 mentions) + "Tom Buchanan" (22 mentions) = same person
     - "Jordan" (73 mentions) + "Jordan Baker" (40 mentions) = same person
     - "Wilson" (65) + "George" (14) + "George Wilson" (3) = same person
     - "Myrtle" (23) + "Myrtle Wilson" (6) = same person
     - "Nick" (24) + "Carraway" (10) = same person (narrator)

2. **Physical descriptions missing for ALL characters (0/28)**
   - Every character has `physical_description: null` despite rich source text

### HIGH

3. **"Town Tattle" extracted as character (false positive)**
   - This is a gossip column, not a character

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed |
| 2 | Main cast extraction failure | src/pipeline/character_extraction_v2/main_cast.py | Diagnostic logging |
| 3 | JSON format for qwen3-next | src/pipeline/character_extraction_v2/main_cast.py | Wrapped object prompts |

## Output Files (Attempt 3)
- HTML: ../output/gatsby/report.html (944K, generated 15:27)
- JSON: ../output/gatsby/analysis.json (485K, generated 15:27)

## Pipeline Notes (Attempt 3)
- Analysis completed successfully with competitive consensus enabled
- Multiple JSON format errors during chapter detection (qwen3-next returning error objects)
- Multiple JSON format errors during pronunciation enrichment
- Pipeline continued despite errors and completed all phases
- Total characters extracted: 33 (see report for details)

## Next Action
**Phase:** awaiting_evaluation

Evaluate Gatsby attempt 3 results and compare to attempt 2 baseline.
