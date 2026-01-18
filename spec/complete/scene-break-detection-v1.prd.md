# PRD: Scene Break Detection and One-Shot Structure/Character Accuracy

**Version:** 1.1
**Status:** Draft (updated based on `output/gatsby_011` failure analysis)
**Priority:** High
**Target:** Improve one-shot accuracy for arbitrary books by (a) preventing false chapter boundaries (scene breaks, boilerplate), (b) correctly anchoring explicit chapter markers and titles, and (c) improving character identity resolution.

## Executive Summary

We need this tool to be accurate on the **first run** across **any book**, not just Gatsby. Recent output (`output/gatsby_011`) shows that false chapter boundaries are only one of several root causes of low one-shot accuracy:

- **Over-splitting**: Gatsby was detected as **16 chapters** instead of 9.
- **Missed explicit markers / weak title propagation**: many real Roman-numeral chapter headings exist in the source text but were not preserved as chapter titles in output.
- **Back matter leakage**: Project Gutenberg license text was included in the final “chapter” summary and polluted character extraction (e.g., “Professor Michael S. Hart”, “the Foundation”).
- **Character identity resolution errors**: missing last names (e.g., “Tom”, “Daisy”), punctuation aliases (e.g., “Daisy!”), failure to merge titled forms (e.g., “Mrs. Wilson” ↔ Myrtle), and family-name collisions (e.g., James Gatz / Mr. Gatz / Jay Gatsby).

**Proposal (book-agnostic):**
1. **Scene break detection + filtering**: reject scene-break markers as chapter boundaries.
2. **Explicit marker anchoring**: deterministic detection of explicit markers (centered Roman numerals, “Chapter N”, etc.) must dominate boundary selection and title assignment.
3. **Back matter detection/exclusion**: detect common boilerplate/back matter blocks and exclude them from chapter detection, summaries, and character extraction.
4. **Character identity resolution guardrails**: normalize names, fix punctuation/possessives, prefer full names as canonicals, and prevent unsafe merges (especially last-name-only and family-member collisions).

---

## Non-Goals and Constraints (Avoid Book-Specific Hacks)

This PRD must improve accuracy **globally** across diverse books and formats. We explicitly avoid fixes that only “make Gatsby work.”

**Non-goals:**
- Do not hard-code book-specific chapter counts (e.g., “Gatsby must be 9”) except as a regression test fixture.
- Do not hard-code specific character lists or identity mappings (e.g., “James Gatz == Jay Gatsby”) except as a regression test fixture.
- Do not hard-code a single source’s brand name as the only back matter detector trigger.

**Constraints:**
- One-shot: the default workflow should succeed without interactive user intervention.
- Conservative merges: for characters, false negatives (missed aliases) are preferable to false positives (wrong merges).
- Deterministic anchors: when explicit chapter markers exist, deterministic detection should dominate over narrative-only heuristics.

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

### Additional Failures Observed in `output/gatsby_011` (One-Shot Quality)

These are not Gatsby-specific heuristics; they reflect common patterns across many public-domain and OCR’d books.

1. **Over-splitting into many untitled chapters**
   - Output contained 16 chapters and many `title: null` chapters.
   - This indicates that explicit marker evidence is not being treated as authoritative enough and/or titles are not being propagated reliably.

2. **Back matter included in narrative processing**
   - The Project Gutenberg license appeared inside a chapter summary and produced spurious “characters”.
   - Back matter leakage degrades *every downstream stage* (summaries, characters, pronunciation).

3. **Character identity resolution errors**
   - Canonical names collapsed to first names (e.g., “Tom”, “Daisy”) even when full names exist.
   - Punctuation variants became aliases (e.g., “Daisy!”).
   - Titled and untitled variants did not merge correctly (e.g., “Mrs. Wilson” vs “Myrtle”).
   - Family collisions and identity/alias cases were mishandled (e.g., James Gatz / Jay Gatsby / Mr. Gatz).

---

## Proposed Solution

### Part 1: Scene Break Detection and Filtering (Chapter Boundary Hygiene)

Add a scene break detection utility and use it to filter false positives from the consensus pipeline.

### Part 2: Explicit Marker Anchoring (Correct Chapters and Titles)

When a book contains explicit chapter markers, chapter detection must treat them as **hard anchors**:

- **Boundary selection**: explicit markers should not be overridden by soft signals (e.g., “this feels like a new scene”).
- **Title assignment**: the chapter title must be the **exact heading text** (normalized only for whitespace), not an inferred “Chapter N”.
- **Roman numerals**: centered/standalone Roman numerals are common in classic literature; they must be recognized robustly.

### Part 3: Back Matter Detection and Exclusion (Prevent Downstream Contamination)

Detect and exclude non-narrative boilerplate blocks so that:

- Chapters do not extend into license/legal/metadata text.
- Summaries do not reference boilerplate.
- Character extraction does not propose “characters” from boilerplate.

This should be implemented as **pattern-based + scoring**, not hard-coded to Gatsby. Project Gutenberg is an example of a globally common pattern, but the mechanism must generalize to other sources.

### Part 4: Character Identity Resolution Guardrails (Canonical Names + Safe Aliases)

Improve character merging and naming in a book-agnostic way:

- **Normalize names**: remove surrounding quotes, trailing punctuation, unicode apostrophe variants, and possessive suffixes.
- **Prefer full names as canonical**: if `First Last` exists, do not keep `First` as canonical.
- **Avoid unsafe aliases**: bare last-name aliases are risky in books with families/spouses.
- **Family collision safety**: do not merge `FirstA Last` with `FirstB Last` without explicit evidence they are the same person.
- **Identity change support**: allow merges like “birth name / real name / formerly known as” *only* when explicitly supported by local context in the text.

### Part 5: Scene Break-Aware Summaries (Quality Enhancement)

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
  "passes": true
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

### Feature 3: Explicit Marker Anchoring and Title Propagation

**Priority:** CRITICAL  
**Rationale:** If explicit markers exist, they must dominate to avoid over-splitting and missing titles.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Explicit chapter markers (e.g., centered Roman numerals, 'CHAPTER N') are treated as hard boundaries when present",
  "steps": [
    "Run chapter detection on a book with explicit headings",
    "Verify boundaries align with explicit headings, not scene breaks or narrative-only guesses",
    "Confirm explicit markers are preserved even when adjacent text does not strongly indicate an ending/beginning",
    "Verify that chapters are not over-split into multiple untitled chapters"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Chapter titles are derived from the actual heading text (normalized whitespace only), not inferred labels",
  "steps": [
    "Run analysis on a book with Roman numeral headings",
    "Verify chapter titles in output match the heading (e.g., 'IV', 'IX')",
    "Confirm we do not emit punctuation variants or inferred numbering when heading is present"
  ],
  "passes": true
}
```

---

### Feature 4: Back Matter Detection and Exclusion

**Priority:** CRITICAL  
**Rationale:** Boilerplate contamination breaks summaries and character extraction in one-shot mode.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Back matter (license/legal/metadata blocks) is detected and excluded from narrative processing",
  "steps": [
    "Run analysis on a public-domain book that contains license/legal boilerplate",
    "Verify the final narrative chapter ends before boilerplate begins",
    "Confirm boilerplate text is not included in any chapter summary",
    "Confirm character extraction does not produce characters sourced only from boilerplate"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Back matter detection is book-agnostic and does not rely on a single source brand name",
  "steps": [
    "Run analysis on texts with different boilerplate styles (e.g., legal disclaimers, scanning metadata, edition notes)",
    "Verify the system identifies non-narrative blocks via pattern + scoring rather than a single hard-coded phrase",
    "Confirm false positives are rare (does not remove actual narrative)"
  ],
  "passes": true
}
```

---

### Feature 5: Character Identity Resolution Guardrails

**Priority:** CRITICAL  
**Rationale:** Narrators need consistent character names and voice notes; bad merges are costly in a one-shot workflow.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Character names are normalized to remove punctuation/quotes/possessives without losing the original mention text",
  "steps": [
    "Run character extraction on text containing names in dialogue with punctuation (e.g., 'Daisy!')",
    "Verify canonical names do not include trailing punctuation",
    "Confirm raw mention evidence still preserves the exact surface text from the book"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Canonical names prefer the most specific non-titled form when available (First Last over First; First Last over Mr./Mrs. Last)",
  "steps": [
    "Run character extraction on a book where both full names and first-name-only references exist",
    "Verify the canonical name is the full name when present",
    "Confirm the first-name-only form is represented as an alias (not the canonical)"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Unsafe last-name-only aliasing is avoided to prevent family-member collisions",
  "steps": [
    "Run character extraction on a book with multiple characters sharing a last name (family/spouses)",
    "Verify the pipeline does not automatically merge solely on last name",
    "Confirm titled forms (Mr./Mrs.) do not collapse into the wrong person"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Identity-change aliases (birth name / real name / formerly known as) are merged only when explicitly supported by local context",
  "steps": [
    "Run character extraction on a text that explicitly states a character's real/birth name",
    "Verify the two names merge into a single character only when the text provides explicit evidence",
    "Confirm we do not merge different family members with the same surname"
  ],
  "passes": true
}
```

---

### Feature 6: Scene Break-Aware Summarization

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
  "passes": true
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
  "passes": true
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
  "passes": true
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

### Additional Modules (New)

```
src/pipeline/text_hygiene/
├── back_matter.py      # NEW: detect boilerplate/back matter spans (license/legal/metadata)
└── normalization.py    # NEW: name/text normalization helpers (punctuation, possessives, unicode)
```

### Modified Modules (Additional)

```
src/pipeline/chapter_detection/
├── proposers/regex.py         # MODIFIED: strengthen explicit marker anchoring/title capture
├── validator.py               # MODIFIED: scoring to prioritize explicit marker evidence
└── consensus.py               # MODIFIED: enforce explicit-marker dominance; exclude back matter region(s)
```

```
src/pipeline/character_extraction/
├── proposers/ner.py           # MODIFIED: normalize extracted names; avoid punctuation variants
├── proposers/llm.py           # MODIFIED: normalize name matching; strip punctuation/possessives
├── validator.py               # MODIFIED: alias evidence checks use mention contexts (not proposal fields)
└── consensus.py               # MODIFIED: guardrails for surname-only merges; canonicalization prefers full names
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

### Phase 3: Explicit Marker Anchoring

**Goal:** When explicit headings exist, output boundaries/titles must align to them.

**Work items:**
- Adjust regex proposer to emit strong evidence for centered Roman numerals / “CHAPTER …” headings.
- Adjust validator/consensus scoring so explicit markers dominate over narrative-only “beginning/ending feel.”
- Ensure title propagation uses the heading text (whitespace-normalized) and avoids punctuation variants.

### Phase 4: Back Matter Detection and Exclusion

**Goal:** Identify boilerplate spans and exclude them from chapter detection, summaries, and character extraction.

**Work items:**
- Add a back matter detector that returns (start, end) spans with confidence and sample evidence.
- Trim/ignore these spans in downstream stages (structure, summaries, characters).
- Log what was excluded to support debugging without requiring manual intervention.

### Phase 5: Character Identity Resolution Guardrails

**Goal:** Stable canonical names and safe alias merges across arbitrary books.

**Work items:**
- Centralize name normalization (punctuation, possessives, unicode apostrophes) and use it consistently across proposers/validator/consensus.
- Fix identity-change evidence checks to read from **mention contexts** (not nonexistent proposal fields).
- Strengthen surname-only merge guardrails (especially in the presence of family members / spouses).
- Canonicalization: prefer full non-titled names when available; prevent first-name canonicals when full name exists.

### Phase 6: Scene Break-Aware Summarization
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

### Test 5: Back Matter Exclusion (Generic Boilerplate)
- Public-domain text with license/disclaimer at end → narrative ends before boilerplate
- Text with “About this edition” / OCR metadata blocks → excluded from chapters/summaries/characters

### Test 6: Character Identity Resolution (Global)
- Punctuation variants in dialogue (`Name!`, `Name?`) → canonical normalized, mentions preserved
- Honorific variants (`Mr. X`, `Mrs. X`, `Dr. X`) → merged with full name only when safe
- Family collisions (multiple `LastName`) → do not merge solely on last name
- Identity-change text (“real name”, “born as”, “formerly known as”) → merge only with explicit evidence

### Test 7: Synthetic Fixture Suite (Book-Agnostic, Deterministic)

Add small fixture texts to `tests/` (or an equivalent fixtures folder) to validate core behaviors without relying on any single real book:

- **Fixture: Explicit Roman Markers**
  - Text containing centered Roman numerals (`I`, `II`, `III`) as headings.
  - Expected: exactly 3 chapters, titles `I`, `II`, `III`.

- **Fixture: Scene Breaks Within Chapters**
  - Text with multiple `----` / `***` / `* * *` lines between paragraphs but no chapter headings.
  - Expected: no additional chapters created; scene breaks are available to summarization for chunking.

- **Fixture: Boilerplate/Back Matter**
  - Narrative followed by a “license/disclaimer” style block (multiple numbered clauses, repeated legal phrases, URLs).
  - Expected: boilerplate excluded from chapters/summaries/characters; no “characters” derived solely from boilerplate.

- **Fixture: Honorific Collision (Spouses/Family)**
  - Contains `Mr. Wilson`, `Mrs. Wilson`, and `George Wilson` in overlapping chapters.
  - Expected: no unsafe merge based on last name alone; titled forms do not collapse into the wrong person.

- **Fixture: Identity Change Evidence**
  - Contains explicit “real name / born as / formerly known as” phrasing linking two names.
  - Expected: merge occurs only when explicit evidence is present in local mention contexts.

- **Fixture: Punctuation Variants**
  - Contains dialogue with `Daisy!`, `“Daisy?”`, `Daisy’s`.
  - Expected: canonical name is `Daisy`; punctuation/possessive forms do not become canonical/alias artifacts.

---

## Success Criteria

1. **Explicit Marker Fidelity (Primary):** For texts with explicit headings, boundaries and titles match those headings (high precision/recall on fixtures).
2. **No False Positives:** Scene breaks and boilerplate are not promoted to chapter boundaries.
3. **Back Matter Safety:** Boilerplate is excluded from narrative chapters/summaries/characters (0 “characters” sourced only from boilerplate in fixtures).
4. **Character Fidelity:** Canonical names are normalized and specific when possible; unsafe merges (family collisions, last-name-only) are avoided.
5. **Regression Prevention:** Books without scene breaks or without explicit markers are unaffected (no accuracy regressions on existing test corpus).
6. **Gatsby Regression:** Gatsby detects exactly 9 narrative chapters titled `I`–`IX` and does not include Project Gutenberg license as narrative content.
7. **Performance:** No significant performance impact from added detection/normalization steps.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scene break pattern misses some formats | Medium | Start with common patterns, expand based on testing |
| Filtering removes legitimate chapter markers | High | Use conservative threshold (100 chars), log filtered proposals |
| Summary quality degrades | Medium | Keep original chunking as fallback for non-scene-break text |
| Back matter detection removes real narrative | High | Use scoring + conservative defaults; require strong boilerplate signals; log boundaries and samples |
| Character alias merges incorrectly combine family members | High | Prefer false negatives; add explicit guardrails for surname-only merges and family collisions; require contextual evidence for identity-change merges |

---

## References

- Current chapter detection: `src/pipeline/chapter_detection/`
- Current summarizer: `src/pipeline/chapter_summary/summarizer.py`
- LLM marker proposer: `src/pipeline/chapter_detection/proposers/llm.py`
- Consensus builder: `src/pipeline/chapter_detection/consensus.py`
