# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 9
- **Phase:** analysis_running (4th restart — full fix set)
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

### Fix E: Step 4.5 - narrator_character_id guard (9b90ac3)
- `if narrator_detected is None and narrator_info.narrator_character_id:`
- Prevents "Robert Walton" from being set via Step 4.5 when narrator can't be matched
- But INSUFFICIENT alone: F6 adds "Robert Walton" → Step 4.5 can now match it → still sets narrator_detected

### Fix E2: narrator_name export revert (24669d3)
- Revert 9068f81: only export narrator_name when narrator_character_id is set
- Prevents V2 pipeline line ~1115 from setting narrator_detected unconditionally
- But INSUFFICIENT alone: Step 4.5 still fires after F6 adds "Robert Walton"

### Fix E3: Step 6.9 is_narrator fallback (00f2a73)
- If narrator_detected is None, use first is_narrator=True character (Victor)
- Then Step 6.95/Fix B corrects letters (→ Robert Walton) and creature chapters (→ The narrator)
- But INSUFFICIENT alone: narrator_detected might be set to "Robert Walton" by Step 4.5

### Fix E4: Step 4.5 _had_narrator_before_45 guard (34f8651)
- Capture whether is_narrator=True was set BEFORE Step 4.5 runs
- If V2 already found an inner narrator (Victor), Step 4.5 can't override narrator_detected
- Combined with E, E2, E3: narrator_detected stays None → fallback uses Victor → Step 6.95/Fix B corrects letters/creature ✓

### Fix F: extract_core_noun - strip parentheticals (1cb6cdf)
- `extract_core_noun("the blind father (De Lacey)")` was returning "lacey)" due to parenthetical
- Fix: strip parenthetical annotations before splitting on spaces

### Fix G: Rule 0.5b - strip parentheticals (342435a)
- Person/non-person semantic check had same parenthetical bug
- Fix: strip parenthetical before taking `split()[-1]`

### Fix H: Fix 5/Fix 6 in summarizer.py - early return + density check (013081d)
- Fix 5 now has early return so Fix 6 doesn't also fire
- Fix 6: Chapter text opens with ANY quoted prose + FP density ≥ 4 → inner narrator chapter

### Fix I: Step 4.5.9b - first-initial variant dedup (1d432b1)
- Merges "R. Walton" → "Robert Walton" at analyzer level after F6 runs

### Fix J: Signatory expansion "R. Walton" → "Robert Walton" (3f524d3)
- Added Path A and Path B expansion for "Initial. Lastname" format signatories

### Fix K: Letter signatory Path B name-only line fallback (c1985f9)
- Letter 3 ends with "R.W." (no "Your affectionate...") — added fallback to detect name-only closing lines

### Fix L: Letter 4 vocative fallback (f0a3664)
- Letter 4 has no closing signature — added "Captain Walton" address detection to identify narrator
