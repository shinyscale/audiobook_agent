# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Pipeline Notes
Analysis completed successfully in 10m 15s.

**Pipeline output:**
- Found 1 chapter (short story)
- Extracted 5 characters: John G. (15 mentions), John (19 mentions), Corporal Richardson, Captain Adams, First Sergeant Price
- Generated 2 character profiles (2 eligible characters)
- Flagged 48 pronunciation words
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority) - stages: characters, structure, summaries

**Warnings during execution:**
- LLM marker proposer returned non-list (structure detection)
- LLM validation failed (got dict) - kept batch candidates
- Some Ollama json_mode validation warnings

**Performance:**
- Bottleneck: Pronunciation Guide (41.7% of time, 4m17s)
- Total LLM calls: 55
- Total tokens: 42,238

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (awaiting evaluation) | - | - | - |

## Notes
Analysis complete. Ready for evaluation phase.
