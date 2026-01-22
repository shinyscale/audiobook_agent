# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null

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
Analysis completed successfully in 10m 11s using V2 character extraction.

### Key Statistics:
- 3,954 words analyzed
- 3 chapters detected
- 3 characters extracted (V2 summary-driven approach)
- 3 character profiles generated
- 52 pronunciation flags
- 22 LLM calls total (45,106 tokens)

### Pipeline Performance:
- Chapter Detection: 23.8s (8 LLM calls)
- Chapter Summaries: 5m 22s (3 LLM calls) - bottleneck (52.6% of time)
- Character Extraction V2: 26.2s (2 LLM calls)
- Character Profiles: 3m 55s (9 LLM calls)
- Pronunciation Guide: 2.7s (0 LLM calls)

### Warnings:
- Removed Gutenberg boilerplate (46.4% of original text)
- LLM identity detection failed (500 error) - did not affect core analysis
- Failed to generate plot summary via LLM - did not affect core analysis
