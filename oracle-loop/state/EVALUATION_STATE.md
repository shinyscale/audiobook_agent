# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_analysis

## Latest Scores
(Analysis failed — awaiting fix)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |

## Pipeline Errors (Attempt 1) — FIXED
1. `LLM marker proposer returned non-list: <class 'dict'>` — non-critical warning, already handled by fallback in llm.py:232
2. `Summarization failed for chapter 1: name 'text' is not defined` — **FIXED**: `_consolidate_chunks` in summarizer.py:858 referenced undefined `text` var; removed the unused kwarg (defaults to `""`)
3. `CharacterMap.__init__() got an unexpected keyword argument 'source_file'` — **FIXED**: Two fallback calls in analyzer.py:917 and 1142 passed invalid `source_file` kwarg; replaced with correct fields (`low_confidence_characters=[], total_mentions=0, total_chapters=0`)

## Output Files
- HTML: ../output/monkeys_paw/report.html (not generated)
- JSON: ../output/monkeys_paw/analysis.json (not generated)

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py and summarizer.py
  - Root cause 1: `summarizer.py:_consolidate_chunks:858` — `chapter_text=text` but `text` not in scope; omitted kwarg (uses default `""`)
  - Root cause 2: `analyzer.py:917,1142` — `PipelineCharacterMap(source_file=...)` but `CharacterMap` dataclass has no `source_file` field; replaced with correct empty-map fields
  - Smoke test: syntax validation passed; `CharacterMap()` instantiation verified

## Notes
Fresh run — manifest reset from beginning. Starting analysis for monkeys_paw.
Pipeline crashed before producing output. Two bugs fixed; re-running analysis.
