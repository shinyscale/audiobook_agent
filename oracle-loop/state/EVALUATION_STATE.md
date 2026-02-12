# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 6.98

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 4/10 ✗
- Character Extraction: 8/10 ✓
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 7/10 ✗
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 6.98/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Structure detection missed three-part division (I., II., III.)**
   - Problem: "The Monkey's Paw" has 3 parts marked with Roman numerals ("I.", "II.", "III." on lines 45, 284, 411 of source text), but only 1 chapter was detected
   - Evidence: `grep -n "^I\.\|^II\.\|^III\." source_text` finds all three markers; structure output shows `chapter_count: 1`
   - Impact: Cascading failure — summaries and character-per-chapter tracking lose granularity
   - Location: `src/pipeline/chapter_detection/` — Roman numeral pattern with trailing period ("I.", "II.", "III.") not recognized as section markers
   - Fix: Ensure chapter detection regex patterns recognize standalone Roman numerals with periods (I., II., III.) as valid section dividers. Check `proposers/regex.py` and `proposers/llm.py` for pattern matching.

### HIGH
2. **Pronunciation artifacts: "himselfin" and "beliefin" are concatenated words from text refinement**
   - Problem: The text has "himself in" and "belief in" merged into single words during ingestion/refinement, and the pronunciation system flags them as unusual words
   - Evidence: These words don't exist in the original source text (`grep` returns nothing), but appear in the refined/processed text
   - Location: `src/ingestion/refine.py` — text refinement is concatenating words at line breaks or spaces
   - Fix: This is an upstream ingestion bug. Check if the refinement step incorrectly removes spaces. The pronunciation system is correctly flagging them (they ARE unusual), but the root cause is in text refinement.

3. **Chapter summaries lack per-section granularity**
   - Problem: With only 1 detected chapter, the entire story gets a single summary instead of 3 per-part summaries
   - Evidence: Summary covers all events accurately but a narrator needs to know what happens in each section
   - Impact: Directly caused by Critical #1 (structure detection failure)
   - Location: Resolves automatically when structure detection is fixed
   - Fix: Fix Critical #1 and this resolves itself

### MEDIUM
4. **Morris relationship to Mr. White labeled "victimizer" — inaccurate**
   - Problem: Sergeant-Major Morris is labeled as "victimizer" of Mr. White. Morris actually warns Mr. White against using the paw and tries to destroy it
   - Evidence: Text shows Morris saying "Better let it burn" and warning about consequences
   - Location: Character profiling LLM — relationship type assignment in `src/pipeline/character_profiling/`
   - Fix: This is an LLM interpretation issue; the relationship should be "friend" or "mentor" (as correctly labeled from Mr. White's perspective). The asymmetric labeling is the issue.

5. **Herbert's profile contains misattributed quote**
   - Problem: Herbert's voice guidance includes `"Sounds like the _Arabian Nights_," said Mrs. White...` — this is Mrs. White's line, not Herbert's
   - Evidence: The quote explicitly says "said Mrs. White"
   - Location: `src/pipeline/character_profiling/` — quote extraction/attribution
   - Fix: Quote attribution should check the speaker tag ("said X") before assigning to a character profile

6. **Mr. White's profile has hallucinated detail: "wears spectacles (implied by chess focus)"**
   - Problem: The text never mentions or implies spectacles; chess-playing doesn't imply glasses
   - Evidence: No mention of spectacles in the source text
   - Location: `src/pipeline/character_profiling/` — LLM physical description generation
   - Fix: LLM profiling issue; the system should only report explicitly stated physical details

7. **Pronunciation false positives: "sideboard", "sightless"**
   - Problem: Common English words flagged for pronunciation guidance
   - Evidence: These are standard vocabulary that any narrator would know
   - Location: `src/pipeline/pronunciation/` — word filtering
   - Fix: These should be caught by the common word exception list. Consider adding them or improving the frequency-based filtering.

### LOW
8. **HTML grammar: "1 chapters" instead of "1 chapter"**
   - Problem: Overview says "This book contains 1 chapters"
   - Location: HTML template in `src/pipeline/` or `src/export/`
   - Fix: Add singular/plural handling for chapter count display

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.98 | - | Baseline. Structure detection major failure (3 parts → 1 chapter) |

## Fix History
- Attempt 1 → 2: Fixed structure detection for Roman numerals with periods (I., II., III.)
  - Root cause: `src/pipeline/chapter_detection/proposers/regex.py` - `_extract_title()` method did not handle `pattern_type == "roman_numeral_with_period"`, causing titles to retain trailing period which broke sequential pattern detection
  - Modified: `src/pipeline/chapter_detection/proposers/regex.py` line 301
  - Test suite: All 298 tests pass (10 skipped)
  - Cascades fix: This will also fix the "Chapter summaries lack per-section granularity" issue (HIGH #3)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Structure detection missed I./II./III. markers | `src/pipeline/chapter_detection/proposers/regex.py` | Fixed: Added "roman_numeral_with_period" to pattern handling in `_extract_title()` |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (MoE) — appropriate
- No retries or JSON parse failures in any stage
- All characters high confidence — good
- `character_llm_chunk_chars: 5000` — adequate for this short story (~4000 words)
- Structure detection: 10 LLM calls for 1 item with medium confidence — suggests the LLM tried but couldn't find structure markers

## Next Action
Re-run analysis with structure detection fix applied. Expect:
- Structure: 3 chapters detected (I., II., III.)
- Summaries: 3 per-part summaries instead of 1 single summary
- Pronunciation artifacts (himselfin, beliefin) may resolve or may need separate investigation if they persist
