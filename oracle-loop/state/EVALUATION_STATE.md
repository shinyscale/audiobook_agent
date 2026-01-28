# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Pipeline Notes
- Analysis completed in 9m 59s
- Found 1 chapter, 9 characters (Lincoln, Milton, Rance, Bert, Jennings + 4 more)
- 70 pronunciation flags
- Competitive consensus enabled for all stages (characters, structure, summaries)
- Some warnings: "LLM marker proposer returned non-list", "No passages provided" for some characters
- Character profile generation used json_mode fix successfully (no JSON parsing errors)

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## External Changes Applied

### Human Intervention: Reverted Salvage Code, Applied Root Cause Fix

**Date:** 2026-01-28

**Problem:** Character profile JSON parsing was failing for a_camping_trip. The oracle loop applied two fixes:
1. `337b2be` - Brace-balanced JSON extraction + thinking tag stripping
2. `9d4f9e0` - Regex-based structured field salvaging (~140 lines)

These fixes chased symptoms (salvaging malformed JSON after the fact) rather than addressing the root cause.

**Human Analysis:** The root cause was that the LLM (qwen3-next:80b) was emitting malformed JSON because nothing was enforcing JSON output format at the provider level.

**Action Taken:**
1. Reverted both salvage commits (`5828830`)
2. Applied root cause fix (`bb5ca45`): Enable `json_mode` for LLM providers
   - `LLMClient.query()` now accepts `json_mode=True` parameter
   - Ollama: Sets `format: "json"` to enforce JSON at token-sampling level
   - OpenAI: Sets `response_format: {"type": "json_object"}`
   - Character profile generation now uses `json_mode=True`

**Why This Is Better:**
- Provider-enforced JSON is fundamentally more reliable than post-hoc regex recovery
- ~14 lines of code vs ~140 lines of brittle salvage heuristics
- Works for ANY JSON-expecting call, not just observed failure patterns

**Restart:** Analysis should be re-run from scratch with the json_mode fix in place.

## Notes
Starting fresh analysis for a_camping_trip with json_mode fix applied.
