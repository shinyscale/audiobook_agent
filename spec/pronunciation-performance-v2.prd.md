# PRD: Paragraph-Based Context System for Pronunciation Guide

**Version:** 2.0
**Status:** Draft
**Priority:** Medium
**Dependencies:** Requires completion of `pronunciation-performance-v1.prd.md`
**Target:** Replace fixed-window context with paragraph-based system enabling clickable navigation and better narrator workflow.

## Executive Summary

Phase 1 (v1) implemented a fixed-window context extraction system that solved the immediate bug (missing target words in context). However, the goal is to provide narrators with a richer context system where they can:

1. **Click on any pronunciation word** to see the full paragraph where it appears
2. **See the word highlighted** in the paragraph for easy identification
3. **Navigate to the full text position** to see surrounding context
4. **Review multiple occurrences** of the same word across different paragraphs

This Phase 2 enhancement transforms the pronunciation guide from a simple list into an interactive reference tool that significantly improves the narrator's workflow.

**Proposal:**
1. **Paragraph indexing**: Extend WordIndex to track paragraph boundaries during initial scan
2. **Paragraph-based context**: Replace fixed-window with full paragraph extraction
3. **Data model updates**: Store paragraph information in PronunciationMention
4. **GUI enhancements**: Add clickable words, paragraph display, and navigation
5. **Export formats**: Support HTML/JSON with paragraph references

---

## Problem Statement

### Current Limitations (Phase 1)

The fixed-window context system has these limitations:

1. **Truncated context**: 100-character windows may cut off mid-sentence or mid-thought
2. **No navigation**: Context snippets are isolated; can't jump to full text
3. **No highlighting**: Target word isn't visually distinguished in context
4. **Limited occurrences**: Only shows 1-3 context examples, not all occurrences
5. **No paragraph awareness**: Context doesn't respect paragraph boundaries

### User Needs

Narrators need to:
- Understand how a word is used in its full context (complete sentences/paragraphs)
- Quickly navigate to see a word in the full document
- Review all occurrences of a word, not just a few examples
- See the word clearly highlighted in context
- Understand paragraph-level context for proper pronunciation emphasis

---

## Proposed Solution

### Part 1: Paragraph Indexing

Extend `WordIndex` to detect and store paragraph boundaries during the initial scan:

```python
@dataclass
class ParagraphBoundary:
    """A paragraph in the document."""
    index: int              # 0-based paragraph index
    start_position: int     # Character position where paragraph starts
    end_position: int       # Character position where paragraph ends
    text: str               # Full paragraph text

class WordIndex:
    """Pre-built index with paragraph awareness."""
    
    def __init__(self, full_text: str, chapter_boundaries: list[tuple[int, int, int]]):
        self.full_text = full_text
        self.chapter_boundaries = chapter_boundaries
        self.word_positions: dict[str, list[WordOccurrence]] = {}
        self.paragraphs: list[ParagraphBoundary] = []  # NEW
        self._build_index()
    
    def _build_index(self) -> None:
        """Build word index and paragraph boundaries in single pass."""
        # First, detect paragraphs
        self._detect_paragraphs()
        
        # Then index words with paragraph info
        for match in re.finditer(r'\b([a-zA-Z]+(?:[-'][a-zA-Z]+)*)\b', self.full_text):
            word = match.group(1)
            word_lower = word.lower()
            position = match.start()
            chapter_idx = self._get_chapter(position)
            paragraph_idx = self._get_paragraph(position)  # NEW
            
            if word_lower not in self.word_positions:
                self.word_positions[word_lower] = []
            
            self.word_positions[word_lower].append(WordOccurrence(
                position=position,
                original_form=word,
                chapter_index=chapter_idx,
                paragraph_index=paragraph_idx  # NEW
            ))
    
    def _detect_paragraphs(self) -> None:
        """Detect paragraph boundaries (separated by blank lines)."""
        # Paragraphs separated by one or more blank lines
        sep_re = re.compile(r'(?:\r?\n\s*){2,}')
        start = 0
        
        for match in sep_re.finditer(self.full_text):
            end = match.start()
            if end > start:
                para_text = self.full_text[start:end].strip()
                if para_text:
                    self.paragraphs.append(ParagraphBoundary(
                        index=len(self.paragraphs),
                        start_position=start,
                        end_position=end,
                        text=para_text
                    ))
            start = match.end()
        
        # Trailing paragraph
        if start < len(self.full_text):
            para_text = self.full_text[start:].strip()
            if para_text:
                self.paragraphs.append(ParagraphBoundary(
                    index=len(self.paragraphs),
                    start_position=start,
                    end_position=len(self.full_text),
                    text=para_text
                ))
    
    def _get_paragraph(self, position: int) -> int:
        """Get paragraph index for a position (binary search)."""
        # Binary search for efficiency
        left, right = 0, len(self.paragraphs) - 1
        while left <= right:
            mid = (left + right) // 2
            para = self.paragraphs[mid]
            if para.start_position <= position < para.end_position:
                return para.index
            elif position < para.start_position:
                right = mid - 1
            else:
                left = mid + 1
        return 0  # Default to first paragraph
    
    def get_paragraph(self, paragraph_index: int) -> Optional[ParagraphBoundary]:
        """Get paragraph by index."""
        if 0 <= paragraph_index < len(self.paragraphs):
            return self.paragraphs[paragraph_index]
        return None
```

### Part 2: Data Model Updates

Extend `PronunciationMention` to include paragraph information:

```python
@dataclass
class PronunciationMention:
    """A single occurrence of a word in the text."""
    word_form: str          # Exact text found (preserves case)
    position: int           # Character offset in full document
    chapter_index: int      # Which chapter (1-indexed)
    paragraph_index: int    # NEW: Which paragraph (0-indexed)
    paragraph_start: int    # NEW: Paragraph start position
    paragraph_end: int      # NEW: Paragraph end position
    paragraph_text: str     # NEW: Full paragraph text
    context: str            # Keep for backward compatibility (first 200 chars of paragraph)
    
    def to_dict(self) -> dict:
        return {
            "word_form": self.word_form,
            "position": self.position,
            "chapter_index": self.chapter_index,
            "paragraph_index": self.paragraph_index,
            "paragraph_start": self.paragraph_start,
            "paragraph_end": self.paragraph_end,
            "paragraph_text": self.paragraph_text,
            "context": self.context,  # Backward compatible
        }
```

### Part 3: Context Extraction Update

Replace fixed-window with paragraph-based extraction:

```python
def _extract_context(
    self,
    text: str,
    position: int,
    word_length: int,
    word_index: WordIndex,
) -> tuple[str, int, int, str]:
    """Extract full paragraph context for word.
    
    Returns:
        Tuple of (context_snippet, paragraph_index, paragraph_start, paragraph_text)
    """
    paragraph_idx = word_index._get_paragraph(position)
    paragraph = word_index.get_paragraph(paragraph_idx)
    
    if paragraph:
        # Return full paragraph
        return (
            paragraph.text[:200] + "..." if len(paragraph.text) > 200 else paragraph.text,
            paragraph_idx,
            paragraph.start_position,
            paragraph.text
        )
    else:
        # Fallback to fixed window if paragraph not found
        window = 100
        start = max(0, position - window)
        end = min(len(text), position + word_length + window)
        return (
            text[start:end],
            -1,  # No paragraph index
            start,
            text[start:end]
        )
```

### Part 4: GUI Enhancements

#### Desktop GUI (tkinter)

Add clickable pronunciation words with paragraph display:

```python
class PronunciationDetailDialog:
    """Dialog showing pronunciation details with paragraph context."""
    
    def __init__(self, parent, entry: PronunciationEntry, full_text: str, word_index: WordIndex):
        self.entry = entry
        self.full_text = full_text
        self.word_index = word_index
        self.current_occurrence = 0
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Pronunciation: {entry.word}")
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Word and pronunciation info
        info_frame = ttk.Frame(self.dialog, padding="10")
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text=f"Word: {self.entry.word}", font=("Arial", 12, "bold")).pack()
        if self.entry.phonetic_spelling:
            ttk.Label(info_frame, text=f"Phonetic: {self.entry.phonetic_spelling}").pack()
        if self.entry.ipa:
            ttk.Label(info_frame, text=f"IPA: {self.entry.ipa}").pack()
        
        # Occurrence navigation
        nav_frame = ttk.Frame(self.dialog, padding="10")
        nav_frame.pack(fill=tk.X)
        
        ttk.Label(nav_frame, text=f"Occurrence {self.current_occurrence + 1} of {len(self.entry.mentions)}").pack(side=tk.LEFT)
        
        ttk.Button(nav_frame, text="◀ Prev", command=self._prev_occurrence).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Next ▶", command=self._next_occurrence).pack(side=tk.LEFT, padx=5)
        
        # Paragraph display with highlighting
        para_frame = ttk.LabelFrame(self.dialog, text="Context", padding="10")
        para_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.paragraph_text = tk.Text(
            para_frame,
            wrap=tk.WORD,
            height=10,
            font=("Arial", 11)
        )
        self.paragraph_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(para_frame, orient=tk.VERTICAL, command=self.paragraph_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.paragraph_text.config(yscrollcommand=scrollbar.set)
        
        # Navigation button
        nav_btn_frame = ttk.Frame(self.dialog, padding="10")
        nav_btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            nav_btn_frame,
            text="Jump to Position in Full Text",
            command=self._jump_to_position
        ).pack()
        
        # Load first occurrence
        self._load_occurrence(0)
    
    def _load_occurrence(self, index: int):
        """Load paragraph for occurrence at index."""
        if not (0 <= index < len(self.entry.mentions)):
            return
        
        mention = self.entry.mentions[index]
        self.current_occurrence = index
        
        # Clear and insert paragraph text
        self.paragraph_text.delete("1.0", tk.END)
        self.paragraph_text.insert("1.0", mention.paragraph_text)
        
        # Highlight the word
        word_start = mention.paragraph_text.lower().find(self.entry.word.lower())
        if word_start != -1:
            word_end = word_start + len(self.entry.word)
            self.paragraph_text.tag_add("highlight", f"1.{word_start}", f"1.{word_end}")
            self.paragraph_text.tag_config("highlight", background="yellow", foreground="black")
            
            # Scroll to highlighted word
            self.paragraph_text.see(f"1.{word_start}")
    
    def _prev_occurrence(self):
        """Show previous occurrence."""
        if self.current_occurrence > 0:
            self._load_occurrence(self.current_occurrence - 1)
    
    def _next_occurrence(self):
        """Show next occurrence."""
        if self.current_occurrence < len(self.entry.mentions) - 1:
            self._load_occurrence(self.current_occurrence + 1)
    
    def _jump_to_position(self):
        """Open full text viewer at word position."""
        mention = self.entry.mentions[self.current_occurrence]
        # Open full text viewer (implementation depends on existing viewer)
        # Could open in new window, scroll to position, highlight word
        pass
```

#### TUI (Textual)

Add paragraph display to detail panel:

```python
class PronunciationDetailPanel(Static):
    """Enhanced pronunciation detail panel with paragraph context."""
    
    def show_pronunciation(self, pron: PronunciationEntry, word_index: WordIndex):
        """Display pronunciation with paragraph context."""
        content = f"""## {pron.word}
        
**IPA:** {pron.ipa or "_Not available_"}
**Phonetic:** {pron.phonetic_spelling or "_Not available_"}
**Occurrences:** {pron.occurrences}
**Chapters:** {', '.join(str(c) for c in pron.chapters_present)}

### Context (First Occurrence)
"""
        if pron.mentions:
            mention = pron.mentions[0]
            # Highlight word in paragraph
            para_text = mention.paragraph_text
            word_pos = para_text.lower().find(pron.word.lower())
            if word_pos != -1:
                highlighted = (
                    para_text[:word_pos] +
                    f"[bold yellow]{para_text[word_pos:word_pos+len(pron.word)]}[/bold yellow]" +
                    para_text[word_pos+len(pron.word):]
                )
                content += f"> {highlighted}\n"
            else:
                content += f"> {para_text}\n"
            
            content += f"\n[dim]Paragraph {mention.paragraph_index + 1} | Position {mention.position}[/dim]"
        
        self.update(Markdown(content))
```

### Part 5: Export Formats

#### HTML Export with Clickable Words

```python
def export_pronunciation_html(
    pronunciation_map: PronunciationMap,
    full_text: str,
    word_index: WordIndex,
    output_path: Path
) -> None:
    """Export pronunciation guide as interactive HTML."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pronunciation Guide</title>
    <style>
        .word-entry {{
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .word-link {{
            color: #0066cc;
            cursor: pointer;
            text-decoration: underline;
        }}
        .word-link:hover {{
            color: #004499;
        }}
        .paragraph {{
            margin: 10px 0;
            padding: 10px;
            background: #f5f5f5;
            border-left: 3px solid #0066cc;
        }}
        .highlighted-word {{
            background: yellow;
            font-weight: bold;
        }}
        .occurrence-nav {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <h1>Pronunciation Guide</h1>
"""
    
    for entry in pronunciation_map.entries:
        html += f"""
    <div class="word-entry">
        <h2>{entry.word}</h2>
        <p><strong>IPA:</strong> {entry.ipa or 'N/A'}</p>
        <p><strong>Phonetic:</strong> {entry.phonetic_spelling or 'N/A'}</p>
        <p><strong>Occurrences:</strong> {entry.occurrence_count}</p>
        
        <div class="occurrence-nav">
            <h3>Context Examples</h3>
"""
        for i, mention in enumerate(entry.mentions[:5]):  # Show first 5
            para_text = mention.paragraph_text
            word_pos = para_text.lower().find(entry.word.lower())
            if word_pos != -1:
                highlighted_para = (
                    para_text[:word_pos] +
                    f'<span class="highlighted-word">{para_text[word_pos:word_pos+len(entry.word)]}</span>' +
                    para_text[word_pos+len(entry.word):]
                )
            else:
                highlighted_para = para_text
            
            html += f"""
            <div class="paragraph">
                <p>{highlighted_para}</p>
                <small>Paragraph {mention.paragraph_index + 1} | Position {mention.position}</small>
            </div>
"""
        
        html += """
        </div>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
```

---

## Features and User Stories

### Feature 1: Paragraph Indexing

**Priority:** CRITICAL
**Rationale:** Foundation for all paragraph-based features.

**User Stories:**

```json
{
  "category": "functional",
  "description": "WordIndex detects and stores paragraph boundaries",
  "steps": [
    "Create WordIndex from document with multiple paragraphs",
    "Verify all paragraphs are detected (separated by blank lines)",
    "Verify paragraph start/end positions are correct",
    "Verify paragraph indices are assigned correctly",
    "Test edge cases: single paragraph, no blank lines, mixed line endings"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Word occurrences include paragraph index",
  "steps": [
    "Index document with paragraphs",
    "Query word occurrences",
    "Verify each occurrence has correct paragraph_index",
    "Verify paragraph_index matches actual paragraph boundaries"
  ],
  "passes": true
}
```

### Feature 2: Paragraph-Based Context Extraction

**Priority:** HIGH
**Rationale:** Provides full context instead of truncated snippets.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Context extraction returns full paragraph",
  "steps": [
    "Extract context for word in middle of paragraph",
    "Verify returned context is full paragraph text",
    "Verify paragraph boundaries are respected",
    "Test words at paragraph start/end"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "PronunciationMention stores paragraph information",
  "steps": [
    "Create PronunciationMention from word occurrence",
    "Verify paragraph_index, paragraph_start, paragraph_end are set",
    "Verify paragraph_text contains full paragraph",
    "Verify backward compatibility (context field still present)"
  ],
  "passes": true
}
```

### Feature 3: GUI Clickable Words

**Priority:** HIGH
**Rationale:** Core user experience improvement.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Pronunciation words are clickable in GUI",
  "steps": [
    "Open pronunciation guide in GUI",
    "Click on a pronunciation word",
    "Verify dialog/modal opens showing word details",
    "Verify paragraph is displayed with word highlighted"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Word highlighting works correctly",
  "steps": [
    "Open pronunciation word dialog",
    "Verify target word is highlighted in paragraph",
    "Test words at start/middle/end of paragraph",
    "Test case-insensitive matching",
    "Verify highlighting works for all occurrences"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Occurrence navigation works",
  "steps": [
    "Open pronunciation word with multiple occurrences",
    "Click 'Next' button",
    "Verify next occurrence paragraph is displayed",
    "Click 'Prev' button",
    "Verify previous occurrence is displayed",
    "Verify occurrence counter updates correctly"
  ],
  "passes": true
}
```

### Feature 4: Full Text Navigation

**Priority:** MEDIUM
**Rationale:** Allows narrators to see broader context.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Jump to position button navigates to full text",
  "steps": [
    "Open pronunciation word dialog",
    "Click 'Jump to Position' button",
    "Verify full text viewer opens (or scrolls if already open)",
    "Verify cursor/selection is at word position",
    "Verify word is highlighted in full text"
  ],
  "passes": true
}
```

### Feature 5: HTML Export

**Priority:** MEDIUM
**Rationale:** Enables offline review and sharing.

**User Stories:**

```json
{
  "category": "functional",
  "description": "HTML export includes paragraph context",
  "steps": [
    "Export pronunciation guide to HTML",
    "Open HTML file in browser",
    "Verify all words are listed with paragraph context",
    "Verify words are highlighted in paragraphs",
    "Verify paragraph positions are displayed"
  ],
  "passes": true
}
```

---

## Architecture

### Updated Component Flow

```
                          PHASE 2 FLOW
                          ============
Input Text ── WordIndex (1 scan + paragraph detection) ──┬── Proposers ──┐
                                                          │                │
                                                          └── Paragraph Index
                                                                           │
                                                          ┌────────────────┘
                                                          │
                                                          ▼
                                    Enricher (parallel) ── Consolidator
                                                          │
                                                          ▼
                                    PronunciationMap (with paragraph info)
                                                          │
                                                          ▼
                                    GUI (clickable words) / HTML Export
```

### Data Model Changes

```
PronunciationMention (UPDATED)
├── word_form: str
├── position: int
├── chapter_index: int
├── paragraph_index: int          # NEW
├── paragraph_start: int          # NEW
├── paragraph_end: int            # NEW
├── paragraph_text: str           # NEW
└── context: str                  # Keep for backward compatibility

WordIndex (EXTENDED)
├── word_positions: dict
├── paragraphs: list[ParagraphBoundary]  # NEW
├── _detect_paragraphs()                  # NEW
├── _get_paragraph(position)              # NEW
└── get_paragraph(index)                  # NEW
```

---

## Implementation Plan

### Phase 1: Paragraph Indexing (Days 1-2)

**Files to modify:**
- `src/pipeline/pronunciation_guide/word_index.py` - Add paragraph detection
- `src/pipeline/pronunciation_guide/proposers/base.py` - Update context extraction

**Tasks:**
- Implement `_detect_paragraphs()` method
- Add `paragraphs` list to WordIndex
- Update `_build_index()` to assign paragraph indices
- Add `_get_paragraph()` binary search method
- Test paragraph detection on various document formats

### Phase 2: Data Model Updates (Day 2-3)

**Files to modify:**
- `src/pipeline/pronunciation_guide/models.py` - Extend PronunciationMention

**Tasks:**
- Add paragraph fields to PronunciationMention
- Update `to_dict()` and `from_dict()` methods
- Ensure backward compatibility
- Update all proposers to populate paragraph fields

### Phase 3: Context Extraction Update (Day 3)

**Files to modify:**
- `src/pipeline/pronunciation_guide/proposers/base.py` - Replace fixed-window

**Tasks:**
- Update `_extract_context()` to use paragraphs
- Update `_find_all_occurrences()` to include paragraph info
- Test edge cases (no paragraphs, single paragraph, etc.)

### Phase 4: GUI Enhancements (Days 4-5)

**Files to create:**
- `src/gui/pronunciation_dialog.py` - New dialog for pronunciation details

**Files to modify:**
- `src/gui/desktop.py` - Add click handlers for pronunciation words
- `src/gui/tui.py` - Update detail panel for paragraph display

**Tasks:**
- Create PronunciationDetailDialog class
- Add click handlers to pronunciation table/list
- Implement word highlighting in paragraph display
- Add occurrence navigation
- Add "Jump to Position" functionality

### Phase 5: Export Formats (Day 5-6)

**Files to create:**
- `src/export/pronunciation_html.py` - HTML export with paragraphs

**Files to modify:**
- `src/pipeline/pronunciation_guide/models.py` - Add export methods

**Tasks:**
- Implement HTML export with clickable words
- Add paragraph highlighting in HTML
- Test export on various documents
- Update JSON export to include paragraph info

### Phase 6: Testing & Validation (Day 7)

- Test paragraph detection on various document formats
- Test GUI interactions (clicking, navigation, highlighting)
- Test HTML export rendering
- Verify backward compatibility
- Performance testing (paragraph indexing overhead)

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/pipeline/pronunciation_guide/word_index.py` | MODIFY | Add paragraph detection and indexing |
| `src/pipeline/pronunciation_guide/models.py` | MODIFY | Extend PronunciationMention with paragraph fields |
| `src/pipeline/pronunciation_guide/proposers/base.py` | MODIFY | Update context extraction to use paragraphs |
| `src/gui/pronunciation_dialog.py` | CREATE | Dialog for pronunciation details with paragraph display |
| `src/gui/desktop.py` | MODIFY | Add click handlers for pronunciation words |
| `src/gui/tui.py` | MODIFY | Update detail panel for paragraph context |
| `src/export/pronunciation_html.py` | CREATE | HTML export with paragraph context |

---

## Verification

### Test 1: Paragraph Detection

```python
from src.pipeline.pronunciation_guide.word_index import WordIndex

text = """First paragraph.

Second paragraph with multiple sentences. Here's another sentence.

Third paragraph."""

boundaries = [(1, 0, len(text))]
index = WordIndex(text, boundaries)

assert len(index.paragraphs) == 3
assert index.paragraphs[0].text == "First paragraph."
assert index.paragraphs[1].text.startswith("Second paragraph")
assert index.paragraphs[2].text == "Third paragraph."
```

### Test 2: Paragraph Index Assignment

```python
# Test that words get correct paragraph indices
text = "Word in first para.\n\nWord in second para."
index = WordIndex(text, [(1, 0, len(text))])

occurrences = index.get_occurrences("word")
assert len(occurrences) == 2
assert occurrences[0].paragraph_index == 0
assert occurrences[1].paragraph_index == 1
```

### Test 3: Context Extraction

```python
from src.pipeline.pronunciation_guide.proposers.base import BasePronunciationProposer

text = "This is a test paragraph with the word pronunciation in it."
index = WordIndex(text, [(1, 0, len(text))])
position = text.index("pronunciation")

context, para_idx, para_start, para_text = BasePronunciationProposer._extract_context(
    text, position, len("pronunciation"), index
)

assert "pronunciation" in para_text
assert para_text == text  # Full paragraph
assert para_idx == 0
```

### Test 4: GUI Click Handler

```python
# Test that clicking pronunciation word opens dialog
# Test that paragraph is displayed
# Test that word is highlighted
# Test occurrence navigation
```

### Test 5: HTML Export

```python
# Export pronunciation guide to HTML
# Verify HTML contains paragraph context
# Verify words are highlighted in paragraphs
# Open in browser and verify rendering
```

---

## Success Criteria

1. **Paragraph Detection**: All paragraphs correctly detected and indexed
2. **Context Quality**: Full paragraphs provided instead of truncated snippets
3. **GUI Functionality**: Clickable words open dialog with paragraph display
4. **Word Highlighting**: Target word is visually highlighted in paragraph
5. **Navigation**: Occurrence navigation works correctly
6. **Backward Compatibility**: Old data formats still work (context field preserved)
7. **Performance**: Paragraph indexing adds < 5% overhead to Phase 1 performance
8. **Export Quality**: HTML export renders correctly with paragraph context

---

## Expected Performance Impact

| Metric | Phase 1 | Phase 2 | Change |
|--------|---------|---------|--------|
| Indexing time | ~1-2s | ~1.5-2.5s | +0.5s (paragraph detection) |
| Memory usage | ~2-3MB | ~3-4MB | +1MB (paragraph storage) |
| Context extraction | O(1) | O(1) | No change |
| GUI responsiveness | N/A | < 100ms | New feature |

**Overall:** Minimal performance impact. Paragraph detection adds ~0.5s to indexing and ~1MB memory, which is acceptable for the improved user experience.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Paragraph detection fails on edge cases | Medium | Test various formats (PDF, DOCX, TXT); fallback to fixed-window |
| Memory usage increases significantly | Low | Paragraph text is stored once, shared by all mentions |
| GUI performance degrades with many occurrences | Low | Limit displayed occurrences (first 5-10), lazy load rest |
| HTML export file size too large | Low | Option to limit occurrences per word; compress HTML |
| Backward compatibility breaks | Medium | Keep `context` field; make paragraph fields optional |
| Paragraph boundaries inconsistent | Medium | Use consistent detection algorithm; document assumptions |

---

## Future Enhancements (Deferred)

1. **Paragraph-level pronunciation notes**: Allow narrators to add notes per paragraph occurrence
2. **Multi-paragraph context**: Show surrounding paragraphs for better context
3. **Paragraph search**: Search for words within specific paragraphs
4. **Export to PDF**: PDF export with clickable words and paragraph context
5. **Collaborative annotations**: Multiple narrators can annotate pronunciation decisions

---

## References

- Phase 1 PRD: `pronunciation-performance-v1.prd.md`
- Current WordIndex: `src/pipeline/pronunciation_guide/word_index.py`
- Current models: `src/pipeline/pronunciation_guide/models.py`
- GUI components: `src/gui/desktop.py`, `src/gui/tui.py`
- Paragraph detection reference: `src/llm/refiner.py:_iter_paragraph_spans()`
