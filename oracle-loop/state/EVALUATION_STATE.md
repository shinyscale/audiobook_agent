# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Latest Scores
(Awaiting evaluation)

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Pipeline Notes

**Completion:** Analysis completed successfully in 11m 56s

**Structure:**
- Detected as single-chapter short story (expected)
- 4,287 words, ~28 minute read time

**Characters:**
- Extracted 8 characters total
- 4 major characters with profiles: Lincoln Stewart, Milton Jennings, Rance, Bert
- Narrator detected: Lincoln Stewart (first-person)

**Quality Concerns:**
- 3 low-confidence character profiles (Lincoln Stewart, Milton Jennings, Rance - all 0.30)
- JSON parsing failures for some character profiles (moral valence classification failed)
- 53/69 pronunciation flags are "unknown" (may indicate over-flagging)

**Competitive Consensus:**
- Enabled for all stages (characters, structure, summaries)
- Mode: single (same model at 3 temperatures)
- 11 LLM calls for chapter detection
- 10 LLM calls for character extraction

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (awaiting evaluation) | - | - | - |

## Notes
Analysis complete. Ready for evaluation phase.
