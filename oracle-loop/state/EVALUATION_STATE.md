# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 2
- **Phase:** awaiting_evaluation
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

---

## ⚠️ External Changes Applied (Human Intervention)

**IMPORTANT:** The following changes were made OUTSIDE the oracle loop. Re-run analysis to test them.

### What Happened

1. **Oracle loop proposed a keyword filter fix** - Added `mundane_location_keywords` list to filter "library", "room", etc.
2. **Human reverted it** - Keyword lists are brittle overfitting (commit `8dd1972`)
3. **Human applied prompt fix instead** - Clarified `CHARACTER_IDENTIFICATION_PROMPT` to distinguish settings from characters with agency

### Changes Made

**1. Prompt clarification in `main_cast.py`:**
```
# BEFORE (ambiguous):
"Include plot-central symbolic objects/forces"

# AFTER (clear):
"Include symbolic objects/forces that have AGENCY or POWER (e.g., a cursed
object that grants wishes). Do NOT include settings/locations where events
happen (e.g., a library, a house, a garden, a room) - these are backdrops,
not characters."
```

**2. Removed redundant object_keywords filter from `main_cast.py`:**
- CharacterAgent already has this logic in `_is_valid_alias()`
- Duplicate filtering removed, note added pointing to CharacterAgent

**3. Updated `PROMPT_fix.md` guidance:**
- Explicit ban on deny-list filters (keyword lists that block "bad words")
- Allowed exception: reference lexicons for recognition (titles, ranks, honorifics)
- Required "Fix Classification" checklist before implementing

### Why This Matters

Keyword lists (deny lists) are **overfitting** - they work for the current book but fail on edge cases:
- "the library" should be filtered for Berenice
- But "the Garden" might be symbolic in another book
- The list can never be complete

Prompt clarification teaches the LLM the **concept** (agency vs backdrop), which generalizes to all books.

---

## Current Issues (Priority Order)

### CRITICAL
None

### HIGH
1. **"the library" incorrectly extracted as a character** - FIX APPLIED (prompt clarification)
   - Problem: The library (a setting/location) is listed as a character with 6 mentions
   - Evidence: The library is where events happen (Egaeus born there, mother died there, confronts Berenice there) but it has no agency or dialogue. It's a setting, not a character.
   - Expected: Only Egaeus, Berenice, and the servant should be characters
   - ID pattern: `main_cast_3` - came from main cast pipeline
   - **Fix applied:** Clarified CHARACTER_IDENTIFICATION_PROMPT to distinguish settings (backdrops) from characters with agency
   - **Action:** Re-run analysis to verify fix works

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
| 1 (reverted) | Library as character | `main_cast.py` (mundane_location_keywords) | **REVERTED** - keyword list is overfitting |
| 1 (human fix) | Library as character | `main_cast.py` (CHARACTER_IDENTIFICATION_PROMPT) | Clarified agency vs backdrop distinction |
| 1 (cleanup) | Redundant filter | `main_cast.py` (object_keywords removed) | Removed duplicate of CharacterAgent logic |

## Pipeline Notes (Attempt 2)
- Analysis completed in 13m 44s
- Competitive consensus enabled for all stages (characters, structure, summaries)
- Characters: 5 detected (Berenice, the teeth, servant maiden, menial, Egaeus)
- Narrator: Egaeus (first-person) ✓ Correct
- Validation working: blocked 'the narrator' meta-reference
- Word count: 3,240 words
- Pronunciation flags: 80 entries
- **FIX RESULT:** "the library" NO LONGER extracted ✓ Prompt clarification worked!
- **NEW ISSUE:** "the teeth" extracted as character (6 mentions) - symbolic object or valid?

## Next Action
**Phase:** awaiting_evaluation

Evaluate attempt 2 results:
- VERIFY: Is "the library" still being extracted as a character? (Expected: NO)
- EVALUATE: Is "the teeth" a valid character extraction or should it be filtered?
- SCORE: All categories and determine if we meet the 8.0 threshold
