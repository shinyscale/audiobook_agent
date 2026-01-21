# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 10
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 4/10 ← CRITICAL (Chapter III AND V missing, only 8 chapters)
- Character Extraction: 5/10 ← CRITICAL (Daisy split into 3 entries, 99 total chars)
- Character Profiles: 3/10 ← CRITICAL (0 characters have appearance data)
- Chapter Summaries: 7/10 (Quality good but missing 2 chapters)
- Pronunciation Guide: 5/10 (76% "unknown" categorization, no improvement)
- HTML Presentation: 8/10 (Functional)
- **Overall: 5.10/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |
| 4 | 7.20 | +0.55 | Chapter V back, Wolfsheim merged, pronunciation categories work |
| 5 | 6.70 | +0.05 | REGRESSION: Chapter IV split, profile fix didn't work |
| 6 | 6.15 | -0.50 | REGRESSION: Chapter V MISSING, profiles still broken |
| 7 | - | - | Pipeline crashed (Character model field mismatch) |
| 8 | - | - | Pipeline crashed (same error) |
| 9 | 5.10 | -1.55 | MAJOR REGRESSION: 2 chapters missing, character explosion, 0 profiles |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Attempt 10 Analysis

### What Completed
- **Ingestion:** 51,257 words, 19KB Gutenberg boilerplate removed
- **Structure:** 8 chapters detected (still only 8 chapters!)
- **Summaries:** 8 summaries generated
- **Characters (v2):** 37 characters extracted (down from 99!)
- **Profiles:** 17 profiles for 18 eligible characters (11H/0M/7L confidence)
- **Pronunciation:** 578 entries (506 "unknown" = 87.5%)

### Profiling Data
```
Chapter Detection: 41 LLM calls, 0 retries, 8 items
Chapter Summaries: 43 LLM calls, 0 retries, 8 items
Character Extraction V2: 2 LLM calls, 0 retries, 19 items
Character Profiles: 42 LLM calls, 0 retries, 18 items (11H/0M/7L confidence)
Pronunciation Guide: 21 LLM calls, 0 retries, 578 items
```

### Pipeline Duration
- Total: 55m 58s
- Bottleneck: Character Profiles (21m 42s = 38.8% of time)

### Observations
1. **Character count IMPROVED:** 37 characters (down from 99 in attempt 9)
   - Initial extraction: 19 characters (was 21 in attempt 9)
   - Added from summaries: 18 characters (was 78 in attempt 9)
   - The min_mentions threshold increase (3→5) helped significantly

2. **Profile generation IMPROVED:** 42 LLM calls completed (was only 3 in attempt 9)
   - 11 high confidence, 7 low confidence
   - Some JSON parse failures noted (Nick, Daisy, Tom, Wilson, McKee, Sloane)
   - Ollama was stable this time

3. **Structure UNCHANGED:** Still only 8 chapters detected
   - Chapter detection deferred in attempt 10 fix
   - Still missing chapters III and V

4. **Daisy split status:** Need to check evaluation
   - Daisy Buchanan appears in character list with aliases (Daisy Fay, Daisy)
   - Improved MAIN_CAST_PROMPT may have helped

5. **Pronunciation:** Slightly worse (87.5% unknown vs 76% in attempt 9)
   - Total entries: 578 (down from 635)
   - Unknown: 506 entries

## Attempt 9 Analysis

### What Completed
- **Ingestion:** 51,257 words, 19KB Gutenberg boilerplate removed
- **Structure:** 8 chapters detected (missing Chapter III AND V)
- **Summaries:** 8 summaries generated (quality is good for the chapters that exist)
- **Characters (v2):** 99 characters extracted (WAY too many - was ~21 before reconciliation)
- **Profiles:** 3 LLM calls for 18 eligible characters - 17 LOW confidence (Ollama failures)
- **Pronunciation:** 635 entries (481 "unknown" = 76%)

### What Failed
1. **Chapter Detection** - Only 8 chapters detected:
   - Chapter I → title: null
   - Chapter II → "II"
   - Chapter III → "Section Introduction" (WRONG - not chapter V content, this appears to be Chapter III content)
   - Chapter IV → "IV"
   - Chapter V → MISSING ENTIRELY
   - Chapter VI → "VI"
   - ... through IX

2. **Character Explosion** - 99 total characters instead of ~25-30 expected:
   - V2 pipeline extracted 21 characters initially (reasonable)
   - Then 78 additional characters were added from summaries
   - This suggests summary-driven character extraction is adding too many minor/incidental references

3. **Daisy Split** - Three separate Daisy entries:
   - "Daisy" (179 mentions) - main entry, no aliases
   - "Daisy Buchanan" (3 mentions) - not merged
   - "Daisy Fay" (1 mention) - not merged
   - These should ALL be the same character with "Daisy Buchanan" as canonical name

4. **Profile Generation Cascade Failure** - Only 1 profile generated (Nick Carraway, partial):
   - 17 of 18 eligible characters got LOW confidence
   - Only 3 LLM calls succeeded out of expected 18
   - Profiling data shows: `json_parse_failures: 1`
   - Ollama connection issues during profile phase

### Profiling Data
```
Chapter Detection: 40 LLM calls, 0 retries, 8 items
Chapter Summaries: 44 LLM calls, 0 retries, 8 items
Character Extraction V2: 2 LLM calls, 0 retries, 21 items
Character Profiles: 3 LLM calls (!), 1 json_parse_failure, 18 items (17 LOW confidence)
Pronunciation Guide: 0 LLM calls, 635 items
```

## Current Issues (Priority Order)

### CRITICAL

1. **Structure: Chapters III and V Missing**
   - Problem: Only 8 chapters detected. Chapter III labeled "Section Introduction", Chapter V completely absent
   - Evidence: Gatsby has exactly 9 chapters (I-IX). Output shows: null, II, "Section Introduction", IV, VI, VII, VIII, IX
   - Impact: -6 points on Structure (4/10), -1 point on Summaries (missing content)
   - Location: `src/pipeline/chapter_detection.py` - chapter title/number extraction
   - Analysis: "Section Introduction" title suggests LLM is misinterpreting chapter headings
   - Fix: The chapter detection needs stricter enforcement of roman numeral sequence. If chapters I, II, IV are detected, III must exist between II and IV.

2. **Character Extraction: Daisy Split into 3 Entries**
   - Problem: Daisy Buchanan appears as 3 separate characters:
     - "Daisy" (179 mentions, no aliases)
     - "Daisy Buchanan" (3 mentions, no aliases)
     - "Daisy Fay" (1 mention, no aliases)
   - Evidence: These are the same person - Daisy Fay is her maiden name, Daisy Buchanan her married name
   - Impact: -3 points on Character Extraction (5/10)
   - Location: `src/pipeline/character_extraction_v2/` - alias merging logic
   - Fix: Improve alias resolution to merge "FirstName" with "FirstName LastName" variants

3. **Character Count Explosion: 99 Characters**
   - Problem: 99 total characters when ~25-30 expected for Gatsby
   - Evidence: V2 extraction found 21 initially (reasonable), then summary reconciliation added 78 more
   - Impact: Bloated character list, difficult for narrator to use, dilutes main cast
   - Location: `src/pipeline/character_extraction_v2/` - summary-driven character extraction
   - Fix: Apply stricter filtering to summary-extracted characters (minimum mentions threshold)

4. **Profile Generation: 0 Successful Profiles**
   - Problem: Only Nick Carraway has partial profile (personality/voice but appearance="unknown")
   - Evidence: Profiling shows only 3/18 LLM calls completed, 17 LOW confidence
   - Impact: -7 points on Profiles (3/10 → should be 8+)
   - Location: Profile generation in `src/pipeline/character_extraction_v2/`
   - Root cause: Ollama instability during profile generation phase
   - Fix: Add retry logic with exponential backoff, or run profile generation as separate phase that can be retried

### HIGH

5. **Chapter I Title is Null**
   - Problem: First chapter has `title: null` instead of "I"
   - Evidence: Other chapters (II, IV, VI-IX) have titles
   - Impact: -1 point on Structure
   - Location: `src/pipeline/chapter_detection.py`
   - Fix: Ensure first detected chapter gets roman numeral title

6. **"Nick (narrator)" as Separate Entry**
   - Problem: "Nick (narrator)" (1 mention) listed separately from "Nick Carraway"
   - Evidence: Nick Carraway is correctly marked `is_narrator: true`
   - Location: `src/pipeline/character_extraction_v2/` - needs deduplication
   - Fix: Filter out "Character (role)" style entries when canonical entry exists

### MEDIUM

7. **Pronunciation: 76% "Unknown" Category**
   - Problem: 481 of 635 entries (76%) have `flag_reason: "unknown"`
   - Distribution: proper_noun: 114, homograph: 23, foreign: 17, unknown: 481
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve categorization logic

8. **Wilson Surname Ambiguity**
   - Problem: "Wilson" (65 mentions) separate from George B. Wilson and Myrtle Wilson
   - Note: May be intentional - "Wilson" often genuinely ambiguous in text
   - Impact: Minor

## Path to 8.0

**Current: 5.10/10, Need: 8.0/10, Gap: 2.9 points**

This is the worst score yet due to compounding regressions.

| Fix | Effort | Estimated Impact |
|-----|--------|------------------|
| Fix chapter detection (all 9 chapters) | HIGH | +5 on Structure (4→9) = +1.0 overall |
| Fix Daisy merge + char explosion | HIGH | +3 on Characters (5→8) = +0.75 overall |
| Fix profile generation (retry logic) | MEDIUM | +5 on Profiles (3→8) = +0.75 overall |
| Total expected | | 5.10 + 2.5 = 7.6 |

**Still need ~0.4 more - may require pronunciation improvement**

## Root Cause Analysis

### Structure Non-Determinism
Despite setting temperature=0.0 in attempt 7, structure detection remains unstable:
- Attempt 7: 9 chapters (temp fix applied but pipeline crashed)
- Attempt 8: 11 chapters (crashed again)
- Attempt 9: 8 chapters (Chapter III mislabeled, V missing)

The temperature fix alone is insufficient. Need deterministic chapter title validation.

### Character V2 Pipeline Issues
1. Initial extraction (21 chars) is reasonable
2. Summary reconciliation adds too many characters (78!)
3. Alias merging is not connecting Daisy variants
4. Profile generation has no retry mechanism for Ollama failures

### Ollama Instability
Profile generation failed catastrophically:
- 3 LLM calls completed out of expected 18
- 17 LOW confidence items
- 1 JSON parse failure
- This suggests Ollama crashed or became unresponsive mid-pipeline

## Recommended Fix for Attempt 10

**Priority 1: Structure Detection**
- Add validation to enforce roman numeral sequence
- If chapters I, II, IV, VI exist, chapters III and V MUST be inferred/detected
- Add post-processing to verify chapter count matches expected (9 for Gatsby)

**Priority 2: Character Merging**
- Fix Daisy split: "Daisy" + "Daisy Buchanan" + "Daisy Fay" → "Daisy Buchanan"
- Filter summary-extracted characters more aggressively (require 3+ mentions?)
- Remove "Character (role)" duplicate entries

**Priority 3: Profile Generation Resilience**
- Add retry logic for Ollama failures
- Consider running profile generation as a separate, retriable phase
- Fall back to simpler profiles if LLM fails repeatedly

## Fix History

### Attempt 2
- Fixed chapter detection (was splitting chapter 7 at section break)
- Added character merge logic for main cast

### Attempt 3
- Investigated Chapter V missing (non-deterministic)
- Added role field to character export
- Expanded pronunciation whitelist (115→162 entries)

### Attempt 4
- Added `_merge_within_supporting_cast` function
- Enhanced `_merge_lastname_aliases` with first-name matching
- Chapter V detection improved (now working)
- Wolfsheim merge now working
- George → George Wilson merge working

### Attempt 5
- **FAILED FIX:** Modified `_convert_to_pipeline_characters()` to pass mentions - did not improve profiles
- **SUCCESSFUL FIX:** Added common first names to pronunciation whitelist
- **REGRESSION:** Structure worse (Chapter IV split)

### Attempt 6
- **FAILED FIX:** Updated `mention_results` dict after alias merges - did not improve profiles
- **REGRESSION:** Structure worse (Chapter V now missing entirely)
- Analysis ran for 60m 6s
- Only 3 characters got profiles (Dan Cody, Catherine, Wolfshiem)

### Attempt 7
- **FIX APPLIED:** Modified `apply_profile_to_config()` to preserve temperature=0.0
- **RESULT:** Pipeline crashed - Character model missing "mentions" field

### Attempt 8
- **FIX APPLIED:** Added `mentions` field to Character model
- **RESULT:** Pipeline crashed - same error (fix didn't apply properly)

### Attempt 9
- **FIX APPLIED:** Confirmed `mentions` field added to Character model
- **RESULT:** Pipeline completed but with major regressions
- Structure: 8 chapters (missing III and V)
- Characters: 99 total (explosion from summary reconciliation)
- Profiles: 0 successful (Ollama instability)

### Attempt 10
- **ROOT CAUSE ANALYSIS COMPLETED:**
  1. **Structure:** Chapters III (pos 58148) and V (pos 121448) exist in text but detection finds 8 boundaries, with false positives in middle of Chapter III. Complex issue in consensus builder - deferred.
  2. **Daisy split:** LLM in `MAIN_CAST_PROMPT` returned "Daisy", "Daisy Buchanan", "Daisy Fay" as separate characters instead of one character with aliases. `_merge_same_firstname_variants` should have caught this but didn't (unclear why - needs further investigation).
  3. **Character explosion:** Supporting cast extraction uses `min_mentions=3`, too low for a novel like Gatsby (51K words). Results in 84 supporting chars.
  4. **Profile failures:** Ollama made only 3 LLM calls for 18 characters, indicating crash/hang. Needs retry logic.

- **FIXES APPLIED:**
  1. **MAIN_CAST_PROMPT:** Added explicit rule #3 about maiden/married names being the SAME character. Added concrete examples (Elizabeth Bennet/Darcy) showing how to handle name variants as aliases.
  2. **Supporting cast threshold:** Increased `min_mentions` from 3 to 5 in `characters_v2.py` line 203 to reduce noise from incidental characters.

- **FIXES DEFERRED:**
  1. **Chapter detection:** Too complex for this iteration - requires debugging consensus builder and proposal clustering
  2. **Profile generation retry:** Deferred - needs Ollama monitoring infrastructure

- **Modified files:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (lines 38-77: improved prompt)
  - `src/agents/characters_v2.py` (line 203: min_mentions 3→5)

- **Smoke test:** PASSED - Prompt includes maiden/married guidance, min_mentions updated

## Notes

Attempt 9 represents the worst performance yet. The Character model fix allowed the pipeline to complete, but revealed:
1. Structure detection is still non-deterministic despite temperature=0.0
2. V2 character extraction adds too many characters from summaries
3. Alias merging for Daisy is completely broken
4. Profile generation has no resilience to Ollama failures

The next fix attempt needs to focus on robustness and validation rather than just temperature settings.
