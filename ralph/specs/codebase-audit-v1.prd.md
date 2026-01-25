# PRD: Codebase Audit and Cleanup

**Status:** Pending
**Created:** 2026-01-24
**Priority:** Medium (execute after oracle loop stabilizes)

## Assessment Summary

After 15+ oracle loop iterations, the codebase has accumulated technical debt:

| Category | Issue Count | Priority |
|----------|-------------|----------|
| Dead code | 4 major items | HIGH |
| V1/V2 confusion | 6 files affected | MEDIUM |
| Code duplication | 7+ similarity calcs, 8+ merge methods | MEDIUM |
| Commented blocks | ~50 lines | LOW |

**Codebase Health Score: 7/10** - Functional but needs cleanup.

---

## Phase 1: Dead Code Removal (Low Risk)

### 1.1 Remove Unused Constants
**File:** `src/pipeline/character_extraction/constants.py`
- Delete `NICKNAME_MAP` dictionary (~40 lines) - never imported
- Delete `get_nickname_variants()` function - unused
- Delete `are_potential_nicknames()` function - unused

### 1.2 Delete Backup File
**File:** `src/pipeline/character_extraction_v2/main_cast.py.backup`
- Delete this stale checkpoint (git has the history)

### 1.3 Delete Legacy Analysis Module
**Directory:** `src/analysis/`
- Contains old V1 modules: `characters.py`, `structure.py`, `pronunciation.py`
- Only imported in oracle-loop/ and tests/, not active codebase
- **Decision:** Delete entirely - git has history

### 1.4 Remove Commented Dead Code
**File:** `src/analyzer.py` lines 902-923
- 16-line "OLD CODE" commented block for narrator detection
- Already replaced by V2 narrator pipeline

---

## Phase 2: V1/V2 Consolidation (Medium Risk)

### 2.1 Rename V2 Agent to Primary
```
src/agents/characters_v2.py → src/agents/characters.py
CharacterAgentV2 → CharacterAgent
```
**Imports to update:** ~8 files

### 2.2 Move Prompts from V1 to V2
Move from `src/pipeline/character_extraction/prompts.py`:
- `COMPETITOR_CONFIGS`
- `get_merge_prompts()`

To: `src/pipeline/character_extraction_v2/prompts.py` (new file)

### 2.3 Clean Up V1 Directory
After moving prompts, `src/pipeline/character_extraction/` becomes:
- `models.py` - Shared data models (keep)
- `constants.py` - After cleanup, may be empty (delete if empty)
- `prompts.py` - Delete after moving to V2
- `__init__.py` - Update exports

Consider renaming directory to `character_models/` to clarify its role.

---

## Phase 3: Reduce Duplication (Medium Risk)

### 3.1 Extract Similarity Utility
Create: `src/utils/similarity.py`
```python
from difflib import SequenceMatcher

DEFAULT_SIMILARITY_THRESHOLD = 0.85

def string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def names_similar(name1: str, name2: str, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> bool:
    return string_similarity(name1, name2) >= threshold
```

Replace 7+ duplicate SequenceMatcher usages in:
- `src/agents/characters_v2.py` (7 locations)
- `src/pipeline/character_profiling/handoff_detector.py`
- `src/pipeline/chapter_detection/validator.py`

### 3.2 Consolidate Merge Helpers (Optional)
The 8 merge methods in `characters_v2.py` share patterns. Could extract:
- `build_merge_groups()`
- `apply_merge_groups()`
- `track_merge_for_removal()`

**Risk:** Higher complexity, may not be worth it for oracle loop stability.

---

## Phase 4: Fix TODOs (Low Priority)

### 4.1 Document Parallel Execution Status
**File:** `src/analyzer.py` line 862
- Parallel execution disabled with TODO
- Add proper documentation or remove dead path entirely

### 4.2 Clarify character_profiling Module Role
- Document whether it's complementary to V2 or legacy
- Currently used for F1 (Summary-driven merges) post-extraction

---

## Execution Order

| Step | Description | Risk |
|------|-------------|------|
| 1 | Delete backup file | None |
| 2 | Remove unused constants | Low |
| 3 | Remove commented dead code | Low |
| 4 | Extract similarity utility | Low |
| 5 | Rename characters_v2 → characters | Medium |
| 6 | Move prompts V1 → V2 | Medium |
| 7 | Delete legacy analysis/ | Medium |

---

## Verification

After cleanup:
1. `pytest tests/ -v` - All tests pass
2. `python -c "from src.agents.characters import CharacterAgent"` - Import works
3. `grep -r "characters_v2" src/` - No stale references
4. `ruff check src/` - No new linting errors

---

## Pre-Execution Checklist

- [ ] Oracle loop iteration complete or paused
- [ ] All tests passing
- [ ] No uncommitted changes
