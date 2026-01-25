# Ralph Loop

Ralph is an autonomous PRD-driven implementation system for the audiobook_agent project. It analyzes PRD specifications against the current codebase and implements missing features or fixes bugs.

## Architecture

```
                    ┌─────────────────┐
                    │   User/Manual   │
                    │   Invocation    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │   Oracle Loop   │           │   Ralph Loop    │
    │ (quality testing)│──spawn──▶│ (PRD execution) │
    └─────────────────┘           └─────────────────┘
              │                             │
              │ analyze/evaluate/fix        │ plan/build
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │ EVALUATION_STATE│           │IMPLEMENTATION_  │
    │      .md        │           │    PLAN.md      │
    └─────────────────┘           └─────────────────┘
```

## Quick Start

### Local Execution (Recommended)

```bash
cd ralph

# Plan mode: Analyze specs and generate implementation plan
./loop.sh plan

# Build mode: Execute tasks from the plan
./loop.sh build

# Build mode with iteration limit
./loop.sh build 10
```

**Note:** Local execution is recommended for most users, especially those using Claude Max subscriptions. The Claude CLI uses browser-based OAuth stored in `~/.claude/`, which works seamlessly when running locally.

### Docker (API Key Users Only)

Docker is available for users with Anthropic API keys who want containerized isolation. **Docker does NOT work with Claude Max subscriptions** because the container cannot access browser-based OAuth credentials.

```bash
cd ralph

# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Build the container
docker-compose build

# Run plan mode
MODE=plan docker-compose run ralph

# Run build mode (10 iterations max)
MODE=build MAX_ITER=10 docker-compose run ralph
```

### Oracle Integration

The oracle loop can automatically spawn Ralph when it gets stuck:

```bash
# Enable Ralph auto-fix in oracle loop
RALPH_ENABLED=true ./oracle-loop/oracle-loop.sh
```

## Files

| File | Purpose |
|------|---------|
| `loop.sh` | Main orchestrator script |
| `PROMPT_plan.md` | Prompt for gap analysis and plan generation |
| `PROMPT_build.md` | Prompt for task implementation |
| `AGENTS.md` | Operational learnings for the codebase |
| `spawn_ralph.sh` | Spawn Ralph for a specific PRD (used by oracle) |
| `specs/` | Symlink to ../spec/ (PRD specifications) |
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Container orchestration |

## Modes

### Plan Mode

1. Reads all PRD specs in `specs/`
2. Analyzes codebase for existing implementations
3. Identifies gaps between specs and code
4. Generates `IMPLEMENTATION_PLAN.md` with prioritized tasks
5. Exits after one iteration

### Build Mode

1. Reads `IMPLEMENTATION_PLAN.md`
2. Selects highest-priority INCOMPLETE task
3. Investigates codebase (searches for existing code)
4. Implements the task
5. Validates with `ruff check` and `pytest`
6. Updates plan and commits
7. Exits (loop restarts for next task)

## Implementation Plan Format

```markdown
# Implementation Plan

Generated: 2024-01-24 12:00:00
Source Specs: spec1.prd.md, spec2.prd.md

## Summary

Brief overview of findings.

## Tasks

### Task 1: Fix character extraction bug
- **Priority:** HIGH
- **Status:** INCOMPLETE
- **Source Spec:** character-extraction-v2.prd.json
- **Description:** The V2 pipeline doesn't handle...
- **Files to Modify:** src/pipeline/character_extraction_v2.py
- **Dependencies:** None

### Task 2: Add validation for aliases
- **Priority:** MEDIUM
- **Status:** INCOMPLETE
...
```

## Completion Signal

When all tasks are complete, Ralph adds `<!-- RALPH_COMPLETE -->` to the implementation plan. The loop script checks for this marker to know when to stop.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODE` | `build` | Plan or build mode |
| `MAX_ITER` | `0` | Max iterations (0 = unlimited) |
| `ANTHROPIC_API_KEY` | - | API key for Claude (Docker only) |
| `RALPH_ENABLED` | `false` | Enable Ralph auto-fix in oracle |
| `RALPH_MAX_ITERATIONS` | `10` | Max iterations when spawned from oracle |
| `RALPH_MAX_ESCALATIONS` | `2` | Max times oracle can spawn Ralph before requiring human review |

## Troubleshooting

### "PROMPT_*.md not found"
Make sure you're running from the ralph/ directory.

### Docker build fails
Ensure the parent directory contains `pyproject.toml` and project files.

### Claude CLI not found
The CLI is installed via npm in the Dockerfile. If running locally, install with:
```bash
npm install -g @anthropic-ai/claude-code
```

### Tests fail after Ralph changes
Ralph validates before committing. If tests fail later, check for environmental differences or race conditions.
