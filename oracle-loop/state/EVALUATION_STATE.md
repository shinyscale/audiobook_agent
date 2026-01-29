# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 7.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (CRITICAL REGRESSION)
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold - Character Extraction REGRESSED)

## Analysis of Attempt 6 Results

**CRITICAL REGRESSION DETECTED**: The character extraction has gotten WORSE, not better.

### What Happened

The attempt 6 disambiguation fix was designed to fix PROFILE confusion (father's traits assigned to son), but:

1. **The fix was applied to the WRONG layer** - Profile generation (evidence attribution)
2. **The actual problem is UPSTREAM** - Character identification (initial extraction)
3. **Result**: Father and son are now MERGED at extraction time, before profiles are even generated

### Evidence of Regression

**Attempt 1 Output** (from fix history): "John" and "John Donaldson" were SEPARATE characters
**Attempt 6 Output**: Only ONE "John Donaldson" character exists with alias "Father"

The separation achieved in attempt 1 has been lost. The disambiguation code added in attempt 6 cannot help because there's only ONE character to profile - the merge already happened.

### Root Cause (NEW)

The CHARACTER_IDENTIFICATION_PROMPT in `src/pipeline/character_profiling/identifier.py` contains these rules:
- Line 79: "Nickname variants = SAME person (Cal/Caleb, Cathy/Catherine, Tom/Thomas)"
- Line 80: "Adjacent chapter appearance + similar names = likely SAME person (merge them)"

The LLM interprets "John" and "John Donaldson" as nickname variants and merges them. The prompt says nothing about keeping father/son with same first name SEPARATE.

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE MERGE: Father and son merged into single character (REGRESSION)**
   - Problem: "John" (the son) and "John Donaldson" (the father) are merged into one character
   - Evidence: analysis.json has only 3 characters; `characters_present` in summary has both "John" AND "John Donaldson" separately
   - Evidence: Plot summary says "receives a letter from his father, John Donaldson" proving they should be separate
   - Location: `src/pipeline/character_profiling/identifier.py` - CHARACTER_IDENTIFICATION_PROMPT
   - Root cause: Prompt encourages merging "John" with "John Donaldson" as nickname variants
   - Fix: Add rule to prompt: "First name only (John) vs Full name (John Donaldson) = likely DIFFERENT people if context suggests parent/child relationship - check summaries for family terms like 'father', 'son', 'parent'"

### HIGH

2. **Relationships empty for all characters**
   - Problem: `relationships: {}` for all 3 characters
   - Evidence: Uncle Bill is clearly John's uncle (name contains "Uncle") but no relationship recorded
   - This has persisted through 6 attempts
   - Location: Profile generation - relationship extraction not executing
   - Fix: Deferred - fix character extraction first

### MEDIUM

3. **Physical descriptions null for all characters**
   - Problem: `physical_description: null` for all characters
   - The text does contain physical descriptions (father was "beautiful")
   - Location: Profile generation
   - Fix: Deferred

4. **Profile confusion will return after merge fix**
   - Problem: Once characters are separated, the profile disambiguation (attempt 6 fix) will need to work
   - The disambiguation code may still have issues
   - Fix: Test after merge is fixed

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.95 | - | Baseline. Critical: John/John Donaldson false merge |
| 2 | 8.65 | +0.70 | Character extraction FIXED (9/10). Profiles failing (7/10) |
| 3 | 8.65 | +0.70 | No change. Prompt simplification didn't improve relationships |
| 4 | 8.60 | +0.65 | Profiles dropped to 5/10 due to evidence confusion |
| 5 | 8.65 | +0.70 | Collision fix helped slightly but semantic confusion remains |
| 6 | 7.15 | -0.80 | **REGRESSION**: Character extraction dropped from 9/10 to 4/10 |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | False merge of John/John Donaldson | src/agents/characters.py | **FIXED** - Characters now separate (9/10 extraction) |
| 2 | Empty relationships - added character context | src/analyzer.py | **No change** - Relationships still empty |
| 3 | Empty relationships - simplified prompt | src/analyzer.py | **No change** - Relationships still empty |
| 4 | Empty relationships - enhanced upstream data | src/pipeline/character_profiling/summary_evidence.py | **REGRESSION** - summary_evidence still null, profile data confused |
| 5 | Profile evidence confused between characters | src/analyzer.py, src/pipeline/character_profiling/summary_evidence.py | **Partial** - Collision detection added but semantic confusion remains |
| 6 | Semantic disambiguation for same-name chars | name_disambiguator.py (NEW), passage_gatherer.py, summary_evidence.py, pipeline.py | **REGRESSION** - Fixed wrong layer; extraction now merging |
| 7 | Character extraction V2 prompt - family name guidance | src/pipeline/character_extraction_v2/main_cast.py | **SMOKE TEST PASS** - Two Johns now extracted separately |

## Fix Strategy for Attempt 7

**Target**: CHARACTER_IDENTIFICATION_PROMPT in `src/pipeline/character_profiling/identifier.py`

**Problem**: The prompt has rules that encourage merging:
- "Nickname variants = SAME person"
- "First name + Mrs./Mr. last name = SAME person"

**Missing rule**: "First name (John) vs Full name (John Donaldson) may be DIFFERENT people if summaries mention family relationship"

**Specific fix**:
Add to CRITICAL RULES section (around line 35):
```
8. First name vs Full name may be DIFFERENT people
   - Example: "John" and "John Donaldson" may be father and son
   - Check summaries for family terms: "father", "son", "parent", "child", "Sr.", "Jr."
   - If the summary mentions "X's father Y" where Y has same first name, keep them SEPARATE
```

Add to IMPORTANT MERGE RULES section (around line 81):
```
- First name only vs Full name with same first = CHECK FOR FAMILY RELATIONSHIP
  - If summaries say "X is Y's father/son/parent", they are DIFFERENT people
  - Do NOT merge based on shared first name alone
```

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓ (POST-PROCESSING)

**Root cause:** `src/agents/characters.py:_merge_within_supporting_cast():line 2612`
- Pass 2 used `names_similar()` which includes subset matching
- `names_similar("John", "John Donaldson")` returned True because {"john"} ⊂ {"john", "donaldson"}

**Fix applied:** Replace names_similar() with string_similarity() >= 0.85 threshold

**Result:** VERIFIED FIXED at post-processing layer - but LLM is now merging them upstream!

### Attempts 2-5: Profile/Relationship fixes

Various attempts to fix profiles and relationships. See modification history.

### Attempt 6: Context-Aware Evidence Disambiguation (WRONG LAYER)

**Attempted fix:** Added multi-signal disambiguation to profile evidence extraction

**Result:** REGRESSION - The fix addressed the wrong layer. Characters are merged during initial LLM identification, before profiles are generated. The disambiguation code never sees both characters because they're already merged.

### Attempt 7: Fixed CHARACTER_IDENTIFICATION_PROMPT for family name overlap ✓

**Root cause:** `src/pipeline/character_extraction_v2/main_cast.py:CHARACTER_IDENTIFICATION_PROMPT:lines 75-110`
- Pass 1 LLM received both chapter summaries (correct: "John" and "John Donaldson" listed separately) and plot summary (wrong: "John Donaldson receives letter from his father, John Donaldson")
- LLM gave priority to plot summary's narrative, treating both as one person
- Prompt had no guidance about family members with shared names

**Fix applied:**
1. Added NOTE: "When chapter summaries include a `characters_present` list, treat each entry as distinct even if names are similar"
2. Added Rule 5: "FAMILY MEMBERS WITH SHARED NAMES: If summaries mention family relationships (father/son, uncle/nephew) with shared first names, they are DIFFERENT people."

**Smoke test:** PASS - Extraction now produces 2 characters:
- "John Donaldson" (father, protagonist)
- "John (the writer of the letter)" (son, supporting)

**Modified:** `src/pipeline/character_extraction_v2/main_cast.py` lines 77-86

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify the fix and check if character extraction score improves.
