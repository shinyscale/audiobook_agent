# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_evaluation

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | TBD | - | Completed 23m 20s — awaiting evaluation |

## Pipeline Errors (Attempt 1) — FIXED
1. `LLM marker proposer returned non-list: <class 'dict'>` — non-critical warning, already handled by fallback in llm.py:232
2. `Summarization failed for chapter 1: name 'text' is not defined` — **FIXED**: `_consolidate_chunks` in summarizer.py:858 referenced undefined `text` var; removed the unused kwarg (uses default `""`)
3. `CharacterMap.__init__() got an unexpected keyword argument 'source_file'` — **FIXED**: Two fallback calls in analyzer.py:917 and 1142 passed invalid `source_file` kwarg; replaced with correct fields (`low_confidence_characters=[], total_mentions=0, total_chapters=0`)

## Pipeline Notes (Attempt 2)
- Analysis completed in 23m 20s (exit code 0)
- 4 characters found: Mr. White (aka Herbert White), the monkey's paw, Herbert White (aka Herbert), Morris
- Mrs. White: detected, blocked as alias of Mr. White by Rule 0.4 (different titled people), then dropped — MISSING from output
- Non-fatal warning: `Step 6.95 structural narrator fix failed: 'ChapterSummarizer' has no attribute '_fix_narrator_attribution'`
- Pronunciation: 14 words flagged (9 unknown, 3 homograph, 2 proper noun)
- Structure: treated as 1 chapter (no high-confidence boundaries found)

## Output Files
- HTML: ../output/monkeys_paw/report.html (37794 bytes, Apr 10 12:26)
- JSON: ../output/monkeys_paw/analysis.json (91330 bytes, Apr 10 12:26)

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py and summarizer.py

## Notes
Attempt 2 completed successfully. Ready for evaluation.
