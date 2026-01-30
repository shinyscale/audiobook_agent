# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** null
- **Competitive Mode:** single

## Latest Scores
(Analysis failed with error)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Pipeline Error (Attempt 1)

**Error:** `not enough values to unpack (expected 7, got 6)`

**Stage:** Character profiling (final stage after summaries completed)

**Context:**
- Structure detection: ✓ 9 chapters
- Summary generation: ✓ 9 summaries
- Character extraction: ✓ 27 characters found, 1 merged, 2 added from summaries
- Narrator detection: ✓ Nick Carraway (first-person)
- Character profiling: ✗ Tuple unpacking error

**Additional Warnings:**
- Multiple "LLM marker proposer returned non-list" warnings during structure detection
- "Narrator 'Nick Carraway' identified but NOT found in main_cast" warnings
- Profile generation failed for 'Lucille': `name 'pipeline_char_map' is not defined`

**Pipeline completed stages before failure:**
1. Ingestion (51,257 words)
2. Text refinement (removed Gutenberg boilerplate)
3. Chapter detection (9 chapters)
4. Summary generation (9 summaries)
5. Character extraction (29 total characters after merges)
6. Narrator detection (Nick Carraway)
7. Character profiling - **FAILED**

**Output files:**
- ../output/gatsby/analysis.json (OLD - from Jan 27, not updated)
- ../output/gatsby/report.html (OLD - from Jan 27, not updated)

## Notes
Analysis runtime: ~50 minutes before failure.
Error occurs during character profiling phase, likely in code that returns a tuple.
Need to investigate tuple unpacking in character profiling code.
