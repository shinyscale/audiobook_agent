# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 8
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Latest Scores (Attempt 7)
- Structure Detection: ~8.5/10 ✓ (28 chapters ✓, Letter 1 title=null ✗)
- Character Extraction: ~7.5/10 ✗ (creature/dæmon unified ✓, Alphonse full name ✓, R.Walton duplicate ✗, De Lacey absorbed into dæmon ✗)
- Character Profiles: ~8.0/10 ✓ (19 profiles generated, Victor narrator notes ✓)
- Chapter Summaries: ~7.0/10 ✗ (Letters 1/3/4 = Victor Frankenstein ✗, creature ch 12-14/16 = Victor Frankenstein ✗)
- Pronunciation Guide: ~7.5/10 ✗ (Walton/Clerval/Justine ✓, Frankenstein still missing ✗)
- HTML Presentation: ~9.5/10 ✓
- **Overall: ~7.9/10** (significant improvement from attempt 6 ~5.5)

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 2 | 7.75 | Profiles improved |
| 3 | 7.58 | Profiles regressed |
| 4 | 7.08 | Summaries regressed 6.5→4.0 (narrator substitution undid fix) |
| 5 | ~7.08 | Same root cause: Step 6.9 undoes narrator fix |
| 6 | ~5.5 | Regression: LLM hallucinated Elizabeth Lavenza as narrator throughout |
| 7 | ~7.9 | Major recovery: 28 chapters ✓, Alphonse fixed ✓, but letters/creature chapters misattributed |

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

## Attempt 7 Root Cause Analysis
### Letters 3/4 not fixed by Step 6.95
- `_fix_narrator_attribution` WOULD fix Letters 3/4 (simulation confirms signatory detection works)
- But Step 6.95 is somehow NOT applying the fix in the actual pipeline
- Most likely: chapter_index mismatch in `_ch_texts_final.get(chapter_index, "")` returns ""
- Result: Fix never applies → summaries stay as "Victor Frankenstein writes..."

### Creature chapters 12-14/16 not fixed
- Chapter 12-14 prose: creature describes cottagers, NO "my creator" in first 3000 chars
- No appositive/awakening pattern in those summaries
- Fix 3 and Fix 4 in `_fix_narrator_attribution` don't trigger

### Step 6.9 uses wrong narrator name for epistolary texts
- `_nn_final` starts as "Robert Walton" (narrator_detected)
- Loop overrides with first is_narrator=True character: "Victor Frankenstein"
- ALL "the narrator" → "Victor Frankenstein" globally (correct for Victor chapters, wrong for letters/creature)

## Fixes Applied for Attempt 8

### Fix A: Step 6.9 - use narrator_detected directly
- Don't override _nn_final with first is_narrator char
- Only use canonical if it MATCHES narrator_detected
- For Frankenstein: _nn_final = "Robert Walton" → letter chapters get "Robert Walton"

### Fix B: _convert_chapters - final safety net
- After building each StructuralElement, apply `_fix_narrator_attribution` one final time
- Uses the chapter start/end positions directly (no index mismatch possible)
- This catches any summaries that Step 6.95 missed

### Fix C: summarizer.py - active_characters clarity (already committed as b192dbd)
- active_characters/characters_mentioned lists use narrator's ACTUAL NAME if stated
- Allows Robert Walton to be extracted as a character from letter summaries

### Fix D: Creature chapter detection
- Add detection pattern for chapter text that starts with quoted first-person speech
- Universal: if chapter text body begins with `"I ` pattern after chapter header, it's an inner narrator chapter
