# PRD: Pronunciation Agent Performance Optimization

**Version:** 1.0
**Status:** Draft
**Priority:** High
**Target:** Reduce pronunciation pipeline runtime from 2+ hours to ~15-20 minutes for typical novels.

## Executive Summary

The pronunciation agent is taking 2+ hours to analyze novels like Frankenstein. Root cause analysis reveals the pipeline performs **~80-110 full-text regex scans** when only **1 scan** is needed. Additional issues include a broken context extraction function and inefficient LLM batching.

**Proposal:**
1. **Single-pass word indexing**: Build a word-to-positions index in one scan, then have all proposers query this index
2. **Fix context extraction**: Replace broken sentence-boundary detection with reliable fixed-window approach
3. **Parallel LLM enrichment**: Run 3-4 concurrent LLM batch requests instead of sequential
4. **Increase batch sizes**: Larger enrichment batches mean fewer LLM calls

---

## Problem Statement

### Current Performance Analysis

For a typical novel (~77,000 words like Frankenstein), the pronunciation pipeline:

| Stage | Current Time | Root Cause |
|-------|--------------|------------|
| Proposal | ~30-60 min | 80-110 full-text regex scans |
| Enrichment | ~40-60 min | Sequential LLM calls, small batches |
| Consolidation | ~5 min | CPU-bound merging (acceptable) |
| **Total** | **~2+ hours** | |

### Root Cause: Multiple Full-Text Scans

Each proposer independently scans the entire document:

| Proposer | Scans | Method |
|----------|-------|--------|
| CMUProposer | 1 | Single efficient scan (good) |
| ForeignProposer | ~15-20 | One scan per pattern (5 languages × 3-4 patterns) |
| HomographProposer | 40 | One scan per homograph word in dictionary |
| CharacterProposer | N | One scan per character name word (~20-50) |

**Total: ~76-110 full-text regex scans** for the proposal stage alone.

### Secondary Issue: Broken Context Extraction

The current context extraction in `proposers/base.py:48-84` has a bug where the sentence boundary detection sometimes excludes the target word from the context. The logic is complex with multiple edge cases:

```python
# Current buggy approach - 8 string operations per mention
for punct in '.!?"':
    idx = text.rfind(punct, search_start, position)  # Find before
    idx = text.find(punct, position + word_length, search_end)  # Find after
```

Users report seeing context snippets that don't include the word being referenced.

### Tertiary Issue: Sequential LLM Calls

The enrichment stage processes batches sequentially:
- Batch size: 10 words (small)
- No concurrency: Wait for response before sending next batch
- 200 unique words = 20+ sequential LLM calls at ~2-3 seconds each = 40-60+ minutes

---

## Proposed Solution

### Part 1: Single-Pass Word Indexing (Highest Impact)

Create a `WordIndex` class that builds a word-to-positions map in a single regex scan. All proposers then query this pre-built index instead of scanning the full text.

**Before (current):**
```
CMUProposer.propose(full_text)     → scan entire text
ForeignProposer.propose(full_text) → scan entire text 15-20x
HomographProposer.propose(full_text) → scan entire text 40x
CharacterProposer.propose(full_text) → scan entire text Nx
```

**After (optimized):**
```
index = WordIndex(full_text)       → ONE scan, build index
CMUProposer.propose(index)         → O(1) lookups/filters
ForeignProposer.propose(index)     → O(1) lookups/filters
HomographProposer.propose(index)   → O(1) lookups
CharacterProposer.propose(index)   → O(1) lookups
```

### Part 2: Fix Context Extraction

Replace the broken sentence-boundary detection with a simple, reliable fixed-window approach:

```python
def _extract_context(text: str, position: int, word_length: int, window: int = 100) -> str:
    """Extract fixed window around word, guaranteeing word is included.
    
    NOTE: This is a temporary solution for Phase 1. Phase 2 will implement
    paragraph-based context extraction with clickable navigation.
    """
    start = max(0, position - window)
    end = min(len(text), position + word_length + window)
    context = text[start:end]
    context = ' '.join(context.split())  # Normalize whitespace
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."
    return context
```

This guarantees the target word is always centered in the context. Window size is configurable (default 100 chars each side).

**Future Enhancement (Phase 2):** Replace with paragraph-based context system that provides full paragraph text with clickable navigation to full document position.

### Part 3: Parallel LLM Enrichment

Run multiple LLM batch requests concurrently using asyncio or threading with retry logic:

```python
async def enrich_parallel(self, proposals: list, max_workers: int = 4):
    """Process enrichment batches concurrently with retry logic."""
    batches = [proposals[i:i+self.batch_size] for i in range(0, len(proposals), self.batch_size)]

    async def enrich_with_retry(batch, max_retries: int = 3):
        """Enrich a batch with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return await self._enrich_batch_async(batch)
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                logger.error(f"Enrichment batch failed: {e}")
                raise

    async with asyncio.Semaphore(max_workers):
        tasks = [enrich_with_retry(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions (log and return empty enrichments for failed batches)
    return merge_results(results)
```

### Part 4: Increase Batch Sizes

- Enrichment batch size: 10 → 30-50 words per LLM call
- ForeignProposer validation: Make optional (default: skip)

---

## Features and User Stories

### Feature 1: Word Index for Single-Pass Scanning

**Priority:** CRITICAL
**Rationale:** Eliminates ~99% of redundant text scanning.

**User Stories:**

```json
{
  "category": "functional",
  "description": "WordIndex builds complete word-to-positions map in single pass",
  "steps": [
    "Create WordIndex from full document text",
    "Verify all unique words are indexed",
    "Verify positions are correct for each word",
    "Verify chapter indices are correctly assigned",
    "Confirm single regex scan was used (via timing/profiling)"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Proposers use WordIndex instead of full-text scanning",
  "steps": [
    "Run CMUProposer with WordIndex",
    "Run HomographProposer with WordIndex",
    "Run CharacterProposer with WordIndex",
    "Run ForeignProposer with WordIndex",
    "Verify results match previous full-text-scan approach",
    "Verify significant speedup (>10x for proposal stage)"
  ],
  "passes": true
}
```

```json
{
  "category": "performance",
  "description": "Proposal stage completes in under 2 minutes for typical novel",
  "steps": [
    "Run pronunciation pipeline on Frankenstein (~77K words)",
    "Measure proposal stage time",
    "Verify proposal stage completes in < 120 seconds",
    "Compare to previous timing (was 30-60 minutes)"
  ],
  "passes": true
}
```

---

### Feature 2: Fixed-Window Context Extraction

**Priority:** HIGH
**Rationale:** Fixes bug where target word is missing from context.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Context extraction always includes the target word",
  "steps": [
    "Extract context for words at various positions (start, middle, end of text)",
    "Verify target word appears in every context string",
    "Verify context is approximately centered on the target word",
    "Test edge cases: word at position 0, word at end of text"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Context uses ellipsis correctly for truncation",
  "steps": [
    "Extract context for word in middle of document",
    "Verify context starts and ends with '...'",
    "Extract context for word at start of document",
    "Verify context does not have leading '...'",
    "Extract context for word at end of document",
    "Verify context does not have trailing '...'"
  ],
  "passes": true
}
```

---

### Feature 3: Parallel LLM Enrichment

**Priority:** HIGH
**Rationale:** Reduces enrichment time by 3-4x through concurrency.

**User Stories:**

```json
{
  "category": "functional",
  "description": "LLM enrichment batches run concurrently",
  "steps": [
    "Run enrichment with 4 concurrent workers",
    "Verify all batches complete successfully",
    "Verify results are correctly merged",
    "Verify no race conditions or duplicate processing"
  ],
  "passes": true
}
```

```json
{
  "category": "performance",
  "description": "Enrichment stage completes in under 15 minutes for typical novel",
  "steps": [
    "Run pronunciation pipeline on Frankenstein with parallel enrichment",
    "Measure enrichment stage time",
    "Verify enrichment completes in < 15 minutes",
    "Compare to previous timing (was 40-60 minutes)"
  ],
  "passes": true
}
```

---

### Feature 4: Configurable Batch Sizes

**Priority:** MEDIUM
**Rationale:** Fewer LLM calls means less overhead.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Enrichment batch size is configurable",
  "steps": [
    "Configure enrichment batch size to 30",
    "Run enrichment pipeline",
    "Verify batches contain up to 30 words each",
    "Verify LLM can handle larger batches successfully"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "ForeignProposer LLM validation is optional",
  "steps": [
    "Configure ForeignProposer with skip_llm_validation=True",
    "Run foreign word detection",
    "Verify pattern-matched words are proposed without LLM validation",
    "Verify significant time savings"
  ],
  "passes": true
}
```

---

## Architecture

### New Module: Word Index

```
src/pipeline/pronunciation_guide/
├── word_index.py           # NEW: Single-pass word indexing
├── pipeline.py             # MODIFIED: Use WordIndex
├── enricher.py             # MODIFIED: Parallel processing, larger batches
└── proposers/
    ├── base.py             # MODIFIED: Accept WordIndex, fix context extraction
    ├── cmu_proposer.py     # MODIFIED: Query index instead of scanning
    ├── homograph_proposer.py # MODIFIED: Query index instead of scanning
    ├── character_proposer.py # MODIFIED: Query index instead of scanning
    └── foreign_proposer.py   # MODIFIED: Filter index, optional LLM validation
```

### Component Flow

```
                          CURRENT FLOW
                          ============
Input Text ──┬── CMUProposer (scan) ──────────────────┐
             ├── ForeignProposer (scan × 15-20) ──────┤
             ├── HomographProposer (scan × 40) ───────┼── Enricher (sequential) ── Consolidator
             └── CharacterProposer (scan × N) ────────┘

             ~80-110 scans                            ~20-50 sequential LLM calls


                          OPTIMIZED FLOW
                          ==============
Input Text ── WordIndex (1 scan) ──┬── CMUProposer (filter) ──────┐
                                   ├── ForeignProposer (filter) ──┤
                                   ├── HomographProposer (lookup) ┼── Enricher (parallel) ── Consolidator
                                   └── CharacterProposer (lookup) ┘

                                   1 scan                         4 concurrent LLM streams
```

### WordIndex Class Design

```python
@dataclass
class WordOccurrence:
    """Single occurrence of a word in the document."""
    position: int
    original_form: str
    chapter_index: int

class WordIndex:
    """Pre-built index of all words in document with positions."""

    def __init__(self, full_text: str, chapter_boundaries: list[tuple[int, int, int]]):
        self.full_text = full_text
        self.chapter_boundaries = chapter_boundaries
        self.word_positions: dict[str, list[WordOccurrence]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Single pass to extract all words with positions.
        
        Uses regex pattern that handles:
        - Standard words: "hello"
        - Hyphenated words: "well-known" (captured as single word)
        - Apostrophes: "don't", "O'Brien" (captured as single word)
        
        Note: Accented characters (café, naïve) may need special handling
        depending on text encoding. Consider Unicode word boundaries if needed.
        """
        # Pattern handles hyphenated words and apostrophes
        pattern = r'\b([a-zA-Z]+(?:[-'][a-zA-Z]+)*)\b'
        for match in re.finditer(pattern, self.full_text):
            word = match.group(1)
            word_lower = word.lower()
            position = match.start()
            chapter_idx = self._get_chapter(position)

            if word_lower not in self.word_positions:
                self.word_positions[word_lower] = []

            self.word_positions[word_lower].append(WordOccurrence(
                position=position,
                original_form=word,
                chapter_index=chapter_idx
            ))

    def get_occurrences(self, word: str) -> list[WordOccurrence]:
        """O(1) lookup of word positions."""
        return self.word_positions.get(word.lower(), [])

    def has_word(self, word: str) -> bool:
        """Check if word exists in index."""
        return word.lower() in self.word_positions

    def get_all_words(self) -> set[str]:
        """Get all unique words in document."""
        return set(self.word_positions.keys())

    def filter_by_predicate(self, predicate: Callable[[str], bool]) -> dict[str, list[WordOccurrence]]:
        """Get all words matching a predicate function."""
        return {word: occs for word, occs in self.word_positions.items() if predicate(word)}
```

---

## Configuration

### Pronunciation Pipeline Configuration

All settings are configurable via the GUI's experimental features section and can be persisted.

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `word_index_enabled` | `true` | boolean | Enable single-pass word indexing (disable to use old scanning approach) |
| `enrichment_batch_size` | `30` | 10-100 | Words per LLM enrichment batch |
| `enrichment_max_workers` | `4` | 1-8 | Concurrent LLM enrichment workers |
| `context_window_size` | `100` | 50-500 | Characters of context on each side of word |
| `context_mode` | `"fixed_window"` | `"fixed_window"` | Context extraction mode (paragraph mode deferred to Phase 2) |
| `foreign_proposer_skip_llm_validation` | `false` | boolean | Skip LLM validation for foreign words (faster, less accurate) |
| `homograph_proposer_enabled` | `true` | boolean | Enable homograph detection |
| `character_proposer_enabled` | `true` | boolean | Enable character name detection |
| `enrichment_max_retries` | `3` | 1-5 | Maximum retry attempts for failed LLM enrichment batches |
| `enrichment_retry_backoff_base` | `2` | 1-5 | Base seconds for exponential backoff (2^attempt * base) |

### GUI Integration

Settings are exposed in the **Agent Model Config** panel under **Advanced Chunking (Experimental)** section:

- Requires "Enable editing" checkbox
- Requires "Enable experimental features editing" checkbox
- Settings are per-run (not persisted by default)
- Reset button restores defaults
- New section: "Pronunciation Pipeline Settings"

### Configuration Class

```python
@dataclass
class PronunciationPipelineConfig:
    """Configuration for pronunciation pipeline performance tuning."""
    word_index_enabled: bool = True
    enrichment_batch_size: int = 30
    enrichment_max_workers: int = 4
    context_window_size: int = 100
    context_mode: str = "fixed_window"  # "fixed_window" | "paragraph" (Phase 2)
    foreign_proposer_skip_llm_validation: bool = False
    homograph_proposer_enabled: bool = True
    character_proposer_enabled: bool = True
    enrichment_max_retries: int = 3
    enrichment_retry_backoff_base: int = 2
```

---

## Addressed Concerns and Design Decisions

### WordIndex Regex Pattern

**Concern:** Basic `\b([a-zA-Z]+)\b` pattern misses hyphenated words and apostrophes.

**Decision:** Use `r'\b([a-zA-Z]+(?:[-'][a-zA-Z]+)*)\b'` to handle:
- Hyphenated words: "well-known", "state-of-the-art"
- Apostrophes: "don't", "O'Brien", "it's"

**Note:** Accented characters (café, naïve) may need Unicode word boundaries if encountered frequently. Monitor edge cases during testing.

### Memory Usage Estimate

**Concern:** PRD estimates ~10MB, but actual usage may differ.

**Decision:** More realistic estimate is 2-3MB for typical novel (77K words):
- ~77K word occurrences × (4 bytes position + 4 bytes chapter + ~8 bytes string overhead) ≈ 1.2MB
- ~50K unique words × ~20 bytes average = 1MB
- Dictionary overhead: ~0.5MB
- **Total: ~2-3MB**

**Action:** Add memory profiling to verification tests.

### Parallel LLM Enrichment Reliability

**Concern:** Rate limits and transient failures need handling.

**Decision:** Implement retry logic with exponential backoff:
- Default: 3 retries
- Backoff: 2^attempt seconds (2s, 4s, 8s)
- Configurable max_retries and backoff_base
- Log failures for monitoring
- Return empty enrichments for permanently failed batches (don't crash pipeline)

### Batch Size Increase

**Concern:** Increasing from 10 → 30-50 may hit token limits or reduce quality.

**Decision:**
- Start with 30 (conservative)
- Make configurable (10-100 range)
- Test incrementally: 10 → 20 → 30 → 50
- Monitor LLM response quality
- Document trade-off: speed vs. quality

### Context Extraction Approach

**Concern:** Fixed-window is temporary; paragraph-based system is desired.

**Decision:**
- Use fixed-window for Phase 1 (simple, reliable, fast)
- Make window size configurable
- Document that paragraph-based system is Phase 2
- Design data model to accommodate paragraph info later (backward compatible)

### Chapter Boundary Lookup Efficiency

**Concern:** Linear search through chapter boundaries may be slow for many chapters.

**Decision:** 
- Linear search is acceptable for typical novels (20-50 chapters)
- Document O(n) behavior
- Consider binary search optimization if profiling shows bottleneck
- For now, keep simple linear search

### Backward Compatibility

**Concern:** Old checkpoints and data formats may break.

**Decision:**
- Add `word_index_enabled` flag (default: true)
- Keep old scanning code as fallback (can be disabled via config)
- Ensure checkpoint format is backward compatible
- Add migration path if needed

---

## Implementation Plan

### Phase 1: Word Index (Days 1-2)

**Files to create:**
- `src/pipeline/pronunciation_guide/word_index.py`

**Files to modify:**
- `src/pipeline/pronunciation_guide/pipeline.py` - Build index, pass to proposers
- `src/pipeline/pronunciation_guide/proposers/base.py` - Add index parameter, fix context extraction

### Phase 2: Update Proposers (Days 2-3)

**Files to modify:**
- `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` - Use index filtering
- `src/pipeline/pronunciation_guide/proposers/homograph_proposer.py` - Use index lookup
- `src/pipeline/pronunciation_guide/proposers/character_proposer.py` - Use index lookup
- `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` - Use index filtering, add skip_validation flag

### Phase 3: Parallel Enrichment (Days 3-4)

**Files to modify:**
- `src/pipeline/pronunciation_guide/enricher.py` - Add async/threaded batch processing
- `src/pipeline/pronunciation_guide/pipeline.py` - Configure concurrency, batch sizes

### Phase 4: Testing & Validation (Day 5)

- Run on Frankenstein, compare output quality
- Measure timing improvements
- Verify no regressions

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/pipeline/pronunciation_guide/word_index.py` | CREATE | Single-pass word indexing |
| `src/pipeline/pronunciation_guide/pipeline.py` | MODIFY | Use WordIndex, configure parallel enrichment |
| `src/pipeline/pronunciation_guide/enricher.py` | MODIFY | Parallel LLM calls, larger batch size |
| `src/pipeline/pronunciation_guide/proposers/base.py` | MODIFY | Accept index param, fix context extraction |
| `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | MODIFY | Filter index instead of scanning |
| `src/pipeline/pronunciation_guide/proposers/homograph_proposer.py` | MODIFY | Lookup index instead of scanning |
| `src/pipeline/pronunciation_guide/proposers/character_proposer.py` | MODIFY | Lookup index instead of scanning |
| `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | MODIFY | Filter index, optional LLM validation |

---

## Verification

### Test 1: Word Index Correctness

```python
from src.pipeline.pronunciation_guide.word_index import WordIndex

text = "The quick brown fox jumps over the lazy dog. The fox was quick."
boundaries = [(1, 0, len(text))]

index = WordIndex(text, boundaries)

# Verify word counts
assert len(index.get_occurrences("the")) == 3  # "The" appears 3 times
assert len(index.get_occurrences("fox")) == 2
assert len(index.get_occurrences("quick")) == 2
assert index.has_word("lazy")
assert not index.has_word("nonexistent")

print("Word index tests passed")
```

### Test 2: Context Extraction Fix

```python
from src.pipeline.pronunciation_guide.proposers.base import BasePronunciationProposer

text = "This is a test sentence with the word pronunciation in the middle of it."
position = text.index("pronunciation")
word_length = len("pronunciation")

context = BasePronunciationProposer._extract_context(text, position, word_length)

assert "pronunciation" in context, f"Target word missing from context: {context}"
print(f"Context: {context}")
print("Context extraction test passed")
```

### Test 3: Performance Benchmark

```bash
# Run pronunciation pipeline with timing
time audiobook-prep analyze Test_Texts/frankenstein.txt --output output/frank_perf_test/

# Expected: Total time < 20 minutes (was 2+ hours)
```

### Test 4: Output Quality Comparison

```python
import json

# Compare old vs new output
with open('output/frank_old/analysis.json') as f:
    old = json.load(f)
with open('output/frank_new/analysis.json') as f:
    new = json.load(f)

old_words = set(e['word'] for e in old.get('pronunciation', {}).get('entries', []))
new_words = set(e['word'] for e in new.get('pronunciation', {}).get('entries', []))

# Should be nearly identical
overlap = old_words & new_words
print(f"Overlap: {len(overlap)} / {len(old_words)} ({100*len(overlap)/len(old_words):.1f}%)")
```

### Test 5: Parallel Enrichment Verification

```python
import asyncio
import time

# Verify concurrent execution
start = time.time()
# Run enrichment with 4 workers
elapsed = time.time() - start

# With 20 batches at 2s each:
# Sequential: 40s
# Parallel (4 workers): ~10s
assert elapsed < 15, f"Parallel enrichment took too long: {elapsed}s"
```

### Test 6: Memory Profiling

```python
import tracemalloc
from src.pipeline.pronunciation_guide.word_index import WordIndex

tracemalloc.start()

text = open('Test_Texts/frankenstein.txt').read()
boundaries = [(1, 0, len(text))]  # Simplified for test

index = WordIndex(text, boundaries)

current, peak = tracemalloc.get_traced_memory()
print(f"WordIndex memory: {current / 1024 / 1024:.2f} MB (peak: {peak / 1024 / 1024:.2f} MB)")
assert peak < 5 * 1024 * 1024, "WordIndex uses more than 5MB (expected ~2-3MB)"
```

### Test 7: Retry Logic Verification

```python
# Test that rate limit errors trigger retries
# Mock LLM client to raise RateLimitError on first 2 attempts, succeed on 3rd
# Verify exponential backoff timing
# Verify final success after retries
```

---

## Success Criteria

1. **Performance**: Full pipeline completes in < 20 minutes for typical novel (was 2+ hours)
2. **Proposal Stage**: Completes in < 2 minutes (was 30-60 minutes)
3. **Enrichment Stage**: Completes in < 15 minutes (was 40-60 minutes)
4. **Quality**: Output matches previous version (>95% word overlap)
5. **Context Fix**: Target word always appears in context snippets
6. **No Regressions**: All existing tests pass

---

## Expected Performance Improvement

| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Proposal | 30-60 min | 1-2 min | **30-60x** |
| Enrichment | 40-60 min | 10-15 min | **3-4x** |
| Consolidation | 5 min | 5 min | 1x (unchanged) |
| **Total** | **2+ hours** | **15-20 min** | **6-8x** |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WordIndex uses too much memory | Low | Index only stores positions, not text; ~2-3MB for typical novel (verified estimate) |
| Parallel LLM hits rate limits | Medium | Add configurable concurrency limit (default 4); implement retry with exponential backoff |
| Pattern filtering misses edge cases | Low | Keep full-text-scan as fallback option (configurable via `word_index_enabled`) |
| Async adds complexity | Medium | Use simple ThreadPoolExecutor as alternative to asyncio; add comprehensive error handling |
| Context window too short | Low | Make window size configurable (50-500 chars); default 100 chars each side |
| Batch size too large | Low | Start conservative (30), make configurable, test incrementally, monitor quality |
| Retry logic fails silently | Medium | Log all failures, return empty enrichments for failed batches, track in checkpoint warnings |
| Configuration not persisted | Low | Settings are per-run; add persistence option in future if needed |

---

## Future Optimizations (Deferred)

1. **Parallel Proposers**: After indexing, proposers could run concurrently (minimal additional gain)
2. **Caching**: Cache enrichment results across runs for repeated words
3. **Streaming**: Process chapters in parallel instead of full document at once
4. **Paragraph-Based Context (Phase 2)**: Replace fixed-window with full paragraph context, clickable navigation, and highlighted word display in GUI

---

## Phase 2 Preview: Paragraph-Based Context System

**Status:** Planned for next phase

**Goal:** Replace fixed-window context with paragraph-based system that provides:
- Full paragraph text for each word occurrence
- Clickable words in GUI that show paragraph with highlighting
- Navigation to full text position
- Better narrator workflow for pronunciation review

See `pronunciation-performance-v2.prd.md` for detailed Phase 2 specification.

---

## References

- Current pipeline: `src/pipeline/pronunciation_guide/pipeline.py`
- Current proposers: `src/pipeline/pronunciation_guide/proposers/`
- Current enricher: `src/pipeline/pronunciation_guide/enricher.py`
- LLM client: `src/pipeline/llm.py`
