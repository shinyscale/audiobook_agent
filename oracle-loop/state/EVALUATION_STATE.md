# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Latest Scores (Attempt 6)
- Structure Detection: ~7.5/10 ✗ (27 chapters vs 28 expected)
- Character Extraction: ~6.5/10 ✗ (creature/dæmon merged ✓, Alphonse as "father" ✗)
- Character Profiles: ~7.0/10 ✗
- Chapter Summaries: ~2.0/10 ✗ (CATASTROPHIC - Elizabeth Lavenza misidentified as narrator)
- Pronunciation Guide: ~7.5/10 ✗ (Walton/Justine/Waldman/Clerval added ✓, Frankenstein missing ✗)
- HTML Presentation: 9.5/10 ✓
- **Overall: ~5.5/10** (regression from attempt 5)

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 2 | 7.75 | Profiles improved |
| 3 | 7.58 | Profiles regressed |
| 4 | 7.08 | Summaries regressed 6.5→4.0 (narrator substitution undid fix) |
| 5 | ~7.08 | Same root cause: Step 6.9 undoes narrator fix |
| 6 | ~5.5 | Regression: LLM hallucinated Elizabeth Lavenza as narrator throughout |

## Attempt 6 Root Cause Analysis
### Elizabeth Lavenza narrator hallucination
- LLM summarizer wrote "Elizabeth Lavenza" directly in summaries (despite prompt saying not to)
- Victor discusses Elizabeth so frequently, LLM confused the subject for the narrator
- `_fix_narrator_attribution` can't fix this: no structural signals for Victor's chapters
- Character extraction then CONFIRMED Elizabeth Lavenza as narrator (she had highest mentions after "father")
- Step 6.9 substituted "the narrator" → "Elizabeth Lavenza" where it appeared
- Result: nearly all 28 chapter summaries were wrong

### Narrator threshold too high (8%)
- NarratorDetector LLM correctly identified Robert Walton as narrator (in both detection passes)
- But 8% threshold: Walton has 8 mentions, max is 161 → 4.97% < 8% → REJECTED
- After rejection, heuristic (Step 5.8.6) selected highest-mention character → Elizabeth Lavenza

### "father" canonical name
- Alphonse Frankenstein extracted as canonical "father" (161 mentions)
- Reduced narrator candidate pool for the heuristic selection

## Fixes Applied for Attempt 7

### Fix 1: summarizer.py - Force "the narrator" placeholder
- Changed all 3 prompt instances from "use name if explicitly stated" → "ALWAYS use 'the narrator'"
- Prevents LLM from ever writing a character's name for the narrative voice
- Step 6.9 injects the correct narrator name during post-processing

### Fix 2: narrator.py - Lower threshold 8% → 4%
- Robert Walton: 8 mentions / 161 max = 4.97% → now passes 4% threshold
- Allows frame/epistolary narrators with naturally low mention counts to be accepted

### Fix 3: characters.py STEP 5.2bb - Upgrade kinship canonical names
- "father" + alias "Alphonse Frankenstein" → canonical becomes "Alphonse Frankenstein"
- Applies universally to father/mother/sister/brother/husband/wife/etc.
- Fixes the narrator candidate pool and character display

## Expected Attempt 7 Improvements
- Chapter Summaries: ~2.0 → ~7.0 (summaries use "the narrator" → Victor substituted)
  - Letters 2-4: correct via signatory detection (Step 6.95)
  - Ch 5-10, 17-24: correct via Victor as narrator (Step 6.9)
  - Ch 11, 15, 16: correct via awakening_re/appositive_re (Step 6.95)
  - Letters 1, Ch 12-14: still wrong (no structural signal)
- Character Extraction: ~6.5 → ~7.5 (Alphonse canonical fix)
- Pronunciation: ~7.5/10 (no change expected)
