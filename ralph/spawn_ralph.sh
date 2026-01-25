#!/bin/bash
# Spawn Ralph to handle a complex bug from oracle escalation
# Usage: ./spawn_ralph.sh <prd_file> [max_iterations]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$1"
MAX_ITERATIONS="${2:-10}"

# Isolated specs mode - prevents Ralph from analyzing ALL specs
ISOLATED_SPECS="$SCRIPT_DIR/.escalation_specs"
SPECS_BACKUP="$SCRIPT_DIR/.specs_backup"

cleanup() {
    # Restore original specs symlink on exit (success or failure)
    if [ -L "$SPECS_BACKUP" ] || [ -d "$SPECS_BACKUP" ]; then
        rm -f "$SCRIPT_DIR/specs"
        mv "$SPECS_BACKUP" "$SCRIPT_DIR/specs"
        echo "Restored original specs symlink"
    fi
    rm -rf "$ISOLATED_SPECS"
}
trap cleanup EXIT

if [ -z "$PRD_FILE" ]; then
    echo "Usage: ./spawn_ralph.sh <prd_file> [max_iterations]"
    echo "  prd_file: Path to the PRD file describing the bug"
    echo "  max_iterations: Max Ralph iterations (default: 10)"
    exit 1
fi

if [ ! -f "$PRD_FILE" ]; then
    echo "Error: PRD file not found: $PRD_FILE"
    exit 1
fi

echo "=========================================="
echo "  Spawning Ralph for Bug Fix"
echo "=========================================="
echo "  PRD: $PRD_FILE"
echo "  Max Iterations: $MAX_ITERATIONS"
echo "=========================================="

# Setup isolated specs directory (only contains the escalation PRD)
rm -rf "$ISOLATED_SPECS"
mkdir -p "$ISOLATED_SPECS"
prd_basename=$(basename "$PRD_FILE")
cp "$PRD_FILE" "$ISOLATED_SPECS/$prd_basename"

# Replace specs symlink temporarily with isolated directory
if [ -L "$SCRIPT_DIR/specs" ] || [ -d "$SCRIPT_DIR/specs" ]; then
    mv "$SCRIPT_DIR/specs" "$SPECS_BACKUP"
fi
ln -sf "$ISOLATED_SPECS" "$SCRIPT_DIR/specs"

echo "Isolated specs: only $prd_basename will be analyzed"

# Clear any existing implementation plan
rm -f "$SCRIPT_DIR/IMPLEMENTATION_PLAN.md"

# Run Ralph in plan mode first
echo ""
echo "=== Phase 1: Planning ==="
cd "$SCRIPT_DIR"
./loop.sh plan

# Check if plan was generated
if [ ! -f "$SCRIPT_DIR/IMPLEMENTATION_PLAN.md" ]; then
    echo "Error: Plan generation failed"
    exit 1
fi

echo ""
echo "=== Phase 2: Building ==="
./loop.sh build "$MAX_ITERATIONS"

# Check completion status
if grep -q "RALPH_COMPLETE" "$SCRIPT_DIR/IMPLEMENTATION_PLAN.md" 2>/dev/null; then
    echo ""
    echo "=========================================="
    echo "  Ralph completed successfully!"
    echo "=========================================="
    exit 0
else
    echo ""
    echo "=========================================="
    echo "  Ralph did not complete (max iterations reached)"
    echo "  Review IMPLEMENTATION_PLAN.md for status"
    echo "=========================================="
    exit 1
fi
