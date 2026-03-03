# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
(Awaiting first evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Pipeline Notes
- Analysis completed in 19m 59s (2,449 words — short story)
- Found 1 chapter (single continuous narrative, correct)
- Found 2 characters: Prince Prospero (6 mentions) and "the gigantic ebony clock" (16 mentions, aliased incorrectly as "the masked figure")
- BLOCKED alias warnings during character extraction:
  - "the intruder", "the Red Death", "a masked figure", etc. blocked from merging with "the masked figure" or "the Red Death" due to symbolic entity core-noun mismatch
  - "the thousand guests" for "the courtiers" blocked as not found in summaries
  - "the narrator" blocked as meta-reference for "the gigantic ebony clock"
- Red Death / masked figure appears to be MISSING from final character list (only Prince Prospero and the clock extracted)
- The clock being aliased as "the masked figure" is clearly wrong
- "Failed to generate plot summary via LLM" (minor — narrator detection fallback)
- 21 pronunciation flags generated
- 0 LLM retries
