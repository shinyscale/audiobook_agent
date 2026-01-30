# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.35

## Latest Scores (Attempt 3)
- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.5/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Progress from Attempt 2

**Major improvement in character consolidation:**
- Attempt 2: "Tom" (170) + "Tom Buchanan" (22) = fragmented
- Attempt 3: "Tom Buchanan" (196) = properly merged ✓

- Attempt 2: "Jordan" (73) + "Jordan Baker" (40) = fragmented
- Attempt 3: "Jordan Baker" (101) = properly merged ✓

- Attempt 2: "Wilson" (65) + "George" (14) + "George Wilson" (3) = fragmented
- Attempt 3: "George Wilson" (88) = properly merged ✓

**Score delta:** +1.15 from baseline (7.35 → 8.5)

## Current Issues (Priority Order)

### HIGH

1. **Duplicate character entry: Meyer Wolfsheim spelling variants**
   - Problem: "Meyer Wolfsheim" (main_cast_7, 32 mentions) and "Meyer Wolfshiem" (supporting_8, 6 mentions) are separate entries
   - Evidence: Both refer to the same character; "Wolfshiem" is Fitzgerald's spelling but appears inconsistently
   - ID patterns: main_cast_7 vs supporting_8 → cross-pipeline merge needed
   - Location: `src/analyzer.py` F6 reconciliation or `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Add fuzzy matching for spelling variants in character merging (Levenshtein distance ≤ 2 for surnames)

2. **Physical appearance data missing for most characters**
   - Problem: Most characters have `appearance.summary: "unknown"` despite source text having descriptions
   - Evidence: Tom Buchanan correctly has "sturdy straw-haired man of thirty", but Gatsby (white suits, rare smile), Daisy (white dresses), Jordan (tan, athletic) are "unknown"
   - Location: `src/pipeline/character_profiling/` - appearance extraction prompts
   - Fix: Improve appearance extraction prompts to capture physical descriptions from source text

### MEDIUM

3. **False positive: "Town Tattle" extracted as character**
   - Problem: "Town Tattle" (supporting_11, 3 mentions) is a gossip magazine, not a character
   - Evidence: The text refers to "Town Tattle" as a publication Tom reads
   - ID pattern: supporting_11 → supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or CHARACTER_IDENTIFICATION_PROMPT
   - Fix: Prompt clarification to exclude publications/media titles

4. **Character naming: "Gatz" should be "Henry C. Gatz"**
   - Problem: Gatsby's father is listed as just "Gatz" instead of full name
   - Evidence: The character is clearly Henry C. Gatz (uses full name in telegram, corrects to "Gatz is my name")
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Use full name from evidence when available

## Fix Recommendations

### Priority 1: Character spelling variant merge (HIGH #1)
Add fuzzy matching for character names with similar spellings:
```python
# In character merging logic
def should_merge_names(name1: str, name2: str) -> bool:
    # Check Levenshtein distance for spelling variants
    if levenshtein_distance(name1, name2) <= 2:
        return True
    # Also check without common title prefixes
    ...
```

### Priority 2: Appearance extraction (HIGH #2)
Update appearance extraction prompts to specifically ask for:
- Physical features mentioned in text
- Clothing and style descriptions
- Age and build descriptions
- Distinctive features (smile, mannerisms)

### Priority 3: Publication filter (MEDIUM #3)
Add to CHARACTER_IDENTIFICATION_PROMPT:
```
Do NOT extract:
- Publications, newspapers, magazines (e.g., "Town Tattle", "The Times")
- Organizations or businesses
```

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed |
| 2 | Main cast extraction failure | src/pipeline/character_extraction_v2/main_cast.py | Diagnostic logging |
| 3 | JSON format for qwen3-next | src/pipeline/character_extraction_v2/main_cast.py | Wrapped object prompts - MAJOR IMPROVEMENT (+1.15) |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |
| 2 | 7.35 | 0.00 | First scoreable run - character fragmentation + missing profiles |
| 3 | 8.5 | +1.15 | Character consolidation fixed, 2 categories still below 8.0 |

## Configuration Notes

Model: qwen3-next:80b-a3b-instruct-q8_0 (user-specified, DO NOT CHANGE)
Competitive Mode: single
Output files regenerated 2026-01-30 15:27

## Next Action

Run PROMPT_fix.md to address:
1. Meyer Wolfsheim/Wolfshiem spelling variant merge (to reach Character Extraction ≥ 8.0)
2. Physical appearance extraction improvement (to reach Character Profiles ≥ 8.0)
