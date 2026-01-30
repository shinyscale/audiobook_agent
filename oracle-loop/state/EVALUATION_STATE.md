# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Model:** qwen3-next:80b-a3b-instruct-q8_0 (MoE, ~3x faster than qwen2.5:32b)
- **Competitive Mode:** single (all stages enabled)

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
Changed JSON output format from raw arrays to wrapped objects for better model compatibility:

**Before (caused issues with some models):**
```
Output JSON array, each item:
[{"canonical_name": ..., "role": ...}]
```

**After (consistent across all tested models):**
```
Output format - return a JSON object with a "characters" array:
{"characters": [{"canonical_name": ..., "role": ...}]}
```

**Why:** Testing showed qwen3-next returns single objects when asked for raw arrays, but properly returns wrapped arrays when the prompt explicitly requests `{"characters": [...]}` format.

### Model Switch: qwen2.5:32b -> qwen3-next:80b

| Aspect | qwen2.5:32b | qwen3-next:80b |
|--------|-------------|----------------|
| Architecture | Dense | MoE (Mixture of Experts) |
| Size | 34GB | 84GB |
| Active params | 32B | ~24B per forward pass |
| Speed on DGX Spark | Slow (~3+ hours) | ~3x faster |
| JSON mode | Native support | Works with wrapped object prompts |

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

### Attempt 1 -> 2: Fixed tuple unpacking error in character profiling
- **Root cause:** `src/analyzer.py:2657` - early return missing 7th element
- **Fix:** Added missing `None` for relationships parameter
- **Result:** Pipeline now completes successfully

### Attempt 2 -> 3: Prompt format + model switch
- **Root cause:** Main cast extraction returned 0 profiles (all characters extracted via NER as supporting cast)
  - Data investigation: ALL 28 characters have `supporting_*` IDs (including Daisy:179 mentions, Tom:170, Gatsby/James Gatz:275)
  - No `main_cast_*` IDs found in output
  - Summaries exist (9 chapters, all populated) - data flow intact
  - Likely cause: LLM JSON parsing failure or error response (returns empty [])
- **Fix:**
  1. Updated prompts to request wrapped JSON objects `{"characters": [...]}` instead of raw arrays
  2. Switched to qwen3-next:80b MoE model for faster analysis (~3x speed improvement)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` - MAIN_CAST_PROMPT, CHARACTER_IDENTIFICATION_PROMPT, system_prompt
- **Result:** FAILED - qwen3-next model incompatible (returns error objects instead of JSON arrays)

### Attempt 3 -> 4: Reverted to qwen2.5:32b-instruct-q8_0
- **Root cause:** qwen3-next:80b-a3b-instruct-q8_0 returns `{"error": "..."}` instead of JSON arrays
  - Structure detection expects list `[]`, receives dict `{"error": "..."}`
  - Model consistently refuses to follow JSON array format (confirmed in 2 consecutive runs)
  - Ground truth: Gatsby has clear chapter markers (Roman numerals I-IX), model should detect them
- **Fix:** Reverted model configuration to known-working qwen2.5:32b-instruct-q8_0
- **Files modified:** `~/.config/audiobook_prep/gui_settings.json` - all agent models
- **Rationale:** qwen2.5:32b is slower but reliable; qwen3-next needs separate investigation

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed - pipeline runs |
| 2 | Main cast extraction failure (needs diagnosis) | src/pipeline/character_extraction_v2/main_cast.py:479-506, 339-347 | Diagnostic logging added |
| 3 | JSON format incompatibility | src/pipeline/character_extraction_v2/main_cast.py:47-72, 100-115, 478-483 | Wrapped object prompts - FAILED (qwen3-next incompatible) |
| 4 | qwen3-next model compatibility | ~/.config/audiobook_prep/gui_settings.json | Model reverted to qwen2.5:32b-instruct-q8_0 |

## Configuration Audit

From `gui_settings.json`:
- Model: qwen2.5:32b-instruct-q8_0 (Dense architecture - slower but reliable)
- All agents using same model (structure, characters, summaries, pronunciation)
- Context length: 65536 tokens
- **Note:** qwen3-next:80b MoE model attempted in attempt 3 but incompatible with pipeline

## Next Action
**Phase:** awaiting_analysis
**Reason:** Model configuration reverted to known-working qwen2.5:32b - re-run analysis to get scoreable results

## Attempt 3 Results: FAILED - Model Compatibility Issue

**Root Cause:** qwen3-next:80b-a3b-instruct-q8_0 model returns error responses instead of JSON arrays for chapter marker detection.

**Evidence:**
- Structure detection failed: Model returned `{"error": "No explicit chapter or section markers found..."}` repeatedly
- Ground truth: Gatsby.txt HAS clear chapter markers (Roman numerals I-IX on standalone lines, starting at line 59)
- The model is refusing to extract markers that are clearly present

**Error Pattern (stderr output):**
```
Model returned error-like response instead of expected data:
{'error': "No explicit chapter or section markers found in the provided text..."}
This model may not support json_mode or structured output properly.
LLM marker proposer failed to parse response: {"error": "No explicit..."}
LLM marker proposer returned non-list: <class 'dict'>
```

**Diagnosis:**
- The model is not following the JSON array format instruction
- Instead of returning `[]` (empty list) when no markers found, it returns `{"error": "..."}`
- This breaks the structure detection consensus system
- The error-response detection logic in `src/pipeline/llm.py` is working correctly (it detects and reports the issue)

**Next Steps:**
1. **Option A (Model Switch):** Revert to qwen2.5:32b-instruct-q8_0 (known to work)
2. **Option B (Debug):** Investigate why qwen3-next returns error objects instead of empty lists
3. **Option C (Prompt Fix):** Update prompts to handle qwen3-next's behavior

**Recommendation:** Switch back to qwen2.5:32b for reliability, then investigate qwen3-next separately

**Re-run Confirmation (2026-01-30):**
- Analysis re-run with same configuration immediately failed with identical error
- qwen3-next:80b-a3b-instruct-q8_0 consistently returns `{"error": "No explicit chapter or section markers..."}` instead of JSON arrays
- Model is incompatible with current structure detection pipeline
- Process stopped to avoid wasting compute time
