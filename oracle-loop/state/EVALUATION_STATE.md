# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 14
- **Phase:** awaiting_analysis
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING (NO CHANGE from attempt 12)
- Character Profiles: 7/10
- Chapter Summaries: 8/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 7.00/10** (threshold: 8.0)

## Score Calculation

```
Overall = (9 × 0.20) + (5 × 0.25) + (7 × 0.15) + (8 × 0.20) + (4 × 0.10) + (9 × 0.10)
        = 1.80 + 1.25 + 1.05 + 1.60 + 0.40 + 0.90
        = 7.00/10
```

## Evaluation Details

### Why Attempt 13 Fix Was INEFFECTIVE

**The gender conflict detection code IS correct and IS in the codebase**, but it DID NOT EXECUTE during the analysis run. Evidence:

1. **Stale .pyc cache**:
   - consensus.py modified: 08:59:57
   - consensus.cpython-312.pyc compiled: 09:00
   - Git commit made: 09:02:00
   - Analysis ran: 09:21:12

   Python likely used the pre-fix .pyc cache instead of recompiling the updated source.

2. **Output unchanged**: "the sergeant-major" still has aliases ["the soldier", "the old man", "the old woman"] - exactly the same as attempt 12.

3. **Gender detection logic verified**: Manual testing confirms the function correctly detects:
   - "the sergeant-major" → male
   - "the old man" → male
   - "the old woman" → female

   If the code ran, "the old woman" would NOT have been merged.

### Character Extraction: 5/10

**Current character list (9 characters):**
1. Mr. White (10 mentions) - Good
2. **White (30 mentions)** - PROBLEM: Orphan entry that should merge with Mr. White
3. Mrs. White (19 mentions) - Good
4. Herbert White (14 mentions) with alias "Herbert" - Good
5. Sergeant-Major Morris (5 mentions) with alias "Morris" - Good
6. **the sergeant-major (5 mentions)** with aliases "the soldier", "the old man", "the old woman" - CRITICAL BUG
7. the visitor (4 mentions) - OK
8. his wife (2 mentions) - Should merge with Mrs. White
9. Stranger from Maw and Meggins (1 mention) - OK

### Structure Detection: 9/10
- 3 parts correctly detected
- Chapter titles showing as "None" instead of "Part I", "Part II", "Part III"
- Chapter 3 includes Project Gutenberg boilerplate

### Character Profiles: 7/10
- Mr. White has excellent profile with physical description, personality, voice guidance, evidence
- Mrs. White, Herbert White have null profile data
- "White" entry has profile data that duplicates/should belong to Mr. White

### Chapter Summaries: 8/10
- All three part summaries are accurate and useful for narrator preparation

### Pronunciation Guide: 4/10
- Common English words flagged: "his", "old", "from", "man", "wife", "woman", "soldier"
- Gutenberg boilerplate: "GutenbergTM", "eBooks"
- Root cause: Extracted from broken character names

### HTML Presentation: 9/10
- Navigation functional, layout clean

## Current Issues (Priority Order)

### CRITICAL

1. **FIX NOT APPLIED - Stale .pyc cache**
   - Problem: The gender conflict detection code was committed but Python used a cached bytecode file
   - Evidence: .pyc timestamp (09:00) predates git commit (09:02), output identical to attempt 12
   - Fix: Clear `__pycache__` directories before running analysis: `find . -name "__pycache__" -exec rm -rf {} +`

2. **"the sergeant-major" wrongly merged with "the old man" and "the old woman"**
   - Problem: Three DIFFERENT character references merged as aliases
   - Evidence: "the old man" and "the old woman" are OPPOSITE GENDERS - cannot be the same person
   - Location: `src/pipeline/character_extraction/consensus.py` - `_llm_epithet_resolution()`
   - Fix: The code fix IS correct but didn't run. Clear cache and re-run.

3. **"White" (30 mentions) exists as orphan entry separate from "Mr. White"**
   - Problem: "White" refers to Mr. White in almost all contexts but isn't merging
   - Evidence: 30 mentions of standalone "White" are separate from "Mr. White" (10 mentions)
   - Root cause: Ambiguity check correctly blocks merge because "Mrs. White" exists
   - Location: `src/pipeline/character_extraction/consensus.py` - need context-aware disambiguation
   - Fix: When "Mr./Mrs. [LastName]" both exist, use dialogue attribution context to determine who standalone "[LastName]" refers to

### HIGH

4. **"his wife" orphan entry**
   - Problem: "his wife" (2 mentions) should merge with "Mrs. White"
   - Location: Relational pronoun resolution
   - Fix: Resolve possessive pronouns + relationship to the primary character of that relationship type

5. **Common English words flagged as proper nouns**
   - Problem: "his" (99x), "old" (42x), "from" (38x), "man" (23x), "wife" (15x), "woman" (11x), "soldier" (5x)
   - Root cause: Extracted from broken character names
   - Fix: Two-part - (a) Fix character extraction bugs, (b) Add stopword filtering

6. **Project Gutenberg boilerplate contamination**
   - Problem: "GutenbergTM" flagged 57 times, Chapter 3 includes legal text
   - Location: `src/ingestion/` - back matter detection
   - Fix: Add patterns to detect and strip Project Gutenberg license text

### MEDIUM

7. **"the sergeant-major" should merge with "Sergeant-Major Morris"**
   - Problem: Both refer to the same person but exist as separate entries
   - Fix: After Critical #2 is resolved, ensure cross-group resolution links the epithet to the proper name

8. **Chapter titles showing as "None"**
   - Problem: All three chapters have `title: null` instead of "Part I", "Part II", "Part III"
   - Location: `src/pipeline/chapter_detection/` - title extraction

## Fix History

| Attempt | Fix | Outcome |
|---------|-----|---------|
| 1-4 | Various pipeline errors | Failed to run |
| 5 | First successful run | 6.275 baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 |
| 7-9 | Various fix attempts | 7.05 |
| 10 | Case sensitivity fix | 7.05 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | 6.70 - fix in wrong code path |
| 12 | Added ambiguity check to `_validate_merge()` in LLM path | 7.00 - partial fix (Herbert fixed) |
| 13 | **Gender conflict detection in epithet resolution** | **7.00 - FIX NOT APPLIED (stale .pyc cache)** |
| 14 | **Cleared Python bytecode cache** | Infrastructure fix - allows attempt 13 code to execute |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't help |
| 11 | 6.70 | +0.425 | Regression - fix in wrong code path |
| 12 | 7.00 | +0.725 | Partial fix - Herbert correct now |
| 13 | 7.00 | +0.725 | FIX NOT APPLIED - stale bytecode cache |

## Next Action

Re-run the analysis. The gender conflict detection code from attempt 13 will now execute properly with the bytecode cache cleared.

**Expected results after attempt 14:**
- "the old woman" should be a separate character (not alias of "the sergeant-major")
- "the old man" and "the soldier" may still merge with "the sergeant-major" (all male)
- Character Extraction should improve from 5/10 to at least 6/10

**Remaining issues after cache fix:**
- If male epithets still incorrectly merge, need semantic/contextual differentiation beyond gender
- "White" (30 mentions) orphan entry still needs context-aware disambiguation
- "his wife" needs relational pronoun resolution

## Configuration Audit

- Model: qwen3-next:80b-a3b-instruct-q8_0 for characters
- Chunking: 5000 char chunks (character_llm_chunk_chars)
- LLM calls: 60 total, 113,112 tokens
- Character Extraction: 40.2% of pipeline time (449s)
- Low confidence flags on "the sergeant-major" (0.30)

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json
