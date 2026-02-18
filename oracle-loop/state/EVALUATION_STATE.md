# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score: 4.65**

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 0/10 ✗ (CRITICAL FAILURE)
  - Completeness: 0/10
  - Identity Resolution: N/A (no characters to evaluate)
  - Alias Grouping: N/A (no characters to evaluate)
- Character Profiles: 0/10 ✗ (CRITICAL FAILURE - blocked by character extraction)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 4.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Character extraction produced ZERO characters** [Completeness]
   - Problem: The characters array in analysis.json is completely empty `[]`
   - Evidence: Profiling shows Character Extraction ran with 2 LLM calls and 15.1 seconds of processing, but `items_processed: 0`. The LLM returned data (227 completion tokens across 2 calls) but nothing was successfully parsed or retained.
   - Expected characters: Montresor (narrator, 50+ mentions), Fortunato (50+ mentions), Luchesi/Luchresi (6 mentions)
   - The chapter summary correctly identifies both Montresor and Fortunato, proving the text is valid
   - Location: `src/pipeline/character_extraction_v2/` — likely `main_cast.py` parsing failure. The LLM returned something but it was rejected/unparseable. Check `_parse_pass1_results()` or `_parse_profiles()`.
   - Possible root cause: The text is very short (~2354 words, single section). The character extraction chunking (`character_llm_chunk_chars: 5000`) may be creating a single small chunk that the LLM handles differently. Or the LLM response format doesn't match expected schema. Need to check logs.
   - Fix approach: Run with DEBUG logging to see what the LLM returned and why it was rejected. The 227 completion tokens suggest a response was generated — investigate parsing.

### HIGH
2. **Character profiles completely empty** [blocked by #1]
   - Problem: 0 LLM calls for Character Profiles — stage was skipped because no characters exist
   - Evidence: Profiling shows `duration_seconds: 0.0, llm_calls: 0` for Character Profiles
   - Location: Will resolve automatically when character extraction is fixed
   - Fix: Fix issue #1 first

3. **Pronunciation guide has excessive false positives** [Pronunciation]
   - Problem: ~10 of 35 entries are common English words that don't need pronunciation guidance
   - False positives: "tight-fitting", "parti-striped", "to-day", "web-work", "cough's", "leer", "Grave", "entrance", "Unsheathing", "reapproached", "re-echoed", "re-erected", "hearkened"
   - Evidence: These are standard English words or simple hyphenated/prefixed forms. A narrator would not need pronunciation help for "leer" or "entrance"
   - Good entries that should be kept: Amontillado, Luchresi, flambeaux, roquelaire, requiescat, impune lacessit, nitre, gemmary, rheum, puncheons, flagon, connoisseurship, imposture, gesticulation, Montresor(s)
   - Missing: "Fortunato" (Italian name that narrators should have guidance for)
   - Location: `src/pipeline/pronunciation/` — the flagging threshold may be too aggressive for short texts, or the word filtering isn't excluding common English words
   - Fix: The false positive rate (~30%) needs to come down. Focus on filtering out standard English words and simple prefix/hyphenation compounds

### MEDIUM
4. **Structure section title is null**
   - Problem: The single section has `"title": null` instead of a meaningful title
   - Evidence: `jq '.structure[0].title' analysis.json` returns `null`
   - Location: `src/pipeline/chapter_detection/` — for a continuous text with no headings, the title could default to the work's title or "Full Text"
   - Impact: Minor — doesn't affect narrator preparation significantly

## Fix History
(First attempt — no previous fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| — | — | — | — |

## Next Action
Run PROMPT_fix.md to address character extraction failure (Critical #1). This is the blocking issue — until characters are extracted, profiles will also score 0. Pronunciation false positives (High #3) should be addressed second.

**Diagnosis priority for fix phase:** The 2 LLM calls with 227 completion tokens prove the model IS responding. The failure is in parsing/processing the response. Run with `DEBUG` logging or inspect `main_cast.py` parse methods to see what the model returned vs. what the parser expected.
