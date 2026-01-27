# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.60
- **Competitive Mode:** single

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 8.60/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
None

### HIGH
1. **Missing relationships for main characters**
   - Problem: Egaeus and Berenice have empty `relationships: {}` fields, but they are cousins AND betrothed to each other - both relationships are central to the story
   - Evidence: The text explicitly states "Berenice and I were cousins" and they are engaged to marry
   - ID patterns: `main_cast_1` (Berenice), F6-reconciled `d013867632e5` (Egaeus)
   - Location: Character profile generation in `src/pipeline/character_extraction_v2/` or profile enrichment
   - Fix: Relationship extraction during profile generation should capture cousin/betrothed relationships

2. **Excessive false positives in pronunciation guide**
   - Problem: ~15-20 common English words are flagged that shouldn't be: "menial", "partook", "wretchedness", "ecstasies", "awaking", "loitered", "commonest", "trembling", "frivolity"
   - Evidence: These are standard English vocabulary, not unusual words needing pronunciation guidance
   - Location: `src/pipeline/pronunciation.py` or pronunciation agent filtering logic
   - Fix: Improve filtering to exclude common English vocabulary; possibly use word frequency lists

### MEDIUM
3. **Egaeus has only 1 mention count despite being narrator**
   - Problem: First-person narrator Egaeus shows only 1 mention, which is technically accurate (he rarely says his own name) but may confuse users
   - Evidence: `"mention_count": 1` in the JSON
   - Location: This is expected behavior for first-person narrators - may want to add a note in the profile or UI
   - Fix: Could add "(Narrator - present throughout)" indicator or calculate "narrative presence" differently for first-person narrators

### LOW
None

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.60 | - | Baseline set. Profiles 7.0, Pronunciation 7.5 |

## Fix History
### Attempt 2
**Issues Addressed:**
1. HIGH #1: Missing relationships for main characters
2. HIGH #2: Excessive pronunciation false positives

**Root Cause #1 - Missing Relationships:**
- **Symptom:** Both Berenice and Egaeus had empty relationships `{}` and null profiles despite being eligible for profile generation
- **Data Investigation:** Both characters eligible (Berenice: 14 mentions, Egaeus: narrator with 1 mention). Profile stage ran 5 LLM calls. BUT all profile fields were null in output.
- **Root Cause:** `src/analyzer.py:1846-1876` - Structured fields (appearance, personality, voice_guidance, relationships) were only assigned if the profile TEXT was non-empty. If LLM returned empty description but populated structured fields, they were discarded.
- **Fix:** Moved structured field assignment OUTSIDE the `if profile:` block (lines 1846-1858), so they get saved even if the profile description is empty.
- **File Modified:** `src/analyzer.py`
- **Confidence:** HIGH - Clear logic bug where valid data was being discarded

**Root Cause #2 - Pronunciation False Positives:**
- **Symptom:** Common English words flagged: "menial", "partook", "wretchedness", "ecstasies", "awaking", "loitered", "commonest", "trembling", "frivolity"
- **Data Investigation:** 104 total pronunciation entries, many with "high" confidence
- **Root Cause:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` - These words are not in CMU dictionary (likely inflected forms) and not in COMMON_WORDS_WHITELIST, so they were flagged
- **Fix:** Added 9 common vocabulary words to COMMON_WORDS_WHITELIST (lines 406-414)
- **File Modified:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
- **Confidence:** HIGH - Direct filtering gap

**Tests:** All 231 tests pass (10 skipped, 1 warning)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | HIGH #1: Missing relationships | `src/analyzer.py` (lines 1846-1876) | Moved structured field assignment outside `if profile:` block |
| 2 | HIGH #2: Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` (lines 406-414) | Added 9 common words to whitelist |

## Pipeline Notes - Attempt 2
**Analysis completed:** 11m 20s (2026-01-27 10:43)
- Competitive consensus: ENABLED (all 3 stages)
- Model: qwen3-next:80b-a3b-instruct-q8_0
- Results: 2 characters, 1 chapter, 97 pronunciation flags
- Total LLM calls: 24 (40,597 tokens)
- Bottleneck: Pronunciation Guide (44.4% of time)

**Warnings observed:**
- "Narrator 'Egaeus' identified but NOT found in main_cast"
- Pronoun blocking: 'her' rejected as alias for 'Berenice'

**Fixes applied in this attempt:**
1. Structured profile fields now saved even if description is empty (`src/analyzer.py`)
2. Added 9 common words to pronunciation whitelist (`cmu_proposer.py`)

**Ready for evaluation.**
