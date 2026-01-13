# PRD: Analysis Quality Improvements v1

**Version:** 1.0
**Status:** Draft
**Priority:** High
**Target:** Fix chapter detection (TOC parsing), character merging (birth names/aliases), and character classification

## Executive Summary

Analysis of gatsby_011 output revealed three systemic issues causing incorrect results:

1. **Chapter Detection**: 16 chapters detected instead of 9. TOC parser reports "expects 91" instead of 9, indicating a parsing bug.
2. **Character Merging**: 41 characters with obvious duplicates not merged (Jay Gatsby/James Gatz, Myrtle/Mrs. Wilson, Owl Eyes/Owl-eyes).
3. **Character Classification**: All characters have `character_type = UNCERTAIN` because proposers don't set this field.

**Proposal:**
1. Fix TOC parsing to correctly count entries and validate against patterns
2. Add aggressive heuristic merging with LLM-driven validation for birth names and aliases
3. Add character type inference to NER proposer with LLM fallback

---

## Problem Statement

### Analysis of gatsby_011 Output

| Expected | Actual | Issue |
|----------|--------|-------|
| 9 chapters (I-IX) | 16 chapters | TOC parsing bug reports "expects 91" |
| ~15 characters | 41 characters | Duplicates not merged |
| Main/Secondary types | All UNCERTAIN | Proposers don't set character_type |

### Character Merging Failures

| Should Be Merged | Currently Separate |
|------------------|-------------------|
| Jay Gatsby + James Gatz + Jimmy | 3 entries |
| Tom + Mr. Thomas Buchanan | 2 entries |
| Mrs. Wilson + Myrtle | 2 entries |
| Nick + Mr. Carraway | 2 entries |
| Owl Eyes + Owl-eyes | 2 entries |

### Root Causes Identified

1. **TOC Parsing**: `_parse_toc_entries()` accepts too many lines as entries, not filtering metadata lines
2. **Character Merging**: `_validate_merge()` rejects birth name patterns (no shared words = rejected)
3. **Character Classification**: NER proposer never sets `character_type`, consensus voting receives empty input

---

## Proposed Solution

### Part 1: TOC Parsing Fix
Add entry validation to filter by pattern (Roman numerals, "Chapter N") and reject implausible counts (>30).

### Part 2: Aggressive Character Merging
Add birth name pattern detection (checking contexts for "real name", "born as") and aggressive alias matching (hyphenation variants). LLM drives final validation.

### Part 3: Character Classification
Add type inference to NER proposer based on dialogue/action signals, plus LLM fallback.

---

## Features and User Stories

### Feature 1: TOC Entry Validation

**Priority:** CRITICAL
**Rationale:** Blocking issue - incorrect chapter count affects all downstream processing.

```json
{
  "category": "functional",
  "description": "TOC parser validates entry count and filters by pattern",
  "steps": [
    "Process Gatsby TOC with Roman numerals I-IX",
    "Verify exactly 9 entries are extracted",
    "Confirm metadata lines (copyright, author) are filtered",
    "Test books with 'Chapter N' pattern",
    "Verify >30 entry counts trigger warning and filtering"
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
    "Verify exactly 9 chapters detected",
    "Check chapters have Roman numeral titles (I-IX)",
    "Confirm TOC log shows 'expects 9' not 'expects 91'"
  ],
  "passes": true
}
```

---

### Feature 2: Birth Name / Alias Merging

**Priority:** CRITICAL
**Rationale:** Core character identification accuracy.

```json
{
  "category": "functional",
  "description": "Birth name patterns are detected and merged",
  "steps": [
    "Process text with 'James Gatz' and 'Jay Gatsby' references",
    "Detect context clues: 'real name', 'born as', 'changed his name'",
    "Verify names with no word overlap but birth name context are merged",
    "Confirm canonical name is selected appropriately"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Hyphenation and spacing variants are merged",
  "steps": [
    "Process text with 'Owl Eyes' and 'Owl-eyes'",
    "Verify variants are automatically merged",
    "Test 'Mr. McKee' vs 'McKee' merging",
    "Confirm no false positives on different names"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Gatsby character merging produces correct results",
  "steps": [
    "Run analysis on gatsby.txt",
    "Verify Jay Gatsby aliases include James Gatz, Jimmy",
    "Verify Myrtle and Mrs. Wilson are merged",
    "Verify Nick and Mr. Carraway are merged",
    "Verify Tom and Daisy Buchanan remain SEPARATE (different people)"
  ],
  "passes": false
}
```

---

### Feature 3: Character Type Classification

**Priority:** HIGH
**Rationale:** Narrator guidance for voice characterization.

```json
{
  "category": "functional",
  "description": "NER proposer infers character type from context",
  "steps": [
    "Extract character with dialogue mentions",
    "Verify character_type is set to STORY (not UNCERTAIN)",
    "Process historical figure reference",
    "Verify character_type is set to HISTORICAL",
    "Check that action verbs in context boost STORY classification"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "LLM fallback classifies uncertain characters",
  "steps": [
    "Process character where NER returned UNCERTAIN",
    "Verify LLM classification is called",
    "Confirm final character_type is non-UNCERTAIN",
    "Check that LLM receives context samples for classification"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Gatsby characters are correctly classified",
  "steps": [
    "Run analysis on gatsby.txt",
    "Verify main characters (Gatsby, Nick, Tom, Daisy) are STORY type",
    "Verify no major characters have UNCERTAIN type",
    "Check that minor mentioned figures are appropriately typed"
  ],
  "passes": false
}
```

---

## Architecture

### Modified Modules

```
src/pipeline/chapter_detection/
├── profiler.py        # MODIFIED: Add TOC entry validation

src/pipeline/character_extraction/
├── consensus.py       # MODIFIED: Birth name detection, aggressive merging
├── proposers/
│   └── ner.py         # MODIFIED: Add character type inference
```

### Component Flow

```
TOC Parsing (Fix)
    │
    ├── _is_metadata_line() → filter copyright, author lines
    ├── _validate_toc_entries() → detect Roman numeral / Chapter N patterns
    │
    ▼
Correct chapter count (9 for Gatsby)

Character Extraction
    │
    ├── NER Proposer (with type inference)
    │   └── _infer_character_type() → STORY/HISTORICAL/REFERENCED
    │
    ▼
Character Merging (Enhanced)
    │
    ├── _check_aggressive_alias_patterns() → hyphenation variants
    ├── _check_birth_name_pattern() → context-based detection
    ├── LLM validation (existing)
    │
    ▼
Character Classification (Fallback)
    │
    ├── Voting on character_type (existing)
    └── _classify_character_type() → LLM fallback when UNCERTAIN
```

---

## Implementation Plan

### Phase 1: TOC Entry Validation

**Files to modify:**
- `src/pipeline/chapter_detection/profiler.py`

**Changes:**

1. Add `_is_metadata_line()` method (~line 255):
```python
def _is_metadata_line(self, line: str) -> bool:
    """Check if a line is metadata rather than a TOC entry."""
    line_lower = line.lower()
    metadata_indicators = [
        'copyright', 'published', 'edition', 'isbn',
        'all rights', 'by', 'author', 'introduction',
        'foreword', 'preface', 'acknowledgments',
    ]
    for indicator in metadata_indicators:
        if indicator in line_lower and len(line) > 50:
            return True
    return False
```

2. Add `_validate_toc_entries()` method:
```python
def _validate_toc_entries(self, entries: list[TOCEntry]) -> list[TOCEntry]:
    """Validate and filter TOC entries for consistency."""
    if not entries:
        return entries

    # Check for Roman numeral sequence
    roman_pattern = re.compile(r'^[IVXLC]+$')
    roman_entries = [e for e in entries if roman_pattern.match(e.title.strip())]

    if len(roman_entries) >= 3 and len(roman_entries) / len(entries) > 0.3:
        logger.info(f"TOC validation: detected Roman numeral pattern, "
                    f"keeping {len(roman_entries)} of {len(entries)} entries")
        return roman_entries

    # Check for "Chapter N" pattern
    chapter_pattern = re.compile(r'^chapter\s+\d+', re.IGNORECASE)
    chapter_entries = [e for e in entries if chapter_pattern.match(e.title.strip())]

    if len(chapter_entries) >= 3 and len(chapter_entries) / len(entries) > 0.3:
        return chapter_entries

    # Warn on unreasonable counts
    if len(entries) > 30:
        logger.warning(f"TOC validation: {len(entries)} entries seems too many")
        level1_entries = [e for e in entries if e.level == 1]
        if len(level1_entries) >= 3:
            return level1_entries

    return entries
```

3. Update `_parse_toc_entries()` to call new validation methods.

---

### Phase 2: Aggressive Alias Patterns

**Files to modify:**
- `src/pipeline/character_extraction/consensus.py`

**Changes:**

1. Add `_check_aggressive_alias_patterns()` method:
```python
def _check_aggressive_alias_patterns(self, name1: str, name2: str) -> tuple[bool, float]:
    """Check for common alias patterns that should be merged aggressively."""
    n1_lower = name1.lower().replace('-', ' ').replace('.', '')
    n2_lower = name2.lower().replace('-', ' ').replace('.', '')

    n1_normalized = ' '.join(n1_lower.split())
    n2_normalized = ' '.join(n2_lower.split())

    # Hyphenation/spacing variants
    if n1_normalized == n2_normalized:
        return True, 0.95

    # "Owl Eyes" vs "Owl-eyes"
    if n1_normalized.replace(' ', '') == n2_normalized.replace(' ', ''):
        return True, 0.90

    return False, 0.0
```

---

### Phase 3: Birth Name Detection

**Files to modify:**
- `src/pipeline/character_extraction/consensus.py`

**Changes:**

1. Enhance `PAIRWISE_ALIAS_PROMPT` to include birth name guidance
2. Add `_check_birth_name_pattern()` method:
```python
def _check_birth_name_pattern(
    self, canonical: str, alias: str, name_groups: dict
) -> tuple[bool, float]:
    """Check if two names represent a birth name / assumed name pattern."""
    # Get all contexts
    all_contexts = []
    for result in name_groups.get(canonical, [])[:10]:
        for mention in result.proposal.mentions[:5]:
            if mention.context:
                all_contexts.append(mention.context.lower())
    for result in name_groups.get(alias, [])[:10]:
        for mention in result.proposal.mentions[:5]:
            if mention.context:
                all_contexts.append(mention.context.lower())

    birth_name_indicators = [
        "born as", "real name", "birth name", "whose real name",
        "formerly known as", "changed his name", "changed her name",
        "once called", "used to be called", "originally named",
    ]

    for context in all_contexts:
        for indicator in birth_name_indicators:
            if indicator in context:
                return True, 0.85

    return False, 0.0
```

3. Update `_validate_merge()` to check birth name patterns before rejecting.

---

### Phase 4: Character Type Inference

**Files to modify:**
- `src/pipeline/character_extraction/proposers/ner.py`
- `src/pipeline/character_extraction/consensus.py`

**Changes to ner.py:**

1. Add `_infer_character_type()` method:
```python
def _infer_character_type(self, name: str, mentions: list) -> CharacterType:
    """Infer character type based on context patterns."""
    story_signals = 0
    for mention in mentions[:10]:
        if mention.in_dialogue:
            story_signals += 2
        context_lower = mention.context.lower() if mention.context else ""
        action_verbs = ['said', 'asked', 'looked', 'walked', 'turned', 'smiled']
        for verb in action_verbs:
            if verb in context_lower:
                story_signals += 1
                break

    if story_signals >= 3:
        return CharacterType.STORY
    if any(m.in_dialogue for m in mentions):
        return CharacterType.STORY
    return CharacterType.UNCERTAIN
```

2. Update `propose()` to call `_infer_character_type()`.

**Changes to consensus.py:**

3. Add `_classify_character_type()` method for LLM fallback.
4. Update character type voting to call LLM fallback when all votes are UNCERTAIN.

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/pipeline/chapter_detection/profiler.py` | MODIFY | TOC entry validation |
| `src/pipeline/character_extraction/consensus.py` | MODIFY | Birth name detection, aggressive merging, LLM classification fallback |
| `src/pipeline/character_extraction/proposers/ner.py` | MODIFY | Character type inference |

---

## Verification

### Test 1: Chapter Detection
```bash
audiobook-prep analyze Test_Texts/gatsby.txt --output /tmp/gatsby_test/
```
- Verify exactly 9 chapters detected
- Check logs show "TOC specifies 9 chapters" (not 91)

### Test 2: Character Merging
```bash
# Check analysis.json for character aliases
python3 -c "
import json
with open('/tmp/gatsby_test/analysis.json') as f:
    data = json.load(f)
    for char in data.get('characters', []):
        if 'gatsby' in char.get('canonical_name', '').lower():
            print(f'{char[\"canonical_name\"]}: {char.get(\"aliases\", [])}')"
```
- Jay Gatsby aliases should include: James Gatz, Jimmy
- Mrs. Wilson aliases should include: Myrtle
- Owl Eyes aliases should include: Owl-eyes

### Test 3: Character Classification
```bash
python3 -c "
import json
with open('/tmp/gatsby_test/analysis.json') as f:
    data = json.load(f)
    for char in data.get('characters', [])[:10]:
        print(f'{char[\"canonical_name\"]}: {char.get(\"character_type\", \"MISSING\")}')"
```
- Main characters should be `story` type (not `uncertain`)

---

## Success Criteria

1. **Chapter Accuracy:** Gatsby detects exactly 9 chapters
2. **Character Merging:** Birth names and aliases correctly merged
3. **Character Classification:** No UNCERTAIN types for main characters
4. **No Regressions:** Books without these patterns work identically

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| TOC filtering too aggressive | Medium | Only filter when pattern is dominant (>30%) |
| Birth name detection false positives | High | Require context indicators, use LLM validation |
| Over-merging different people | Critical | Keep conservative family member checks |
| Classification wrong for edge cases | Low | UNCERTAIN is safe fallback |

---

## References

- Current TOC parsing: `src/pipeline/chapter_detection/profiler.py:150-210`
- Character merging: `src/pipeline/character_extraction/consensus.py:1090-1409`
- NER proposer: `src/pipeline/character_extraction/proposers/ner.py`
- Analysis output: `output/gatsby_011/analysis.json`
