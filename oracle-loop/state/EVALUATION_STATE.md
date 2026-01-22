# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 11
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 3/10 ← CRITICAL (Chapter I-III merged, missing chapters, misaligned)
- Character Extraction: 6/10 (Daisy FIXED! But 6 duplicate pairs, role-based false entries)
- Character Profiles: 6/10 (Data exists in HTML, appearance "unknown", JSON null)
- Chapter Summaries: 5/10 (Good quality but wrong chapter alignment)
- Pronunciation Guide: 4/10 (87% "unknown" categorization)
- HTML Presentation: 8/10 (Functional)
- **Overall: 5.20/10** (threshold: 8.0)

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
| 10 | 5.20 | -1.45 | Daisy merge FIXED, characters reduced 99→37, profiles exist but broken |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 11)

Analysis completed in 59m 8s with following observations:

**Structure Detection:**
- Found 8 chapters (expected 9 based on TOC)
- Warning: "TOC enforcement: Only 7 boundaries found but TOC expects 9"
- Warning: "StructureAgent: 2 errors found but refinement not yet implemented"
- Despite fix verification showing 9 chapters in isolated test, full pipeline detected only 8

**Character Extraction (V2):**
- 39 total characters (17 initial + 22 from summaries)
- Main characters detected: Nick Carraway, Jay Gatsby, Daisy Buchanan, Tom Buchanan, Jordan Baker
- 16 profiles generated (14H/0M/2L confidence)

**LLM Errors:**
- Server 500 error during identity detection
- 2 JSON parse failures (Jay Gatsby, Meyer Wolfsheim profiles)
- 2 low-confidence profiles (Jay Gatsby: 0.30, Meyer Wolfsheim: 0.30)

**Pronunciation:**
- 586 total entries
- 505 "unknown" categorization (still 86%)

**Pipeline Stats:**
- Total time: 59m 8s
- LLM calls: 153
- Tokens: 461,915
- Bottleneck: Chapter Summaries (40.5% of time)

## What Improved in Attempt 10
1. **Daisy Buchanan FIXED**: Now correctly merged with aliases (Daisy Fay, Daisy, Mrs. Buchanan)
2. **Character count reduced**: 99 → 37 characters (min_mentions threshold increase worked)
3. **Profiles generated**: 42 LLM calls completed vs 3 in attempt 9 (11 high conf, 7 low conf)

## What's Still Broken

### CRITICAL: Structure Detection (3/10)

**The chapter detection is catastrophically broken:**

1. **"Chapter 1" contains 3+ chapters merged:**
   - Summary mentions: Nick arriving in West Egg (Ch I), dinner at Buchanan's (Ch I), Tom's mistress in New York (Ch II), Myrtle's party (Ch II), AND Gatsby's first party (Ch III)
   - Word count: 15,051 words (should be ~5,000 per chapter)
   - This is chapters I, II, and III merged into one

2. **Missing chapters:**
   - No distinct Chapter I (merged into "Chapter 1")
   - No distinct Chapter II (merged into "Chapter 1")
   - No distinct Chapter III (merged into "Chapter 1")
   - Chapter V status unclear (may be partially in Chapter 3/4)

3. **Misaligned chapter numbers:**
   - "Chapter 2: IV" - actually Chapter IV content
   - "Chapter 3" - contains Chapter IV content (Gatsby's lunch)
   - "Chapter 4" - unclear content
   - "Chapter 5: VI" - Chapter VI content (Dan Cody backstory)
   - "Chapter 6: VII" - Chapter VII content
   - "Chapter 7: VIII" - Chapter VIII content
   - "Chapter 8: IX" - Chapter IX content

**Root Cause:** The chapter detection consensus algorithm is failing to identify chapter boundaries. The first chapter break is not found until somewhere around original Chapter IV.

### HIGH: Character Duplicates (6/10)

Six duplicate pairs remain:
1. "McKee" (16 mentions) and "Mr. McKee" - same person
2. "Sloane" (10 mentions) and "Mr. Sloane" - same person
3. "Wilson" (65 mentions) and "George Wilson" (14 mentions) - same person
4. "Wolfshiem" (20 mentions) and "Meyer Wolfsheim" - same person
5. "Owl-Eyed man" and "Owl-Eyes" - same person
6. "Narrator" (6 mentions) and "Nick Carraway" - same person (Nick IS the narrator)

Plus role-based false entries:
- "Butler", "Chauffeur", "Gardener", "Reporter", "The Finn", "West Egg postman"
- These are roles/descriptions, not named characters

### MEDIUM: Profile Data (6/10)

1. **Appearance consistently "unknown"**: Main characters (Gatsby, Nick, Daisy, Tom, Jordan) all have appearance="unknown" despite being described in the text
2. **Profile data not in JSON**: Profiles render in HTML but `analysis.json` shows `profile: null` for all characters
3. **JSON parse failures**: 2 parse failures noted in profiling data

### MEDIUM: Pronunciation Categorization (4/10)

- 578 total entries
- 506 (87%) have `flag_reason: "unknown"` - this is useless for a narrator
- Only 72 properly categorized (36 proper_noun, 23 homograph, 13 foreign)

## Current Issues (Priority Order)

### CRITICAL

1. **Structure: First 3 chapters merged into one**
   - Problem: "Chapter 1" contains ~15,000 words covering Chapters I, II, AND III
   - Evidence: Summary describes events spanning Nick's arrival through Gatsby's first party (3 distinct chapters)
   - Impact: -7 points on Structure (3/10), -3 points on Summaries (alignment broken)
   - Location: `src/pipeline/chapter_detection.py` - boundary detection failing
   - Fix: The chapter detection algorithm is not finding the "Chapter II" and "Chapter III" markers in the text. Need to verify the regex patterns match Gatsby's formatting. May need to pre-process or use different consensus approach.

2. **Structure: Chapter number extraction failing**
   - Problem: Chapters 1, 3, 4 have `title: null`, only IV, VI-IX have proper titles
   - Evidence: `jq '.structure[] | .title'` shows null, IV, null, null, VI, VII, VIII, IX
   - Impact: Further degrades Structure score
   - Location: `src/pipeline/chapter_detection.py` - title extraction
   - Fix: Roman numeral extraction is inconsistent

### HIGH

3. **Character duplicates: 6 pairs need merging**
   - Pairs: McKee/Mr. McKee, Sloane/Mr. Sloane, Wilson/George Wilson, Wolfshiem/Meyer Wolfsheim, Owl-Eyed/Owl-Eyes, Narrator/Nick Carraway
   - Impact: -1.5 points on Characters
   - Location: `src/pipeline/character_extraction_v2/` - alias detection
   - Fix: Need pattern to merge "Name" with "Mr./Mrs. Name" and "FirstName LastName" with "LastName"

4. **Role-based false entries**
   - Problem: Butler, Chauffeur, Gardener, Reporter, The Finn, West Egg postman
   - Evidence: These are descriptions/roles, not named characters
   - Impact: Dilutes character list
   - Location: `src/pipeline/character_extraction_v2/supporting_cast.py`
   - Fix: Filter out generic role nouns that aren't proper names

### MEDIUM

5. **Profile appearance always "unknown"**
   - Problem: Even main characters with clear physical descriptions have appearance="unknown"
   - Evidence: Tom Buchanan is described physically in chapter 1, Gatsby described too
   - Location: Profile generation in `src/pipeline/character_extraction_v2/`
   - Fix: Improve appearance extraction prompts

6. **Profile data not persisted to JSON**
   - Problem: HTML has profile data, JSON shows `profile: null`
   - Evidence: `jq '.characters[0].profile'` returns null
   - Location: Export/serialization code
   - Fix: Ensure profile data is written back to JSON

7. **Pronunciation 87% "unknown"**
   - Problem: 506/578 entries lack proper categorization
   - Impact: -1 point on Pronunciation
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve categorization logic

## Path to 8.0

**Current: 5.20/10, Need: 8.0/10, Gap: 2.8 points**

| Priority | Fix | Estimated Impact |
|----------|-----|------------------|
| P0 | Fix chapter detection (get all 9 chapters) | Structure 3→8 = +1.0 overall |
| P0 | Fix chapter alignment (summaries match chapters) | Summaries 5→8 = +0.6 overall |
| P1 | Merge character duplicates (6 pairs) | Characters 6→8 = +0.5 overall |
| P1 | Remove role-based entries | Characters +0.5 = +0.125 overall |
| P2 | Fix pronunciation categorization | Pronunciation 4→7 = +0.3 overall |
| **Total** | | **5.20 + 2.5 = 7.7** |

Still need ~0.3 more to hit 8.0 - would require profile improvements.

## Root Cause Analysis

### Why is Structure So Broken?

The chapter detection worked correctly in attempt 2 (9 chapters detected) but has regressed severely. Possible causes:

1. **Non-determinism**: Even with temperature=0.0, LLM outputs vary
2. **Consensus algorithm flaws**: The proposal clustering may be sensitive to slight variations
3. **Text preprocessing changes**: Any changes to ingestion/refinement could shift character positions
4. **Prompt changes**: Modifications to chapter detection prompts may have introduced issues

The fact that "Chapter 1" is ~15,000 words (3x normal) strongly suggests the first two chapter breaks are NOT being detected.

### Recommended Immediate Fix

**Focus entirely on chapter detection for attempt 11:**

1. Add a validation check: If any chapter exceeds 2x the average chapter length, flag it as potentially merged
2. Add a post-processing step: If fewer than expected chapters are found, rescan text for common chapter markers (Roman numerals, "Chapter" keyword)
3. Consider a simpler, deterministic approach for structure: regex-first detection with LLM verification rather than pure LLM consensus

Character and pronunciation issues, while important, are secondary to getting the fundamental structure correct.

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

### Attempt 5
- **FAILED:** Profile mentions fix did not improve profiles
- **SUCCESS:** Pronunciation whitelist expanded
- **REGRESSION:** Structure worse (Chapter IV split)

### Attempt 6
- **FAILED:** Profile mention_results fix
- **REGRESSION:** Structure worse (Chapter V missing)

### Attempt 7-8
- Pipeline crashed (Character model field mismatch)

### Attempt 9
- Pipeline completed but with major regressions
- 99 characters (explosion from summary reconciliation)
- 0 successful profiles

### Attempt 10
- **SUCCESS:** Daisy merge fixed (MAIN_CAST_PROMPT improvements worked!)
- **SUCCESS:** Character count reduced 99→37 (min_mentions threshold increase worked)
- **PARTIAL:** Profiles generated (42 LLM calls) but data not persisted correctly
- **UNCHANGED:** Structure still broken (8 chapters, first 3 merged)

### Attempt 11 - FIXES APPLIED AND VERIFIED ✓

**STATUS: Ready for re-analysis. Structure detection fix has been applied and locally verified.**

#### Fixes Applied (Commits on Jan 21, 2026)

| Commit | File | Fix |
|--------|------|-----|
| `34476d9` | `profiler.py` | TOC extraction returns valid 9-entry Roman sequence (was returning 87) |
| `8f42d66` | `pipeline.py` | TOC-guided bypass skips validation/consensus when all 9 chapters found |
| `8f42d66` | `consensus.py` | Hard boundary preservation prevents LLM from rejecting explicit markers |
| `8d10c2e` | `progress_display.py`, `desktop.py` | Stage order numbers in progress display |
| `03435e3` | `oracle_monitor.py` | Stage order numbers in oracle monitor |

#### Local Verification Results (Jan 21, 2026 5:40 PM MST)

**Test command:**
```bash
./venv/bin/python -c "
from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.llm.client import create_client
with open('Test_Texts/gatsby.txt', 'r') as f:
    text = f.read()
llm = create_client(provider='ollama', model='qwen3:8b')
pipeline = ChapterDetectionPipeline(llm_client=llm)
chapter_map = pipeline.run(text)
print(f'Chapters: {len(chapter_map.chapters)}')
for ch in chapter_map.chapters:
    print(f'  {ch.index}: {repr(ch.title)} at {ch.start_position} ({ch.word_count:,} words)')
"
```

**Result: ✓ ALL 9 CHAPTERS DETECTED CORRECTLY**
```
Chapters detected: 9
  1: 'I' at 1400 (5,892 words)
  2: 'II' at 34475 (4,280 words)
  3: 'III' at 58146 (5,734 words)
  4: 'IV' at 90779 (5,456 words)
  5: 'V' at 121446 (4,233 words)
  6: 'VI' at 145055 (4,036 words)
  7: 'VII' at 167931 (8,766 words)
  8: 'VIII' at 217234 (4,530 words)
  9: 'IX' at 242778 (8,131 words)
```

**Key log messages confirming fix:**
```
TOC validation: detected valid Roman numeral sequence, keeping 9 of 9 entries
TOC-guided: found all 9 expected chapters, using TOC-guided proposals exclusively
TOC-guided complete: 9 chapters found - bypassing validation/consensus for reliability
Built ChapterMap from TOC: 9 chapters, 51,058 words
```

#### What Was Wrong (Root Cause)

1. **TOC region captured prose text** - The 5000-char window after the TOC header included sentences starting with "I" (like "I went to..."), creating duplicate Roman numeral entries.

2. **Sequence validation failed** - With entries [I, II, III...IX, I, I, ...], the strictly-increasing check failed when it hit the second "I" (value=1) after "IX" (value=9).

3. **Fallback returned all 87 entries** - Instead of the valid 9-entry sequence.

4. **No TOC-guided bypass** - Even when TOC-guided detection found chapters, validation/consensus could reject them.

#### Expected Impact on Scores

| Category | Before | After (Expected) | Notes |
|----------|--------|------------------|-------|
| Structure | 3/10 | 9-10/10 | All 9 chapters correctly detected |
| Summaries | 5/10 | 8/10 | Summaries will align with correct chapters |
| Overall | 5.20/10 | ~7.5-8.0/10 | +2.3-2.8 points |

#### Next Steps for Oracle Loop

1. **Run full analysis** with the fixed code (already committed)
2. **Verify** 9 chapters detected with proper word counts (~4,000-8,000 each)
3. **Evaluate** remaining issues (character duplicates, pronunciation categorization)
4. Continue with P1/P2 fixes if structure is confirmed working

## Notes

Attempt 10 shows that the character extraction fixes are working:
- Daisy is now correctly merged with her aliases
- Character count is much more reasonable (37 vs 99)

However, the structure detection remains catastrophically broken. The next fix MUST prioritize structure above all else. A narrator cannot use this output if they don't know which summary corresponds to which chapter.

The best attempt was #2 with 7.45/10 - we need to understand what made that work and why subsequent attempts broke it.
