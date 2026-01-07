# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Audiobook Prep** is an AI-powered manuscript analysis tool for audiobook narrators. It analyzes books to extract structure (chapters), characters with aliases, pronunciation guidance, and generates summaries. The tool is local-first and uses a multi-agent architecture with support for multiple LLM providers (Ollama, OpenAI, Anthropic).

## Common Commands

```bash
# Install (editable mode with dev dependencies)
pip install -e ".[dev]"
python -m spacy download en_core_web_lg

# Run analysis via CLI
audiobook-prep analyze book.pdf
audiobook-prep analyze book.pdf --output result.json --html report.html
audiobook-prep analyze book.pdf --tui  # Opens interactive TUI after analysis

# Run GUI
./launch_gui.sh  # or: python -m src.gui.desktop

# Run tests
pytest  # Uses tests/ directory per pyproject.toml

# Code formatting
black src/
ruff check src/
```

## Architecture

### Multi-Agent Pipeline

The system uses specialized agents that wrap consensus-based pipelines:

```
Input File → Ingestion → StructureAgent → CharacterAgent → SummaryAgent → PronunciationAgent → Export
                              ↓                ↓                ↓                ↓
                        ChapterMap      CharacterMap    ChapterSummaries   PronunciationMap
```

Each agent:
- Wraps a pipeline with multiple "proposers" that generate candidates
- Uses consensus to select best results
- Implements self-verification with confidence scoring
- Can use a different LLM model (configured via `OrchestratorConfig`)

### Key Modules

| Module | Purpose |
|--------|---------|
| `src/analyzer.py` | Main orchestrator - runs all agents sequentially |
| `src/agents/` | Agent infrastructure (base.py, config.py) and implementations |
| `src/pipeline/` | Analysis pipelines (chapter_detection, character_extraction, etc.) |
| `src/pipeline/llm.py` | Unified LLM client for Ollama/OpenAI/Anthropic |
| `src/ingestion/` | Document parsers (PDF, EPUB, DOCX, TXT) |
| `src/gui/desktop.py` | Tkinter GUI with model management |
| `src/gui/tui.py` | Textual-based terminal UI for result browsing |
| `src/models.py` | Pydantic data models (AnalysisResult, Character, etc.) |

### Agent System

Agents are defined in `src/agents/` and follow this pattern:

```python
class Agent(ABC):
    @property
    def name(self) -> str: ...
    def run(self, context: AgentContext) -> AgentResult: ...
    def verify(self, result: AgentResult) -> VerificationResult: ...
```

Multi-model configuration allows different models per agent:
```python
from src.agents.config import OrchestratorConfig, AgentConfig, create_optimized_config

# Auto-optimize based on available models
config = create_optimized_config(available_models=["qwen2.5:72b", "qwen2.5:7b"])

# Or manual per-agent configuration
config = OrchestratorConfig(default_model="llama3.2")
config.set_agent_config("characters", AgentConfig(model="qwen2.5:72b"))
```

See `src/agents/config.py` for `RECOMMENDED_AGENT_MODELS` with optimal settings per agent type.

### LLM Integration

`LLMClient` in `src/pipeline/llm.py` provides a unified interface:
```python
client = LLMClient(LLMConfig.ollama(model="llama3.2"))
client = LLMClient(LLMConfig.openai(model="gpt-4o-mini"))
client = LLMClient(LLMConfig.anthropic(model="claude-3-5-sonnet-20241022"))
```

Features automatic thinking tag stripping for reasoning models (DeepSeek-R1, QwQ).

## Data Flow

1. **Ingestion**: Extract text from PDF/EPUB/DOCX/TXT via `src/ingestion/`
2. **Refinement**: Normalize text, fix spacing/encoding via `src/ingestion/refine.py`
3. **Structure**: StructureAgent detects chapters using regex + LLM consensus
4. **Characters**: CharacterAgent extracts names via NER + LLM, resolves aliases
5. **Summaries**: SummaryAgent generates per-chapter summaries
6. **Pronunciation**: PronunciationAgent flags proper nouns, foreign words, homographs
7. **Export**: JSON output, HTML report, or interactive TUI

## Important Files

- `docs/AGENT_ARCHITECTURE.md` - Detailed architecture documentation and roadmap
- `src/agents/config.py` - Agent configuration, model recommendations
- `src/pipeline/metrics.py` - Profiling and metrics collection
- Entry points defined in `pyproject.toml`: `audiobook-prep` (CLI), `audiobook-prep-gui` (GUI)

## Coding Standards

### No Novel-Specific Hardcoding

NEVER include examples from specific novels in prompts or validation logic. The system must work for ANY novel without bias toward specific works.

**Examples of what NOT to do:**
- ❌ "Tom Buchanan and Daisy Buchanan are DIFFERENT people (husband and wife)"
- ❌ "Jay Gatsby should be merged with Mr. Gatsby"

**Use generic guidance instead:**
- ✅ "Characters who share a last name but have different first names are typically different people (e.g., spouses, siblings)"
- ✅ "A full name and a first-name-only reference may be the same person"

---

## Development Notes

- Python 3.10+ required
- spaCy `en_core_web_lg` model required for NER
- At least one LLM provider (Ollama, OpenAI, or Anthropic) required for LLM features
- Current branch: `feature/agent-infrastructure` (Phase 3 complete, Phase 4 planned)
- `Output/` directory is gitignored but created during analysis
