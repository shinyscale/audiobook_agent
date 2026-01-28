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
MAX_NO_PROGRESS=10

# Directory paths (relative to oracle-loop/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

STATE_DIR="state"
PROMPTS_DIR="prompts"
LOGS_DIR="logs"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Function to compute state hash (for no-progress detection)
compute_state_hash() {
    local hash=""
    if [ -f "$STATE_DIR/EVALUATION_STATE.md" ]; then
        hash="${hash}$(md5sum "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null | cut -d' ' -f1)"
    fi
    if [ -f "$STATE_DIR/manifest.json" ]; then
        hash="${hash}$(md5sum "$STATE_DIR/manifest.json" 2>/dev/null | cut -d' ' -f1)"
    fi
    echo "$hash"
}

# Quality threshold from manifest
if [ ! -f "$STATE_DIR/manifest.json" ]; then
    echo "Error: $STATE_DIR/manifest.json not found. Create it first with your test texts."
    exit 1
fi

THRESHOLD=$(jq -r '.quality_threshold' "$STATE_DIR/manifest.json")

# === CHECKPOINT SYSTEM ===
# Ensures checkpoints.json exists
init_checkpoints() {
    if [ ! -f "$STATE_DIR/checkpoints.json" ]; then
        echo '{"checkpoints": [], "known_good_baseline": {}}' > "$STATE_DIR/checkpoints.json"
    fi
}

# Create a checkpoint after evaluating code changes
create_checkpoint() {
    local COMMIT="$1"
    local SCORE="$2"
    local TEXT="$3"
    local ATTEMPT="$4"

    # Only checkpoint if src/ files changed
    local SRC_FILES=$(git diff-tree --no-commit-id --name-only -r "$COMMIT" 2>/dev/null | grep "^src/" || true)
    [ -z "$SRC_FILES" ] && return 1

    local CHECKPOINT_ID="cp-$(date +%Y%m%d%H%M%S)"
    local DESCRIPTION=$(git log --format="%s" -1 "$COMMIT")
    local TIMESTAMP=$(git log --format="%aI" -1 "$COMMIT")

    jq --arg id "$CHECKPOINT_ID" \
       --arg commit "$COMMIT" \
       --arg ts "$TIMESTAMP" \
       --argjson attempt "$ATTEMPT" \
       --arg text "$TEXT" \
       --argjson score "$SCORE" \
       --arg files "$SRC_FILES" \
       --arg desc "$DESCRIPTION" \
       '.checkpoints += [{
         "id": $id, "commit": $commit, "timestamp": $ts,
         "attempt": $attempt, "text": $text, "score_after": $score,
         "files_changed": ($files | split("\n")), "description": $desc,
         "is_known_good": false
       }]' "$STATE_DIR/checkpoints.json" > "$STATE_DIR/checkpoints.tmp" && \
       mv "$STATE_DIR/checkpoints.tmp" "$STATE_DIR/checkpoints.json"

    echo "Created checkpoint $CHECKPOINT_ID for $TEXT (score: $SCORE)"
}

# Get known-good commit for a text
get_known_good_checkpoint() {
    local TEXT="$1"
    jq -r ".known_good_baseline[\"$TEXT\"].commit // empty" "$STATE_DIR/checkpoints.json" 2>/dev/null
}

# Get known-good score for a text
get_known_good_score() {
    local TEXT="$1"
    jq -r ".known_good_baseline[\"$TEXT\"].score // empty" "$STATE_DIR/checkpoints.json" 2>/dev/null
}

# Get known-good category scores for a text
get_known_good_category_scores() {
    local TEXT="$1"
    jq -r ".known_good_baseline[\"$TEXT\"].category_scores // {}" "$STATE_DIR/checkpoints.json" 2>/dev/null
}

# Extract category scores from EVALUATION_STATE.md
extract_category_scores() {
    local STATE_FILE="$STATE_DIR/EVALUATION_STATE.md"

    if [ ! -f "$STATE_FILE" ]; then
        echo "{}"
        return 1
    fi

    # Parse scores from format: "- Structure Detection: 8/10"
    local structure=$(grep -oP 'Structure Detection: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)
    local characters=$(grep -oP 'Character Extraction: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)
    local profiles=$(grep -oP 'Character Profiles: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)
    local summaries=$(grep -oP 'Chapter Summaries: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)
    local pronunciation=$(grep -oP 'Pronunciation Guide: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)
    local presentation=$(grep -oP 'HTML Presentation: \K[0-9.]+(?=/10)' "$STATE_FILE" 2>/dev/null | head -1)

    # Default to 0 if not found
    cat << EOF
{
  "structure": ${structure:-0},
  "characters": ${characters:-0},
  "profiles": ${profiles:-0},
  "summaries": ${summaries:-0},
  "pronunciation": ${pronunciation:-0},
  "presentation": ${presentation:-0}
}
EOF
}

# Check per-category regression against baseline
# Returns: 0 if no regression, 1 if regression detected
check_category_regression() {
    local TEXT="$1"
    local NEW_SCORES="$2"  # JSON object with category scores

    # Get tolerance from experiments.json if available, else default
    local TOLERANCE=0.5
    if [ -f "$STATE_DIR/experiments.json" ]; then
        local exp_tol=$(jq -r '.category_regression_tolerance // empty' "$STATE_DIR/experiments.json" 2>/dev/null)
        if [ -n "$exp_tol" ]; then
            TOLERANCE="$exp_tol"
        fi
    fi

    # Get baseline category scores
    local BASELINE=$(get_known_good_category_scores "$TEXT")

    if [ "$BASELINE" = "{}" ] || [ -z "$BASELINE" ]; then
        # No baseline, no regression possible
        return 0
    fi

    local CATEGORIES=("structure" "characters" "profiles" "summaries" "pronunciation" "presentation")
    local REGRESSION_FOUND=0

    for category in "${CATEGORIES[@]}"; do
        local new_score=$(echo "$NEW_SCORES" | jq -r ".$category // 0")
        local baseline_score=$(echo "$BASELINE" | jq -r ".$category // 0")

        if [ "$baseline_score" = "0" ] || [ "$baseline_score" = "null" ]; then
            continue
        fi

        local diff=$(echo "$new_score - $baseline_score" | bc -l 2>/dev/null)
        local threshold_neg=$(echo "-$TOLERANCE" | bc -l 2>/dev/null)

        if [ "$(echo "$diff < $threshold_neg" | bc -l 2>/dev/null)" = "1" ]; then
            echo ""
            echo "  CATEGORY REGRESSION: $category"
            echo "    New:      $new_score"
            echo "    Baseline: $baseline_score"
            echo "    Diff:     $diff (threshold: -$TOLERANCE)"
            REGRESSION_FOUND=1
        fi
    done

    return $REGRESSION_FOUND
}

# Mark checkpoint as known-good (called when score improves)
mark_checkpoint_good() {
    local TEXT="$1"
    local COMMIT="$2"
    local SCORE="$3"

    jq --arg text "$TEXT" --arg commit "$COMMIT" --argjson score "$SCORE" \
       '.known_good_baseline[$text] = {"commit": $commit, "score": $score}' \
       "$STATE_DIR/checkpoints.json" > "$STATE_DIR/checkpoints.tmp" && \
       mv "$STATE_DIR/checkpoints.tmp" "$STATE_DIR/checkpoints.json"

    # Create a git tag for easy reference
    git tag -f "known-good-$TEXT" "$COMMIT" 2>/dev/null || true
    echo "Marked $COMMIT as known-good for $TEXT (score: $SCORE)"
}

# Revert all src/ changes since known-good commit
revert_to_known_good() {
    local TEXT="$1"
    local NEW_SCORE="$2"

    local KNOWN_GOOD=$(get_known_good_checkpoint "$TEXT")
    local KNOWN_GOOD_SCORE=$(get_known_good_score "$TEXT")

    if [ -z "$KNOWN_GOOD" ]; then
        echo "No known-good checkpoint for $TEXT, cannot revert"
        return 1
    fi

    echo ""
    echo "========================================"
    echo "  REVERTING TO KNOWN-GOOD STATE"
    echo "========================================"
    echo "  Text: $TEXT"
    echo "  Current score: $NEW_SCORE"
    echo "  Known-good score: $KNOWN_GOOD_SCORE"
    echo "  Known-good commit: $KNOWN_GOOD"
    echo "========================================"

    # Find all src/ files that changed since known-good
    local CHANGED_FILES=$(git diff --name-only "$KNOWN_GOOD" HEAD -- "src/" 2>/dev/null || true)

    if [ -z "$CHANGED_FILES" ]; then
        echo "No src/ files changed since known-good commit"
        return 1
    fi

    echo ""
    echo "Files to revert:"
    echo "$CHANGED_FILES"
    echo ""

    # Restore each file from known-good commit
    for file in $CHANGED_FILES; do
        if git show "$KNOWN_GOOD:$file" > /dev/null 2>&1; then
            git checkout "$KNOWN_GOOD" -- "$file" 2>/dev/null || true
            echo "  Restored: $file"
        else
            echo "  Skipped (new file): $file"
        fi
    done

    # Commit the revert
    git add -A
    git commit -m "Auto-revert: Regression detected, reverting to known-good ($NEW_SCORE < $KNOWN_GOOD_SCORE)

Reverted src/ files to commit: $KNOWN_GOOD
Text: $TEXT
Score regression: $NEW_SCORE vs $KNOWN_GOOD_SCORE

Files reverted:
$CHANGED_FILES" 2>/dev/null || true

    echo ""
    echo "Reverted to known-good state"
    return 0
}

# Initialize checkpoint system
init_checkpoints

# Source escalation system
source "$SCRIPT_DIR/escalation.sh"

# === SESSION CONFLICT DETECTION ===
# Check for existing Claude CLI sessions that could cause API conflicts
check_claude_session_conflicts() {
    # Find claude processes (excluding our grep and this script's subshells)
    local existing_sessions=$(pgrep -f "^claude" 2>/dev/null | while read pid; do
        # Skip if it's a child of this script
        local ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ "$ppid" != "$$" ] && [ "$pid" != "$$" ]; then
            echo "$pid"
        fi
    done)

    if [ -n "$existing_sessions" ]; then
        echo ""
        echo "========================================"
        echo "  WARNING: Claude Session Conflict"
        echo "========================================"
        echo ""
        echo "Existing Claude CLI session(s) detected:"
        for pid in $existing_sessions; do
            local runtime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
            echo "  PID $pid (running for: $runtime)"
        done
        echo ""
        echo "The oracle loop may fail with '400 API Error: tool use"
        echo "concurrency issues' due to session conflicts."
        echo ""
        echo "Options:"
        echo "  1. Kill existing session(s): kill $existing_sessions"
        echo "  2. Run oracle loop in a separate tmux/screen session"
        echo "  3. Wait for existing session(s) to complete"
        echo ""
        echo "Continuing anyway in 10 seconds... (Ctrl+C to abort)"
        sleep 10
        return 1
    fi
    return 0
}

# Check for session conflicts at startup
check_claude_session_conflicts || true

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
        echo "$PROMPTS_DIR/PROMPT_${PHASE}.md"
        return
    fi

    # Auto-detect from EVALUATION_STATE.md
    if [ ! -f "$STATE_DIR/EVALUATION_STATE.md" ]; then
        echo "$PROMPTS_DIR/PROMPT_analyze.md"
        return
    fi

    # Handle both escaped (\*\*) and unescaped (**) asterisks in markdown
    local current_phase=$(grep -oP '(?<=Phase:\*\* )[a-z_]+|(?<=Phase: )[a-z_]+' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null | head -1)
    current_phase="${current_phase:-analyze}"

    case "$current_phase" in
        awaiting_analysis|analyze)
            echo "$PROMPTS_DIR/PROMPT_analyze.md"
            ;;
        awaiting_evaluation|evaluate)
            echo "$PROMPTS_DIR/PROMPT_evaluate.md"
            ;;
        awaiting_fix|fix)
            echo "$PROMPTS_DIR/PROMPT_fix.md"
            ;;
        complete)
            # Check if there are more texts
            local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' "$STATE_DIR/manifest.json")
            if [ "$incomplete" -eq 0 ]; then
                echo "ALL_COMPLETE"
            else
                echo "$PROMPTS_DIR/PROMPT_analyze.md"
            fi
            ;;
        *)
            echo "$PROMPTS_DIR/PROMPT_analyze.md"
            ;;
    esac
}

# Check if all texts are complete
all_complete() {
    local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' "$STATE_DIR/manifest.json")
    [ "$incomplete" -eq 0 ]
}

# Get current text name for logging
get_current_text() {
    if [ -f "$STATE_DIR/EVALUATION_STATE.md" ]; then
        sed -n 's/.*\*\*Name:\*\* \([^ ]*\).*/\1/p' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null | head -1 || echo "unknown"
    else
        jq -r '.texts[] | select(.complete == false) | .name' "$STATE_DIR/manifest.json" | head -1
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
        jq -r '.texts[] | "  \(.name): \(.final_score // "N/A")/10 in \(.attempts) attempts (\(if .complete then "PASS" else "INCOMPLETE" end))"' "$STATE_DIR/manifest.json"
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
    LOG_FILE="$LOGS_DIR/iteration_${ITERATION}_$(date '+%Y%m%d_%H%M%S').log"

    # Capture state hash BEFORE Claude run (for no-progress detection)
    STATE_HASH_BEFORE=$(compute_state_hash)

    # Select model based on phase - Opus for evaluation (the oracle), Sonnet for fixes
    if [ "$PROMPT_FILE" = "$PROMPTS_DIR/PROMPT_evaluate.md" ]; then
        MODEL="opus"
        echo "Using model: opus (oracle evaluation phase)"
    else
        MODEL="sonnet"
        echo "Using model: sonnet (analysis/fix phase)"
    fi

    # Quick session conflict check before each Claude invocation
    CONFLICT_PIDS=$(pgrep -f "^claude" 2>/dev/null | grep -v "^$$" || true)
    if [ -n "$CONFLICT_PIDS" ]; then
        echo ""
        echo "Warning: Detected existing Claude session(s): $CONFLICT_PIDS"
        echo "If API errors occur, consider terminating conflicting sessions."
        echo ""
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

    # Check for regression after evaluation phase and manage checkpoints
    if [ "$PROMPT_FILE" = "$PROMPTS_DIR/PROMPT_evaluate.md" ]; then
        # Extract score and attempt info from EVALUATION_STATE.md
        NEW_SCORE=$(sed -n 's/.*\*\*Overall: \([0-9.]*\).*/\1/p' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null | head -1)
        NEW_SCORE="${NEW_SCORE:-0}"
        CURRENT_ATTEMPT=$(sed -n 's/.*\*\*Attempt:\*\* \([0-9]*\).*/\1/p' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null | head -1)
        CURRENT_ATTEMPT="${CURRENT_ATTEMPT:-1}"

        # Get known-good score for comparison (or use 0 if none)
        KNOWN_GOOD_SCORE=$(get_known_good_score "$CURRENT_TEXT")
        KNOWN_GOOD_SCORE="${KNOWN_GOOD_SCORE:-0}"

        if [ -n "$NEW_SCORE" ] && [ "$NEW_SCORE" != "0" ]; then
            echo ""
            echo "Checkpoint check: new_score=$NEW_SCORE, known_good=$KNOWN_GOOD_SCORE"

            # Create checkpoint for this evaluation (records the commit and score)
            # Note: || true prevents set -e from killing script when no src/ files changed
            CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null)
            create_checkpoint "$CURRENT_COMMIT" "$NEW_SCORE" "$CURRENT_TEXT" "$CURRENT_ATTEMPT" || true

            # Extract per-category scores for detailed regression check
            CATEGORY_SCORES=$(extract_category_scores)

            # Check if score improved - if so, update known-good baseline
            if [ "$(echo "$NEW_SCORE > $KNOWN_GOOD_SCORE" | bc -l 2>/dev/null)" = "1" ]; then
                echo "Score improved! Updating known-good baseline."
                mark_checkpoint_good "$CURRENT_TEXT" "$CURRENT_COMMIT" "$NEW_SCORE"

                # Also save category scores to checkpoint
                jq --arg text "$CURRENT_TEXT" --argjson cats "$CATEGORY_SCORES" \
                   '.known_good_baseline[$text].category_scores = $cats' \
                   "$STATE_DIR/checkpoints.json" > "$STATE_DIR/checkpoints.tmp" && \
                   mv "$STATE_DIR/checkpoints.tmp" "$STATE_DIR/checkpoints.json"
                echo "Saved category scores to baseline"

            # Check for regression (per-category OR overall score drop)
            elif [ "$KNOWN_GOOD_SCORE" != "0" ]; then
                OVERALL_DIFF=$(echo "$NEW_SCORE - $KNOWN_GOOD_SCORE" | bc 2>/dev/null || echo "0")
                REGRESSION_DETECTED=false

                # Check per-category regression first
                if ! check_category_regression "$CURRENT_TEXT" "$CATEGORY_SCORES"; then
                    echo ""
                    echo "========================================"
                    echo "  PER-CATEGORY REGRESSION DETECTED!"
                    echo "========================================"
                    REGRESSION_DETECTED=true
                fi

                # Also check overall score regression (legacy check, threshold -0.3)
                if [ "$(echo "$OVERALL_DIFF < -0.3" | bc -l 2>/dev/null)" = "1" ]; then
                    echo ""
                    echo "========================================"
                    echo "  OVERALL REGRESSION DETECTED!"
                    echo "========================================"
                    echo "  New score:       $NEW_SCORE"
                    echo "  Known-good:      $KNOWN_GOOD_SCORE"
                    echo "  Diff:            $OVERALL_DIFF (threshold: -0.3)"
                    echo "========================================"
                    REGRESSION_DETECTED=true
                fi

                if [ "$REGRESSION_DETECTED" = "true" ]; then
                    # Revert to known-good state
                    if revert_to_known_good "$CURRENT_TEXT" "$NEW_SCORE"; then
                        # Update phase to awaiting_analysis to re-run with reverted code
                        sed -i 's/\*\*Phase:\*\* awaiting_fix/\*\*Phase:\*\* awaiting_analysis/' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null
                        sed -i 's/\*\*Phase:\*\* awaiting_evaluation/\*\*Phase:\*\* awaiting_analysis/' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null
                        echo "Reset phase to awaiting_analysis"

                        # Reset no-progress counter since regression revert is progress
                        NO_PROGRESS_COUNT=0
                        echo "Reset no-progress counter after regression revert"
                    fi
                fi
            fi

            # Check for stuck condition (same score for N consecutive attempts)
            # This triggers escalation with PRD generation
            if check_and_escalate "$CURRENT_TEXT" "$NEW_SCORE" "$CURRENT_ATTEMPT"; then
                echo ""
                echo "========================================"
                echo "  LOOP STOPPED - ESCALATION TRIGGERED"
                echo "========================================"
                echo "  Human investigation required."
                echo "  Review the generated PRD in spec/ folder."
                echo "========================================"
                echo ""
                exit 2  # Exit code 2 = escalation
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
    echo "Review $LOGS_DIR/ and $STATE_DIR/EVALUATION_STATE.md for status"
    echo ""
fi
