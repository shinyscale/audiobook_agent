# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 15
- **Phase:** awaiting_fix
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 8/10 (unchanged)
- Character Extraction: 8/10 ← IMPROVED from 7/10
- Character Profiles: 7/10 (unchanged)
- Chapter Summaries: 9/10 (unchanged)
- Pronunciation Guide: 6/10 ← IMPROVED from 5/10
- HTML Presentation: 9/10 (unchanged)
- **Overall: 7.95/10** (threshold: 8.0)

## Score Calculation

```
Overall = (8 × 0.20) + (8 × 0.25) + (7 × 0.15) + (9 × 0.20) + (6 × 0.10) + (9 × 0.10)
        = 1.60 + 2.00 + 1.05 + 1.80 + 0.60 + 0.90
        = 7.95/10
```

## Evaluation Details

### Attempt 15 Results - NEARLY PASSING!

**What Attempt 15 Fixed:**
1. ✅ **"the old man" merged with Mr. White** - F6 filter correctly identified epithet
2. ✅ **"the old woman" orphan removed** - Character count down from 7 to 6
3. ✅ **Common words filtered from pronunciation** - "old", "man", "woman", "son" etc. now excluded
4. ✅ Pronunciation count reasonable (73 entries)

**Current Character List (6 characters):**
1. Mr. White (25 mentions) with alias "the old man" - EXCELLENT
2. Mrs. White (10 mentions) - Good (no aliases)
3. Herbert White (15 mentions) with aliases "Herbert", "the son" - EXCELLENT
4. Sergeant-Major Morris (6 mentions) with alias "Morris" - Good
5. the monkey's paw (14 mentions) with aliases "the talisman", "the paw" - Good
6. Stranger from Maw and Meggins (1 mention) - OK

**Character Extraction improved from 7/10 to 8/10** because:
- The orphan "the old man" is now correctly an alias of Mr. White
- The orphan "the old woman" entry is gone (though not explicitly aliased to Mrs. White)
- All major characters properly represented with appropriate aliases

**Pronunciation Guide improved from 5/10 to 6/10** because:
- Common English words successfully filtered
- Proper nouns and unusual words correctly preserved: fakirs, rubicund, Laburnam, antimacassar

## Current Issues (Priority Order)

### HIGH

1. **Project Gutenberg boilerplate in pronunciation guide**
   - Problem: "GutenbergTM", "eBooks", "PGLAF", "MERCHANTABILITY" appear in pronunciation list
   - Evidence: These are legal/trademark terms from the Project Gutenberg license text, not story content
   - Location: `src/ingestion/` - back matter stripping should catch this
   - Fix: Add patterns to detect and strip Project Gutenberg license text from ingestion
   - Impact: +0.5 points to Pronunciation (6→6.5), pushes overall from 7.95 to 8.00

### MEDIUM

2. **"the old woman" not explicitly aliased to Mrs. White**
   - Problem: While the orphan entry is gone, Mrs. White doesn't have "the old woman" as an alias
   - Evidence: Part III uses "the old woman" to refer to Mrs. White
   - Location: F6 filter removes the orphan but doesn't add the alias
   - Fix: F6 filter should add filtered epithets as aliases to matching characters
   - Impact: Minor polish, doesn't affect score significantly

3. **Chapter titles showing as "null"**
   - Problem: All three chapters have `title: null` instead of "Part I", "Part II", "Part III"
   - Location: `src/pipeline/chapter_detection/` - title extraction
   - Fix: Improve title regex for "Part X" format
   - Impact: Would improve Structure from 8 to 9 but not critical

4. **Homographs flagged but possibly excessive**
   - Words: does, read, wind, live, present, minute, object, produce, separate, alternate, subject
   - These are technically correct (multiple pronunciations) but may be noisy
   - Impact: Debatable - keeping for now as they ARE legitimate pronunciation ambiguities

## Fix History

| Attempt | Fix | Score | Delta |
|---------|-----|-------|-------|
| 5 | First successful run | 6.275 | baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 | +0.775 |
| 10 | Case sensitivity fix | 7.05 | +0.775 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | 6.70 | Regression |
| 12 | Added ambiguity check to `_validate_merge()` in LLM path | 7.00 | +0.725 |
| 13 | Gender conflict detection in epithet resolution | 7.00 | Fix didn't execute |
| 14 | **V2 character extraction (summary-driven)** | **7.60** | **+1.325** |
| 15 | F6 epithet filtering + pronunciation stopwords | **7.95** | **+1.675** |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix |
| 11 | 6.70 | +0.425 | Regression |
| 12 | 7.00 | +0.725 | Partial fix |
| 13 | 7.00 | +0.725 | Cache issue |
| 14 | 7.60 | +1.325 | V2 working! |
| **15** | **7.95** | **+1.675** | **Nearly passing!** |

## Path to 8.0

**Current: 7.95**
**Needed: +0.05 points**

The single easiest fix to cross the threshold:

1. **Strip Gutenberg boilerplate from ingestion**: Pronunciation 6→7 (+0.10 weighted)
   - Location: `src/ingestion/` needs pattern matching for Project Gutenberg license text
   - Words to exclude: "GutenbergTM", "eBooks", "PGLAF", "MERCHANTABILITY", etc.

Alternative paths:
- Fix chapter titles (Structure 8→9, +0.20 weighted) but more complex
- The Gutenberg fix is simpler and directly addresses the remaining false positives

## Configuration Audit

- Model: qwen3-next:80b-a3b-instruct-q8_0 for character extraction
- V2 character extraction (summary-driven) working efficiently
- LLM calls: 30 total, 64,411 tokens
- Character Extraction: Only 31.2s (vs 449s in V1 - 93% faster!)
- All characters have good confidence levels

## Next Action

**Phase:** awaiting_fix

Run PROMPT_fix.md to address Gutenberg boilerplate filtering. This single fix should push the score from 7.95 to 8.00+, achieving PASS status.

**Recommended fix:**
Add Project Gutenberg license text detection to `src/ingestion/refine.py` or the text preprocessing stage to strip legal boilerplate before analysis.
