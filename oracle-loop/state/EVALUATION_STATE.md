# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

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
     - "Wilson" (65) + "George" (14) + "George Wilson" (3) = same person (George Wilson)
     - "Myrtle" (23) + "Myrtle Wilson" (6) = same person
     - "Nick" (24) + "Carraway" (10) = same person (narrator)
   - All fragments have `supporting_*` IDs - issue is in supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - alias resolution/merging
   - Fix: When a short name (e.g., "Tom") matches the first name of a full-name entry (e.g., "Tom Buchanan"), they should be merged with the short name as an alias

2. **Physical descriptions missing for ALL characters (0/28)**
   - Problem: Every character has `physical_description: null` despite rich source text
   - Evidence:
     - Tom Buchanan in text: "a sturdy, straw-haired man of thirty with a rather hard mouth and a supercilious manner"
     - Gatsby in text: "an elegant young roughneck, a year or two over thirty"
     - Jordan Baker in text: "a slender, small-breasted girl, with an erect carriage"
     - All show "Appearance: unknown" in HTML
   - Location: `src/pipeline/character_profiling/` - physical description extraction
   - Fix: Debug why passage gathering or LLM extraction is failing to populate `physical_description` field

### HIGH

3. **"Town Tattle" extracted as character (false positive)**
   - Problem: "Town Tattle" is a gossip column mentioned in the text, not a character
   - Evidence: ID `supporting_27`, 3 mentions - this is a publication name
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - entity filtering
   - Fix: Improve entity classification to reject publication/business names

### MEDIUM

4. **Daisy lacks "Daisy Buchanan" alias**
   - Problem: Daisy is listed without her married name alias
   - Evidence: Relationships correctly show "Tom Buchanan (spouse)" but alias not added
   - Location: Alias resolution logic
   - Fix: When spouse relationship detected, consider adding shared surname as alias

5. **Nick/Carraway narrator fragmentation**
   - Problem: Narrator "Nick" (is_narrator=true) is separate from "Carraway" (is_narrator=false)
   - Evidence: Both refer to Nick Carraway, the narrator
   - Location: Same as Critical #1 - supporting cast alias resolution
   - Fix: Same merge logic, but ensure narrator flag propagates to merged entry

## Fix History

### Attempt 1 → 2: Fixed tuple unpacking error in character profiling
- **Root cause:** `src/analyzer.py:2657` - early return missing 7th element
- **Fix:** Added missing `None` for relationships parameter
- **Result:** Pipeline now completes successfully

### Attempt 2 → 3: Added diagnostic logging for main cast extraction failure
- **Root cause:** Main cast extraction returned 0 profiles (all characters extracted via NER as supporting cast)
  - Data investigation: ALL 28 characters have `supporting_*` IDs (including Daisy:179 mentions, Tom:170, Gatsby/James Gatz:275)
  - No `main_cast_*` IDs found in output
  - Summaries exist (9 chapters, all populated) - data flow intact
  - Likely cause: LLM JSON parsing failure or error response (returns empty [])
- **Fix:** Added diagnostic logging to capture raw LLM response when extraction fails
  - `src/pipeline/character_extraction_v2/main_cast.py:479-506` - logs model, success status, response content
  - Logs at BOTH primary and fallback model attempts
  - Error message clarifies impact: "ALL characters will be extracted via NER as supporting cast, leading to fragmentation"
- **Result:** Next analysis will reveal exact LLM failure (awaiting re-run)
- **Smoke test:** Not applicable - diagnostic only, requires re-run to see output

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed - pipeline runs |
| 2 | Main cast extraction failure (needs diagnosis) | src/pipeline/character_extraction_v2/main_cast.py:479-506, 339-347 | Diagnostic logging added |

## Configuration Audit

From `analysis.json._config`:
- Pipeline completed in 253m 13s
- 493 LLM calls, 410,318 tokens
- Model: qwen2.5:32b-instruct-q8_0 (JSON-capable)

Potential config issues:
- Main cast extraction silently failed (0 profiles extracted despite valid summaries)
- Next run will reveal LLM failure details via new diagnostic logging

## Pipeline Notes

From `_profiling`:
- Character Extraction stage ran (57s, 3 LLM calls) but produced 0 main cast characters
- All 28 characters have `supporting_*` IDs (NER-based extraction)
- Bottleneck: Pronunciation guide (52.8% of runtime)
- Non-fatal warnings: LLM marker proposer returned dict instead of list (20 occurrences)
- `pipeline_char_map` undefined for Lucille, Rosy, Owl-Eyes (minor)

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to capture diagnostic logs that reveal why main cast extraction failed.
Once logs captured, return to fix phase with actual root cause data.
