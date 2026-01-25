# PRD: Chapter V Detection Bug - The Great Gatsby

## Status: Fixed (2026-01-23)

**Created:** 2026-01-22
**Priority:** High
**Affected Text:** The Great Gatsby (and likely other classic literature with Roman numeral chapters)

---

## Problem Statement

Chapter V is not being detected in The Great Gatsby analysis. The output shows 8 chapters instead of 9, with Chapter V's content merged into Chapter IV.

**Expected:** 9 chapters (I, II, III, IV, V, VI, VII, VIII, IX)
**Historical Actual (pre-fix):** 8 chapters (null/I, II, III, IV, VI, VII, VIII, IX) - Chapter V missing (merged into IV)
**Current Actual (post-fix):** 9 chapters (I, II, III, IV, V, VI, VII, VIII, IX)

---

## Root Cause Analysis

### Root Cause #1: LLM Proposer Position Matching Bug (FIXED)

**Location:** `src/pipeline/chapter_detection/proposers/llm.py` - `_find_text_position()`

**Problem:** When the LLM correctly identified "V" as a chapter marker, the function did `chunk.find("V")` which matched the first "V" character in the chunk - the "V" in "**V**entura" at position 116737, NOT the actual Chapter V at position 121446.

**Evidence:**
```
Cluster 4: pos=116737, title='V', score=0.86, strategies=['llm_marker']
Cluster 5: pos=121446, title='Chapter V', score=0.79, strategies=['regex']
```

The 4709 character gap exceeded the 200-char clustering threshold, so they formed separate clusters.

**Fix Applied:** Short markers (roman numerals ≤4 chars) now require standalone matches using regex patterns that enforce whitespace/line boundaries:
```python
pattern = rf'^\s*{escaped}\s*$'  # Centered/standalone markers
```

### Root Cause #2: LLM Sequence Validator Removing TOC-matched Chapters (FIXED)

**Location:** `src/pipeline/chapter_detection/consensus.py` - `_validate_chapter_sequence()`

**Problem:** The LLM sequence validator saw two entries for "V" (one at wrong position from bug #1, one correct from regex) and decided they were "duplicates", removing both - even though the TOC clearly listed I through IX.

**Fix Applied:** Added TOC protection - chapters matching TOC entries are never removed by the LLM sequence validator:
```python
toc_protected_titles = set()
if profile and profile.table_of_contents:
    for entry in profile.table_of_contents.entries:
        toc_protected_titles.add(entry.title.strip().upper())
        toc_protected_titles.add(f"CHAPTER {entry.title}")
```

### Root Cause #3: TXT Ingestion Whitespace Normalization Destroyed Centered Roman Numeral Headers (FIXED)

**Location:** `src/ingestion/base.py` - `DocumentIngester._normalize_text()`

**Problem:** The ingestion “whitespace normalization” stripped leading indentation on *every line* (`line.strip()`), which **destroyed centered chapter headers** like:

- `"                                  I"`
- `"                                  V"`

This mattered because the chapter detector’s safest regex for classic books is the centered roman numeral hard-boundary:

- `^\s{10,}([IVXLC]+)\s*$`

When indentation was removed, single-letter chapters like **I** and **V** could no longer be reliably detected:

- The “relaxed” roman regex intentionally requires **2+ chars** (`[IVXLC]{2,7}`) to avoid matching the pronoun “I” in dialogue.
- Result: **II/III/IV/VI…** might still show up, but **I and V** drop out, which in turn caused **V to be merged into IV** in the final structure output.

**Runtime evidence (NDJSON debug logs):**
- Before fix: `centered_roman_count` went from **9 → 0** after `_normalize_text()`.
- After fix: `centered_roman_count` remained **9 → 9**, and Chapter V was present in `RegexProposer` and `StructureAgent`.

**Fix Applied:** Preserve leading indentation while still normalizing internal and trailing whitespace.
- New behavior: keep the exact leading whitespace prefix, normalize the remainder, and keep blank lines blank.

---

### Root Cause #4: TOC End Fallback Swallowed the Real Chapter I Marker (FIXED)

**Location:** `src/pipeline/chapter_detection/profiler.py` - `DocumentProfiler._extract_toc()`

**Problem:** Gatsby’s “Table of Contents” section is formatted with only **two** blank lines after the list (not three). The profiler tried to find TOC end via triple-blank-line detection:

- `\n\s*\n\s*\n`

When that wasn’t found, it fell back to treating the next **5000 chars** as TOC. That overly-large TOC region accidentally included the real centered Chapter I marker in the body (≈ position **526** in refined text). This made:

- `toc_end_position` far too large (e.g. ≈ **5129**)
- `front_matter_end` start searching after TOC end
- Chapter I marker classified as “front matter” and skipped by the regex proposer
- Downstream result: **first chapter title became `null`** even when later chapters were correct.

**Runtime evidence (NDJSON debug logs):**
- Pre-fix: `toc_end_mode="fallback_5k"` and `centered_I_within_toc_region=true`.
- Post-fix: `toc_end_mode="fallback_5k_trimmed_by_content_marker"` and `centered_I_within_toc_region=false`.
- Post-fix: `RegexProposer` emitted `"Chapter I"` and `StructureAgent` titles were `["I","II",...,"IX"]`.

**Fix Applied:** If TOC end falls back to “5k chars”, trim TOC end to the **earliest strong content-start marker** (e.g., centered roman numeral header) inside that region. This prevents the TOC region from swallowing real chapter markers.

---

## Test Results

### Isolated Structure Detection Test (PASSED)
When running just the chapter detection pipeline directly, all 9 chapters are detected:
```
=== FINAL CHAPTERS (9) ===
  1: title='I', pos=1400, words=5892
  2: title='II', pos=34475, words=4280
  3: title='III', pos=58146, words=5734
  4: title='IV', pos=90779, words=5456
  5: title='V', pos=121446, words=4233    ← Chapter V detected!
  6: title='VI', pos=145055, words=4036
  7: title='VII', pos=167931, words=8766
  8: title='Part VIII', pos=217234, words=4530
  9: title='IX', pos=242778, words=8131
```

### Full CLI Analysis (FAILED)
When running the full analysis via CLI, Chapter V is still missing:
```json
{"title": null, "word_count": 5037}
{"title": "II", "word_count": 4280}
{"title": "III", "word_count": 5734}
{"title": "IV", "word_count": 9689}   ← Contains both IV and V content
{"title": "VI", "word_count": 4036}
...
```

### Full CLI Analysis (PASSED after Root Cause #3 + #4 fixes)
After fixing ingestion indentation preservation and TOC end trimming:
- Chapter count: **9**
- Titles: **I, II, III, IV, V, VI, VII, VIII, IX**
- Chapter V is no longer merged into Chapter IV
- Chapter I is no longer `null`

---

## Resolution Summary (for oracle-loop logging/docs)

**What broke:**
- Ingestion normalization removed leading indentation, breaking centered roman numeral chapter headers (dropping I + V).
- TOC end detection fallback (“take next 5k chars”) swallowed the real Chapter I marker; front matter end then skipped it, producing a `null` first title.

**What we changed:**
- `src/ingestion/base.py`: Preserve leading indentation during whitespace normalization (still normalizes internal/trailing whitespace).
- `src/pipeline/chapter_detection/profiler.py`: When TOC end falls back to 5k chars, trim TOC end to the earliest strong content marker to avoid swallowing body chapter markers.

**What to log in oracle-loop going forward (high-signal fields):**
- **Ingestion normalization**:
  - `centered_roman_count` pre vs post normalization
  - whether `centered_has_I/centered_has_V` flip unexpectedly
- **Profiler TOC bounds**:
  - `toc_start/toc_end/toc_end_mode`
  - whether `centered_I_within_toc_region` is true (should be false)
  - `front_matter_end` and whether Chapter I falls before/after it
- **Regex proposer output**:
  - whether `has_I/has_V` are true
  - final chapter titles list (first 10) from `StructureAgent`

---

## Source Text Details

**File:** `Test_Texts/gatsby.txt`

**Chapter V marker location:**
- Line 2756, position 121446
- Format: `"                                  V"` (centered with ~34 leading spaces)

**Regex pattern that should match:**
```python
r'^\s{10,}([IVXLC]+)\s*$'  # Centered roman numerals with 10+ leading spaces
```

---

## Commits Related to This Bug

1. `a69e1b4` - Fix: Chapter V detection - two root causes identified and fixed
2. `5593dfd` - Fix: Remove early return from _enforce_toc_count (oracle loop attempt)
3. `fe140cc` - Fix: Chapter V rescue + pronunciation whitelist expansion (oracle loop attempt)
4. `b0bcd38` - Fix: Chapter V TOC enforcement (oracle loop attempt)

---

## Debug Commands

```bash
# Verify Chapter V exists in source
grep -n "^[[:space:]]*V[[:space:]]*$" Test_Texts/gatsby.txt

# Check detected chapter structure in output
jq '.structure[] | {title, word_count}' output/gatsby/analysis.json

# Run isolated structure detection test
python3 -c "
from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.llm import LLMClient, LLMConfig

with open('Test_Texts/gatsby.txt', 'r') as f:
    text = f.read()

config = LLMConfig.ollama(model='qwen3:4b-instruct')
llm = LLMClient(config)
pipeline = ChapterDetectionPipeline(llm_client=llm)
chapter_map = pipeline.run(text)

for ch in chapter_map.chapters:
    print(f'{ch.index}: {ch.title}, {ch.word_count} words')
"

# Run with debug logging
LOG_LEVEL=DEBUG python -m src.cli analyze Test_Texts/gatsby.txt \
  --output /tmp/debug.json \
  --structure-model "qwen3:4b-instruct" 2>&1 | tee /tmp/debug.log
```

---

## Acceptance Criteria

1. All 9 chapters (I-IX) detected in The Great Gatsby
2. Chapter V at correct position (121446) with correct word count (~4233)
3. Chapter IV word count ~5456 (not ~9689)
4. Chapter I has title "I" (not null)
5. Fix works for both isolated pipeline test AND full CLI analysis

**Status:** Met for Gatsby after Root Cause #3 + #4 fixes (and earlier #1/#2 fixes where applicable).

---

## Related Issues

- Chapter I null title (separate but related issue)
- Multiple owl-eyed man entries (deduplication issue)
- Meyer Wolfshiem/Wolfsheim spelling variants not merged
