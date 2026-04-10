# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** null
- **Competitive Mode:** none

## Latest Scores
(Analysis failed — awaiting fix)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |

## Pipeline Errors (Attempt 1)
1. `LLM marker proposer returned non-list: <class 'dict'>` — structure detection returning dict instead of list; fell back to 1 chapter
2. `Summarization failed for chapter 1: name 'text' is not defined` — NameError in summarizer
3. `CharacterMap.__init__() got an unexpected keyword argument 'source_file'` — **main crash**: CharacterMap constructor called with unknown kwarg

## Output Files
- HTML: ../output/monkeys_paw/report.html (not generated)
- JSON: ../output/monkeys_paw/analysis.json (not generated)

## Notes
Fresh run — manifest reset from beginning. Starting analysis for monkeys_paw.
Pipeline crashed before producing output. Needs fix phase to address the three errors above.
