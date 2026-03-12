# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 9
- **Phase:** analysis_running
- **baseline_score:** 7.35

## Latest Scores (Attempt 8)
- Structure Detection: ~8.5/10 ✓ (28 chapters ✓)
- Character Extraction: ~7.5/10 (unknown, regression overshadows)
- Chapter Summaries: ~3.0/10 ✗ MAJOR REGRESSION (nearly all chapters say "Robert Walton" instead of Victor/creature)
- Letters 1-4: "Robert Walton" ✓ but with duplication artifacts ("Robert Walton, Robert Walton,")
- Chapters 2-10 (Victor): "Robert Walton reflects/begins with Robert Walton..." ← WRONG
- Chapter 11 (creature): "Robert Walton, a newly awakened being..." ← WRONG
- Chapters 12-13 (creature): "The narrator, living in a hovel..." ✓ (Fix 5 worked)
- Chapters 14-16 (creature): "Robert Walton recounts..." ← WRONG
- Chapters 17-24 (Victor): "Robert Walton consumed by guilt..." ← WRONG
- **Overall: ~5.0/10** (REGRESSION from attempt 7 ~7.9)

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
| 8 | ~5.0 | REGRESSION: Step 4.5 set narrator_detected="Robert Walton" without char match → Step 6.9 substituted globally |

## Attempt 8 Root Cause Analysis
### Step 4.5 set narrator_detected unconditionally
- Fix C in attempt 8 fixed letter summaries to correctly say "Robert Walton"
- F6 then added "Robert Walton" to character list (from letter summaries)
- Step 4.5 second NarratorDetector ran with "Robert Walton" now in character list
- NarratorDetector found "Robert Walton" but could not match narrator_character_id (only "R. Walton" in cast)
- Step 4.5 code: `if narrator_detected is None: narrator_detected = narrator_info.narrator_name`
- This fired UNCONDITIONALLY — even when narrator_character_id was None (no character match)
- narrator_detected = "Robert Walton" → Step 6.9 substituted "the narrator" → "Robert Walton" globally
- Victor's chapters that used "the narrator" placeholder became "Robert Walton narrates..."
- Fix C (attempt 7's approach): The attempt 7 had Victor Frankenstein letter summaries — Step 4.5 would have found "Victor Frankenstein" as narrator (matched), and narrator_detected would have been "Victor Frankenstein" from the first pass anyway

### Duplicate artifact in letters
- "Robert Walton, Robert Walton, begins his journey..." artifacts from Fix B applying twice
- Fix B in `_convert_chapters` applied `_fix_narrator_attribution` AFTER summaries were already corrected
- The signatory detection found "Robert Walton" → replaced leading name → led to duplication

## Fixes Applied for Attempt 9

### Fix E: Step 4.5 - require narrator_character_id
- `if narrator_detected is None and narrator_info.narrator_character_id:` — only set narrator_detected when narrator was matched to a character
- Prevents "Robert Walton" from being set via Step 4.5 when R. Walton can't be matched
- Root cause fix for attempt 8 regression

### Fix F: extract_core_noun - strip parentheticals
- `extract_core_noun("the blind father (De Lacey)")` was returning "lacey)" due to parenthetical
- Fix: strip parenthetical annotations before splitting on spaces

### Fix G: Rule 0.5b - strip parentheticals
- Person/non-person semantic check had same parenthetical bug
- Fix: strip parenthetical before taking `split()[-1]`

### Fix H: Fix 5/Fix 6 in summarizer.py - early return + density check
- Fix 5 now has early return so Fix 6 doesn't also fire
- Fix 6: Chapter text opens with ANY quoted prose + FP density ≥ 4 → inner narrator chapter

### Fix I: Step 4.5.9b - first-initial variant dedup
- Merges "R. Walton" → "Robert Walton" at analyzer level after F6 runs
- Prevents duplicate entries in character list
