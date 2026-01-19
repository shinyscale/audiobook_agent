# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 6 of 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.45

## Output Files
- HTML: output/cask_of_amontillado/report.html
- JSON: output/cask_of_amontillado/analysis.json

## Pipeline Notes (Attempt 6)
- **Pipeline COMPLETED successfully** (10m 54s)
- LLM validation warning: "LLM validation attempt 1 for 'Montresors' returned array: got list with 0 elements" - but handled gracefully
- Character profiling had issues: "Moral valence classification failed for Amontillado", "Low confidence profile for Amontillado: 0.30"
- Character extraction found 3 characters: Amontillado (16 mentions), Fortunato (14 mentions), Montresor (1 mention)
- Narrator detection: "Detected narrator: Amontillado" (incorrect - should be Montresor)
- Quality concerns: 1 low-confidence character profile
- Same critical issues persist from previous attempts

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 2/10 ← CRITICAL FAILURE
- Character Profiles: 3/10 ← CRITICAL FAILURE
- Chapter Summaries: 7/10
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10
- **Overall: 5.95/10** (threshold: 8.0)

## REGRESSION DETECTED
- **Previous (Attempt 1):** 6.45/10
- **Current (Attempt 2):** 5.95/10
- **Delta:** -0.50 points

**The Attempt 2 fix made things WORSE.** The enhanced object detection heuristic in `validator.py` did NOT filter out "Amontillado" as expected. The issue persists exactly as before.

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (wine) still identified as a main character**
   - Problem: The tool identified "Amontillado" (a type of sherry wine) as a main character with 16 mentions
   - Evidence: Amontillado is NOT a person. It's the wine used as bait. The title "The Cask of Amontillado" refers to a BARREL OF WINE.
   - Location: `src/pipeline/character_extraction/validator.py` - The heuristic fix from Attempt 2 is not working
   - Why Attempt 2 failed: The heuristic checks for object patterns like "a pipe of Amontillado" but spaCy's NER extracted "Amontillado" standalone, not in phrase context. The regex may not be matching correctly, OR the LLM validation is still overriding the heuristic result.
   - Fix approach: Need to trace the actual execution path. Add logging OR use a different approach entirely - check if the entity EVER performs person-like actions (speaks, thinks, moves) in the text.

2. **Montresor (actual narrator) still demoted to 1 mention**
   - Problem: Montresor is the first-person narrator and protagonist, but listed with only 1 mention
   - Evidence: The entire story is told from Montresor's perspective ("I vowed revenge", "I said", etc.). His name is only spoken once ("For the love of God, Montresor!") but HE is the narrator.
   - Location: Narrator detection is NOT connected to character extraction
   - Fix approach: First-person narrator detection needs enhancement. When a story is first-person ("I" narration) AND a character name is mentioned in dialogue addressing the narrator, that character should be flagged as the narrator with boosted mention count.

3. **Narrator still incorrectly identified as "Amontillado" in plot_summary**
   - Problem: From `overview.plot_summary`: "Amontillado, the story's first-person narrator..."
   - Evidence: Montresor is the narrator, not the wine
   - Location: `src/agents/summary_agent.py` - narrator identification
   - Fix approach: This is downstream of issue #1. If Amontillado is removed from characters, the summary won't call it the narrator.

### HIGH

4. **Luchresi still missing from character list**
   - Problem: Luchresi (rival wine expert) mentioned 6 times but not in characters
   - Evidence: Appears in pronunciation guide (6 occurrences) but not characters
   - Location: Likely filtered by mention count threshold
   - Fix approach: Lower mention threshold OR add logic to include characters mentioned by name even with low counts

### MEDIUM

5. **Montresor's profile content attributed to "Amontillado"**
   - Problem: The accurate narrator profile is assigned to wrong entity
   - Evidence: Profile says "The character is the first-person narrator" but attached to "Amontillado"
   - Fix approach: Downstream of #1

6. **~35-40% pronunciation false positives**
   - Problem: Common words like "jingled", "orbs", "leer", "filmy" flagged
   - Evidence: 56 words flagged, ~20 are standard English
   - Location: `src/agents/pronunciation_agent.py`
   - Fix approach: Common word frequency filtering (top 5000-10000 English words)

## Root Cause Analysis

### Why Attempt 2 Fix Failed

The fix in Attempt 2 added heuristics to `validator.py` to detect object patterns:
```python
# Added in Attempt 2 - lines 218-263
# Checks for patterns like "a pipe of X", "the X", "of X"
# Should have rejected "Amontillado" based on object_pattern_count
```

**Possible failure modes:**
1. The regex patterns aren't matching the actual text context
2. The heuristic runs AFTER LLM validation already accepted it
3. The mention_boost override the rejection
4. The code path isn't being executed at all

**Recommended investigation:**
- Add debug logging to see if the heuristic code is even being reached
- Print the actual object_pattern_count and person_context_count for "Amontillado"
- Verify the heuristic runs BEFORE or can override LLM acceptance

### The Core Problem

The system has TWO separate issues:

1. **Object vs Person discrimination:** NER extracts "Amontillado" as PERSON. The validator doesn't have strong enough filters to reject it. The fix needs to be MORE aggressive - perhaps checking if the entity EVER performs person-like verbs (said, thought, walked, felt) anywhere in the text.

2. **First-person narrator detection:** The narrator is implicit in first-person stories. "Montresor" appears once by name but IS the narrator. The system needs narrator-specific logic: when addressee mentions a name ("Montresor!") in dialogue with the first-person narrator, that's the narrator's identity.

## Fix History

### Attempt 3: Person-action verb detection for non-person entity filtering
**Date:** 2026-01-18
**Root cause:** src/pipeline/character_extraction/validator.py:_heuristic_validation():line 195-213
  - Entities with 5+ mentions and 0 dialogue tags were passed to LLM validation
  - LLM validation could accept non-person entities if context was ambiguous
  - No check for whether entity PERFORMS person-like actions (speaks, thinks, walks, etc.)
**Smoke test:** PASS
  - Test with "Amontillado" (wine): Correctly rejected with reasoning "Entity has 16 mentions but never performs person actions (0/16 contexts checked)"
  - Test with "Fortunato" (character with actions): Passed to LLM validation as expected
**Modified:** src/pipeline/character_extraction/validator.py (lines 212-241)
  - Added check: if entity has 5+ mentions, 0 dialogue tags, and NEVER performs person-action verbs → reject
  - Checks pattern "{name} {verb}" to detect person actions (e.g., "Fortunato laughed")
  - Scans up to 20 mention contexts for person-action patterns
**Addresses:** Issue #1 (Amontillado as character) and downstream issues #3 and #5

### Attempt 2: Enhanced object/non-person entity filtering (FAILED - REGRESSION - REVERTED)
**Date:** 2026-01-18
**Modified:** `src/pipeline/character_extraction/validator.py`
**Result:** Score dropped from 6.45 to 5.95 (-0.50 points)
**Why it failed:** Pattern-based object detection didn't match actual text contexts
**Status:** REVERTED in commit 6ef2046

## Pipeline Error (Attempt 5)

**Error:** LLM validation returned empty array
**Details:**
- Entity: "Montresors"
- Error message: "LLM validation returned invalid JSON for 'Montresors' after 3 attempts: Invalid JSON: got list with 0 elements"
- Root cause: The LLM (qwen3-next:80b-a3b-instruct-q8_0) is returning an empty JSON array `[]` for entity "Montresors"
- Location: src/pipeline/character_extraction/validator.py:280-294 - `_llm_validation()` method
- Expected: JSON object with fields {is_person, is_person_reasoning, context_supports, alias_candidates, overall_valid}
- Actual: Empty JSON array `[]` (0 elements)

**Impact:** The analysis pipeline cannot complete. Character extraction fails during LLM validation.

**Fix needed:** The validation code needs to handle empty array responses. Options:
1. Treat empty array as "reject entity" (overall_valid=False)
2. Add more explicit prompt instructions to prevent empty array responses
3. Fall back to heuristic validation when LLM returns empty array
4. Consider if "Montresors" is a malformed entity that should be filtered earlier

**Analysis:** "Montresors" is likely a plural/possessive form ("the Montresors" or "Montresor's") that shouldn't be extracted as a separate entity. The empty array might be the LLM's way of signaling "this is not a valid entity" but the code expects a structured rejection with reasoning.

## Fix History

### Attempt 4: Fix LLM validation JSON format parsing
**Date:** 2026-01-18
**Root cause:** src/pipeline/character_extraction/validator.py:_llm_validation():line 280
  - Prompt didn't explicitly forbid array responses
  - LLM (qwen3-next:80b-a3b-instruct-q8_0) returned JSON array `[...]` instead of object `{...}`
  - Code rejected arrays entirely without fallback handling
**Smoke test:** PASS
  - Prompt template now explicitly requests "JSON object (not an array)"
  - Prompt specifies format: "starting with { and ending with }"
  - Added fallback: single-element arrays are unwrapped to extract the dict
  - Code inspection confirms array handling logic is present
**Modified:** src/pipeline/character_extraction/validator.py (lines 50-66, 280-294)
  - Updated VALIDATION_PROMPT_TEMPLATE to explicitly request object format
  - Added array detection and unwrapping logic before dict type check
**Addresses:** Pipeline error blocking analysis completion

(Previous fix history from Attempt 3 preserved above)

## Next Action

**Phase:** awaiting_fix
Fix the empty array handling in validator.py to allow the pipeline to complete.
