# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
Analysis complete. Pipeline ran successfully.

### Pipeline Observations
- Structure: "LLM marker proposer returned non-list: <class 'dict'>" warnings (known issue with qwen3-next model)
- Character extraction: Alias blocking working correctly (comma phrases, hallucinated aliases, cross-character conflicts all blocked)
- Notable alias blocks: "The green light" aliases blocked (dock/bay core noun mismatch), "Dan Cody's yacht" blocked as cross-character, comma-phrase aliases for George Wilson blocked
- Profiling: Secondary LLM call for Doctor T. J. Eckleburg (empty relationships after filtering); Gardener/Butler/Chauffeur had no passages
- Contradictory relationships removed: Henry C. Gatz↔James Gatz (both labeled parent), Dan Cody↔James Gatz (both labeled mentor)
- Pronunciation: Several json_mode validation errors (model preamble/refusals); LLM validation failed (got dict), kept batch candidates
- Gutenberg boilerplate removed: 19320 chars (6.7%)
