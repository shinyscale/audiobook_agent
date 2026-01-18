# Revert Plan: Return to Pre-Oracle-Loop State

## Target Commit
```
f1bca9f Add analysis start/end timestamps to overview page
Date: Sun Jan 11 20:19:47 2026
```

This is the last commit before the oracle loop infrastructure was added.

## What Will Be Reverted

### Source Code (REVERT)
All changes to `src/` since f1bca9f will be reverted. This includes:

**Character Extraction (9 "fix" commits that caused regressions):**
- d501086 Fix: Prioritize relational descriptor pairing
- 432f7c1 Fix: Add comprehensive diagnostic logging
- ba1215a Fix: Allow relational descriptor merges
- 4e3cf44 Fix: Enhance alias candidate pair generation
- cd860e0 Fix: Add critical early validation to block family member merges
- 9bf7131 Debug: Add comprehensive diagnostic logging
- 31233a9 Fix: Filter ambiguous last-name-only entries
- 9a29656 Fix: Prevent family member merging
- 9bde9e5 Fix: Prioritize hard boundary titles

**Other Source Changes:**
- LLM module consolidation (232dbfc) - may want to preserve this
- Plot summary hallucination fixes (a737c07) - may want to preserve this
- First-person narrator handling (38b4950) - may want to preserve this

### Files to Preserve (DO NOT REVERT)
These files were created by the loop but contain useful documentation:

```
AGENTS.md                    - Useful codebase documentation
spec/output_quality.md       - Evaluation rubric (useful)
spec/complete/*.md           - Completed feature PRDs
spec/*.prd.json             - Feature specifications
```

### Files to Delete (Created by Loop, Not Useful in Current Form)
```
EVALUATION_STATE.md          - Will recreate with proper structure
PROMPT_analyze.md            - Will recreate with fixes
PROMPT_evaluate.md           - Will recreate with fixes
PROMPT_fix.md                - Will recreate with fixes
manifest.json                - Will recreate with proper structure
oracle-loop.sh               - Will recreate with regression protection
```

### Output Files (Safe to Delete)
```
output/gatsby/               - Can regenerate
output/frankenstein/         - Can regenerate
logs/iteration_*.log         - Historical, can archive or delete
```

## Revert Strategy

### Option A: Hard Revert (Recommended)
Reset source code to known-good state, preserve documentation.

```bash
# 1. Archive current state for reference
git stash push -m "Pre-revert state for reference"
# Or: git branch archive/oracle-loop-attempt-1

# 2. Create a new branch from the clean state
git checkout f1bca9f
git checkout -b main-clean

# 3. Cherry-pick useful commits (if any)
# Review each and decide:
# git cherry-pick 232dbfc  # LLM module consolidation - maybe
# git cherry-pick a737c07  # Plot summary fixes - maybe

# 4. Copy over preserved documentation
git checkout main -- AGENTS.md
git checkout main -- spec/output_quality.md
git checkout main -- spec/complete/

# 5. Replace main
git branch -m main main-broken
git branch -m main-clean main
```

### Option B: Selective Revert
Revert only the problematic "Fix:" commits.

```bash
# Revert in reverse order
git revert d501086  # Prioritize relational descriptor pairing
git revert 432f7c1  # Add comprehensive diagnostic logging
git revert ba1215a  # Allow relational descriptor merges
# ... etc
```

**Problem:** This is complex and may not fully restore working state due to merge conflicts.

### Option C: File-Level Restore
Restore specific files to f1bca9f state.

```bash
# Restore character extraction to known-good state
git checkout f1bca9f -- src/pipeline/character_extraction/
git checkout f1bca9f -- src/pipeline/chapter_detection/
git checkout f1bca9f -- src/agents/
```

**Recommended:** Option A or C, depending on whether we want to preserve any recent work.

## Post-Revert Steps

1. **Verify baseline quality**
   ```bash
   # Run analysis on Gatsby with clean code
   audiobook-prep analyze Test_Texts/gatsby.txt \
     --html output/gatsby/report.html \
     --output output/gatsby/analysis.json
   ```

   Expected: Should get similar or better results than pre-loop (5.15+ for Gatsby)

2. **Implement loop design fixes** (see ORACLE_LOOP_DESIGN_FIXES.md)
   - Add regression protection
   - Add rollback mechanism
   - Remove novel-specific content from prompts
   - Add deterministic sanity checks

3. **Re-run loop with fixed design**

## Risks

1. **Loss of good changes:** Some commits between f1bca9f and HEAD may have been beneficial. Review before reverting:
   - a737c07 Fix plot summary hallucination - likely good
   - 38b4950 Improve first-person narrator handling - likely good
   - 232dbfc Consolidate LLM modules - structural, probably good

2. **Documentation loss:** Mitigated by preserving AGENTS.md and spec files

3. **Time investment:** The loop ran for ~30 iterations. That work is lost, but it was producing negative value anyway.

## Verification Checklist

After revert, verify:
- [ ] `pytest` passes
- [ ] Can run analysis without errors
- [ ] Gatsby analysis produces reasonable output
- [ ] No orphaned imports or references to reverted code

## Decision Needed

Before executing revert:
1. Should we wait for Frankenstein attempt 5 to complete? (Currently running)
2. Which "good" commits to cherry-pick after revert?
3. Archive current branch or delete?
