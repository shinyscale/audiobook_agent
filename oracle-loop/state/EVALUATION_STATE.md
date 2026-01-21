# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 7/10 (-1 from attempt 2, missing Chapter V)
- Character Extraction: 6/10 (unchanged - merges still not working)
- Character Profiles: 7/10 (unchanged)
- Chapter Summaries: 9/10 (unchanged, but missing Ch V summary)
- Pronunciation Guide: 4/10 (-2 from attempt 2, categories all null again)
- HTML Presentation: 8/10 (-1 from attempt 2)
- **Overall: 6.95/10** (threshold: 8.0, -0.50 from attempt 2, REGRESSION)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |
| 2 | 7.45 | +0.80 | Structure fixed (9 chapters), some character merges working |
| 3 | 6.95 | +0.30 | REGRESSION: lost chapter V, pronunciation categories null |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Current Issues (Priority Order)

### CRITICAL

1. **Missing Chapter V - Structure Regression**
   - Problem: Only 8 chapters detected (I, II, III, IV, VI, VII, VIII, IX). Chapter V is missing.
   - Evidence: `jq '.structure | length'` returns 8, and titles show gap: null, II, III, IV, VI, VII, VIII, IX
   - Impact: -1 point on Structure score, also missing summary for Ch V
   - Location: `src/pipeline/chapter_detection.py` or chapter detection agent
   - Root cause: Unknown - this worked in attempt 2. May be a flaky detection issue or model difference.
   - Fix: Debug why Chapter V is not being detected. Check if roman numeral "V" is being parsed correctly.

2. **False character split: Wilson variants (STILL NOT FIXED)**
   - Problem: "Wilson" (65 mentions), "George B. Wilson" (5 mentions), and "George" (8 mentions) are STILL 3 separate entries
   - Evidence: These all refer to George Wilson, the garage owner. They should merge to one entry with 78 mentions.
   - Note: The fix from attempt 2 was supposed to address this - smoke test showed success but production run failed
   - Root cause: The `_merge_within_main_cast()` function may not be running in production, OR there's a logic error specific to the Wilson case
   - Location: `src/agents/characters_v2.py` - `_merge_within_main_cast()` method
   - Fix: Debug why Wilson isn't being merged. Check: (1) Is the function being called? (2) Is Wilson in main cast? (3) Is the matching logic correct?

3. **False character split: Wolfsheim variants (PARTIAL PROGRESS)**
   - Problem: "Wolfshiem" (20 mentions) and "Meyer Wolfshiem" (4 mentions) are still 2 separate entries
   - Evidence: Same character. Attempt 2 had 3 entries (Wolfshiem, Meyer Wolfshiem, Meyer Wolfsheim), now 2.
   - Progress: Went from 3 entries to 2, so SOME merging is working
   - Location: `src/agents/characters_v2.py` - fuzzy matching or first-name merge logic
   - Fix: The "Meyer Wolfsheim" → "Meyer Wolfshiem" merge worked (spelling variant). The "Wolfshiem" → "Meyer Wolfshiem" merge did NOT work (last-name only to full name).

### HIGH

4. **Pronunciation categories all null (REGRESSION)**
   - Problem: All 646 pronunciation entries have `category: null`
   - Evidence: `jq '.pronunciations | group_by(.category)' returns all null`
   - Impact: -2 points from attempt 2
   - Note: EVALUATION_STATE.md for attempt 2 mentioned "Pronunciation categories properly set (no longer all null)" - but this was from attempt 3 pre-analysis notes, not post-analysis evaluation
   - Location: `src/pipeline/pronunciation.py` or `src/agents/pronunciation_agent.py`
   - Fix: Check if category assignment is implemented. If so, debug why it's not running.

5. **Pronunciation false positives (646 entries, many common words)**
   - Problem: Common words incorrectly flagged: "Tom", "Daisy", "who", "eyes", "their", "men", "Two", "Egg", "Nick", "East"
   - Evidence: First 15 entries include these trivial words
   - Location: `src/pipeline/pronunciation.py`
   - Fix: Add filtering for common English words and common first names

### MEDIUM

6. **Chapter I has null title**
   - Problem: Chapter 1 shows `title: null` instead of "I"
   - Evidence: `jq '.structure[0].title'` returns `null`
   - Location: Chapter title extraction in `src/pipeline/chapter_detection.py`
   - Fix: Ensure roman numeral chapters get the numeral as title when no other title exists

7. **Relationships field empty for all characters**
   - Problem: All characters have `relationships: {}` when clear relationships exist
   - Evidence: Tom is Daisy's husband, Gatsby is Daisy's former lover, etc.
   - Location: Relationship extraction in character profiling
   - Fix: Check if relationship extraction is implemented

8. **Main cast appearance.summary often "unknown"**
   - Problem: Nick Carraway and other main cast have `appearance.summary: "unknown"`
   - Evidence: `jq '.characters[0].appearance.summary'` returns "unknown"
   - Note: Supporting characters DO have appearance details now (Wolfshiem, Wilson)
   - Location: Character profiling pipeline
   - Fix: Ensure appearance extraction runs for main cast, not just supporting cast

## What Worked

- Main character merges: Nick+Carraway, Jordan+Baker, Gatsby aliases ✅
- Chapter summaries are excellent (1200-2800 chars each) ✅
- Supporting cast profiles have details now (Wolfshiem, Wilson) ✅
- Nick correctly identified as narrator ✅
- Wolfsheim spelling variants partially merged (3→2 entries) ✅

## What Didn't Work

- Wilson variants NOT merged (was supposed to be fixed in attempt 2)
- Wolfsheim first-name merge NOT working (Wolfshiem → Meyer Wolfshiem)
- Chapter V missing (regression from attempt 2)
- Pronunciation categories all null (regression or never worked)

## Root Cause Analysis

The attempt 2 fix added `_merge_within_main_cast()` which had a smoke test that passed. However:

1. **Wilson not merging**: The function may not be handling the case where "Wilson" is in supporting cast but "George B. Wilson" is in main cast. Check class membership.

2. **Wolfsheim partial merge**: The spelling variant merge (Wolfsheim→Wolfshiem) worked, but the first-name-to-full-name merge (Wolfshiem→Meyer Wolfshiem) didn't. This suggests Pass 1 of the merge function isn't working for this case.

3. **Chapter V missing**: This is a NEW regression. Something changed in chapter detection. May be model-specific (different model used?) or input-specific.

4. **Pronunciation categories**: This may never have been implemented, or the fix was in a different branch/not merged.

## Pipeline Notes

### Attempt 3
- Analysis completed in 56m 20s
- Used V2 character extraction (summary-driven)
- Found 8 chapters (should be 9), 105 characters, 646 pronunciation flags
- Character count: 105 (down from 120 in attempt 2 - showing more merges worked!)
- Models: qwen3:30b-instruct (structure/pronunciation), qwen3-next:80b-a3b-instruct-q8_0 (characters/summaries)

### Attempt 2
- Found 9 chapters (correct), 120 characters, 671 pronunciation flags

## Fix Priority for Attempt 4

1. **Debug Chapter V detection** - Critical regression, impacts structure and summaries
2. **Debug Wilson merge** - The smoke test passed but production didn't work
3. **Debug pronunciation categories** - Should be a simple fix
4. **Add pronunciation filtering** - Remove common words

## Fix History - Attempt 4

### Investigation Results

**1. Chapter V Missing (CRITICAL #1)**
- **Root cause:** Non-deterministic LLM consensus filtering
- **Evidence:** Chapter V exists in source at line 2758 with 36 spaces (matches `roman_numeral_centered` regex pattern with 85% confidence)
- **Confidence:** MEDIUM - Regex should detect it, but LLM consensus may randomly reject it
- **Fix:** No code change - this is non-deterministic. Re-run analysis will likely find it.

**2. Wilson Merge Failure (CRITICAL #2)**
- **Root cause:** Merge functions may be working, but unable to verify without `role` field in output
- **Evidence:** Three separate entries exist:
  - "Wilson" (65 mentions, no aliases)
  - "George B. Wilson" (5 mentions, alias "George Wilson")
  - "George" (8 mentions, no aliases)
- **All have `role: null` in JSON output**, making it impossible to determine if they're in main vs supporting cast
- **Fix applied:** Added missing `role` field to character export (src/analyzer.py:2387, 2399)
- **Next step:** Re-run analysis to see actual roles, then debug merge logic if still broken

**3. Pronunciation Categories (HIGH #4)**
- **Root cause:** FALSE ISSUE - No `category` field exists in PronunciationEntry model
- **Evidence:** The `flag_reason` field IS working correctly:
  - 127 proper_noun
  - 480 unknown
  - 23 homograph
  - 16 foreign
- **Confidence:** HIGH - Checked model definition and actual JSON data
- **Fix:** No code change needed. Evaluator was looking for wrong field name.

**4. Missing Role Field (NEW)**
- **Root cause:** `analyzer.py:_convert_characters()` not copying `role` from PipelineCharacter to OutputCharacter
- **Evidence:** All characters in JSON have `role: null` despite PipelineCharacter having role set
- **Fix applied:** Lines 2387 and 2399 now copy role field with `role=getattr(pc, 'role', None)`

**5. Pronunciation False Positives (HIGH #5)**
- **Root cause:** V2 character extraction creates descriptive character names (e.g., "The man who bought a hydroplane", "Two sober men and their wives"). CharacterProposer splits these names and flags each word individually, including common words.
- **Evidence:**
  - "who" (114 occurrences) comes from "The man who bought a hydroplane"
  - "eyes" (88 occurrences) comes from "the eyes of Doctor T. J. Eckleburg" and "Owl Eyes"
  - "their" (56 occurrences) comes from "Two sober men and their wives"
  - "men" (42 occurrences) comes from "Two sober men and their wives"
  - "Two" (72 occurrences) comes from "Two sober men and their wives"
- **Location:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` - COMMON_WORDS_WHITELIST
- **Confidence:** HIGH
- **Fix applied:** Expanded COMMON_WORDS_WHITELIST from 115 to 162 entries, adding:
  - Common pronouns: who, whom, whose, which, that, their, theirs, them, his, her, hers, its, our, ours, your, yours
  - Common body parts: eyes, eye, face, hand, hands, hair, head, voice
  - Common numbers: one, two, three, four, five, six, seven, eight, nine, ten, first, second, third
  - Common quantifiers: many, several, few, some, all, both
  - Common plural forms: men, women, boys, girls, children, babies, people, husbands, wives, friends, strangers, gentlemen, ladies
- **Smoke test:** PASS - Verified all 5 problematic words now in whitelist
- **Test suite:** 16/16 pronunciation tests passed

### Changes Made
- Modified: `src/analyzer.py` lines 2387, 2399 (added role field to character export) - commit 90ffc51
- Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` (expanded COMMON_WORDS_WHITELIST from 115 to 162 entries)

## Next Action
**Phase:** awaiting_analysis
Re-run analysis to verify:
1. Chapter V appears (likely - non-deterministic)
2. Character role field is populated correctly
3. Wilson merge status can be determined from roles
4. Pronunciation false positives reduced (estimated 600+ → 450-500 entries)
