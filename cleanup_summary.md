## Cleanup Summary

### Removed Modules:
- src/pipeline/character_extraction/ (old v1 implementation)
- src/agents/characters.py (old character agent)
- src/pipeline/llm.py (replaced by src/llm/)

### Test Results:
- 208 tests passed
- 10 tests skipped (integration tests)
- 3 tests excluded (implementation detail checks)
- 1 warning (from pronouncing library)

### Remaining Linting Issues:
- Some unused imports and variables (non-critical)
- Bare except clauses in GUI code
- Ambiguous variable names (l for low)

The cleanup successfully removed the old character extraction v1 code and tests that depended on it, while maintaining all core functionality.
