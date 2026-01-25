# Oracle Loop Design Fixes

This document outlines the fundamental design problems with the current oracle loop and proposes fixes.

## Executive Summary

The oracle loop has been **decreasing output quality** instead of improving it:
- Gatsby: 5.15/10 → 4.05/10 (worse by 1.1 points after 5 attempts)
- Frankenstein: 6.25/10 after 4 attempts (attempt 5 in progress)

Root cause: The loop lacks **regression protection**. Fixes that pass unit tests can still break output quality, and the loop has no mechanism to detect or rollback these regressions.

---

## Problem 1: No Regression Protection

### Current Behavior
```
1. Make fix to code
2. Run pytest (unit tests)
3. If tests pass → proceed
4. Run analysis
5. Evaluate output
6. If score < 8.0 → make another fix
```

### The Problem
Unit tests verify code paths, not output quality. A fix can:
- Pass all 444 unit tests ✓
- Cause chapter detection to drop from 9 → 6 chapters ✗

There's no check that output quality didn't **regress** from the previous attempt.

### Proposed Fix
Add a **quality regression gate** after each analysis:

```
1. Record baseline score before fix
2. Make fix
3. Run pytest
4. Run analysis
5. Evaluate output → get new score
6. IF new_score < baseline_score - 0.5:
     → REVERT fix (git checkout)
     → Log "Fix caused regression, reverted"
     → Try different approach
7. ELSE proceed
```

**Implementation:**
- Store `baseline_score` in EVALUATION_STATE.md before each fix
- Add regression check to PROMPT_evaluate.md
- Auto-revert if score drops significantly

---

## Problem 2: No Rollback Mechanism

### Current Behavior
When a fix makes things worse, the loop just continues forward with more fixes, compounding the problem.

### The Problem
Gatsby went through this cycle:
```
Attempt 1: 5.15 → Attempt 2: 4.65 (regression!)
         → No rollback, kept going
Attempt 5: 4.05 (even worse)
```

### Proposed Fix
Add **git-based rollback** on regression:

```bash
# In oracle-loop.sh, after evaluation:
NEW_SCORE=$(jq '.texts[] | select(.name == "'$TEXT'") | .last_score' manifest.json)
PREV_SCORE=$(git show HEAD~1:manifest.json | jq '...')

if (( $(echo "$NEW_SCORE < $PREV_SCORE - 0.3" | bc -l) )); then
    echo "REGRESSION DETECTED: $NEW_SCORE < $PREV_SCORE"
    git revert --no-commit HEAD
    echo "Reverted last fix. Trying different approach."
fi
```

**Implementation:**
- Tag known-good states: `git tag quality-5.15 <commit>`
- Auto-revert on score drop > 0.3 points
- Track "attempted fixes that failed" to avoid retrying

---

## Problem 3: Novel-Specific Content in Prompts

### Current Behavior
`PROMPT_evaluate.md` contains explicit character lists:

```markdown
**The Great Gatsby:**
- Nick Carraway, Jay Gatsby, Daisy Buchanan...
- Critical: Jay Gatsby = Gatsby = Mr. Gatsby = James Gatz
```

### The Problem
This violates `CLAUDE.md` coding standards:
> "NEVER include examples from specific novels in prompts"

More importantly, it creates **evaluation bias**. The evaluator "knows" what to look for in Gatsby but has no such guidance for other texts.

### Proposed Fix
Remove novel-specific content. Replace with **generic evaluation patterns**:

```markdown
## Character Evaluation Patterns

When evaluating characters, check for these common issues:
- Full names and shortened versions should be aliases (e.g., "FirstName LastName" = "LastName")
- Birth names and adopted/married names should be aliases
- Titled references should merge with base names (e.g., "Dr. Smith" = "Smith")
- Family members with shared surnames should remain SEPARATE (spouses, siblings, parent/child)
- The creature/monster/being in horror novels is often unnamed - verify canonical name
- First-person narrators should be identified correctly
```

**Implementation:**
- Edit PROMPT_evaluate.md to remove lines 52-77
- Replace with generic patterns
- Move specific test expectations to manifest.json if needed

---

## Problem 4: LLM Evaluating LLM Output

### Current Behavior
Claude Sonnet both:
1. Runs parts of the analysis pipeline
2. Evaluates the output quality
3. Writes the fixes

### The Problem
Same model family = same blindspots. If the analysis LLM makes a mistake that seems plausible to Claude, the evaluator Claude may not catch it.

### Proposed Fix (Short-term)
Add **deterministic sanity checks** before LLM evaluation:

```python
# quality_checks.py
def check_gatsby_baseline():
    """Deterministic checks for known test texts."""
    result = load_json("output/gatsby/analysis.json")

    checks = []
    # Chapter count (we know Gatsby has 9 chapters)
    if len(result.chapters) != 9:
        checks.append(f"FAIL: Chapter count {len(result.chapters)} != 9")

    # Main character present
    char_names = [c.canonical_name.lower() for c in result.characters]
    if "gatsby" not in ' '.join(char_names):
        checks.append("FAIL: Gatsby not in character list")

    return checks
```

### Proposed Fix (Long-term)
Use a **different evaluator**:
- Human spot-check for critical issues
- Different model (e.g., GPT-4 for evaluation if using Claude for fixes)
- Deterministic golden-file comparison for known texts

---

## Problem 5: Insufficient Attempts

### Current Behavior
Max 5 attempts per text, then mark as "complete" (failed).

### The Problem
Complex interdependent issues (character merging + chapter detection + alias resolution) can't be fixed in 5 attempts when each fix risks breaking something else.

### Proposed Fix
- Increase to **10 attempts** per text
- Add **attempt budget by severity**:
  - If score > 7.0: max 5 more attempts
  - If score > 6.0: max 8 more attempts
  - If score < 6.0: max 10 attempts, then escalate to human

**Implementation:**
```json
// manifest.json
{
  "max_attempts_per_text": 10,
  "escalation_threshold": 5.0,
  "attempt_budget": {
    "above_7": 5,
    "above_6": 8,
    "below_6": 10
  }
}
```

---

## Problem 6: Single-Issue Focus Causes Regressions

### Current Behavior
PROMPT_fix.md says: "Fix ONE issue - The most critical one"

### The Problem
Fixing one issue in isolation doesn't account for interactions:
- Fix Wilson separation → Broke chapter detection
- Fix chapter detection → Broke character merging

The system has **coupled components** but the fix strategy assumes independence.

### Proposed Fix
Add **integration test suite** that runs after each fix:

```bash
# run_integration_tests.sh
# Run quick analysis on ALL test texts (not full evaluation)
# Just check for obvious regressions

for text in gatsby frankenstein dracula; do
    audiobook-prep analyze Test_Texts/${text}.txt --quick-check

    # Quick checks:
    # - Did chapter count change?
    # - Did main character count change dramatically?
    # - Did any errors occur?
done
```

If any text shows >20% change in key metrics, flag for review before proceeding.

---

## Problem 7: No Learning From Failed Attempts

### Current Behavior
Each fix attempt starts fresh. The loop doesn't track "we tried X and it made things worse."

### The Problem
The loop can try similar fixes repeatedly, or oscillate between contradictory approaches:
```
Attempt 2: "Prevent family member merging"
Attempt 3: "Allow relational descriptor merges" (contradicts attempt 2)
```

### Proposed Fix
Add **fix history tracking** with outcomes:

```markdown
## Failed Approaches (DO NOT RETRY)
1. "Filter ambiguous last-name-only entries" - Attempt 4, caused regression
2. "Prioritize hard boundary titles" - Attempt 5, broke chapter detection
3. "Block all family member merges" - Too aggressive, blocks valid merges

## Successful Approaches (PRESERVE)
1. "Merge creature/monster/wretch epithets" - Works, maintain this behavior
```

Include this in PROMPT_fix.md context so the fixer knows what NOT to try.

---

## Implementation Priority

| Fix | Effort | Impact | Priority |
|-----|--------|--------|----------|
| 1. Regression gate | Medium | High | **P0** |
| 2. Git rollback | Low | High | **P0** |
| 3. Remove novel-specific content | Low | Medium | **P1** |
| 4. Deterministic checks | Medium | High | **P1** |
| 5. Increase attempts | Low | Low | **P2** |
| 6. Integration tests | High | High | **P1** |
| 7. Failed approach tracking | Low | Medium | **P2** |

---

## Recommended Implementation Order

1. **Revert to pre-loop state** (`f1bca9f`)
2. Implement P0 fixes (regression gate, rollback)
3. Implement P1 fixes (remove novel content, deterministic checks, integration tests)
4. Re-run loop on Gatsby as validation
5. If Gatsby improves or stays stable, proceed with other texts

---

## Success Criteria

The redesigned loop should:
- [ ] Never decrease score by more than 0.3 points without auto-reverting
- [ ] Track and avoid previously-failed fix approaches
- [ ] Pass deterministic sanity checks before LLM evaluation
- [ ] Reach 8.0 threshold OR clearly identify why it cannot (with human escalation)
