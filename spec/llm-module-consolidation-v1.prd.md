# PRD: LLM Module Consolidation

**Version:** 1.0
**Status:** Draft
**Priority:** Medium
**Target:** Technical debt reduction and code maintainability

## Executive Summary

The codebase has two LLM modules with overlapping functionality: `src/llm/` (legacy, 4 files, ~2,700 LOC) and `src/pipeline/llm.py` (modern, 1 file, 520 LOC). This duplication creates confusion about which module to use, potential import conflicts, and maintenance burden.

**Proposal:** Consolidate to a single `src/llm/` module that combines the clean API from `pipeline/llm.py` with the useful utilities from the legacy module, while deprecating redundant code.

---

## Problem Statement

### Current State

Two separate LLM modules exist with overlapping purposes:

| Module | Files | LOC | Primary Purpose |
|--------|-------|-----|-----------------|
| `src/llm/` | 4 | ~2,700 | Legacy: config, refiner, prompts, exceptions |
| `src/pipeline/llm.py` | 1 | 520 | Modern: clean LLMClient API |

### Duplication Analysis

**Overlapping Functionality:**

| Feature | `src/llm/` | `src/pipeline/llm.py` |
|---------|------------|----------------------|
| Provider enum | `LLMProvider` in config.py | Literal type in LLMConfig |
| Configuration class | `ModelConfig` (hardware-focused) | `LLMConfig` (API-focused) |
| API calls | `LLMRefiner._query()` | `LLMClient.query()` |
| JSON parsing | In refiner.py | `LLMClient.query_json()` |
| Connection testing | `test_connection()` | `LLMClient.test_connection()` |
| Thinking tag cleanup | Not present | `_clean_thinking_tags()` |

**Unique to `src/llm/`:**
- `config.py`: Model recommendations, VRAM calculations, Ollama model management (pull/delete/info)
- `prompts.py`: Prompt templates (`PromptConfig`, `DEFAULT_PROMPTS`)
- `exceptions.py`: Custom exceptions (`ChapterDetectionError`, etc.)
- `refiner.py`: Legacy batch refinement methods (likely unused)

**Unique to `src/pipeline/llm.py`:**
- Clean `LLMClient` class with lazy initialization
- `LLMResponse` dataclass with token tracking
- Thinking tag cleanup for reasoning models (DeepSeek-R1, QwQ, Qwen3)
- JSON repair utilities
- Health check functionality
- Metrics integration

### Current Usage

**`src/pipeline/llm.py` is the primary API** - used by 20+ files:
```
src/pipeline/chapter_detection/    (5 files)
src/pipeline/character_extraction/ (4 files)
src/pipeline/character_profiling/  (9 files)
src/pipeline/chapter_summary/      (2 files)
src/pipeline/pronunciation_guide/  (2 files)
src/pipeline/overview/             (1 file)
src/pipeline/metrics.py            (1 file)
```

**`src/llm/` has limited usage:**
- `src/gui/desktop.py` → imports `config.py` (model management) and `prompts.py`
- `src/analyzer.py` → imports `prompts.py` for `PromptConfig`

### Problems

1. **Confusion**: Developers don't know which module to use
2. **Inconsistency**: Two different ways to make LLM calls
3. **Maintenance burden**: Bug fixes may need to be applied in two places
4. **Import complexity**: `from ..llm` could resolve to either module depending on context
5. **Dead code**: `refiner.py` (1,654 LOC) appears largely unused

---

## Proposed Solution

### Target Architecture

Consolidate into a single `src/llm/` module with clear submodules:

```
src/llm/
├── __init__.py          # Public API exports
├── client.py            # LLMClient, LLMConfig, LLMResponse (from pipeline/llm.py)
├── models.py            # Model recommendations, hardware detection (from config.py)
├── ollama.py            # Ollama-specific utilities (from config.py)
├── prompts.py           # Prompt templates (keep existing)
└── exceptions.py        # Custom exceptions (keep existing)
```

### Migration Strategy

**Phase 1: Create new structure**
- Move `pipeline/llm.py` → `llm/client.py`
- Split `llm/config.py` into `llm/models.py` and `llm/ollama.py`
- Keep `llm/prompts.py` and `llm/exceptions.py` as-is
- Update `llm/__init__.py` to export public API

**Phase 2: Update imports**
- Update all `from ..llm import` to `from src.llm import`
- Update `from .llm.config import` to `from .llm.models import` or `from .llm.ollama import`

**Phase 3: Deprecate refiner.py**
- Mark `LLMRefiner` as deprecated
- Remove after one release cycle

**Phase 4: Remove pipeline/llm.py**
- Delete `src/pipeline/llm.py`
- All LLM functionality now in `src/llm/`

---

## Features and User Stories

### Feature 1: Unified LLM Client API

**Priority:** CRITICAL
**Rationale:** Single source of truth for LLM interactions.

**Current behavior:** Two ways to make LLM calls (`LLMClient` vs `LLMRefiner`).

**Proposed behavior:** Single `LLMClient` class as the only way to interact with LLMs.

**User Stories:**

```json
{
  "category": "functional",
  "description": "All pipeline modules use the consolidated LLMClient",
  "steps": [
    "Search codebase for LLM client imports",
    "Verify all imports resolve to src/llm/client.py (directly or via shim)",
    "Confirm all LLM calls use LLMClient.query() or query_json()"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "LLMClient supports all three providers",
  "steps": [
    "Create client with LLMConfig.ollama()",
    "Create client with LLMConfig.openai()",
    "Create client with LLMConfig.anthropic()",
    "Verify all three can make successful queries"
  ],
  "passes": true
}
```

**Implementation:**

```python
# src/llm/__init__.py
from .client import LLMClient, LLMConfig, LLMResponse, create_client
from .models import ModelConfig, RECOMMENDED_MODELS, get_model_for_hardware
from .ollama import (
    detect_available_models,
    pull_ollama_model,
    delete_ollama_model,
    get_ollama_model_info,
)
from .prompts import PromptConfig, DEFAULT_PROMPTS
from .exceptions import (
    ChapterDetectionError,
    CharacterProfileError,
    ChapterSummaryError,
)

__all__ = [
    # Client API
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "create_client",
    # Model management
    "ModelConfig",
    "RECOMMENDED_MODELS",
    "get_model_for_hardware",
    # Ollama utilities
    "detect_available_models",
    "pull_ollama_model",
    "delete_ollama_model",
    "get_ollama_model_info",
    # Prompts
    "PromptConfig",
    "DEFAULT_PROMPTS",
    # Exceptions
    "ChapterDetectionError",
    "CharacterProfileError",
    "ChapterSummaryError",
]
```

**Affected files:**
- New: `src/llm/client.py` (moved from `src/pipeline/llm.py`)
- Modified: `src/llm/__init__.py`
- Deleted: `src/pipeline/llm.py` (after migration)

---

### Feature 2: Separated Model Management

**Priority:** HIGH
**Rationale:** Model recommendations and Ollama utilities are distinct concerns from the client API.

**Current behavior:** Model management mixed with provider configuration in `config.py`.

**Proposed behavior:** Separate `models.py` for recommendations, `ollama.py` for Ollama-specific operations.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Model recommendations are accessible from llm.models",
  "steps": [
    "Import from src.llm.models",
    "Access RECOMMENDED_MODELS list",
    "Call get_model_for_hardware(vram_gb=48)",
    "Verify appropriate model is returned"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "Ollama operations are accessible from llm.ollama",
  "steps": [
    "Import from src.llm.ollama",
    "Call pull_ollama_model()",
    "Call get_ollama_model_info()",
    "Call delete_ollama_model()",
    "Verify all operations work correctly"
  ],
  "passes": true
}
```

**Implementation:**

```python
# src/llm/models.py
"""Model recommendations and hardware detection."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelConfig:
    """Configuration for a local LLM model."""
    name: str
    description: str
    min_vram_gb: float
    ollama_name: str
    active_params: str
    context_length: int = 8192
    recommended_for: list[str] = None

RECOMMENDED_MODELS = [...]  # Move from config.py

def get_model_for_hardware(vram_gb: float, use_case: str = "general") -> ModelConfig:
    """Select the best model for available VRAM and use case."""
    ...  # Move from config.py
```

```python
# src/llm/ollama.py
"""Ollama-specific utilities for model management."""

from typing import Optional, Callable

def detect_available_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Fetch available models from Ollama."""
    ...  # Move from config.py

def pull_ollama_model(
    model: str,
    base_url: str = "http://localhost:11434",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> tuple[bool, str]:
    """Pull a model from the Ollama library."""
    ...  # Move from config.py

def delete_ollama_model(model: str, base_url: str = "http://localhost:11434") -> tuple[bool, str]:
    """Delete a model from Ollama."""
    ...  # Move from config.py

def get_ollama_model_info(model: str, base_url: str = "http://localhost:11434") -> Optional[dict]:
    """Get detailed information about an Ollama model."""
    ...  # Move from config.py
```

**Affected files:**
- New: `src/llm/models.py`
- New: `src/llm/ollama.py`
- Modified: `src/llm/config.py` → deleted after migration
- Modified: `src/gui/desktop.py` (update imports)

---

### Feature 3: Deprecate and Remove LLMRefiner

**Priority:** MEDIUM
**Rationale:** `LLMRefiner` is a 1,654 LOC class that duplicates `LLMClient` functionality.

**Current behavior:** `LLMRefiner` exists but is not used by any pipeline code.

**Proposed behavior:** Deprecate, then remove `LLMRefiner` entirely.

**User Stories:**

```json
{
  "category": "functional",
  "description": "LLMRefiner has been removed (was unused dead code)",
  "steps": [
    "Verify refiner.py has been deleted from src/llm/",
    "Verify no exports of LLMRefiner in src/llm/__init__.py",
    "Verify no production code references LLMRefiner"
  ],
  "passes": true
}
```

```json
{
  "category": "functional",
  "description": "No production code uses LLMRefiner",
  "steps": [
    "Search codebase for 'LLMRefiner' usage",
    "Verify no code references LLMRefiner (class has been deleted)",
    "Confirm all active pipelines use LLMClient"
  ],
  "passes": true
}
```

**Implementation:**

```python
# src/llm/refiner.py (temporary, during deprecation)
import warnings
from .client import LLMClient, LLMConfig

class LLMRefiner:
    """
    DEPRECATED: Use LLMClient instead.

    This class will be removed in a future release.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "LLMRefiner is deprecated. Use LLMClient from src.llm instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # ... existing implementation for backward compatibility
```

**Affected files:**
- Modified: `src/llm/refiner.py` (add deprecation warning)
- Deleted: `src/llm/refiner.py` (after deprecation period)

---

### Feature 4: Clean Import Paths

**Priority:** HIGH
**Rationale:** Consistent imports reduce cognitive load and prevent errors.

**Current behavior:** Mixed import patterns across codebase.

**Proposed behavior:** Single, consistent import pattern for all LLM functionality.

**User Stories:**

```json
{
  "category": "functional",
  "description": "All LLM imports work via consistent pattern or backward-compatible shims",
  "steps": [
    "Verify new imports from src.llm work",
    "Verify backward-compat imports from src.pipeline.llm work via shim",
    "Verify backward-compat imports from src.llm.config work via shim",
    "All 444 tests pass"
  ],
  "passes": true
}
```

**Standard import patterns:**

```python
# For client functionality
from src.llm import LLMClient, LLMConfig, LLMResponse, create_client

# For model recommendations
from src.llm import ModelConfig, RECOMMENDED_MODELS, get_model_for_hardware

# For Ollama management
from src.llm import detect_available_models, pull_ollama_model

# For prompts
from src.llm import PromptConfig, DEFAULT_PROMPTS

# For exceptions
from src.llm import ChapterDetectionError, CharacterProfileError
```

**Affected files:**
- All files in `src/pipeline/` that import from `..llm`
- `src/gui/desktop.py`
- `src/analyzer.py`

---

## Architecture

### Before (Current State)

```
src/
├── llm/                          # Legacy module
│   ├── __init__.py
│   ├── config.py                 # ModelConfig, LLMProvider, Ollama utils, VRAM detection
│   ├── refiner.py                # LLMRefiner class (1,654 LOC) - UNUSED
│   ├── prompts.py                # PromptConfig, DEFAULT_PROMPTS
│   └── exceptions.py             # Custom exceptions
│
└── pipeline/
    └── llm.py                    # LLMClient, LLMConfig, LLMResponse (ACTIVE)
```

**Problems:**
- `LLMClient` (active) buried in pipeline/
- `LLMRefiner` (legacy) at top level
- Model management mixed with configuration
- Inconsistent import paths

### After (Proposed State)

```
src/
└── llm/                          # Consolidated module
    ├── __init__.py               # Public API exports
    ├── client.py                 # LLMClient, LLMConfig, LLMResponse (from pipeline/llm.py)
    ├── models.py                 # ModelConfig, RECOMMENDED_MODELS, hardware detection
    ├── ollama.py                 # Ollama-specific: detect, pull, delete, info
    ├── prompts.py                # PromptConfig, DEFAULT_PROMPTS (unchanged)
    └── exceptions.py             # Custom exceptions (unchanged)
```

**Benefits:**
- Single source of truth for LLM interactions
- Clear separation of concerns (client, models, Ollama, prompts)
- Consistent import paths
- No dead code

---

## Implementation Phases

### Phase 1: Create New Structure (No Breaking Changes)

**Scope:** Create new files, set up exports
**Risk:** Low - additive only
**Deliverables:**
- Create `src/llm/client.py` (copy from `src/pipeline/llm.py`)
- Create `src/llm/models.py` (extract from `config.py`)
- Create `src/llm/ollama.py` (extract from `config.py`)
- Update `src/llm/__init__.py` with new exports
- Both old and new paths work during migration

### Phase 2: Migrate Pipeline Imports

**Scope:** Update all pipeline files to use new import paths
**Risk:** Low - automated refactoring
**Deliverables:**
- Update 20+ pipeline files
- Run full test suite
- Verify no regressions

### Phase 3: Migrate GUI/Analyzer Imports

**Scope:** Update GUI and analyzer imports
**Risk:** Low - limited scope
**Deliverables:**
- Update `src/gui/desktop.py`
- Update `src/analyzer.py`
- Test GUI functionality
- Test CLI functionality

### Phase 4: Deprecate Legacy Code

**Scope:** Add deprecation warnings, remove dead code
**Risk:** Medium - potential for missed usage
**Deliverables:**
- Add deprecation warning to `LLMRefiner`
- Delete `src/pipeline/llm.py`
- Delete old `src/llm/config.py`
- Update documentation

### Phase 5: Remove Deprecated Code (Future Release)

**Scope:** Remove `LLMRefiner` entirely
**Risk:** Low - after deprecation period
**Deliverables:**
- Delete `src/llm/refiner.py`
- Final cleanup

---

## Validation Strategy

### Test Cases

| Test Case | Expected Result | Validates |
|-----------|-----------------|-----------|
| Import LLMClient from src.llm | Success | Feature 1 |
| Import LLMConfig from src.llm | Success | Feature 1 |
| LLMClient.query() works | Returns LLMResponse | Feature 1 |
| LLMClient.query_json() works | Returns parsed dict | Feature 1 |
| Import ModelConfig from src.llm | Success | Feature 2 |
| get_model_for_hardware() works | Returns ModelConfig | Feature 2 |
| Import pull_ollama_model from src.llm | Success | Feature 2 |
| LLMRefiner raises DeprecationWarning | Warning raised | Feature 3 |
| No imports from src.pipeline.llm | Zero matches | Feature 4 |
| Full test suite passes | All green | All |

### Success Metrics

1. **Code Reduction:** ~1,600 LOC removed (refiner.py)
2. **Import Consistency:** 100% of LLM imports use `from src.llm import`
3. **Test Coverage:** All existing tests pass
4. **No Regressions:** All pipelines produce identical output

### Regression Tests

- Run full analysis on test corpus before/after
- Compare JSON output for identical results
- Verify token usage metrics unchanged

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed import during migration | Medium | Low | Automated grep + test suite |
| Breaking change in API | Low | High | Phase 1 maintains both paths |
| GUI breakage | Medium | Medium | Manual GUI testing |
| Performance regression | Low | Medium | Benchmark before/after |

---

## Files to Modify

### New Files
- `src/llm/client.py` (from `src/pipeline/llm.py`)
- `src/llm/models.py` (from `src/llm/config.py`)
- `src/llm/ollama.py` (from `src/llm/config.py`)

### Modified Files
- `src/llm/__init__.py` - new exports
- `src/gui/desktop.py` - update imports
- `src/analyzer.py` - update imports
- All files in `src/pipeline/` importing from `..llm` (~20 files)

### Deleted Files
- `src/pipeline/llm.py` (after Phase 2)
- `src/llm/config.py` (after Phase 3)
- `src/llm/refiner.py` (after Phase 5)

---

## Open Questions

1. **Timing of refiner.py removal:** Wait one release cycle or remove immediately?
   - *Recommendation:* Keep for one release with deprecation warning

2. **Should prompts.py move to a different location?**
   - *Recommendation:* Keep in `src/llm/` - prompts are LLM-related

3. **Should exceptions.py be consolidated with other exceptions?**
   - *Recommendation:* Keep in `src/llm/` for now - they're LLM-specific

---

## References

- Current LLM client: `src/pipeline/llm.py`
- Legacy config: `src/llm/config.py`
- Legacy refiner: `src/llm/refiner.py`
- CLAUDE.md architecture documentation
