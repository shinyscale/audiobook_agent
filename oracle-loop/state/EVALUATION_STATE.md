# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Pipeline Notes
- Analysis completed successfully in 32m 7s
- 5 characters extracted: Mr. White, Mrs. White, Herbert White, Sergeant-Major Morris, monkey's paw
- 1 chapter detected (single chapter text)
- 25 pronunciation flags generated
- Warnings during analysis:
  - F19: Some ungrounded evidence quotes detected for multiple characters (13 for Mr. White, 3 for Mrs. White, 4 for Herbert, 4 for Morris, 1 for paw)
  - 1 JSON parse failure in pronunciation LLM batch enrichment
  - "it" and "the cursed object" correctly BLOCKED as invalid aliases for "monkey's paw"
- Competitive consensus: ENABLED (3 LLMs at different temperatures, 2/3 supermajority)
- Stages: characters, structure, summaries (all enabled)
