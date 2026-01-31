# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Last modified: 2026-01-30 19:14:52 (AFTER fix commit at 15:40:29)

## Pipeline Notes
- Competitive consensus enabled (single model, 3 temperatures)
- Competitive stages: characters, structure, summaries (via --competitive-all)
- Model: qwen3-next:80b-a3b-instruct-q8_0
- Analysis completed successfully with Wolfsheim fuzzy merge fix applied
- Minor errors in pronunciation agent (LLM JSON format issues - non-blocking)
- Profile generation failed for 'Doctor T. J. Eckleburg' (pipeline_char_map not defined)

## Latest Scores (Attempt 4 - SAME AS ATTEMPT 3)

Since the output files weren't regenerated, the scores are identical to attempt 3:

- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.5/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold) - and output needs regeneration

## Evidence: Output Files Not Regenerated

```
$ stat analysis.json
Modify: 2026-01-30 15:27:26

$ git log --oneline -3
5c6c8d6 Analyze: gatsby attempt 4 - complete           (17:12:20)
cff867f Analyze: gatsby attempt 4 - running            (15:41:47)
f038a3b Fix: Add fuzzy full-name matching              (15:40:29)
```

The "Analyze complete" commit was made at 17:12 but the files were last modified at 15:27 (13 minutes BEFORE the fix was committed). The analysis did not actually run after the fix was applied.

## Character Extraction Issues (Unchanged from Attempt 3)

**Meyer Wolfsheim duplication persists:**
```json
{"id": "main_cast_7", "name": "Meyer Wolfsheim", "aliases": ["Wolfshiem"], "mentions": 32}
{"id": "supporting_8", "name": "Meyer Wolfshiem", "aliases": [], "mentions": 6}
```

The main cast entry has "Wolfshiem" as an alias (good), but the supporting cast entry "Meyer Wolfshiem" (full name with spelling variant) was NOT merged into main_cast_7.

**Other character issues:**
- "Gatz" (supporting_7) should be "Henry C. Gatz"
- "Town Tattle" (supporting_11) is a publication, not a character
- "The man with owl-eyed glasses" should be "Owl Eyes" (recognized minor character)

## Current Issues (Priority Order)

### CRITICAL

1. **Analysis must be re-run to test the Wolfsheim fix**
   - Problem: Output files were not regenerated after fix was applied
   - Evidence: File timestamps predate the fix commit
   - Action: Run analysis pipeline before evaluation can proceed

### HIGH

2. **Meyer Wolfsheim spelling variant not merged (may be fixed - needs verification)**
   - Problem: "Meyer Wolfsheim" (main_cast_7) and "Meyer Wolfshiem" (supporting_8) are separate
   - Evidence: jq output shows two entries with 32 and 6 mentions respectively
   - ID patterns: main_cast_7 vs supporting_8 → cross-pipeline merge issue
   - Location: Fix was applied to `src/agents/characters.py:2419-2445`
   - Status: **Cannot evaluate until analysis is re-run**

3. **Physical appearance data missing for most characters**
   - Problem: Most characters have `appearance.summary: "unknown"`
   - Evidence: Gatsby, Daisy, Jordan all have "unknown" despite text descriptions
   - Only Tom Buchanan has appearance data ("sturdy straw-haired man of thirty")
   - Location: `src/pipeline/character_profiling/` - appearance extraction prompts
   - Fix: Improve appearance extraction to find physical descriptions

### MEDIUM

4. **False positive: "Town Tattle" extracted as character**
   - Problem: Publication listed as character (supporting_11)
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Prompt clarification to exclude publications/media

5. **Character naming: "Gatz" should be "Henry C. Gatz"**
   - Problem: Gatsby's father listed with incomplete name
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Use full name when evidence supports it

6. **"The man with owl-eyed glasses" could be "Owl Eyes"**
   - Problem: Unnamed descriptive reference instead of recognized nickname
   - Evidence: Character is referred to as "Owl Eyes" in literary discussion
   - Location: Alias recognition in character extraction
   - Note: May be acceptable as-is since "Owl Eyes" may not appear in text

## Fix History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Tuple unpacking crash | src/analyzer.py:2657 | Fixed |
| 2 | Main cast extraction failure | src/pipeline/character_extraction_v2/main_cast.py | Diagnostic logging |
| 3 | JSON format for qwen3-next | src/pipeline/character_extraction_v2/main_cast.py | Wrapped object prompts - MAJOR IMPROVEMENT (+1.15) |
| 4 | Wolfsheim/Wolfshiem spelling variants | src/agents/characters.py:2419-2445 | **NOT TESTED - output not regenerated** |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | CRASH | - | Tuple unpacking error (fixed) |
| 2 | 7.35 | 0.00 | First scoreable run - character fragmentation + missing profiles |
| 3 | 8.5 | +1.15 | Character consolidation fixed, 2 categories still below 8.0 |
| 4 | N/A | N/A | Output not regenerated - cannot score |

## Configuration Notes

Model: qwen3-next:80b-a3b-instruct-q8_0 (user-specified, DO NOT CHANGE)
Competitive Mode: single
Output files: **STALE** - last modified 2026-01-30 15:27

## Next Action

**REQUIRED:** Re-run analysis pipeline to test the Wolfsheim fuzzy merge fix (commit f038a3b).

**Why:** The previous analysis run (attempt 4) did NOT regenerate output files. The files are timestamped 15:27 but the fix was committed at 15:40. The analysis must run now to verify whether the fix worked.

**Note to analyze phase:** After analysis completes, verify that output file timestamps are AFTER the fix commit time (15:40:29).
