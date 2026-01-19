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
NO_PROGRESS_COUNT=0
MAX_NO_PROGRESS=3

# Ensure logs directory exists
mkdir -p logs

# Function to compute state hash (for no-progress detection)
compute_state_hash() {
    local hash=""
    if [ -f "EVALUATION_STATE.md" ]; then
        hash="${hash}$(md5sum EVALUATION_STATE.md 2>/dev/null | cut -d' ' -f1)"
    fi
    if [ -f "manifest.json" ]; then
        hash="${hash}$(md5sum manifest.json 2>/dev/null | cut -d' ' -f1)"
    fi
    echo "$hash"
}

# Quality threshold from manifest
if [ ! -f "manifest.json" ]; then
    echo "Error: manifest.json not found. Create it first with your test texts."
    exit 1
fi

THRESHOLD=$(jq -r '.quality_threshold' manifest.json)

echo ""
echo "========================================"
echo "  Audiobook Analysis Oracle Loop"
echo "========================================"
echo "Quality Threshold: $THRESHOLD"
echo "Max Total Iterations: $MAX_ITERATIONS"
echo "Mode: Stay on each text until PASS"
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

    local current_phase=$(sed -n 's/.*\*\*Phase:\*\* \([a-z_]*\).*/\1/p' EVALUATION_STATE.md 2>/dev/null | head -1)
    current_phase="${current_phase:-analyze}"

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
        sed -n 's/.*\*\*Name:\*\* \([^ ]*\).*/\1/p' EVALUATION_STATE.md 2>/dev/null | head -1 || echo "unknown"
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

    # Capture state hash BEFORE Claude run (for no-progress detection)
    STATE_HASH_BEFORE=$(compute_state_hash)

    # Select model based on phase - Opus for evaluation (the oracle), Sonnet for fixes
    if [ "$PROMPT_FILE" = "PROMPT_evaluate.md" ]; then
        MODEL="opus"
        echo "Using model: opus (oracle evaluation phase)"
    else
        MODEL="sonnet"
        echo "Using model: sonnet (analysis/fix phase)"
    fi

    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model "$MODEL" \
        --verbose \
        2>&1 | tee "$LOG_FILE"

    EXIT_CODE=${PIPESTATUS[1]}

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "Warning: Claude exited with code $EXIT_CODE"
        echo "Check $LOG_FILE for details"
    fi

    # Check for no-progress (state unchanged after Claude run)
    STATE_HASH_AFTER=$(compute_state_hash)
    if [ "$STATE_HASH_BEFORE" = "$STATE_HASH_AFTER" ]; then
        NO_PROGRESS_COUNT=$((NO_PROGRESS_COUNT + 1))
        echo ""
        echo "Warning: No state change detected (iteration $NO_PROGRESS_COUNT of $MAX_NO_PROGRESS)"

        if [ $NO_PROGRESS_COUNT -ge $MAX_NO_PROGRESS ]; then
            echo ""
            echo "========================================"
            echo "  NO-PROGRESS GUARDRAIL TRIGGERED"
            echo "========================================"
            echo "  $MAX_NO_PROGRESS consecutive no-progress iterations"
            echo "  State files unchanged - loop is stuck"
            echo "========================================"
            echo ""
            exit 1
        fi
    else
        # Reset counter on progress
        if [ $NO_PROGRESS_COUNT -gt 0 ]; then
            echo "Progress detected, resetting no-progress counter"
        fi
        NO_PROGRESS_COUNT=0
    fi

    # Check for regression after evaluation phase
    if [ "$PROMPT_FILE" = "PROMPT_evaluate.md" ]; then
        # Extract new score and baseline from EVALUATION_STATE.md
        NEW_SCORE=$(sed -n 's/.*\*\*Overall: \([0-9.]*\).*/\1/p' EVALUATION_STATE.md 2>/dev/null | head -1)
        NEW_SCORE="${NEW_SCORE:-0}"
        BASELINE=$(sed -n 's/.*\*\*baseline_score:\*\* \([0-9.]*\).*/\1/p' EVALUATION_STATE.md 2>/dev/null | head -1)
        BASELINE="${BASELINE:-0}"

        if [ -n "$BASELINE" ] && [ "$BASELINE" != "0" ] && [ -n "$NEW_SCORE" ] && [ "$NEW_SCORE" != "0" ]; then
            DIFF=$(echo "$NEW_SCORE - $BASELINE" | bc 2>/dev/null || echo "0")
            echo ""
            echo "Regression check: new_score=$NEW_SCORE, baseline=$BASELINE, diff=$DIFF"

            if [ "$(echo "$DIFF < -0.3" | bc -l 2>/dev/null)" = "1" ]; then
                echo ""
                echo "========================================"
                echo "  REGRESSION DETECTED!"
                echo "========================================"
                echo "  New score: $NEW_SCORE"
                echo "  Baseline:  $BASELINE"
                echo "  Diff:      $DIFF (threshold: -0.3)"
                echo "========================================"
                echo ""
                echo "Reverting last fix..."

                # Get the last commit that was a fix
                LAST_FIX=$(git log --oneline -1 --grep="^Fix:" 2>/dev/null | cut -d' ' -f1)
                if [ -n "$LAST_FIX" ]; then
                    git revert --no-commit "$LAST_FIX" 2>/dev/null
                    git commit -m "Auto-revert: Fix caused regression ($NEW_SCORE < $BASELINE)

Reverted commit: $LAST_FIX
Score drop: $DIFF points" 2>/dev/null
                    echo "Reverted commit $LAST_FIX"

                    # Update phase to awaiting_analysis to re-run with reverted code
                    sed -i 's/\*\*Phase:\*\* awaiting_fix/\*\*Phase:\*\* awaiting_analysis/' EVALUATION_STATE.md 2>/dev/null
                    echo "Reset phase to awaiting_analysis"
                else
                    echo "Could not find fix commit to revert"
                fi
            fi
        fi
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
