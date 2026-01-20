# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 14
- **Phase:** complete
- **baseline_score:** 6.05

## Latest Scores (Attempt 14) - PASS ✓
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓ (up from 5 - narrator assignment fixed!)
- Character Profiles: 5/10 (voice quotes still wrong, Egaeus missing profile)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10 ✓
- **Overall: 8.15/10** (threshold: 8.0) - **PASS!** ✓

## Score Calculation
```
Overall = (10×0.20) + (8×0.25) + (5×0.15) + (9×0.20) + (7×0.10) + (9×0.10)
        = 2.0 + 2.0 + 0.75 + 1.8 + 0.7 + 0.9
        = 8.15
```

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 (baseline) | 6.05 | - | Egaeus missing from character list |
| 2 | 5.35 | -0.70 | Regression |
| 3 | 4.85 | -1.20 | Regression |
| 4 | 5.55 | -0.50 | |
| 5 | 5.55 | -0.50 | |
| 6 | 5.55 | -0.50 | |
| 7 | - | - | FAILED (runtime error) |
| 8 | - | - | FAILED (field name error) |
| 9 | 5.55 | -0.50 | F6 reconciliation claimed to work but didn't |
| 10 | 7.75 | +1.70 | F6 reconciliation WORKED - Egaeus now in character list |
| 11 | 7.00 | +0.95 | REGRESSION - narrator fix backfired |
| 12 | 7.00 | +0.95 | FIX DID NOT WORK - identical to attempt 11 |
| 13 | 7.00 | +0.95 | Fix disabled early narrator detection - still failed |
| 14 | **8.15** | **+2.10** | **PASS!** ✓ Filter low-count chars from overview prompt |

## What Fixed the Narrator Issue

**Root Cause:** The OverviewGenerator was including low-mention-count characters in its "MAIN CHARACTERS" prompt section. Egaeus (added from summaries with mention_count=1) was ranked below Berenice (13 mentions), causing the LLM to assume Berenice was the main character/narrator.

**Fix Applied (Attempt 14):** Modified `src/pipeline/overview/generator.py` lines 201-207 to filter out characters with `mention_count < 3` from the main characters list. This prevents first-person narrators (who often refer to themselves as "I" rather than by name) from being deprioritized.

**Result:**
- Plot summary now correctly says "The story unfolds through the first-person retrospective narration of Egaeus..."
- Egaeus: `is_narrator: true` ✓
- Berenice: `is_narrator: false` ✓

## Remaining Issues (Not Blocking - Score > 8.0)

### HIGH (but not blocking threshold)

1. **Berenice's voice_guidance contains Egaeus's quotes**
   - Problem: "Berenice! --I call upon her name --Berenice!" is Egaeus calling out
   - Problem: "Would to God that I had never beheld them" is Egaeus's internal thought
   - Reality: Berenice NEVER speaks in the story
   - Location: Character profile extraction assigns speaker-adjacent text to wrong character
   - Future fix: Improve quote attribution in `src/pipeline/character_extraction/`

2. **Egaeus has no profile data**
   - Problem: appearance: null, personality: null, voice_guidance: null
   - Cause: He was added by F6 reconciliation from summaries, which doesn't generate profiles
   - Future fix: Trigger profile generation for narrator characters added from summaries

### MEDIUM

3. **Mad'selle Sallé should not be a character**
   - Historical/literary allusion to 18th-century French dancer
   - She never appears, speaks, or takes action in the narrative
   - Future fix: Filter out literary/historical references

4. **Common words flagged as proper_noun in pronunciation**
   - "family", "physician", "servant", "maiden" flagged incorrectly
   - These are common English words, not unusual terms
   - Future fix: Improve common word filtering in pronunciation pipeline

## Fix History

### Attempt 14 - SUCCESS ✓
**Issue Targeted:** Root cause of biased plot summary
**Fix Applied:** Filter low-mention-count characters from OverviewGenerator prompt
**Modified:** `src/pipeline/overview/generator.py` lines 201-207
**Result:** Score 8.15 - PASS! Narrator correctly identified as Egaeus

### Previous Attempts
- Attempts 1-9: Various failures with F6 reconciliation
- Attempt 10: F6 reconciliation worked - Egaeus added to character list (7.75)
- Attempts 11-12: Narrator clearing attempts failed (7.00)
- Attempt 13: Disabled early narrator detection - still failed (7.00)

## Next Action

**Phase:** complete

Berenice has passed with score 8.15/10. Ready to advance to next text in manifest.json.

Next text: **monkeys_paw** (The Monkey's Paw)
