# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 7.80 (from attempt 1)

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 6/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Hallucinated character: Mad'selle Salle extracted as a character who interacts with Egaeus**
   - Problem: "Mad'selle Salle" (Marie Sallé) is NOT a character in the story. She was a famous 18th-century French dancer mentioned ONLY in a literary/poetic comparison: "Of Mad'selle Salle it has been well said, 'que tous ses pas etaient des sentiments'" (her every step was a sentiment)
   - Evidence: The text uses her as an example of expressive movement, comparing it to how Egaeus perceives Berenice's teeth as "ideas" (des idées)
   - Impact: This false character has been assigned relationships ("guardian" to Berenice, "informant" to Egaeus) and appears in the chapter summary as delivering news of Berenice's death - ALL of this is hallucinated
   - Location: Likely `src/pipeline/character_extraction_v2/main_cast.py` - the LLM misinterpreted a literary reference as a character
   - Fix: The character extraction prompts need to distinguish between:
     - Characters who ACT in the story (extract)
     - Historical/literary figures mentioned for comparison (do not extract)

2. **Hallucinated plot point in chapter summary: "Mad'selle Salle informs Egaeus of Berenice's death"**
   - Problem: The chapter summary states: "Upon learning from Mad'selle Salle that Berenice died suddenly..."
   - Evidence: In the actual story, an unnamed "menial" servant informs Egaeus of Berenice's death. Mad'selle Sallé is never portrayed as interacting with any character
   - Impact: This hallucination propagates the false character into the narrative summary, making it doubly confusing for narrators
   - Location: `src/pipeline/chapter_summary/summarizer.py` - LLM generated false information based on name proximity in text
   - Fix: This may be a downstream effect of Issue #1. If Mad'selle Salle is not extracted as a character, the summary LLM may not hallucinate her role

### HIGH
3. **Missing character: The unnamed servant**
   - Problem: The menial servant who actually informs Egaeus of Berenice's death is not extracted
   - Evidence: Evidence item ev-2-6 correctly states "Egaeus learns of Berenice's death from a servant" - so the profiling caught it, but no character entry exists
   - Impact: The narrator doesn't know about this minor but significant character
   - Location: Character extraction filtering - possibly filtered due to lack of name
   - Fix: Consider extracting unnamed but plot-significant characters with descriptive names like "The Servant"

### MEDIUM
4. **Character profile fields incomplete for Egaeus**
   - Problem: Physical appearance shows "unknown" but Egaeus describes himself in some detail (mentions being "ill" and discusses his library/study habits extensively)
   - Evidence: Profile shows "Appearance: unknown" but personality/voice guidance are well-populated
   - Location: `src/pipeline/character_profiling/` - physical description extraction may need narrator-specific handling
   - Fix: For first-person narrators, extract self-descriptive statements more carefully

5. **Mad'selle Salle relationships are entirely fabricated**
   - Problem: She's listed as "guardian" to Berenice and "informant" to Egaeus - both are invented
   - Evidence: Neither relationship exists in the text; she appears only in a single comparative sentence
   - Impact: If Issue #1 is fixed (don't extract her), this issue resolves automatically
   - Location: `src/pipeline/character_profiling/relationship_extractor.py`
   - Fix: Cascades from fixing Issue #1

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (correct per USER_NOTES.md)
- Pronunciations: Excellent (82 with 100% IPA coverage)
- Structure: Appropriate for a short story (1 continuous piece)

## Fix History
- Attempt 1: Initial analysis, scored 7.80/10 - same issues present
- Attempt 2: Fixed Mad'selle Salle hallucination (two-layer fix)
  - **Root cause:** Summary LLM extracted literary references as if they were story participants; F6 blindly trusted summary character lists
  - **Data flow trace:**
    1. Source text: "Of Mad'selle Salle it has been well said..." (literary comparison in quoted French)
    2. Summary LLM: Listed "Mad'selle Salle" in `active_characters` (should have been in `mentioned_characters` or omitted)
    3. F6 Reconciliation: Created Character with hash ID `977f29a86b3a` (no grounding verification)
    4. Summary generation: Hallucinated "Mad'selle Salle informs Egaeus of Berenice's death" (false narrative)
  - **Fix #1 (Upstream - summarizer.py):** Added prompt guidance to exclude historical/literary figures mentioned only in comparisons/quotations
  - **Fix #2 (Defensive - analyzer.py F6):** Added grounding verification before creating characters from summary lists
  - **Smoke test:** Pending re-analysis
  - **Modified:**
    - `src/pipeline/chapter_summary/summarizer.py` (lines 115-126, 186-197)
    - `src/analyzer.py` (lines 1640-1690)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | N/A | Baseline established |
| 2 | Mad'selle Salle hallucination | summarizer.py, analyzer.py | Awaiting verification |

## Next Action
Re-run analysis to verify the two-layer fix for hallucinated literary references:
1. Summary prompts now exclude historical/literary figures mentioned only in comparisons
2. F6 reconciliation now verifies grounding in raw text before creating characters

Expected outcomes:
- Mad'selle Salle should NOT appear in summaries' `active_characters` lists
- If she does appear (prompt guidance fails), F6 will reject her (0 grounding mentions)
- Summary narrative should NOT include hallucinated interactions with Mad'selle Salle
- The unnamed servant should still not be extracted (separate issue - needs descriptive character support)
