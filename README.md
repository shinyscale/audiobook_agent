# Audiobook Prep

AI-powered manuscript analysis for audiobook narrators. A standalone, local-first tool that helps narrators prepare for recording sessions.

## Features

**Phase 1: Document Ingestion & Structure Analysis**
- Supports PDF, DOCX, EPUB, and TXT formats
- Automatic chapter/section detection
- Scene break identification
- Journal entries, letters, and other structural elements
- Word counts and duration estimates per section

**Phase 2: Character & Pronunciation Intelligence**
- Named Entity Recognition for character extraction
- Automatic alias clustering ("Elizabeth" / "Lizzy" / "Mrs. Darcy")
- Character description extraction
- Pronunciation flagging for:
  - Proper nouns and character names
  - Foreign words and phrases
  - Homographs (read/read, lead/lead)
  - Unusual or uncommon words
- CMU Dictionary integration for known pronunciations

## Installation

```bash
# Clone the repository
git clone https://github.com/yourname/audiobook-prep.git
cd audiobook-prep

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Download spaCy model
python -m spacy download en_core_web_lg
```

## Usage

### Command Line

```bash
# Full analysis
audiobook-prep analyze book.pdf

# With custom output path
audiobook-prep analyze manuscript.epub --output prep.json

# Adjust narration speed estimate
audiobook-prep analyze book.docx --wpm 160

# Quick summary only
audiobook-prep summary book.txt
```

### Python API

```python
from src import analyze_book

# Analyze a book
result = analyze_book("path/to/book.pdf")

# Access results
print(f"Title: {result.metadata.title}")
print(f"Duration: {result.metadata.estimated_total_duration_minutes:.0f} minutes")

# Get characters
for char in result.characters[:5]:
    print(f"- {char.canonical_name}: {char.mention_count} mentions")

# Get pronunciation flags
for pron in result.pronunciations[:10]:
    print(f"- {pron.word}: {pron.flag_reason.value}")

# Export to JSON
from src.analyzer import AudiobookAnalyzer
analyzer = AudiobookAnalyzer()
analyzer.analyze_to_json("book.pdf", "analysis.json")
```

## Output Format

Analysis results include:

```json
{
  "metadata": {
    "title": "Pride and Prejudice",
    "author": "Jane Austen",
    "total_word_count": 122189,
    "estimated_total_duration_minutes": 814.59
  },
  "structure": [
    {
      "type": "chapter",
      "title": "Chapter 1",
      "word_count": 1523,
      "estimated_duration_minutes": 10.15,
      "characters_present": ["char_001", "char_002"]
    }
  ],
  "characters": [
    {
      "id": "char_001",
      "canonical_name": "Elizabeth Bennet",
      "aliases": ["Elizabeth", "Lizzy", "Eliza"],
      "descriptions": ["a lively, playful disposition"],
      "mention_count": 597
    }
  ],
  "pronunciations": [
    {
      "word": "Bingley",
      "flag_reason": "proper_noun",
      "occurrences": 234,
      "context_examples": ["...Mr. Bingley had soon made himself..."]
    }
  ]
}
```

## Hardware Requirements

**Minimum (Phase 1-2):**
- 8GB RAM
- Any modern CPU
- No GPU required

**Recommended (with LLM refinement):**
- 16GB+ RAM
- NVIDIA GPU with 8GB+ VRAM for faster processing

**Development hardware:**
- RTX 6000 (96GB VRAM) for large model experimentation
- Strix Halo (128GB unified memory) for edge case testing

## Roadmap

- [x] Phase 1: Document ingestion and structure analysis
- [x] Phase 2: Character extraction and pronunciation flagging
- [ ] Phase 3: Recording session interface with live transcription
- [ ] Phase 4: Post-production QC (transcription diff, error detection)
- [ ] Phase 5: Distribution-ready standalone application

## License

MIT License - see LICENSE file for details.
