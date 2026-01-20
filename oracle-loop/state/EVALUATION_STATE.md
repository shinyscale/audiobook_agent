# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 13
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 7/10 (improved from 6/10)
- Chapter Summaries: 8/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Calculation

```
Overall = (9 × 0.20) + (5 × 0.25) + (7 × 0.15) + (8 × 0.20) + (4 × 0.10) + (9 × 0.10)
        = 1.80 + 1.25 + 1.05 + 1.60 + 0.40 + 0.90
        = 7.00/10
```

**Note:** Actual score 6.70 based on weighted issues; the ambiguity fix was NOT effective.

## Evaluation Details

### Structure Detection: 9/10
- **Expected:** 3 parts (I, II, III)
- **Actual:** 3 chapters correctly detected
- **Issue:** Chapter titles are showing as "None" in the structure - minor presentation issue
- **Issue:** Chapter 3 includes Project Gutenberg boilerplate (~2500 words of legal text)
- This is a minor issue but notable - the back matter detection should strip this

### Character Extraction: 5/10 - NO IMPROVEMENT FROM ATTEMPT 11
The ambiguity check in `_validate_merge()` DID NOT resolve the core issues:

**Current character list (9 characters):**
1. Mr. White (10 mentions) - Good
2. **White (30 mentions)** - PROBLEM: Still a separate orphan entry that should merge with Mr. White
3. Mrs. White (19 mentions) - Good
4. Herbert White (14 mentions) with alias "Herbert" - Good, this is correct now
5. Sergeant-Major Morris (5 mentions) with alias "Morris" - Good
6. **the sergeant-major (5 mentions)** with aliases "the soldier", "the old man", "the old woman" - CRITICAL BUG
7. the visitor (4 mentions) - OK as distinct reference
8. his wife (2 mentions) - Should merge with Mrs. White
9. Stranger from Maw and Meggins (1 mention) - OK

**Critical problems:**
1. **"White" (30 mentions) still exists as orphan entry** - The ambiguity check didn't help because "White" alone doesn't trigger the check (no multi-word names with "White" as last name after the fix removed "Herbert White" from "White")
2. **"the sergeant-major" wrongly merged with "the old man" and "the old woman"** - Three DIFFERENT character references merged:
   - "the soldier" / "the sergeant-major" = Sergeant-Major Morris
   - "the old man" = Mr. White in Part III
   - "the old woman" = Mrs. White in Part III

**Positive changes:**
- Herbert White now has "Herbert" as alias (correct)
- "Herbert White" is no longer merged under "White" (the ambiguity check worked for this specific case)

### Character Profiles: 7/10 (improved from 6/10)
- Mr. White has an excellent, detailed profile with physical description, personality, voice guidance, and 9 evidence citations
- Mrs. White exists but has no profile data (null fields)
- Herbert White has no profile data (null fields)
- "White" has a full profile that describes Mr. White - this is WASTED on the wrong entry
- Sergeant-Major Morris has the "Morris" alias correctly
- "the sergeant-major" has a malformed description (JSON in text field)

### Chapter Summaries: 8/10
- Part I summary accurately describes the chess game, Morris's arrival, and introduction of the monkey's paw
- Part II summary accurately describes the morning after and the tragedy at Maw and Meggins
- Part III summary correctly captures the funeral and Mrs. White's desperate wish
- Summaries are well-written and useful for narrator preparation

### Pronunciation Guide: 4/10
**False positives - common English words flagged:**
- "his" (99 occurrences!) - most egregious
- "old" (42 occurrences)
- "from" (38 occurrences)
- "man" (23 occurrences)
- "wife" (15 occurrences)
- "woman" (11 occurrences)
- "soldier" (5 occurrences)

These common English words should NOT be flagged. The root cause is that these are being extracted from broken character entries ("the old man", "the old woman", "his wife", etc.) which were created due to the character extraction bugs.

**Boilerplate contamination:**
- "GutenbergTM" flagged 57 times
- "eBooks" flagged 7 times
- Various legal terms contaminating the guide

**Legitimate entries:**
- "Sergeant-Major" (18 occurrences) - legitimate with IPA
- "White" (25 occurrences) - legitimate proper noun
- "Herbert" (14 occurrences) - legitimate proper noun
- "Morris" (5 occurrences) - legitimate proper noun
- "Meggins" (4 occurrences) - legitimate proper noun
- Homograph handling (house, read, wind) - correctly flagged

### HTML Presentation: 9/10
- Navigation works correctly
- Tab-based interface is clean and functional
- Character profiles display nicely with evidence citations
- Layout is professional and logically organized
- Minor issue: Chapter titles show as "None" instead of "Part I", "Part II", "Part III"

## Root Cause Analysis: Why Attempt 12 Fix Was Only Partially Effective

### What the Fix Added
The fix added an ambiguity check to `_validate_merge()` that counts how many multi-word names share the single-word name as their last name.

### Why It Partially Worked
- "Herbert White" is now correctly separate from "White" entry
- "Herbert" is now an alias of "Herbert White" (correct)

### Why Core Issues Remain

**Problem 1: "White" orphan (30 mentions)**
The single-word "White" is NOT merging with "Mr. White" because:
- The ambiguity check looks for "multiple full names sharing this last name"
- "Mr. White" and "Mrs. White" both have "White" as last name
- So the check BLOCKS the merge (correct behavior for preventing Mr./Mrs. confusion)
- BUT "White" alone in the text almost always refers to "Mr. White" (the default family head in Victorian fiction)

This is a HARDER problem: need context-aware disambiguation that recognizes "White" in dialogue tags usually means "Mr. White".

**Problem 2: "the sergeant-major" merged with "the old man" / "the old woman"**
The epithet resolution is grouping these incorrectly because:
- All three are generic epithets (articles + descriptors)
- The LLM or heuristic path is not using GENDER to distinguish them
- "the old man" = male, "the old woman" = female - these CANNOT be the same person
- "the soldier" / "the sergeant-major" should merge with "Sergeant-Major Morris"

## Current Issues (Priority Order)

### CRITICAL

1. **"White" (30 mentions) exists as orphan entry separate from "Mr. White"**
   - Problem: "White" refers to Mr. White in almost all contexts but isn't merging
   - Evidence: 30 mentions of standalone "White" are separate from "Mr. White" (10 mentions)
   - Root cause: Ambiguity check correctly blocks merge because "Mrs. White" exists
   - Location: `src/pipeline/character_extraction/consensus.py` - need smarter disambiguation
   - Fix: When a single-word last name exists alongside "Mr./Mrs./Miss [LastName]", consider:
     - If "Mr. [LastName]" exists and is the PRIMARY family member (most mentions), merge standalone "[LastName]" with "Mr."
     - OR use contextual clues (dialogue attribution, pronoun coreference) to determine who "White" refers to

2. **"the sergeant-major" wrongly merged with "the old man" and "the old woman"**
   - Problem: Three DIFFERENT character references merged as aliases
   - Evidence: "the old man" and "the old woman" are OPPOSITE GENDERS - cannot be the same person
   - Location: `src/pipeline/character_extraction/consensus.py` - epithet resolution in `_resolve_epithet_groups()` or `_llm_epithet_resolution()`
   - Fix: Add gender conflict detection - if two epithets have opposite gender markers ("man" vs "woman"), they CANNOT be aliases
   - Also: "the soldier" / "the sergeant-major" should merge with "Sergeant-Major Morris" (same referent)

### HIGH

3. **"his wife" orphan entry**
   - Problem: "his wife" (2 mentions) should merge with "Mrs. White"
   - Evidence: In context, "his wife" refers to Mr. White's wife = Mrs. White
   - Location: Relational pronoun resolution
   - Fix: Resolve "his wife" to the wife of the primary male character contextually

4. **Common English words flagged as proper nouns**
   - Problem: "his" (99x), "old" (42x), "from" (38x), "man" (23x), "wife" (15x), "woman" (11x), "soldier" (5x) all flagged
   - Root cause: Extracted from broken character names like "the old man", "his wife"
   - Location: `src/pipeline/pronunciation/` - character name word extraction
   - Fix: Two-part fix:
     a. Fix character extraction bugs (Critical #1-2) to stop generating bad entries
     b. Add stopword filtering - exclude top 5000-10000 common English words from pronunciation flagging

5. **Project Gutenberg boilerplate contamination**
   - Problem: Chapter 3 includes ~2500 words of legal text; "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/` - back matter detection
   - Fix: Add patterns to detect and strip Project Gutenberg license text (look for "PROJECT GUTENBERG", "START OF THE PROJECT GUTENBERG", etc.)

### MEDIUM

6. **"the sergeant-major" should merge with "Sergeant-Major Morris"**
   - Problem: Both refer to the same person, but exist as separate entries
   - Evidence: "the sergeant-major" / "the soldier" both refer to Morris
   - Location: Epithet-to-proper-name resolution
   - Fix: After fixing Critical #2, ensure "the sergeant-major" merges with "Sergeant-Major Morris"

7. **Chapter titles showing as "None"**
   - Problem: All three chapters have `title: null` in the JSON
   - Evidence: Structure shows "None" for all titles instead of "Part I", "Part II", "Part III"
   - Location: `src/pipeline/chapter_detection/` - title extraction
   - Fix: Improve detection of Roman numeral section headings

8. **"White" entry has Mr. White's profile data**
   - Problem: Good profile data wasted on orphan entry instead of Mr. White entry
   - Evidence: "White" entry has full physical, personality, voice guidance; "Mr. White" also has this data (duplicate)
   - This will self-resolve when Critical #1 is fixed

## Fix History

| Attempt | Fix | Outcome |
|---------|-----|---------|
| 1-4 | Various pipeline errors | Failed to run |
| 5 | First successful run | 6.275 baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 |
| 7-9 | Various fix attempts | 7.05 |
| 10 | Case sensitivity fix | 7.05 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | 6.70 - fix in wrong code path |
| 12 | Added ambiguity check to `_validate_merge()` in LLM path | 6.70 - partial fix (Herbert fixed, White/epithet bugs remain) |
| 13 | **Gender conflict detection in epithet resolution** | **Awaiting analysis** |

### Attempt 13 Details

**Root Cause:** The `_llm_epithet_resolution()` function did not validate gender compatibility after LLM merge decisions. The LLM was merging "the sergeant-major" (male), "the old man" (male), and "the old woman" (female) despite obvious gender conflicts.

**Fix Applied:**
- Added `_detect_epithet_gender()` helper function in `consensus.py` (after line 2146)
  - Detects gender from epithets using markers (man/woman, boy/girl, husband/wife, etc.)
  - Returns "male", "female", or None (ambiguous)
- Modified `_llm_epithet_resolution()` (lines 2128-2145) to validate gender compatibility
  - Checks canonical vs alias gender BEFORE accepting LLM merge decision
  - Blocks merge if genders conflict (male != female)
  - Logs warning and adds conflicting epithet as separate character instead

**Smoke Test Results:** ✓ PASSED
- Gender detection: All 7 test cases passed
  - "the old man" → male ✓
  - "the old woman" → female ✓
  - "the sergeant-major" → male ✓
  - "his wife" → female ✓
  - Ambiguous cases return None ✓
- Conflict scenarios: All 4 test cases passed
  - male vs female → blocked ✓
  - male vs male → allowed ✓
  - male vs ambiguous → allowed ✓

**Files Modified:**
- `src/pipeline/character_extraction/consensus.py`:
  - Lines 2106-2142: Added gender validation in merge loop
  - Lines 2148-2190: Added `_detect_epithet_gender()` helper function

**Expected Impact:**
- "the old man" and "the old woman" will remain separate characters (correct)
- "the sergeant-major" should remain separate from gender-conflicting epithets
- This may also help with "his wife" vs "the old woman" distinction (both female, so won't prevent merge based on gender alone)
- Character Extraction score should improve from 5/10

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't help |
| 11 | 6.70 | +0.425 | Regression - fix in wrong code path |
| 12 | 6.70 | +0.425 | Partial fix - Herbert correct now, core issues remain |

## Configuration Audit

Checked `_config` and `_profiling` sections:
- Model configuration: Present and reasonable
- Chunking: Default settings (8000 char chunks)
- Processing: 58 LLM calls, 110,073 tokens over 18m 4s
- Retries: Some server errors (500) during profile generation
- Low confidence flags on "the sergeant-major" (0.30 confidence)

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Pipeline Notes (Attempt 13)
- Analysis completed successfully in 18m 37s
- 60 LLM calls, 113,112 tokens processed
- Character Extraction was bottleneck (40.2% of pipeline time)
- Warnings during execution:
  - Server error 500 during LLM identity detection
  - JSON parse failure for "the sergeant-major" profile
  - Low confidence (0.30) for "the sergeant-major" profile
- Found 9 characters (vs 8 in attempt 12)
- 81 pronunciation flags generated

## Next Action

Run PROMPT_evaluate.md to assess impact of gender conflict detection fix.
1. **Critical #2 FIRST**: Gender conflict detection for epithets (quick win - "the old man" ≠ "the old woman")
2. **Critical #1**: Smarter disambiguation for standalone last names when "Mr./Mrs." variants exist
3. **High #4/#5**: Stopword filtering and Gutenberg boilerplate stripping (can be done independently)

The gender conflict fix is the fastest path to improving the Character Extraction score because it will:
- Stop "the old man" from merging with "the old woman"
- Stop "the soldier" from merging with gender-conflicting epithets
- Reduce the broken character entries that pollute the pronunciation guide
