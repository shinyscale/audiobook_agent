# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Single chapter detected (short story)
- 5 characters extracted: Johnny (narrator), John Donaldson (Father), Uncle Bill, Joe Barron, Ted Frith
- 2 characters added from chapter summaries (F6 reconciliation)
- Margaret Donaldson added from mentioned_characters
- Narrator detected: Johnny (first-person)
- 4 profiles generated
- 14 pronunciation flags
- Total runtime: 16m 47s

## Pipeline Warnings
- LLM validation failed on chapter boundary parse (fell back to single chapter — correct for this text)
- Pass 2 failed for Uncle Bill (no aliases added)
- Several alias BLOCKED messages (cross-character conflicts detected and correctly blocked)
- "The dying man" extracted as separate character — may be phantom duplicate of John Donaldson (Father)

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
First analysis run. "The dying man" as separate character warrants attention during evaluation.
