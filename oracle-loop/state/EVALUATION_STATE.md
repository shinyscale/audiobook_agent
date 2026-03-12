# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 13
- **Phase:** analysis_running
- **baseline_score:** 7.35

## Latest Scores
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
| 9-11 | ~1.5 | All chapters "Robert Walton" — Step 4.5 early sub undid Fix 5 work |
| 12 | ~7.9 | Victor chapters (1-10, 17-24) correct ✓; creature chapters (11-16) still "Victor Frankenstein" (Fix 5/6 early-return bug); letters all wrong |

## Attempt 13 Fixes

### Fix M: Step 4.5 pervasive guard (ab0921b) — Attempt 12
- Added `_narrator_is_pervasive` guard to prevent early narrator substitution for outer frame narrator

### Fix N: Fix 5/6 early-return removed (e307943)
- Removed early-return in Fix 5 and Fix 6 when `wrong_name == narrator_detected`
- Both fixes now ALWAYS replace outer-quote chapter leading names with "The narrator"
- Outer-quote chapters are creature chapters (11-16), not Victor chapters

### Fix O: _detect_letter_signatory improvements (e307943)
- Refactored: extracted _expand_initials() + _extract_tail_signatory() helpers
- Extended search range to 20000 chars (Fix L: Letter 4 "Captain Walton" at position 12232)
- narrator_detected as fallback for initials expansion (Letter 3 "R.W" → "Robert Walton")
- Path C: tail-closing fallback without salutation (Letter 1 starts mid-text, missing header)

### Fix P: _apply_letter_narrator artifact stripping (e307943)
- Strips "narrator, Name2, " artifact when leading name already matches signatory
- Handles LLM output like "Robert Walton narrator, Victor Frankenstein, writes..."

## Expected Chapter Attribution
- Letters 1-4: "Robert Walton" (his narrative frame)
- Chapters 1-10: "Victor Frankenstein" (inner narrator)
- Chapters 11-16: "The narrator" (creature's narration, innermost)
- Chapters 17-24: "Victor Frankenstein" (back to Victor)
- Chapter 25+: "Robert Walton" (back to outer frame)
