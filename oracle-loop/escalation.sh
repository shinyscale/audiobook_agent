#!/bin/bash
# Escalation system for oracle loop
# Detects stuck conditions and generates PRD for human investigation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$SCRIPT_DIR/state"
SPEC_DIR="$SCRIPT_DIR/../spec"
RALPH_DIR="$SCRIPT_DIR/../ralph"

# Configuration
STUCK_THRESHOLD=4  # Number of attempts with same score (±0.1) to trigger escalation
SCORE_TOLERANCE=0.15  # Score difference that counts as "same"
RALPH_ENABLED="${RALPH_ENABLED:-false}"  # Set to 'true' to auto-spawn Ralph on escalation
RALPH_MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-10}"  # Max iterations for Ralph
RALPH_MAX_ESCALATIONS=2  # Max times to escalate to Ralph before requiring human review

# Escalation counter - prevents infinite Ralph spawn loops
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

# Extract score history from EVALUATION_STATE.md
# Returns: attempt:score pairs, one per line
get_score_history() {
    local state_file="$STATE_DIR/EVALUATION_STATE.md"
    [ ! -f "$state_file" ] && return 1

    # Parse the Score History table
    # Format: | Attempt | Score | Delta from Baseline | Notes |
    grep -E '^\| [0-9]+ \|' "$state_file" 2>/dev/null | \
        sed 's/[~*]//g' | \
        awk -F'|' '{gsub(/[[:space:]]/, "", $2); gsub(/[[:space:]]/, "", $3); if ($3 ~ /^[0-9.]+$/) print $2 ":" $3}'
}

# Check if loop is stuck (same score for N consecutive attempts)
# Returns: 0 if stuck, 1 if not stuck
is_stuck() {
    local history=$(get_score_history)
    [ -z "$history" ] && return 1

    # Get last N scores
    local recent_scores=$(echo "$history" | tail -n "$STUCK_THRESHOLD" | cut -d: -f2)
    local count=$(echo "$recent_scores" | wc -l)

    [ "$count" -lt "$STUCK_THRESHOLD" ] && return 1

    # Check if all scores are within tolerance of each other
    local first_score=$(echo "$recent_scores" | head -1)
    local all_same=true

    while read -r score; do
        local diff=$(echo "scale=2; $score - $first_score" | bc 2>/dev/null | tr -d '-')
        if [ "$(echo "$diff > $SCORE_TOLERANCE" | bc -l 2>/dev/null)" = "1" ]; then
            all_same=false
            break
        fi
    done <<< "$recent_scores"

    [ "$all_same" = "true" ] && return 0 || return 1
}

# Get files modified in fix attempts (from git log)
get_modified_files() {
    local text_name="$1"
    local attempts="$2"

    # Get commits related to this text's fix attempts
    git log --oneline --since="7 days ago" --all -- "src/" 2>/dev/null | \
        head -20 | \
        while read -r commit msg; do
            git diff-tree --no-commit-id --name-only -r "$commit" 2>/dev/null
        done | sort | uniq -c | sort -rn | head -20
}

# Get files NOT modified (potential blind spots)
get_unmodified_files() {
    local modified="$1"

    # Key pipeline files that might be blind spots
    local key_files=(
        "src/ingestion/base.py"
        "src/ingestion/refine.py"
        "src/pipeline/chapter_detection/profiler.py"
        "src/pipeline/chapter_detection/proposers/regex.py"
        "src/pipeline/chapter_detection/proposers/llm.py"
        "src/pipeline/chapter_detection/validator.py"
        "src/pipeline/chapter_detection/consensus.py"
        "src/pipeline/chapter_detection/pipeline.py"
        "src/agents/structure.py"
        "src/analyzer.py"
    )

    for file in "${key_files[@]}"; do
        if ! echo "$modified" | grep -q "$file"; then
            echo "$file"
        fi
    done
}

# Extract current issues from EVALUATION_STATE.md
get_current_issues() {
    local state_file="$STATE_DIR/EVALUATION_STATE.md"
    [ ! -f "$state_file" ] && return 1

    # Extract issues section
    sed -n '/## Current Issues/,/## Score Calculation/p' "$state_file" | head -80
}

# Extract fix history from EVALUATION_STATE.md
get_fix_history() {
    local state_file="$STATE_DIR/EVALUATION_STATE.md"
    [ ! -f "$state_file" ] && return 1

    # Extract fix history section
    sed -n '/## Fix History/,/## Recommended Priority/p' "$state_file" | head -100
}

# Generate escalation PRD
generate_escalation_prd() {
    local text_name="$1"
    local current_score="$2"
    local attempt="$3"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local prd_file="$SPEC_DIR/oracle-loop-escalation-${text_name}-${timestamp}.prd.md"

    mkdir -p "$SPEC_DIR"

    # Get modified files
    local modified_files=$(get_modified_files "$text_name" "$attempt")
    local unmodified_files=$(get_unmodified_files "$modified_files")

    # Get score history
    local score_history=$(get_score_history)
    local recent_scores=$(echo "$score_history" | tail -n "$STUCK_THRESHOLD")

    cat > "$prd_file" << EOF
# Oracle Loop Escalation: ${text_name}

## Status: Requires Human Investigation

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Text:** ${text_name}
**Attempt:** ${attempt}
**Current Score:** ${current_score}
**Stuck Duration:** ${STUCK_THRESHOLD} consecutive attempts with score ±${SCORE_TOLERANCE}

---

## Why This Escalation Was Triggered

The oracle loop has been stuck on the same score (±${SCORE_TOLERANCE}) for ${STUCK_THRESHOLD} consecutive attempts. This indicates:

1. The fixes being attempted are not addressing the root cause
2. The root cause may be in a code layer the loop hasn't been examining
3. Human investigation is needed to identify blind spots

---

## Recent Score History

| Attempt | Score |
|---------|-------|
$(echo "$recent_scores" | while IFS=: read -r att sc; do echo "| $att | $sc |"; done)

---

## Current Issues (from EVALUATION_STATE.md)

$(get_current_issues)

---

## Fix History (Recent Attempts)

$(get_fix_history)

---

## Code Analysis

### Files Modified During Fix Attempts (last 7 days)

\`\`\`
$(echo "$modified_files" | head -15)
\`\`\`

### Files NOT Modified (Potential Blind Spots)

These key pipeline files have NOT been touched during fix attempts. The bug may be here:

\`\`\`
$(echo "$unmodified_files")
\`\`\`

**IMPORTANT:** When fixes in one layer don't work, the bug is often in an upstream layer:
- If \`consensus.py\` fixes don't work → check \`profiler.py\`, \`proposers/\`, or \`ingestion/\`
- If \`character_extraction\` fixes don't work → check \`ingestion/\` text normalization
- If structure detection fails → check if ingestion is destroying formatting

---

## Recommended Investigation Steps

1. **Check data flow from ingestion to detection:**
   \`\`\`bash
   # Verify source text has expected patterns
   grep -n "^[[:space:]]*V[[:space:]]*\$" Test_Texts/${text_name}.txt

   # Check what ingestion does to the text
   LOG_LEVEL=DEBUG python -c "
   from src.ingestion import ingest_document
   text = ingest_document('Test_Texts/${text_name}.txt')
   # Check if patterns survive
   import re
   centered = re.findall(r'^\s{10,}[IVXLC]+\s*\$', text, re.MULTILINE)
   print(f'Centered roman numerals after ingestion: {len(centered)}')
   print(centered[:5])
   "
   \`\`\`

2. **Run isolated pipeline tests:**
   \`\`\`bash
   # Test structure detection in isolation
   python -c "
   from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
   from src.pipeline.llm import LLMClient, LLMConfig

   with open('Test_Texts/${text_name}.txt', 'r') as f:
       text = f.read()

   config = LLMConfig.ollama(model='qwen3:4b-instruct')
   pipeline = ChapterDetectionPipeline(llm_client=LLMClient(config))
   result = pipeline.run(text)

   for ch in result.chapters:
       print(f'{ch.index}: {ch.title}, {ch.word_count} words')
   "
   \`\`\`

3. **Compare isolated test vs full CLI:**
   - If isolated test passes but CLI fails, bug is in ingestion or agent layer
   - If both fail, bug is in the pipeline itself

4. **Add diagnostic logging to blind spot files:**
   - Add logging to ingestion showing text patterns before/after normalization
   - Add logging to profiler showing TOC detection and front_matter_end

---

## State Files for Reference

- \`oracle-loop/state/EVALUATION_STATE.md\` - Full evaluation state
- \`oracle-loop/state/manifest.json\` - Test manifest
- \`oracle-loop/state/checkpoints.json\` - Checkpoint history
- \`oracle-loop/logs/\` - Recent iteration logs

---

## Resolution

Once the root cause is identified and fixed:

1. Update this PRD with the resolution
2. Restart the oracle loop: \`cd oracle-loop && ./oracle-loop.sh\`
3. The loop will continue from where it left off

EOF

    echo "$prd_file"
}

# Spawn Ralph to fix a complex bug
# Returns: 0 if Ralph completed successfully, 1 otherwise
spawn_ralph() {
    local prd_file="$1"

    if [ ! -d "$RALPH_DIR" ]; then
        echo "Warning: Ralph directory not found at $RALPH_DIR"
        return 1
    fi

    if [ ! -x "$RALPH_DIR/spawn_ralph.sh" ]; then
        echo "Warning: spawn_ralph.sh not found or not executable"
        return 1
    fi

    local escalation_count=$(get_escalation_count)
    echo ""
    echo "========================================"
    echo "  SPAWNING RALPH FOR AUTO-FIX"
    echo "  Escalation attempt: $((escalation_count + 1)) of $RALPH_MAX_ESCALATIONS"
    echo "========================================"
    echo ""

    # Record start time for commit tracking
    local start_time=$(date -Iseconds)

    # Run Ralph with the PRD
    if "$RALPH_DIR/spawn_ralph.sh" "$prd_file" "$RALPH_MAX_ITERATIONS"; then
        echo ""
        echo "Ralph completed successfully."

        # Log Ralph commits made during this session
        echo ""
        echo "Ralph commits made:"
        git log --oneline --since="$start_time" --grep="^Ralph:" 2>/dev/null | head -10 || echo "  (none found)"
        echo ""

        echo "Resuming oracle loop..."
        return 0
    else
        echo ""
        echo "Ralph did not complete. Manual investigation may be needed."
        return 1
    fi
}

# Main escalation check function (called from oracle-loop.sh)
check_and_escalate() {
    local text_name="$1"
    local current_score="$2"
    local attempt="$3"

    if is_stuck; then
        echo ""
        echo "========================================"
        echo "  ESCALATION TRIGGERED"
        echo "========================================"
        echo "  Text: $text_name"
        echo "  Score: $current_score"
        echo "  Stuck for: $STUCK_THRESHOLD attempts"
        echo "========================================"
        echo ""

        local prd_file=$(generate_escalation_prd "$text_name" "$current_score" "$attempt")

        echo "PRD generated: $prd_file"
        echo ""

        # Optionally spawn Ralph to auto-fix
        if [ "$RALPH_ENABLED" = "true" ]; then
            local escalation_count=$(get_escalation_count)

            # Check if we've exceeded max escalations
            if [ "$escalation_count" -ge "$RALPH_MAX_ESCALATIONS" ]; then
                echo ""
                echo "========================================"
                echo "  RALPH ESCALATION LIMIT REACHED"
                echo "========================================"
                echo "  Ralph has been spawned $escalation_count times without success."
                echo "  Human review is required."
                echo ""
                echo "  To reset the counter and try again:"
                echo "    rm $RALPH_ESCALATION_COUNT_FILE"
                echo "========================================"
                echo ""
                return 0  # Signal to stop the loop
            fi

            # Increment counter before spawning
            increment_escalation_count

            if spawn_ralph "$prd_file"; then
                # Ralph succeeded, continue the loop
                echo "Ralph completed. Resetting evaluation state..."
                # Reset to awaiting_analysis so oracle re-evaluates
                sed -i 's/^phase: .*/phase: awaiting_analysis/' "$STATE_DIR/EVALUATION_STATE.md" 2>/dev/null || true
                # Note: Don't reset escalation count here - wait for score improvement
                return 1  # Continue the loop (Ralph fixed it)
            else
                echo ""
                echo "Ralph did not complete successfully (attempt $(get_escalation_count) of $RALPH_MAX_ESCALATIONS)."
                echo "Manual investigation is needed."
                echo ""
                return 0  # Signal to stop the loop
            fi
        fi

        echo "The oracle loop has been stuck on the same score for $STUCK_THRESHOLD consecutive attempts."
        echo "This usually means the fixes are targeting the wrong code layer."
        echo ""
        echo "To enable automatic Ralph fix attempts, set RALPH_ENABLED=true:"
        echo "  RALPH_ENABLED=true ./oracle-loop.sh"
        echo ""
        echo "Please review the PRD for investigation steps."
        echo ""

        return 0  # Signal to stop the loop
    fi

    return 1  # Continue the loop
}

# If run directly, check current state
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "Checking for stuck condition..."

    if is_stuck; then
        echo "Loop appears to be STUCK"
        echo "Recent scores:"
        get_score_history | tail -5
    else
        echo "Loop is NOT stuck"
        echo "Recent scores:"
        get_score_history | tail -5
    fi
fi
