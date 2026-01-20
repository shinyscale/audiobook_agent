# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** null

## Latest Scores
FAILED - NEW ERROR: LLM responses being truncated mid-JSON

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAILED | - | LLM validation error for 'Maw and Meggins' |
| 2 | FAILED | - | Same error - fix from attempt 1 was insufficient |
| 3 | FAILED | - | NEW ERROR: LLM responses truncated during parsing |

## Pipeline Error Details

**Error:** LLM character proposer failed to parse response - JSON truncated mid-response

**Stage:** Character extraction (CharacterAgent) - earlier than previous failures

**Context:**
- Multiple LLM proposers (marker proposer, character proposer) are getting truncated responses
- Example error: Response ends with `"name": "Herbert White", "type": "sto` (truncated mid-word)
- This is a DIFFERENT error than attempts 1-2, which failed during validation
- This error occurs earlier in the pipeline during the proposal phase

**Pipeline Output Before Failure:**
- Ingestion: Success (6,996 words extracted)
- Text refinement: Success (1 front matter region detected)
- Structure detection: Partial success (Found 2 chapters, but with truncated LLM responses)
- Character extraction: Failed during character proposer phase (before validation)

**Models Used:**
- Structure: qwen3:30b-instruct
- Characters: qwen3-next:80b-a3b-instruct-q8_0
- Summaries: qwen3-next:80b-a3b-instruct-q8_0
- Pronunciation: qwen3:30b-instruct

## Previous Text Completed
- **berenice:** 8.15/10 in 14 attempts ✓

## Fix History

### Attempt 1 → 2: Fixed character validation for company names
**Root Cause Analysis:**
- **Symptom:** Pipeline failed - LLM returned `[]` (empty list) instead of expected JSON object
- **Data flow trace:**
  1. Error raised in: `src/pipeline/character_extraction/validator.py:303`
  2. **Originates in:** `src/pipeline/character_extraction/validator.py:_llm_validation()` lines 273-303
- **Root cause:** The VALIDATION_SYSTEM_PROMPT listed rejection categories but did NOT explicitly mention "companies", "organizations", or "businesses". When the LLM encountered "Maw and Meggins" (a company), it was uncertain how to respond and returned an empty list instead of the expected JSON object with `"is_person": false`.
- **Confidence:** HIGH

**Fix Applied:**
- Modified: `src/pipeline/character_extraction/validator.py`
- Changes:
  1. Added "Companies, businesses, or organizations" to rejection criteria in VALIDATION_SYSTEM_PROMPT (line 60)
  2. Updated analysis questions to include "company" as a non-person category (lines 75-77)
  3. Updated JSON field description to include "company" in rejection list (line 80)
- Category: Prompt Issue - Made rejection criteria more explicit to guide LLM behavior
- Smoke test: Unit tests passed (12/12 in test_character_agent.py)

**Expected Outcome:**
LLM should now properly return `{"is_person": false, "is_person_reasoning": "This is a company/business name", ...}` instead of an empty list when encountering organization names.

### Attempt 2 → 3: Fixed LLM response type handling and added explicit examples
**Root Cause Analysis:**
- **Symptom:** Pipeline still failed - LLM continued to return `[]` (empty list) instead of JSON object
- **Data flow trace:**
  1. Error raised in: `src/pipeline/character_extraction/validator.py:304`
  2. Invalid type check at: `src/pipeline/character_extraction/validator.py:288`
  3. JSON parsed by: `src/llm/client.py:_extract_json()` lines 408-439
  4. **Originates in:** `src/llm/client.py:_extract_json()` line 430 - Returns list when LLM outputs `[]`
- **Root cause:** The `_extract_json()` function had type annotation `Optional[dict]` but implementation could return lists. When LLM output `[]`, it was successfully parsed as JSON and returned, but validator expected dict. The previous prompt fix wasn't sufficient because the LLM still didn't understand the expected output format.
- **Confidence:** HIGH

**Fix Applied:**
- Modified: `src/llm/client.py` and `src/pipeline/character_extraction/validator.py`
- Changes:
  1. **Type-safe JSON extraction** (`src/llm/client.py` lines 420-436):
     - Added `isinstance(parsed, dict)` validation after `json.loads()`
     - Now returns `None` when LLM outputs a list, triggering retry logic
  2. **Explicit prompt examples** (`src/pipeline/character_extraction/validator.py` lines 86-98):
     - Added "IMPORTANT: Always return a JSON object" instruction
     - Added 3 concrete examples showing exact format for valid character, company rejection, and place rejection
     - Examples use double-braced `{{}}` syntax for template string safety
- Category: Code Logic Bug + Prompt Issue - Both type safety AND clearer guidance needed
- Smoke test:
  - All 444 unit tests passed
  - Custom smoke test verified `_extract_json` correctly rejects lists and accepts dicts

**Expected Outcome:**
1. If LLM still returns `[]`, `_extract_json` will return `None` instead of list, triggering retry
2. The explicit examples should guide LLM to output proper object format even for rejections

## Diagnostic Notes

The fixes from attempts 1-2 may have inadvertently changed behavior that now causes truncation. Possible causes:
1. LLM output length limits being hit
2. Response parsing cutting off valid JSON
3. Model-specific issue with qwen3-next:80b-a3b-instruct-q8_0

The fact that multiple proposers (marker AND character) are experiencing truncation suggests this is a systemic issue in the LLM client or response handling, not specific to character extraction.

## Next Action
Investigate LLM response truncation issue. Check:
1. `src/llm/client.py` for response length handling
2. `src/pipeline/chapter_detection/llm_marker_proposer.py` for parsing logic
3. `src/pipeline/character_extraction/llm_character_proposer.py` for parsing logic
4. Whether recent changes to `_extract_json()` affected response parsing
