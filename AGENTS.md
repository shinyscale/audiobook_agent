# Audiobook Agent - Operational Guide

This guide provides operational commands and codebase navigation for the autonomous improvement loop.

## Running the Analysis Pipeline

### Basic Commands

```bash
# Full analysis on a text file with HTML output
audiobook-prep analyze Test_Texts/gatsby.txt --html output/gatsby/report.html --output output/gatsby/analysis.json

# With specific models per agent
audiobook-prep analyze Test_Texts/gatsby.txt \
    --structure-model qwen2.5:14b \
    --character-model qwen2.5:32b \
    --summary-model qwen2.5:32b \
    --pronunciation-model qwen2.5:14b \
    --html output/gatsby/report.html

# Set default model for all agents
audiobook-prep analyze Test_Texts/gatsby.txt --llm-model qwen2.5:32b --html output/gatsby/report.html

# Adjust minimum character mentions threshold
audiobook-prep analyze Test_Texts/gatsby.txt --min-mentions 3 --html output/gatsby/report.html
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output FILE` | JSON output path | `{input_stem}.analysis.json` |
| `--html FILE` | HTML report path | None |
| `--tui` | Open interactive TUI after analysis | False |
| `--wpm N` | Words per minute for duration estimates | 150 |
| `--min-mentions N` | Minimum character mentions to include | 2 |
| `--llm-model MODEL` | Default model for all agents | System default |
| `--structure-model MODEL` | Model for chapter detection | Default |
| `--character-model MODEL` | Model for character extraction | Default |
| `--summary-model MODEL` | Model for chapter summaries | Default |
| `--pronunciation-model MODEL` | Model for pronunciation flags | Default |

## Output Locations

```
output/
└── {book_name}/
    ├── report.html          # HTML report for narrator prep
    └── analysis.json        # Full JSON analysis data
```

## Test Texts

Available in `Test_Texts/`:
- `gatsby.txt` - The Great Gatsby (306 KB)
- `Frankenstein_ebook.txt` - Frankenstein (421 KB)
- `East of Eden - East Of Eden.pdf` - East of Eden (1.6 MB)
- `I_Have_No_Mouth_And_I_Must_Scream.pdf` - Ellison short story (325 KB)
- `One Hundred Years of Solitude - One_Hundred_Years_of_Solitude.pdf` - Marquez (1.5 MB)
- `See the Light V-15 11-11-25.docx` - Test document (1.2 MB)

## Key Source Files

### Agent System
| File | Purpose |
|------|---------|
| `src/agents/base.py` | Abstract Agent class with verify/refine methods |
| `src/agents/structure.py` | StructureAgent - chapter detection |
| `src/agents/characters.py` | CharacterAgent - character extraction & aliases |
| `src/agents/summaries.py` | SummaryAgent - chapter summaries |
| `src/agents/pronunciation.py` | PronunciationAgent - pronunciation flags |
| `src/agents/config.py` | OrchestratorConfig, per-agent model settings |
| `src/agents/validation.py` | Upstream validation types |

### Pipeline
| File | Purpose |
|------|---------|
| `src/analyzer.py` | Main orchestrator - runs all agents |
| `src/pipeline/character_extraction/` | Character NER and extraction |
| `src/pipeline/character_profiling/` | Character profile generation |
| `src/pipeline/llm.py` | Unified LLM client (Ollama/OpenAI/Anthropic) |
| `src/pipeline/metrics.py` | Profiling and metrics |

### Entry Points
| File | Purpose |
|------|---------|
| `src/cli.py` | CLI entry point (`audiobook-prep`) |
| `src/gui/desktop.py` | Tkinter GUI |
| `src/gui/tui.py` | Textual-based terminal UI |

### Data Models
| File | Purpose |
|------|---------|
| `src/models.py` | Core Pydantic models (AnalysisResult, Character, etc.) |
| `src/pipeline/character_extraction/models.py` | Character extraction models |
| `src/pipeline/character_profiling/models.py` | Character profiling models |

## Configuration

### Agent Model Recommendations

From `src/agents/config.py`:

```python
RECOMMENDED_AGENT_MODELS = {
    "structure": ["qwen2.5:14b", "qwen2.5:7b", "llama3.2"],
    "characters": ["qwen2.5:32b", "qwen2.5:72b", "llama3.1:70b"],
    "summaries": ["qwen2.5:32b", "qwen2.5:72b", "llama3.1:70b"],
    "pronunciation": ["qwen2.5:14b", "qwen2.5:32b", "llama3.2"],
}
```

### Verification Levels

Agents support three verification levels:
- `STRUCTURAL` - Fast heuristic checks, no LLM
- `SELF_CHECK` - Local LLM validation, book-agnostic
- `ORACLE` - Claude-assisted (used by this improvement loop)

## Common Issues & Fixes

### Ollama Connection
```bash
# Ensure Ollama is running
ollama serve

# Check available models
ollama list

# Pull a model if needed
ollama pull qwen2.5:32b
```

### Out of Memory
- Reduce model size: Use 14b instead of 32b
- Process shorter texts first
- Check GPU memory: `nvidia-smi`

### Slow Analysis
- Full analysis of a novel can take 10-60 minutes
- Use smaller models for faster iteration during development
- Check `output/{book}/pipeline.log` for progress

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific agent tests
pytest tests/test_character_agent.py -v
pytest tests/test_structure_agent.py -v
pytest tests/test_summary_agent.py -v
pytest tests/test_pronunciation_agent.py -v

# Run alias/merging tests
pytest tests/test_alias_merging.py -v
pytest tests/test_coreference.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Loop-Specific Files

| File | Purpose |
|------|---------|
| `oracle-loop.sh` | Bash orchestrator for the improvement loop |
| `PROMPT_analyze.md` | Phase 1 instructions |
| `PROMPT_evaluate.md` | Phase 2 oracle evaluation instructions |
| `PROMPT_fix.md` | Phase 3 fix instructions |
| `manifest.json` | Test text tracking |
| `EVALUATION_STATE.md` | Current state and issues |
| `spec/output_quality.md` | Quality evaluation rubric |
| `logs/` | Iteration logs |
