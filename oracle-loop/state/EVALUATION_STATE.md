# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 8.85
- **Competitive Mode:** single

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 8/10 ✓
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 9.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.85 | - | Baseline established. Pronunciation lacking IPA. |
| 2 | 9.05 | +0.20 | Dict fix did not resolve IPA issue. Console shows "LLM validation failed (got dict)". |

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **No IPA provided for any pronunciation entries (0/70)**
   - Problem: All 70 pronunciation flags have `ipa: null` - no phonetic guidance provided
   - Evidence: `jq '[.pronunciations[] | select(.ipa != null)] | length' analysis.json` returns 0
   - Previous fix attempt: Modified `src/pipeline/pronunciation_guide/enricher.py` to handle dict responses
   - Result: Fix did not work - console shows "LLM validation failed (got dict), keeping batch candidates"
   - Root cause: The validation is rejecting dict responses even after the fix was applied
   - Location: `src/pipeline/pronunciation_guide/enricher.py` - validation logic after line 163
   - Fix needed: Investigate WHY validation still fails after dict handling was added. The LLM returns `{"word": "...", "ipa": "..."}` but validation rejects it.

### MEDIUM
2. **"Jennings" profile confuses Milton with the Jennings surname**
   - Problem: The "Jennings" character entry has personality summary "Milton appears proactive..."
   - Evidence: Profile text references "Milton" when describing a "Jennings" entry
   - Location: Character profile generation in summary/profile pipeline
   - Severity: Medium - affects 1 of 9 characters, a minor/ambiguous character
   - Fix: Lower priority - this is acceptable ambiguity (Jennings could mean Milton Jennings, Mr. Jennings, or Mrs. Jennings)

3. **Excessive false positives in pronunciation flagging**
   - Problem: Old-fashioned spellings like "to-day", "to-morrow", "good-by", "mid-water" flagged
   - Evidence: These are phonetically self-explanatory hyphenated compounds
   - Location: `src/pipeline/pronunciation_guide/` - word flagging logic
   - Impact: Minor - 15-20 unnecessary entries in a list of 70

### LOW
(None)

## Fix History
- Attempt 1: Tried to fix IPA generation - batch enrichment was only handling list responses, not dict responses
  - Root cause identified: `src/pipeline/pronunciation_guide/enricher.py` line 163 - only checked `isinstance(result, list)`
  - Fix applied: Added dict handling + validation improvements
  - Result: DID NOT WORK - validation still rejects dict responses

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | No IPA data (0/70 entries) | src/pipeline/pronunciation_guide/enricher.py | No change - IPA still 0/70 |

## Debugging Notes for Fix Phase

The previous fix added dict handling but validation still fails. The fix phase should:

1. **Add diagnostic logging** to `enricher.py` to see exactly what the LLM returns
2. **Check the validation function** - what field names does it expect? The LLM might return `{word, ipa}` but validation expects different fields
3. **Verify the prompt** - is ENRICHER_BATCH_PROMPT asking for the right JSON structure?
4. **Check if enrichment is even being called** - maybe the pipeline skips enrichment entirely

Console output from attempt 2 shows: "LLM validation failed (got dict), keeping batch candidates"
This confirms the code reaches the dict branch but validation rejects the data.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) - appropriate
- Context length: 32768 - sufficient
- Temperature: 0.7 - reasonable

### Processing Notes (from `_profiling`)
- No LLM retries or JSON parse failures in main stages
- Character Profiles stage: 5 characters processed with high confidence
- Pronunciation Guide: 70 items flagged, 18 high confidence, rest medium
- IPA enrichment step appears to run but output is null

## Next Action
Run PROMPT_fix.md to investigate and fix IPA validation rejection in enricher.py
