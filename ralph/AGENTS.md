# Ralph Operational Learnings

This file contains operational knowledge specific to the audiobook_agent codebase. Read this at the start of every iteration.

## Project Structure

```
audiobook_agent/
├── src/
│   ├── analyzer.py          # Main orchestrator
│   ├── models.py            # Pydantic data models
│   ├── agents/              # Agent infrastructure
│   │   ├── base.py          # Base Agent class
│   │   ├── config.py        # OrchestratorConfig, AgentConfig
│   │   ├── structure.py     # StructureAgent
│   │   ├── characters.py    # CharacterAgent
│   │   ├── summary.py       # SummaryAgent
│   │   └── pronunciation.py # PronunciationAgent
│   ├── pipeline/            # Analysis pipelines
│   │   ├── llm.py           # LLMClient (Ollama/OpenAI/Anthropic)
│   │   ├── character_extraction_v2.py  # V2 character pipeline
│   │   ├── character_profiling_v2.py   # V2 profiling pipeline
│   │   └── ...
│   ├── ingestion/           # Document parsers
│   └── gui/                 # Desktop and TUI interfaces
├── tests/                   # pytest tests
├── spec/                    # PRD specifications
├── oracle-loop/             # Quality testing loop
└── ralph/                   # This implementation loop
```

## Key Files

| Task Type | Key Files |
|-----------|-----------|
| Character extraction | `src/pipeline/character_extraction_v2.py`, `src/agents/characters.py` |
| Character profiling | `src/pipeline/character_profiling_v2.py` |
| Chapter detection | `src/pipeline/chapter_detection.py`, `src/agents/structure.py` |
| LLM integration | `src/pipeline/llm.py` |
| Data models | `src/models.py` |
| Configuration | `src/agents/config.py` |

## V2 Pipeline Architecture

The V2 pipelines use a consensus-based approach:

1. Multiple "proposers" generate candidate results
2. Results are merged/reconciled
3. Confidence scoring validates output
4. Self-verification catches errors

When modifying V2 pipelines:
- Look for `*_v2.py` files
- Check the proposer/consensus pattern
- Maintain backward compatibility with V1 interfaces

## Common Commands

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_character_extraction.py -v

# Lint check
ruff check src/

# Format code
black src/

# Run full analysis (for manual testing)
audiobook-prep analyze sample.pdf --output test.json
```

## Testing Notes

- Tests use pytest with fixtures in `conftest.py`
- Mock LLM responses for unit tests
- Integration tests may need real LLM (skip in CI)
- Character extraction tests often use sample text fixtures

## Common Patterns

### Adding a new pipeline feature:
1. Update the relevant `*_v2.py` pipeline
2. Update `src/models.py` if new data structures needed
3. Update the corresponding agent in `src/agents/`
4. Add tests in `tests/`

### Fixing character extraction bugs:
1. Check `character_extraction_v2.py` for extraction logic
2. Check `character_profiling_v2.py` for alias/merge logic
3. LLM prompts are embedded in pipeline files
4. Validation rules affect confidence scoring

### LLM prompt changes:
1. Prompts are in pipeline files, not separate templates
2. Test with multiple models (different response formats)
3. Handle thinking tags for reasoning models (DeepSeek-R1, QwQ)

## Known Issues / Gotchas

- Always use generic guidance in prompts, never novel-specific examples
- spaCy NER can miss character names; LLM extraction supplements it
- Large books may need chunking for LLM context limits
- Ollama models need to be pulled before use

## Git Conventions

- Commit message format: `Ralph: {description}`
- Keep commits atomic (one logical change)
- Don't commit `.env` or API keys
- `Output/` directory is gitignored

---

*Last updated by Ralph automation*
