# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Pipeline Notes
- Completed in 128m 32s
- 75,060 words, 28 chapters detected (TOC expected 31, found 27 boundaries → 28 output)
- 19 characters (24 extracted, +7 from summary reconciliation, merged to 19 final)
- 206 pronunciation flags (145 unknown, 24 proper_noun, 21 homograph, 16 foreign)
- 433 LLM calls, 660,116 tokens
- Competitive consensus: ENABLED (3 temps, stages: characters, structure, summaries)
- Warnings:
  - TOC: 31 entries expected, only 27 boundaries found → 28 chapters
  - "LLM marker proposer returned non-list: <class 'dict'>" (30x during structure detection — known issue)
  - Several Ollama JSON validation errors in pronunciation guide (recovered)
  - Several alias blocks (meta-references, co-occurrence check failures)

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
First analysis run complete. Ready for evaluation.
