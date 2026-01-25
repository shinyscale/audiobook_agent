# Draft: Narrator Workflow Integration

**Status:** Future Planning (Draft)
**Created:** 2026-01-23
**Vision:** First step in an AI-assisted audiobook recording suite

---

## Overview

Audiobook Prep is envisioned as the **pre-production layer** in a complete narrator workflow, comparable to how Hindenburg Narrator Studio handles recording and post-production. This document outlines how the tool could evolve to support professional narrators working on **new manuscripts** (not in any training data) with minimal friction.

### Reference: Hindenburg Narrator Studio
https://hindenburg.com/products/narrator-studio/

Key features we'd complement:
- Punch and roll recording
- Manuscript proofing (compare audio to text)
- ACX-compliant export
- Session management per chapter

---

## The Complete Narrator Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NARRATOR WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. PREP PHASE (Audiobook Prep)                                    │
│     ├── Import manuscript (PDF, EPUB, DOCX, TXT)                   │
│     ├── Narrator answers intake questions (2-3 min)                │
│     ├── AI analyzes: chapters, characters, pronunciations          │
│     ├── Narrator reviews/corrects in editable UI                   │
│     └── Export "prep package" for recording                        │
│                                                                     │
│  2. RECORD PHASE (Hindenburg / DAW)                                │
│     ├── Import chapter markers from prep package                   │
│     ├── Character voice notes in sidebar                           │
│     ├── Pronunciation alerts during proofing                       │
│     └── Per-chapter session files                                  │
│                                                                     │
│  3. PROOF & MASTER PHASE                                           │
│     ├── Compare recording to manuscript                            │
│     ├── Fix pickups with character context                         │
│     └── Export ACX-compliant files                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pre-Analysis Intake Form

For books not in training data, we need ground truth from the narrator. This should take **2-3 minutes** to complete.

### Quick Questions (Required)

```yaml
manuscript_info:
  title: "Book Title"
  author: "Author Name"
  genre:
    - fiction_literary
    - fiction_genre (sci-fi, fantasy, romance, thriller, etc.)
    - non_fiction
    - memoir
    - children

structure:
  chapter_count: 24  # or "not sure" - AI will detect
  has_prologue: true/false
  has_epilogue: true/false
  chapter_naming:
    - numbered (Chapter 1, Chapter 2)
    - titled (named chapters)
    - mixed
    - roman_numerals
    - unmarked (no explicit chapter markers)

narrative:
  pov:
    - first_person
    - third_person_limited
    - third_person_omniscient
    - multiple_pov
  narrator_character: "Nick Carraway"  # or null for third person
  tense:
    - past
    - present
    - mixed

characters:
  main_characters:
    - "Jay Gatsby"
    - "Daisy Buchanan"
    - "Nick Carraway"
    - "Tom Buchanan"
    - "Jordan Baker"
  # Just names - AI will find aliases, descriptions, etc.

setting:
  time_period: "1920s"  # Affects pronunciation expectations
  location: "New York, Long Island"
  dialect_notes: "Some characters use regional dialects"
```

### Optional (From Author/Publisher)

```yaml
author_notes:
  pronunciation_guide:
    - word: "Carraway"
      ipa: "/ˈkærəweɪ/"
      notes: "Rhymes with 'faraway'"
    - word: "Gatsby"
      ipa: "/ˈɡætsbɪ/"

  character_voices:
    - character: "Gatsby"
      notes: "Affected upper-class accent, slightly artificial"
    - character: "Tom"
      notes: "Brusque, old money, entitled"

  special_instructions:
    - "Chapter 5 is the emotional climax - slower pacing"
    - "Gatsby's 'old sport' catchphrase should feel natural, not forced"
```

### Intake UI Mockup

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUDIOBOOK PREP - New Project                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📚 Manuscript                                                      │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Drop file here or click to browse                       │       │
│  │  Supports: PDF, EPUB, DOCX, TXT                         │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  ─────────────────────────────────────────────────────────────     │
│                                                                     │
│  📖 Quick Questions (2-3 min)                                      │
│                                                                     │
│  How many chapters?        [____] or ☐ Not sure, detect for me    │
│                                                                     │
│  Main characters (3-5):    [________________________________]      │
│                            (comma-separated names)                  │
│                                                                     │
│  Point of view:            ○ First person (narrator is character)  │
│                            ○ Third person                          │
│                            ○ Multiple POV                          │
│                                                                     │
│  If first person, who      [____________________]                  │
│  is the narrator?                                                   │
│                                                                     │
│  Time period/setting:      [____________________]                  │
│                            (helps with pronunciation)               │
│                                                                     │
│  Genre:                    [Fiction - Literary      ▼]             │
│                                                                     │
│  ─────────────────────────────────────────────────────────────     │
│                                                                     │
│  📝 Author's Notes (optional)                                      │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Paste any pronunciation guide or character notes from   │       │
│  │  the author/publisher here...                            │       │
│  │                                                          │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│                                    [ Cancel ]  [ Start Analysis ]  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Post-Analysis Correction Workflow

After AI analysis, narrators need to review and correct without re-running the entire pipeline.

### Correction UI Principles

1. **Inline editing** - Click to edit, no separate forms
2. **Drag-and-drop merging** - Drag one character onto another to merge
3. **Split with context** - Select mentions to split into new character
4. **Undo/redo** - Full history of corrections
5. **Diff view** - See what changed from AI output

### Characters Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  CHARACTERS                                          [+ Add] [Undo] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ Main Cast ──────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  👤 Jay Gatsby (268 mentions)                    [Edit] [⋮]  │  │
│  │     Aliases: James Gatz, Gatsby, Mr. Gatsby                  │  │
│  │     Role: Protagonist                                         │  │
│  │     ⚠️ Suggested merge: "the host" (3 mentions)              │  │
│  │        [ Merge ] [ Ignore ]                                   │  │
│  │                                                               │  │
│  │  👤 Nick Carraway (145 mentions)                 [Edit] [⋮]  │  │
│  │     Aliases: Nick                                             │  │
│  │     Role: Narrator ✓                                         │  │
│  │                                                               │  │
│  │  👤 Daisy Buchanan (97 mentions)                 [Edit] [⋮]  │  │
│  │     Aliases: Daisy, Daisy Fay                                │  │
│  │     ⚠️ "Daisy Fay" may be maiden name - verify               │  │
│  │        [ Keep merged ] [ Split ]                              │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─ Supporting Cast ────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  👤 Meyer Wolfshiem (34 mentions)                [Edit] [⋮]  │  │
│  │     ⚠️ Also appears as "Wolfsheim" (1) - spelling variant?   │  │
│  │        [ Merge ] [ Keep separate ]                            │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─ Flagged for Review ─────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  ❓ "the man" (12 mentions) - ambiguous reference            │  │
│  │     Context: "the man in the pink suit" (ch.3, 5, 7)         │  │
│  │     [ Assign to: [Jay Gatsby ▼] ] [ New character ] [ Drop ] │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Pronunciations Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRONUNCIATIONS                          [+ Add] [Filter] [Export] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Search: [________________]  Show: ○ All ● Flagged ○ Corrected    │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Word          │ IPA/Phonetic  │ Notes           │ Actions     │ │
│  ├───────────────┼───────────────┼─────────────────┼─────────────┤ │
│  │ Carraway      │ /ˈkærəweɪ/    │ Character name  │ [✓] [Edit]  │ │
│  │ Wolfshiem     │ /ˈwʊlfʃiːm/   │ ⚠️ Verify      │ [?] [Edit]  │ │
│  │ coupe         │ /kuːp/        │ 1920s car       │ [✓] [Edit]  │ │
│  │ ❌ house      │ -             │ Common word     │ [Remove]    │ │
│  │ orgastic      │ /?/           │ ⚠️ Rare word   │ [?] [Edit]  │ │
│  └───────────────┴───────────────┴─────────────────┴─────────────┘ │
│                                                                     │
│  ⚠️ 3 items need review    ❌ 1 flagged for removal                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Chapters Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  CHAPTERS                                    [+ Add] [Reorder] [⋮] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   #  │ Title              │ Words  │ Characters    │ Status        │
│  ────┼────────────────────┼────────┼───────────────┼───────────────│
│   1  │ [Chapter I      ]  │ 5,892  │ Nick, Tom...  │ ✓             │
│   2  │ [Chapter II     ]  │ 4,280  │ Nick, Myrtle  │ ✓             │
│   3  │ [Chapter III    ]  │ 5,734  │ Nick, Gatsby  │ ✓             │
│   4  │ [Chapter IV     ]  │ 5,456  │ Nick, Gatsby  │ ✓             │
│   5  │ [Chapter V      ]  │ 4,233  │ Nick, Gatsby  │ ✓             │
│  ... │                    │        │               │               │
│   9  │ [Chapter IX     ]  │ 8,131  │ Nick          │ ✓             │
│                                                                     │
│  Total: 9 chapters, 51,058 words                                   │
│  Estimated recording time: ~5.5 hours @ 9,300 words/hour           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Prep Package Export Format

The "prep package" is a portable format that can be imported into recording software.

### File Structure

```
my_book_prep/
├── manifest.json           # Metadata, version, checksums
├── manuscript.txt          # Clean, normalized text
├── structure.json          # Chapters with markers
├── characters.json         # Full character data
├── pronunciations.json     # Pronunciation guide
├── summaries.json          # Chapter summaries
├── corrections.json        # Human corrections (for feedback loop)
├── markers/
│   ├── chapters.csv        # Import to DAW as markers
│   └── characters.csv      # Character appearance timeline
└── reports/
    ├── prep_report.html    # Human-readable summary
    └── voice_notes.pdf     # Printable character cards
```

### DAW Integration Formats

```yaml
# chapters.csv - Import as session markers
chapter,start_word,end_word,title,duration_estimate
1,0,5892,"Chapter I","38:00"
2,5893,10172,"Chapter II","28:00"
...

# characters.csv - Import as notes/comments
character,first_appearance_chapter,mention_count,voice_notes
"Jay Gatsby",3,268,"Affected upper-class, slightly artificial"
"Nick Carraway",1,145,"Midwest earnest, observational"
...
```

---

## Feedback Loop for Improvement

Corrections made by narrators become training signal.

### Correction Types to Track

```yaml
corrections:
  character_merges:
    - merged: ["the host", "Jay Gatsby"]
      reason: "same person"
      confidence_was: 0.45  # AI wasn't sure

  character_splits:
    - split: "the man"
      into: ["Jay Gatsby", "Tom Buchanan"]
      reason: "context-dependent reference"

  pronunciation_removals:
    - word: "house"
      reason: "common word, not ambiguous"

  pronunciation_additions:
    - word: "orgastic"
      ipa: "/ɔːrˈɡæstɪk/"
      notes: "rare word, verify author intent"

  chapter_boundary_adjustments:
    - chapter: 5
      adjustment: "+47 chars"
      reason: "included scene break in wrong chapter"
```

### How Corrections Improve the System

1. **Pattern Learning**: If narrators frequently remove "house" from pronunciations, add to global whitelist

2. **Merge Heuristics**: If "the host" → "protagonist" merges are common, increase that pattern's weight

3. **Genre-Specific Rules**: Fantasy books might need different character extraction than literary fiction

4. **Feedback to Oracle Loop**: Corrections can be converted to evaluation criteria for future runs

---

## Integration Points with Recording Software

### Hindenburg Narrator Studio

Potential integration via:
- **Marker import**: Chapter boundaries as session markers
- **Comment import**: Character notes as text comments
- **Proofing enhancement**: Highlight pronunciation words in manuscript view

### Other DAWs (Reaper, Audacity, etc.)

- Export chapter markers as standard formats (CSV, EDL, cue sheets)
- Character notes as PDF/text for reference

### Custom Recording App (Future)

If building a custom recording interface:
- Real-time character context while recording
- Pronunciation popup when approaching flagged word
- Chapter progress tracking
- Voice consistency checking (future AI feature)

---

## Implementation Phases

### Phase 1: Intake Form (Near-term)
- Add pre-analysis questions to CLI and GUI
- Store answers in analysis config
- Use answers to guide/validate AI analysis

### Phase 2: Correction UI (Medium-term)
- Build web-based review interface
- Inline editing for characters, pronunciations, chapters
- Export corrections as JSON

### Phase 3: Prep Package (Medium-term)
- Define portable export format
- Generate DAW-compatible marker files
- Create printable prep materials

### Phase 4: Feedback Loop (Long-term)
- Aggregate corrections across users
- Improve models based on common corrections
- Genre-specific tuning

### Phase 5: Recording Integration (Long-term)
- Partner with or build recording tools
- Real-time prep integration during recording
- Voice consistency AI

---

## Open Questions

1. **Privacy**: How to handle corrections from copyrighted texts?
2. **Offline**: Should prep package work fully offline?
3. **Versioning**: How to handle manuscript revisions mid-prep?
4. **Collaboration**: Multiple narrators on same book (full cast)?
5. **ACX Integration**: Direct submission prep for Audible?

---

## References

- Hindenburg Narrator Studio: https://hindenburg.com/products/narrator-studio/
- ACX Audio Submission Requirements: https://www.acx.com/help/acx-audio-submission-requirements/
- Audiobook Creation Exchange: https://www.acx.com/
