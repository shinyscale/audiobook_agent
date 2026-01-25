#!/bin/bash
# Ralph Loop - PRD-driven implementation system
# Usage: ./loop.sh [plan|build] [max_iterations]

set -e

MODE="${1:-build}"  # plan or build
MAX_ITERATIONS="${2:-0}"  # 0 = unlimited

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Validate mode
if [[ "$MODE" != "plan" && "$MODE" != "build" ]]; then
    echo "Error: Mode must be 'plan' or 'build'"
    echo "Usage: ./loop.sh [plan|build] [max_iterations]"
    exit 1
fi

PROMPT_FILE="PROMPT_${MODE}.md"

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "Error: $PROMPT_FILE not found"
    exit 1
fi

echo "=========================================="
echo "  Ralph Loop Starting"
echo "  Mode: $MODE"
echo "  Max Iterations: ${MAX_ITERATIONS:-unlimited}"
echo "=========================================="

iteration=0

while :; do
    ((++iteration)) || true
    echo ""
    echo "=== Ralph iteration $iteration (mode: $MODE) ==="
    echo "Started at: $(date)"
    echo ""

    # Run Claude with the appropriate prompt
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --model claude-opus-4-20250514 \
        --verbose

    exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "Warning: Claude exited with code $exit_code"
    fi

    echo ""
    echo "Finished at: $(date)"

    # Check for completion signal in IMPLEMENTATION_PLAN.md
    if [[ -f "IMPLEMENTATION_PLAN.md" ]]; then
        if grep -q "RALPH_COMPLETE" IMPLEMENTATION_PLAN.md 2>/dev/null; then
            echo ""
            echo "=========================================="
            echo "  Ralph signaled completion!"
            echo "  Total iterations: $iteration"
            echo "=========================================="
            break
        fi
    fi

    # In plan mode, exit after first iteration (plan generation)
    if [[ "$MODE" == "plan" ]]; then
        echo ""
        echo "Plan mode complete. Review IMPLEMENTATION_PLAN.md"
        break
    fi

    # Check iteration limit
    if [[ $MAX_ITERATIONS -gt 0 && $iteration -ge $MAX_ITERATIONS ]]; then
        echo ""
        echo "=========================================="
        echo "  Max iterations ($MAX_ITERATIONS) reached"
        echo "=========================================="
        break
    fi

    # Brief pause between iterations
    sleep 2
done

echo ""
echo "Ralph loop finished."
