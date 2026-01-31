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
- Last modified: 2026-01-31 02:51 (attempt 1 analysis complete)

## Pipeline Notes

**Analysis completed in 154m 15s**

### Warnings/Issues Encountered:
1. **Profile generation errors**:
   - `name 'pipeline_char_map' is not defined` for characters: Werter, the people of the inn
   - This prevented profile generation for these characters

2. **Pronunciation guide LLM failures**:
   - Multiple batches failed with model returning error objects instead of JSON arrays
   - qwen3-next appears to have issues with pronunciation prompts requesting arrays
   - Example errors: "Invalid JSON format. Expected an array but received an object."

3. **Missing main characters**:
   - Victor Frankenstein not found in main_cast (likely a major issue)
   - Robert Walton (narrator) not found in main_cast
   - Alphonse Frankenstein had no passages provided

4. **Structure detection**:
   - TOC validation: 31 entries seemed too many (likely page numbers)
   - Only 27 boundaries found vs 31 expected
   - Final result: 28 chapters detected

### Pipeline Statistics:
- Chapter Detection: 11m59s, 87 LLM calls, 166K tokens
- Chapter Summaries: 42m43s (27.7% of total time - bottleneck)
- Character Extraction: 17m2s, 112 LLM calls, 241K tokens
- Character Profiles: 39m42s, 61 LLM calls, 263K tokens (7 low-confidence)
- Pronunciation Guide: 41m20s, 457 LLM calls, 190K tokens
- **Total**: 154m15s, 717 LLM calls, 860K tokens

### Output Summary:
- 28 chapters
- 33 characters (24 from extraction + 9 from summaries)
- 459 pronunciation flags (386 unknown, 32 proper_noun, 21 homograph, 20 foreign)
- Top characters: Elizabeth Lavenza (92m), Henry Clerval (82m), Justine Moritz (55m), William Frankenstein (52m)

## Next Action
Evaluation phase will assess quality and assign scores.
