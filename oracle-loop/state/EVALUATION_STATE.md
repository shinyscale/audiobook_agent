# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 7.05
- **Competitive Mode:** multi

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 5/10 ← CRITICAL ISSUE
- Character Profiles: 4/10 ← CRITICAL ISSUE
- Chapter Summaries: 9/10
- Pronunciation Guide: 8/10
- HTML Presentation: 8/10
- **Overall: 7.05/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.05 | - | Baseline - Mrs. White missing |

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Current Issues (Priority Order)

### CRITICAL
1. **Missing main character: Mrs. White**
   - Problem: Mrs. White is completely absent from the character list despite being one of the three main characters (the mother/wife)
   - Evidence: She appears throughout all three chapters. In Part III, she is the one desperately trying to open the door while Mr. White searches for the paw. The summaries reference her: "Mrs. White said, 'Tut, tut!'", "Mrs. White anxiously awaits the postman", "his wife shrieking in horror"
   - ID patterns: All characters have `supporting_*` IDs, suggesting main cast extraction failed entirely
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - main cast not producing results, falling back to supporting only
   - Fix: Investigate why main cast pipeline returned 0 characters. Mrs. White is mentioned many times and should be detected.

### HIGH
2. **Canonical names missing titles**
   - Problem: Characters extracted as "White", "Herbert", "Morris" instead of "Mr. White", "Herbert White", "Sergeant-Major Morris"
   - Evidence: The text uses "Mr. White", "Mrs. White", "Herbert White", "Sergeant-Major Morris" as full names
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - title stripping too aggressive
   - Fix: Preserve titles (Mr., Mrs., Sergeant-Major) in canonical names

3. **No relationships captured**
   - Problem: All characters have empty `relationships: {}`
   - Evidence: Herbert is the son of Mr. and Mrs. White; Morris is a friend/acquaintance of Mr. White
   - Location: Profile generation in supporting cast pipeline
   - Fix: Ensure relationship extraction is enabled and functioning

4. **Mr. White profile data malformed**
   - Problem: The `descriptions` field contains a jumbled JSON-like string instead of proper structured data
   - Evidence: Description text includes fragments like `"appearance\": \"summary\": \"unknown\"` embedded in the text
   - Location: `src/pipeline/character_extraction_v2/` profile generation
   - Fix: Check LLM response parsing for malformed JSON

### MEDIUM
5. **Chapter titles not extracted**
   - Problem: All 3 chapters have `title: null` instead of "Part I", "Part II", "Part III"
   - Location: Structure detection in `src/pipeline/chapter_detection/`
   - Fix: Look for "Part I/II/III" patterns as chapter titles

6. **"the old man/woman" aliases not linked**
   - Problem: Chapter 3 summary uses "the old man" and "the old woman" which should be aliases for Mr./Mrs. White
   - Location: Alias resolution
   - Fix: (Blocked by CRITICAL #1 - Mrs. White must be detected first)

## Fix Priority

**To reach 8.0 threshold:**
1. Fix CRITICAL #1 (Mrs. White missing) - this alone would raise Character Extraction from 5→8 (+0.75 overall)
2. Fix HIGH #2 (canonical names) - minor improvement
3. Fix HIGH #3 (relationships) - would raise Profiles from 4→6 (+0.3 overall)

Fixing issues #1 and #3 should be sufficient to pass: 7.05 + 0.75 + 0.3 ≈ 8.1

## Pipeline Notes
- Total time: 36m 14s
- All characters came from supporting_cast pipeline (IDs: supporting_0, supporting_1, supporting_2)
- Main cast pipeline produced 0 characters - this is the root cause of missing Mrs. White
- 1 low-confidence character profile (Mr. White)
- Some deepseek-r1 timeouts during execution but pipeline completed

## Configuration Notes
- Config present: Yes
- Profiling present: Yes
- Model timeouts occurred (deepseek-r1) but didn't cause complete failure

## Fix History
### Attempt 1 - Fix 1: Allow generic descriptors as character aliases
- **Root Cause:** `src/pipeline/character_extraction_v2/main_cast.py:_are_different_titled_people()` lines 1494-1495, 1503-1504
  - The function checks if two names represent different people based on titles
  - When one name has a title (e.g., "Mr. White") and the other doesn't (e.g., "father"), it checks for substring overlap
  - Generic family descriptors like "father", "mother", "the old man" have no overlap with surnames, so they were incorrectly blocked
- **Symptom:** Main cast extraction actually DID extract 7 characters (verified via debug logs), but `verify_aliases()` blocked family descriptors, leaving characters without key aliases. This may have caused grounding failures or other downstream issues.
- **Fix Applied:** Added whitelist of generic descriptors (family relationships, age/gender terms, role descriptors) at line 1447
  - If either name is in the whitelist, return False (allow as alias) immediately
  - Descriptors include: "father", "mother", "son", "daughter", "the old man", "the old woman", etc.
- **Smoke Test:** Ran `test_main_cast.py` on monkeys_paw summaries
  - ✓ Mrs. White now extracted
  - ✓ Mr. White has "father" as alias
  - ✓ Mrs. White has "the old woman" and "mother" as aliases
  - ✓ 7 main cast profiles extracted (vs 0 characters reaching final output in broken version)
- **Expected Impact:**
  - Fixes CRITICAL #1 (Mrs. White missing) - main cast extraction will now produce results
  - Partially fixes MEDIUM #6 ("the old man/woman" aliases) - these are now allowed as aliases
  - May improve Character Extraction score from 5→8 (+0.75 overall)
- **Modified Files:** `src/pipeline/character_extraction_v2/main_cast.py`

## Next Action
Re-run analysis to verify fix (phase: awaiting_analysis)
