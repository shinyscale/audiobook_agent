# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 14
- **Phase:** analysis_running
- **baseline_score:** 7.35

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 2 | 7.75 | Profiles improved |
| 3 | 7.58 | Profiles regressed |
| 4 | 7.08 | Summaries regressed (narrator substitution undid fix) |
| 5 | ~7.08 | Same root cause |
| 6 | ~5.5 | Regression: LLM hallucinated Elizabeth Lavenza as narrator |
| 7 | ~7.9 | Major recovery: 28 chapters ✓, letters/creature chapters misattributed |
| 8 | ~5.0 | REGRESSION: Step 4.5 early sub → all chapters attributed to outer narrator |
| 9-11 | ~1.5 | All chapters "Robert Walton" — Step 4.5 early sub regression |
| 12 | ~7.9 | Fix M: Victor chapters correct, creature chapters wrong, letters wrong |
| 13 | ~4.0 | Fix N/O/P: creature chapters fixed but Victor chapters still "Robert Walton" (narrator detection fragile) |

## Attempt 14 Fixes (commit 8d474af)

### Fix Q: narrator.py secondary narrator threshold
- Accept secondary narrator when primary has < 15 mentions (outer frame narrator)
- Victor Frankenstein (55 mentions) now accepted as secondary narrator
  even though Walton (8 mentions) is primary — because Walton is non-pervasive frame

### Fix R: analyzer.py Step 4.5 narrator_detected clearing
- When Step 4.5 marks a narrator as non-pervasive AND narrator_detected was already
  set to that name (from V2 pipeline), clear narrator_detected to None
- Allows Step 6.9 preamble to find Victor (now is_narrator=True) as inner narrator
- _blocked_pat_69 then replaces "Robert Walton" → "Victor Frankenstein" in non-letter chapters

### Fix S: _apply_letter_narrator initials matching
- Extended regex to handle "R. Walton" and "R.W" style abbreviated names
- Initials comparison: "R.W" matches "Robert Walton" → enables artifact stripping

## Expected Chapter Attribution After Fixes
- Letters 1-4: "Robert Walton" (correct — his narrative frame)
- Chapters 1-10: "Victor Frankenstein" (inner narrator confirmed from is_narrator flag)
- Chapters 11-16: "The narrator" (creature's narration, fixed by Fix N/6)
- Chapters 17-24: "Victor Frankenstein" (back to Victor)
- Chapter 25+: "Robert Walton" (back to outer frame, not present in this text)
