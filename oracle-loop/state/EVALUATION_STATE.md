# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 8.25
- **Competitive Mode:** single

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Current Issues (Priority Order)

### CRITICAL
None

### HIGH
1. **"the library" incorrectly extracted as a character**
   - Problem: The library (a setting/location) is listed as a character with 6 mentions
   - Evidence: The library is where events happen (Egaeus born there, mother died there, confronts Berenice there) but it has no agency or dialogue. It's a setting, not a character.
   - Expected: Only Egaeus, Berenice, and the servant should be characters
   - ID pattern: `main_cast_3` - came from main cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - location extraction should be filtered
   - Fix: Add validation to reject common setting words (library, house, mansion, garden, etc.) from character extraction, OR improve the character vs. setting classification in the main_cast pipeline

### MEDIUM
2. **Missing relationship between Egaeus and Berenice**
   - Problem: HTML shows "No explicit relationships detected" but Egaeus and Berenice are cousins AND betrothed
   - Evidence: Text states "Berenice!—I call upon her name—Berenice!—and from the gray ruins of memory a thousand tumultuous recollections are startled at the sound!... she my cousin, and we grew up together in the halls"
   - Location: Character profile generation or relationship extraction
   - Fix: Ensure relationships are populated from profile evidence
   - Impact: Minor - profiles have other useful info, but relationship is important for narrator

3. **Some unnecessary pronunciation false positives**
   - Problem: Common words flagged unnecessarily: "thirty-two", "ringlets", "noonday", "day-dreamer", "refracted"
   - Evidence: These are common English words that any native speaker would know
   - Location: `src/pipeline/pronunciation/` - filtering logic
   - Fix: Add common word filtering to reduce false positives
   - Impact: Low - the Latin and proper noun coverage is excellent, just some noise

### LOW
None

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.25 | - | Baseline. Library extracted as character (HIGH), missing relationships (MEDIUM) |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Filter "the library" location extraction | src/pipeline/character_extraction_v2/main_cast.py | Awaiting verification |

## Pipeline Notes
- Analysis completed in 10m 53s
- Competitive consensus enabled for all stages (characters, structure, summaries)
- Characters: 4 detected (Berenice, the library, servant maiden, Egaeus)
- Narrator: Egaeus (first-person) ✓ Correct
- Validation working: blocked 'the narrator' meta-reference, blocked inanimate object aliases
- Word count: 3,240 words
- Pronunciation flags: 80 entries (all with IPA)

## Fix History

### Attempt 2: Filter mundane location extractions
- **Root cause:** `src/pipeline/character_extraction_v2/main_cast.py:extract()` line 390-392
  - Comment noted non-sentient entity filter was removed to allow symbolic objects (e.g., "the monkey's paw")
  - But this also allowed mundane locations like "the library" to pass through
  - The LLM extracted "the library" from summaries because it appears frequently and seems important to narrative
- **Fix approach:** Programmatic post-processing filter (preferred over prompt changes per Fix Philosophy)
  - Added `_filter_mundane_locations()` method (lines 1295-1360)
  - Filters mundane location keywords (library, room, house, garden, etc.) from canonical names
  - Preserves symbolic objects marked with `is_symbolic=True`
  - Called after alias verification, before competitive consensus (line 391)
- **Smoke test:** N/A (would take too long - proceeding to full re-analysis)
- **Expected outcome:** "the library" should be filtered out, leaving only Egaeus, Berenice, and servant

## Next Action
Re-run analysis to verify fix
