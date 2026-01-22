# User Notes for Oracle Loop

---

## Current Notes (Jan 21, 2026)

**IMPORTANT: Structure detection fix has been applied and verified.**

### What Was Fixed (by external Claude session)

The critical structure detection bug that caused chapters I-III to merge has been fixed. Four commits were made:

1. **`34476d9`** - `profiler.py`: TOC extraction now returns valid 9-entry Roman sequence (was returning 87 due to prose "I" entries breaking sequence validation)

2. **`8f42d66`** - `pipeline.py` + `consensus.py`:
   - TOC-guided bypass: when all 9 TOC chapters are found, skips validation/consensus
   - Hard boundary preservation: explicit chapter markers can't be rejected by LLM

3. **`8d10c2e`** - Stage order numbers added to progress display (cosmetic)

4. **`03435e3`** - Stage order numbers added to oracle monitor (cosmetic)

### Verification Results

Local testing confirmed the fix works:
```
Chapters detected: 9
  1: 'I' at 1400 (5,892 words)
  2: 'II' at 34475 (4,280 words)
  3: 'III' at 58146 (5,734 words)
  ...
  9: 'IX' at 242778 (8,131 words)
```

Key log: `"TOC-guided complete: 9 chapters found - bypassing validation/consensus for reliability"`

### Your Task

1. **Run the analysis** - the code is already fixed and committed
2. **Verify** 9 chapters are detected with proper word counts
3. **Evaluate** the results and update scores
4. **Continue** with remaining issues (character duplicates, pronunciation) if structure is fixed

### DO NOT

- Do not re-investigate the structure detection bug - it's already fixed
- Do not modify `profiler.py`, `pipeline.py`, or `consensus.py` unless evaluation shows new issues
- The previous analysis run (killed at 31 minutes) was using OLD code before the fix

See EVALUATION_STATE.md "Attempt 11" section for full details.
