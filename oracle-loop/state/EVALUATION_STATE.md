# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 8.85
- **Competitive Mode:** single

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 8/10 ✓
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 8.85/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.85 | - | Baseline established. Pronunciation lacking IPA. |

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **No IPA provided for any pronunciation entries (0/70)**
   - Problem: All 70 pronunciation flags have `ipa: null` - no phonetic guidance provided
   - Evidence: `jq '[.pronunciations[] | select(.ipa != null)] | length' analysis.json` returns 0
   - Location: `src/pipeline/pronunciation/` - IPA generation step
   - Expected: At minimum, proper nouns like "Rance" and homographs like "bass" should have IPA
   - Fix: Ensure IPA generation step is being called and outputting data

### MEDIUM
2. **"Jennings" profile incorrectly describes Milton instead of the Jennings family**
   - Problem: The "Jennings" character entry has personality summary "Milton is proactive, sociable..."
   - Evidence: The text uses "Jennings" for Milton Jennings, Mr. Jennings, and Mrs. Jennings
   - Location: Character profile generation may be confusing different uses of "Jennings"
   - Fix: This is acceptable ambiguity - the name refers to multiple people. Low priority.

3. **Excessive false positives in pronunciation flagging**
   - Problem: Old-fashioned spellings like "to-day", "mid-water", "grass-grown" flagged as "unknown"
   - Evidence: These are self-explanatory hyphenated compounds, not pronunciation challenges
   - Location: `src/pipeline/pronunciation/` - word flagging logic
   - Fix: Deprioritize hyphenated compound words that are phonetically regular

4. **No relationships detected despite clear friendships**
   - Problem: HTML shows "No explicit relationships detected"
   - Evidence: Lincoln and Milton are clearly friends; Lincoln's father is Mr. Stewart; Mrs. Jennings hosts them
   - Location: Character relationship extraction
   - Fix: Lower priority - relationships exist in character profiles' evidence but not extracted to relationship map

### LOW
(None)

## Fix History
- Attempt 1: Fixed IPA generation - batch enrichment was only handling list responses, not dict responses
  - Root cause: `src/pipeline/pronunciation_guide/enricher.py` line 163 - only checked `isinstance(result, list)`
  - LLMs often return bare dict `{"word": "...", "ipa": "..."}` instead of array `[{...}]` for single/small batches
  - Smoke test: Single-word enrichment confirmed LLM returns dict, not list
  - Modified: `src/pipeline/pronunciation_guide/enricher.py` - added dict handling + validation
  - Modified: Improved ENRICHER_BATCH_PROMPT to emphasize array format

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | No IPA data (0/70 entries) | src/pipeline/pronunciation_guide/enricher.py | Fixed - awaiting analysis |

## Next Action
Set phase to `awaiting_analysis` and re-run analysis to verify IPA generation now works.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) - appropriate for all stages
- Context length: 32768 - sufficient
- Temperature: 0.7 - reasonable for this task

### Processing Notes (from `_profiling`)
- No LLM retries or JSON parse failures
- Character Profiles stage: 5 characters processed with high confidence
- Pronunciation Guide: 70 items processed, 18 high confidence, rest medium

### Root Cause Analysis for IPA Issue
The pronunciation pipeline is identifying words to flag (70 items) but not generating IPA for any of them. This suggests:
1. IPA generation step may be disabled or failing silently
2. External IPA lookup service may not be configured
3. LLM-based IPA generation may not be implemented for this pipeline

Investigation needed in `src/pipeline/pronunciation/` to determine why IPA output is null for all entries.
