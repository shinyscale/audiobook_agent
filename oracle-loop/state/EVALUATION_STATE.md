# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Completed in 13m 50s
- Structure: 1 chapter detected (no high-confidence chapter boundaries found in PDF text)
- Characters: 7 characters extracted (6 profiles generated)
- Warnings:
  - JSON parsing failure for Nimdok character profile
  - Low confidence profile for Nimdok (0.30)
  - Removed repeating header from PDF
  - Rejoined 47 split words at line breaks
- Pipeline profiling: Character Profiles was bottleneck (38.8% of time)
- 47 LLM calls, 75K tokens total
- Competitive consensus enabled on all 3 stages (characters, structure, summaries)
