# Oracle → Ralph Integration Fixes

## Overview

Fix issues in the Oracle Loop's ability to spawn Ralph for complex bug resolution.

## Problem Statement

The current integration has several issues:
1. `specs` symlink causes Ralph to analyze ALL specs instead of just the escalation PRD
2. No escalation counter allows infinite spawn loops
3. No post-Ralph verification to detect if the fix worked
4. Docker recommendation doesn't work with Claude Max subscriptions

## Requirements

### R1: Isolated Escalation Mode
When Oracle spawns Ralph for a specific bug:
- Ralph MUST only analyze the escalation PRD
- Other specs in `spec/` MUST be ignored
- Original specs symlink MUST be restored after Ralph completes

### R2: Escalation Counter
- Track number of times Oracle has escalated to Ralph for the same issue
- Stop after 2 failed Ralph attempts
- Reset counter when score improves

### R3: Post-Ralph Verification
- Log Ralph commits made during the session
- Track whether score improved after Ralph's changes
- Provide clear feedback about Ralph's success/failure

### R4: Documentation Update
- Recommend local execution over Docker
- Document Claude Max limitations
- Keep Docker option for API-key users

## Acceptance Criteria

- [ ] `spawn_ralph.sh` creates isolated specs directory
- [ ] `spawn_ralph.sh` restores original symlink on exit (including on error)
- [ ] `escalation.sh` tracks escalation count
- [ ] Oracle stops after 2 failed Ralph escalations
- [ ] Oracle logs Ralph commits after completion
- [ ] README updated with local execution as primary method

## Files to Modify

- `ralph/spawn_ralph.sh`
- `oracle-loop/escalation.sh`
- `ralph/README.md`

## Implementation Details

### Task 1: Fix spawn_ralph.sh for Isolated Escalation

Replace the specs handling with proper isolation:

```bash
# Near top, after SCRIPT_DIR
ISOLATED_SPECS="$SCRIPT_DIR/.escalation_specs"
SPECS_BACKUP="$SCRIPT_DIR/.specs_backup"

cleanup() {
    # Restore original specs symlink on exit
    if [ -L "$SPECS_BACKUP" ]; then
        rm -f "$SCRIPT_DIR/specs"
        mv "$SPECS_BACKUP" "$SCRIPT_DIR/specs"
    fi
    rm -rf "$ISOLATED_SPECS"
}
trap cleanup EXIT

# Setup isolated specs
rm -rf "$ISOLATED_SPECS"
mkdir -p "$ISOLATED_SPECS"
cp "$PRD_FILE" "$ISOLATED_SPECS/"

# Replace specs symlink temporarily
if [ -L "$SCRIPT_DIR/specs" ]; then
    mv "$SCRIPT_DIR/specs" "$SPECS_BACKUP"
fi
ln -sf "$ISOLATED_SPECS" "$SCRIPT_DIR/specs"
```

### Task 2: Add Escalation Counter to escalation.sh

Add functions:
- `get_escalation_count()` - reads from state file
- `increment_escalation_count()` - increments counter
- `reset_escalation_count()` - clears counter

Modify `check_and_escalate()`:
- Check counter before spawning Ralph (max 2 attempts)
- Increment after spawn
- Reset only when score improves (handled by oracle-loop.sh)

```bash
# Escalation counter functions
RALPH_ESCALATION_COUNT_FILE="$STATE_DIR/ralph_escalation_count"

get_escalation_count() {
    cat "$RALPH_ESCALATION_COUNT_FILE" 2>/dev/null || echo 0
}

increment_escalation_count() {
    echo $(($(get_escalation_count) + 1)) > "$RALPH_ESCALATION_COUNT_FILE"
}

reset_escalation_count() {
    rm -f "$RALPH_ESCALATION_COUNT_FILE"
}

# In check_and_escalate(), before spawning Ralph:
if [ "$(get_escalation_count)" -ge 2 ]; then
    echo "Ralph has failed twice. Stopping for human review."
    return 0
fi
```

### Task 3: Add Post-Ralph Verification

After `spawn_ralph` returns success:
1. Count Ralph commits since escalation: `git log --oneline --since="1 hour ago" | grep "^Ralph:" | wc -l`
2. If commits exist, log them
3. Return to oracle loop with state reset

### Task 4: Update README

- Remove Docker as primary recommendation
- Add note about Claude Max requiring local execution
- Keep Docker section for API-key users

## Testing

1. **Test isolation:** Run `./spawn_ralph.sh ../spec/some.prd.md` and verify only that PRD is analyzed
2. **Test counter:** Manually trigger escalation twice, verify it stops on third
3. **Test recovery:** After Ralph fixes something, verify oracle continues properly
