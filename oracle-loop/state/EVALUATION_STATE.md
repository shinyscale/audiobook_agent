# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Latest Scores
(Awaiting evaluation of attempt 2)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |

## Fix History

### Attempt 1 → 2: Fixed tuple unpacking error in character profiling

**Root cause:** `src/analyzer.py:2657` - `_generate_character_profile()` early return
- Function signature declares 7-element tuple return: `(profile, evidence, confidence, appearance, personality, voice_guidance, relationships)`
- Line 2657 (early return when no contexts available) returned only 6 elements: `"", [], 0.0, None, None, None`
- Missing final element: `relationships`

**Fix:** Added missing `None` for relationships parameter
- Changed: `return "", [], 0.0, None, None, None`
- To: `return "", [], 0.0, None, None, None, None`

**Smoke test:** ✓ Python syntax validation passed
**Verification:** All return statements in the function now return 7 elements (lines 2657, 3265, 3266, 3281, 3295)

**Modified:** `src/analyzer.py:2657`

## Output Files
- HTML: ../output/gatsby/report.html (907K, Jan 30 08:47)
- JSON: ../output/gatsby/analysis.json (372K, Jan 30 08:47)

## Pipeline Notes
**Completed successfully in 253m 13s**

Pipeline statistics:
- 9 chapters detected
- 28 characters extracted (20 with profiles)
- 493 LLM calls, 410,318 tokens
- Bottleneck: Pronunciation guide (52.8% of runtime)

Non-fatal warnings during execution:
- LLM marker proposer returned dict instead of list (20 occurrences during structure detection)
- Narrator detection initially failed to find "Nick Carraway" in main_cast (later resolved)
- `pipeline_char_map` undefined for 3 minor characters (Lucille, Rosy, Owl-Eyes)
- LLM validation failures in pronunciation phase (got dict format)

Tuple unpacking fix verified: No crashes, pipeline completed all phases.

## Next Action
Evaluate output quality and assign score
