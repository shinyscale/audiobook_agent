# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Attempt 1 Pipeline Output (Run Notes)

### Characters Found (3 final)
```
Egaeus - 1 mention  [protagonist/narrator - first-person]
Berenice - 14 mentions  [title character]
Ebn Zaiat - 2 mentions  [minor]
(4 extracted, 3 in final output)
```

### Pipeline Notes
- 1 chapter (no chapter boundaries — treated as single chapter short story)
- 3 profiles generated for 3 eligible characters
- 44 pronunciation flags (26 unknown, 13 proper_noun, 5 foreign)
- 3,240 words, 18m 30s total

### Warnings / Anomalies
- Narrator detection inconsistency: "Egaeus has only 1 mention — too few to be a narrator; skipping narrator assignment" BUT later pipeline stage says "Detected narrator: Egaeus (first-person)" AND "No definitive narrator identified from plot summary"
  - Final output: No narrator marked (narrator detection failed at end)
  - Berenice is 1st-person story told by Egaeus — this is a known issue
- Relationship "cousin" blocked: both Egaeus→Berenice and Berenice→Egaeus labeled "cousin" — removed as logically impossible symmetric non-symmetric label
  - (They ARE cousins — the label is correct, just the inverse-consistency logic rejects it)
- BLOCKED alias: 'the first-person narrator' for 'Egaeus' — hallucinated
- BLOCKED alias: 'the visionary' for 'Egaeus' — hallucinated
- BLOCKED alias: 'her grave' for 'Berenice' — hallucinated

### Models Used
- structure: qwen3.5:35b-a3b
- characters: qwen3.5:122b-a10b
- summaries: qwen3.5:122b-a10b
- pronunciation: qwen3.5:35b-a3b
