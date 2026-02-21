# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_184428/

## Pipeline Notes
- Analysis completed successfully in 9m 42s
- 5,048 words extracted (short story)
- 1 chapter detected (no structural divisions)
- 4 characters found: John (16 mentions), Uncle Bill/Bill (18 mentions), John Donaldson (7 mentions), Joe Barron (3 mentions)
- 3 character profiles generated (3 eligible)
- 27 pronunciation flags (13 unknown, 5 foreign, 5 homograph, 4 proper_noun)

## Warnings
- "LLM marker proposer returned non-list: <class 'dict'>" x2 — chapter detection fallback triggered
- "No valid proposals - returning single chapter" — single chapter result
- Narrator 'John Donaldson (the uncle)' identified but NOT found in main_cast — narrator detection issue
- "No passages provided for John / John Donaldson, returning UNCERTAIN" — profile confidence uncertain
- "Ollama json_mode validation error" — non-critical, batch candidates kept

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | TBD | - | First analysis |
