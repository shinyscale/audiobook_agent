#!/bin/bash
set -euo pipefail

# Audiobook Analysis Oracle Improvement Loop
# Usage: ./oracle-loop.sh [phase] [max_iterations]
# Examples:
#   ./oracle-loop.sh                    # Auto-detect phase, run until complete
#   ./oracle-loop.sh analyze            # Force analyze phase
#   ./oracle-loop.sh evaluate           # Force evaluate phase
#   ./oracle-loop.sh fix                # Force fix phase
#   ./oracle-loop.sh full 50            # Run full cycle, max 50 iterations total

PHASE="${1:-auto}"
MAX_ITERATIONS="${2:-100}"
ITERATION=0

# Ensure logs directory exists
mkdir -p logs

# Quality threshold from manifest
if [ ! -f "manifest.json" ]; then
    echo "Error: manifest.json not found. Create it first with your test texts."
    exit 1
fi

THRESHOLD=$(jq -r '.quality_threshold' manifest.json)
MAX_ATTEMPTS=$(jq -r '.max_attempts_per_text' manifest.json)

echo ""
echo "========================================"
echo "  Audiobook Analysis Oracle Loop"
echo "========================================"
echo "Quality Threshold: $THRESHOLD"
echo "Max Attempts per Text: $MAX_ATTEMPTS"
echo "Max Total Iterations: $MAX_ITERATIONS"
echo "========================================"

# Determine which prompt to use
get_prompt_file() {
    if [ "$PHASE" != "auto" ]; then
        echo "PROMPT_${PHASE}.md"
        return
    fi

    # Auto-detect from EVALUATION_STATE.md
    if [ ! -f "EVALUATION_STATE.md" ]; then
        echo "PROMPT_analyze.md"
        return
    fi

    local current_phase=$(grep -oP '(?<=\*\*Phase:\*\* )\w+' EVALUATION_STATE.md 2>/dev/null || echo "analyze")

    case "$current_phase" in
        awaiting_analysis|analyze)
            echo "PROMPT_analyze.md"
            ;;
        awaiting_evaluation|evaluate)
            echo "PROMPT_evaluate.md"
            ;;
        awaiting_fix|fix)
            echo "PROMPT_fix.md"
            ;;
        complete)
            # Check if there are more texts
            local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' manifest.json)
            if [ "$incomplete" -eq 0 ]; then
                echo "ALL_COMPLETE"
            else
                echo "PROMPT_analyze.md"
            fi
            ;;
        *)
            echo "PROMPT_analyze.md"
            ;;
    esac
}

# Check if all texts are complete
all_complete() {
    local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' manifest.json)
    [ "$incomplete" -eq 0 ]
}

# Get current text name for logging
get_current_text() {
    if [ -f "EVALUATION_STATE.md" ]; then
        grep -oP '(?<=\*\*Name:\*\* )\S+' EVALUATION_STATE.md 2>/dev/null || echo "unknown"
    else
        jq -r '.texts[] | select(.complete == false) | .name' manifest.json | head -1
    fi
}

# Main loop
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    PROMPT_FILE=$(get_prompt_file)

    if [ "$PROMPT_FILE" = "ALL_COMPLETE" ]; then
        echo ""
        echo "========================================"
        echo "  ALL TEXTS COMPLETE"
        echo "========================================"
        echo ""
        jq -r '.texts[] | "  \(.name): \(.final_score // "N/A")/10 in \(.attempts) attempts (\(if .complete then "PASS" else "INCOMPLETE" end))"' manifest.json
        echo ""
        break
    fi

    if [ ! -f "$PROMPT_FILE" ]; then
        echo "Error: $PROMPT_FILE not found"
        exit 1
    fi

    ITERATION=$((ITERATION + 1))
    CURRENT_TEXT=$(get_current_text)

    echo ""
    echo "========================================"
    echo "  ITERATION $ITERATION"
    echo "========================================"
    echo "Prompt: $PROMPT_FILE"
    echo "Text: $CURRENT_TEXT"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Run Claude Code with the appropriate prompt
    # Using claude CLI in headless mode with piped prompt
    LOG_FILE="logs/iteration_${ITERATION}_$(date '+%Y%m%d_%H%M%S').log"

    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model sonnet \
        --verbose \
        2>&1 | tee "$LOG_FILE"

    EXIT_CODE=${PIPESTATUS[1]}

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "Warning: Claude exited with code $EXIT_CODE"
        echo "Check $LOG_FILE for details"
    fi

    # Brief pause between iterations to avoid rate limiting
    echo ""
    echo "Iteration complete. Pausing 5 seconds before next iteration..."
    sleep 5
done

if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    echo ""
    echo "========================================"
    echo "  MAX ITERATIONS REACHED: $MAX_ITERATIONS"
    echo "========================================"
    echo "Review logs/ and EVALUATION_STATE.md for status"
    echo ""
fi
