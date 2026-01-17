# Phase: FIX

You are fixing issues identified in the evaluation phase of an autonomous improvement loop for an audiobook narrator preparation tool.

## 0. Orient

0a. Read `EVALUATION_STATE.md` to understand current issues and their priorities.
0b. Read `spec/output_quality.md` to understand the quality criteria.
0c. Read `AGENTS.md` for codebase navigation and commands.
0d. Read `CLAUDE.md` for coding standards (especially: no novel-specific hardcoding).

## 1. Analyze Issues

Review the issues in EVALUATION_STATE.md, prioritized by severity:
- **CRITICAL**: Must fix before re-running - blocks progress
- **HIGH**: Significant impact on quality score
- **MEDIUM**: Noticeable but manageable impact
- **LOW**: Polish items, can defer

Focus on **CRITICAL** issues first. Only address **one issue per iteration** to keep changes isolated and testable.

## 2. Investigate

Before making changes, understand the current implementation:

1. **Locate the relevant code** - Use the file hints in the issue description
   ```bash
   # Example searches
   grep -r "alias" src/agents/characters.py
   grep -r "merge" src/pipeline/character_extraction/
   ```

2. **Understand the current behavior** - Read the relevant functions/classes

3. **Identify the root cause** - Is it:
   - A prompt issue? → Edit prompts in the agent files
   - A code logic issue? → Edit `src/agents/` or `src/pipeline/`
   - A configuration issue? → Edit `src/agents/config.py`
   - A threshold issue? → Adjust parameters in the relevant module

## 3. Implement Fix

Make minimal, targeted changes:

1. **Fix ONE issue** - The most critical one
2. **Make the smallest change that solves the problem**
3. **Do NOT refactor surrounding code** - Stay focused
4. **Do NOT add features** - Only fix the identified issue
5. **Follow coding standards** from CLAUDE.md:
   - No novel-specific hardcoding (no "Gatsby", "Frankenstein", etc. in prompts)
   - Use generic guidance patterns

## 4. Test

Run relevant tests to ensure you haven't broken anything:

```bash
# Run all tests
pytest tests/ -v

# Or run specific tests for the area you modified
pytest tests/test_character_agent.py -v
pytest tests/test_alias_merging.py -v
# etc.
```

If tests fail:
- Fix the test failures before proceeding
- If the test itself is wrong, document why and fix the test

## 5. Document Changes

Update `EVALUATION_STATE.md`:

1. Move the fixed issue from "Current Issues" to "Fix History" with:
   - What was changed
   - Which file(s) modified
   - Brief description of the fix

2. Set `**Phase:**` to `awaiting_analysis`

3. Note any concerns about the fix or potential side effects

Example:
```markdown
## Fix History
- Attempt 1: Fixed chapter detection regex for Roman numerals (src/agents/structure.py)
- Attempt 2: Improved alias resolution to handle "FirstName LastName" -> "LastName" matching (src/agents/characters.py, line 342)

## Next Action
Re-run analysis to verify fix
```

## 6. Commit and Exit

```bash
git add -A
git commit -m "Fix: {brief description of the fix}

Addresses: {issue description from EVALUATION_STATE.md}
Modified: {file paths}"
```

The loop will restart with PROMPT_analyze.md to re-run the pipeline with your fix.

## Guidelines

### One Issue at a Time
Fix the most critical issue, then re-run the full cycle. Don't batch multiple fixes - this makes it hard to identify which fix worked (or broke something).

### Preserve Working Behavior
Run tests before AND after your changes. If you break something, revert and try a different approach.

### Document the Why
Future iterations depend on understanding what was tried. Be explicit about your reasoning.

### If Stuck
If you can't figure out how to fix an issue after reasonable investigation:
1. Document what you tried in EVALUATION_STATE.md
2. Lower the issue priority or mark it as "deferred"
3. Move on to the next issue
4. The loop will eventually hit max attempts and advance

### Avoid Over-Engineering
The goal is to cross the 8.0 quality threshold, not to achieve perfection. If the score is 7.8, make the minimum change needed to pass.
