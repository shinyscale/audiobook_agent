# PRD: Scene Break Detection and Summary Enhancement

**Version:** 1.0
**Status:** Draft
**Priority:** High
**Target:** Fix false chapter detection from scene breaks + enhance summaries with scene structure

## Executive Summary

The chapter detection pipeline is incorrectly treating scene break markers (lines of dashes "--------") as chapter boundaries. This causes a 9-chapter book (The Great Gatsby) to be detected as having 27 chapters.

**Root Cause:** The LLM Marker Proposer returns scene break lines as chapter markers despite explicit prompt instructions not to. The consensus builder accepts these proposals because they meet the confidence threshold.

**Proposal:**
1. Add scene break detection and filtering to reject these false chapter markers
2. Use detected scene breaks to enhance chapter summaries with natural paragraph structure

---

## Problem Statement

### Analysis of gatsby_010 Output

| Expected | Actual | Issue |
|----------|--------|-------|
| 9 chapters (I-IX) | 27 chapters | Scene breaks counted as chapters |
| Roman numeral titles | 18 "None" titled chapters | Scene breaks have no title |
| Proper chapter structure | Fragmented chapters | Chapter I split into multiple parts |

### Source File Structure

The gatsby.txt file contains:
- **Lines 35-43:** Table of contents (I-IX listed together - informational, not chapter markers)
- **Line 59, 776, 1323, etc.:** Centered Roman numerals (actual chapter markers)
- **25 scene break lines:** `------------------------------------------------------------------------` (scene transitions WITHIN chapters)

The 9 actual chapters are at:
| Chapter | Line |
|---------|------|
| I | 59 |
| II | 776 |
| III | 1323 |
| IV | 2053 |
| V | 2758 |
| VI | 3331 |
| VII | 3868 |
| VIII | 5209 |
| IX | 5760 |

### Current Detection Failures

1. **LLM Marker Proposer** ignores its own instructions to skip scene breaks
2. **No explicit scene break filtering** exists in the consensus pipeline
3. **Chapter summaries** don't leverage scene breaks for structure

---

## Proposed Solution

### Part 1: Scene Break Detection and Filtering

Add a scene break detection utility and use it to filter false positives from the consensus pipeline.

### Part 2: Scene Break-Aware Summaries

Modify the chapter summarizer to use scene breaks as natural chunk boundaries, resulting in better-structured summaries.

---

## Features and User Stories

### Feature 1: Scene Break Detection Utility

**Priority:** CRITICAL
**Rationale:** Foundation for both filtering and summary enhancement.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Scene breaks are detected from common patterns (dashes, asterisks, equals)",
  "steps": [
    "Process text containing scene break lines",
    "Verify scene break pattern matches ----, ***, ===, and similar",
    "Confirm positions are correctly identified",
    "Test with spaced asterisks (e.g., * * *)",
    "Verify no false positives on other content"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Scene break utility provides position lookup for filtering",
  "steps": [
    "Call find_scene_breaks() on text with scene breaks",
    "Verify returns list of (start, end) positions",
    "Call is_near_scene_break() with various positions",
    "Verify correctly identifies positions near scene breaks",
    "Confirm threshold parameter works correctly"
  ],
  "passes": true
}
```

---

### Feature 2: Chapter Detection Filtering

**Priority:** CRITICAL
**Rationale:** Prevents scene breaks from being detected as chapters.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Chapter detection filters out proposals near scene breaks",
  "steps": [
    "Run chapter detection on a book with scene breaks",
    "Verify proposals near scene break lines are filtered",
    "Check that actual chapter markers are preserved",
    "Confirm filtered count is logged for debugging",
    "Test with various scene break patterns (dashes, asterisks)"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "The Great Gatsby detects exactly 9 chapters",
  "steps": [
    "Run analysis on gatsby.txt",
    "Verify exactly 9 chapters are detected",
    "Check chapters have Roman numeral titles (I-IX)",
    "Confirm no 'None' titled chapters from scene breaks",
    "Verify chapter boundaries match expected positions"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Books without scene breaks are unaffected",
  "steps": [
    "Run analysis on a book without scene break markers",
    "Verify chapter detection works as before",
    "Confirm no regression in detection accuracy",
    "Check that normal paragraph breaks are not affected"
  ],
  "passes": true
}
```

---

### Feature 3: Scene Break-Aware Summarization

**Priority:** HIGH
**Rationale:** Improves summary quality by respecting narrative structure.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Chapter summarizer detects scene breaks within chapters",
  "steps": [
    "Summarize a chapter containing scene breaks",
    "Verify scene breaks are detected within chapter text",
    "Confirm scene break positions are used for chunking",
    "Check that chunks align with scene transitions"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Summaries have natural paragraph breaks at scene transitions",
  "steps": [
    "Generate summary for a chapter with multiple scene breaks",
    "Review the summary text",
    "Verify paragraph breaks align with scene transitions",
    "Confirm summary flows naturally with scene structure",
    "Check that each section of the summary covers one scene"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Long scenes are still chunked appropriately",
  "steps": [
    "Summarize a chapter with very long scenes (>3000 words per scene)",
    "Verify long scenes are further chunked at sentence boundaries",
    "Confirm summary maintains coherence across chunk boundaries",
    "Check that original chunking logic is preserved as fallback"
  ],
  "passes": false
}
```

---

## Architecture

### New Module: Scene Break Detection

```
src/pipeline/chapter_detection/
├── scene_breaks.py    # NEW: Scene break detection utility
├── consensus.py       # MODIFIED: Add scene break filtering
└── ...
```

### Modified Module: Chapter Summary

```
src/pipeline/chapter_summary/
├── summarizer.py      # MODIFIED: Scene break-aware chunking
└── ...
```

### Component Flow

```
Input Text
    │
    ▼
Scene Break Detection (new)
    │   └── find_scene_breaks(text) → [(start, end), ...]
    │
    ├──────────────────────────────┐
    │                              │
    ▼                              ▼
Chapter Detection               Chapter Summary
(filtering)                     (chunking)
    │                              │
    │ Filter proposals             │ Split at scene breaks
    │ near scene breaks            │ before word-count chunking
    │                              │
    ▼                              ▼
Correct chapter count           Structured summaries
(9 for Gatsby)                  (paragraph breaks at scenes)
```

---

## Implementation Plan

### Phase 1: Scene Break Detection Utility
**Files to create:**
- `src/pipeline/chapter_detection/scene_breaks.py`

**Implementation:**

```python
"""Scene break detection utility."""

import re

# Pattern matches lines of repeated punctuation
SCENE_BREAK_PATTERN = re.compile(
    r'^[\s]*[-=*~.]{3,}[\s]*$|'    # ----, ***, ===, ~~~, ...
    r'^\s*[*]\s+[*]\s+[*]\s*$',    # * * * (spaced asterisks)
    re.MULTILINE
)


def find_scene_breaks(text: str) -> list[tuple[int, int]]:
    """Find positions of scene break markers in text."""
    return [(m.start(), m.end()) for m in SCENE_BREAK_PATTERN.finditer(text)]


def is_near_scene_break(
    position: int,
    scene_breaks: list[tuple[int, int]],
    threshold: int = 100
) -> bool:
    """Check if position is near a scene break."""
    for start, end in scene_breaks:
        if abs(position - start) < threshold or abs(position - end) < threshold:
            return True
    return False


def get_scene_break_positions(text: str) -> list[int]:
    """Get start positions of all scene breaks."""
    return [start for start, _ in find_scene_breaks(text)]
```

---

### Phase 2: Chapter Detection Filtering
**Files to modify:**
- `src/pipeline/chapter_detection/consensus.py`
- `src/pipeline/chapter_detection/__init__.py`

**Modification to consensus.py:**

Add import:
```python
from .scene_breaks import find_scene_breaks, is_near_scene_break
```

Add filtering in `build_consensus()` after line 136:
```python
# Filter proposals near scene breaks (false positives from "-----" lines)
scene_breaks = find_scene_breaks(text)
if scene_breaks:
    pre_filter_count = len(valid_proposals)
    valid_proposals = [
        v for v in valid_proposals
        if not is_near_scene_break(v.proposal.position, scene_breaks, threshold=100)
    ]
    filtered_count = pre_filter_count - len(valid_proposals)
    if filtered_count > 0:
        logger.info(f"ConsensusBuilder: filtered {filtered_count} proposals near scene breaks")
```

---

### Phase 3: Scene Break-Aware Summarization
**Files to modify:**
- `src/pipeline/chapter_summary/summarizer.py`

**Modification to summarizer.py:**

Add import:
```python
from ..chapter_detection.scene_breaks import find_scene_breaks
```

Replace `_split_into_chunks()` with scene-break-aware version:
```python
def _split_into_chunks(self, text: str) -> list[str]:
    """Split text into chunks, respecting scene breaks as natural boundaries."""
    scene_breaks = find_scene_breaks(text)

    if scene_breaks:
        return self._split_by_scene_breaks(text, scene_breaks)
    else:
        return self._split_by_word_count(text)


def _split_by_scene_breaks(
    self,
    text: str,
    scene_breaks: list[tuple[int, int]]
) -> list[str]:
    """Split text at scene breaks, then chunk large sections if needed."""
    sections = []
    prev_end = 0

    for start, end in scene_breaks:
        section = text[prev_end:start].strip()
        if section:
            sections.append(section)
        prev_end = end

    # Don't forget the last section
    final = text[prev_end:].strip()
    if final:
        sections.append(final)

    # Chunk any sections that are too long
    chunks = []
    for section in sections:
        word_count = len(section.split())
        if word_count > self.chunk_size * 1.2:
            chunks.extend(self._split_by_word_count(section))
        else:
            chunks.append(section)

    return chunks


def _split_by_word_count(self, text: str) -> list[str]:
    """Original chunking logic: split by word count at sentence boundaries."""
    # [Move existing _split_into_chunks logic here]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # ... rest of original implementation
```

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/pipeline/chapter_detection/scene_breaks.py` | CREATE | Scene break detection utility |
| `src/pipeline/chapter_detection/consensus.py` | MODIFY | Add scene break filtering (line ~136) |
| `src/pipeline/chapter_detection/__init__.py` | MODIFY | Export scene_breaks module |
| `src/pipeline/chapter_summary/summarizer.py` | MODIFY | Scene break-aware chunking |

---

## Verification

### Test 1: Chapter Detection Fix
```bash
# Run analysis on gatsby.txt
audiobook-prep analyze Test_Texts/gatsby.txt --output output/gatsby_test/

# Verify chapter count
python3 -c "
import json
with open('output/gatsby_test/analysis.json') as f:
    data = json.load(f)
    chapters = data.get('structure', [])
    print(f'Chapters detected: {len(chapters)}')
    for ch in chapters[:10]:
        print(f'  {ch.get(\"title\", \"None\")}')
"
# Expected: 9 chapters with Roman numeral titles
```

### Test 2: Scene Break Detection
```python
from src.pipeline.chapter_detection.scene_breaks import find_scene_breaks

text = """
Some text here.

------------------------------------------------------------------------

More text after the break.
"""

breaks = find_scene_breaks(text)
assert len(breaks) == 1
print(f"Found {len(breaks)} scene break(s)")
```

### Test 3: Summary Structure
- After fix, review chapter summaries for gatsby
- Verify summaries have paragraph structure that reflects scene transitions
- Confirm summary quality is improved or maintained

### Test 4: Edge Cases
- Book with no scene breaks → should work normally
- Book with different scene break formats (*, ===, ~~~) → should detect all
- Very long scenes (>3000 words) → should still be chunked appropriately

---

## Success Criteria

1. **Chapter Detection Accuracy:** Gatsby detects exactly 9 chapters (not 27)
2. **No False Positives:** Scene breaks correctly filtered, not detected as chapters
3. **Summary Quality:** Summaries maintain or improve quality with scene-aware structure
4. **Regression Prevention:** Books without scene breaks work identically to before
5. **Performance:** No significant performance impact from scene break detection

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scene break pattern misses some formats | Medium | Start with common patterns, expand based on testing |
| Filtering removes legitimate chapter markers | High | Use conservative threshold (100 chars), log filtered proposals |
| Summary quality degrades | Medium | Keep original chunking as fallback for non-scene-break text |

---

## References

- Current chapter detection: `src/pipeline/chapter_detection/`
- Current summarizer: `src/pipeline/chapter_summary/summarizer.py`
- LLM marker proposer: `src/pipeline/chapter_detection/proposers/llm.py`
- Consensus builder: `src/pipeline/chapter_detection/consensus.py`
