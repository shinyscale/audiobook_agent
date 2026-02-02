#!/bin/bash
set -euo pipefail

# Experiment Framework for Universal Config Discovery
# Usage: ./experiment-runner.sh [experiment_id]
# If no experiment_id, runs all pending experiments

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

STATE_DIR="state"
LOGS_DIR="logs/experiments"
EXPERIMENTS_FILE="$STATE_DIR/experiments.json"
CHECKPOINTS_FILE="$STATE_DIR/checkpoints.json"

# Ensure directories exist
mkdir -p "$LOGS_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ==========================================
# Configuration from experiments.json
# ==========================================

get_book_sets() {
    local set_name="$1"
    jq -r ".book_sets.${set_name}[]" "$EXPERIMENTS_FILE" 2>/dev/null
}

get_threshold() {
    local threshold_name="$1"
    jq -r ".${threshold_name}" "$EXPERIMENTS_FILE" 2>/dev/null
}

get_experiment() {
    local exp_id="$1"
    jq ".experiments[] | select(.id == \"$exp_id\")" "$EXPERIMENTS_FILE" 2>/dev/null
}

get_pending_experiments() {
    jq -r '.experiments[] | select(.status == "pending") | .id' "$EXPERIMENTS_FILE" 2>/dev/null
}

get_baseline_experiment() {
    jq '.experiments[] | select(.status == "baseline")' "$EXPERIMENTS_FILE" 2>/dev/null
}

# ==========================================
# Score Extraction from EVALUATION_STATE.md
# ==========================================

# Extract category scores from EVALUATION_STATE.md
# Returns JSON object with category scores
extract_category_scores() {
    local state_file="$STATE_DIR/EVALUATION_STATE.md"

    if [ ! -f "$state_file" ]; then
        echo "{}"
        return 1
    fi

    # Parse scores from format: "- Structure Detection: 8/10"
    local structure=$(grep -oP 'Structure Detection: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local characters=$(grep -oP 'Character Extraction: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local profiles=$(grep -oP 'Character Profiles: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local summaries=$(grep -oP 'Chapter Summaries: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local pronunciation=$(grep -oP 'Pronunciation Guide: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local presentation=$(grep -oP 'HTML Presentation: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)
    local overall=$(grep -oP 'Overall: \K[0-9.]+(?=/10)' "$state_file" 2>/dev/null | head -1)

    # Default to 0 if not found
    structure="${structure:-0}"
    characters="${characters:-0}"
    profiles="${profiles:-0}"
    summaries="${summaries:-0}"
    pronunciation="${pronunciation:-0}"
    presentation="${presentation:-0}"
    overall="${overall:-0}"

    cat << EOF
{
  "overall": $overall,
  "category_scores": {
    "structure": $structure,
    "characters": $characters,
    "profiles": $profiles,
    "summaries": $summaries,
    "pronunciation": $pronunciation,
    "presentation": $presentation
  }
}
EOF
}

# ==========================================
# Experiment Execution
# ==========================================

# Apply experiment config and run analysis
run_analysis_with_config() {
    local exp_id="$1"
    local book_name="$2"
    local log_file="$LOGS_DIR/${exp_id}_${book_name}_$(date '+%Y%m%d_%H%M%S').log"

    log_info "Running analysis for $book_name with config from $exp_id"

    # Get the experiment config
    local config=$(get_experiment "$exp_id" | jq -r '.config')

    # Extract config values
    local character_model=$(echo "$config" | jq -r '.character_model // "qwen2.5:32b"')
    local structure_model=$(echo "$config" | jq -r '.structure_model // "qwen2.5:14b"')
    local summary_model=$(echo "$config" | jq -r '.summary_model // "qwen2.5:32b"')
    local pronunciation_model=$(echo "$config" | jq -r '.pronunciation_model // "qwen2.5:14b"')
    local context_length=$(echo "$config" | jq -r '.context_length // 32768')
    local min_mentions=$(echo "$config" | jq -r '.min_mentions // 2')
    local competitive_consensus=$(echo "$config" | jq -r '.competitive_consensus // false')

    # Get book file from manifest
    local book_file=$(jq -r ".texts[] | select(.name == \"$book_name\") | .file" "$STATE_DIR/manifest.json")

    if [ -z "$book_file" ] || [ "$book_file" = "null" ]; then
        log_error "Book file not found for $book_name"
        return 1
    fi

    # Build CLI flags
    local cli_flags=""
    cli_flags+=" --character-model $character_model"
    cli_flags+=" --structure-model $structure_model"
    cli_flags+=" --summary-model $summary_model"
    cli_flags+=" --pronunciation-model $pronunciation_model"
    cli_flags+=" --context-length $context_length"
    cli_flags+=" --min-mentions $min_mentions"

    if [ "$competitive_consensus" = "true" ]; then
        cli_flags+=" --competitive-consensus"
        local competitive_models=$(echo "$config" | jq -r '.competitive_models[]?' 2>/dev/null | tr '\n' ',')
        if [ -n "$competitive_models" ]; then
            cli_flags+=" --competitive-model ${competitive_models%,}"
        fi
    fi

    log_info "CLI flags: $cli_flags"

    # Run the analysis
    # Note: This uses the audiobook-prep CLI; adjust path if needed
    if command -v audiobook-prep &> /dev/null; then
        audiobook-prep analyze "../$book_file" --output "../output/${book_name}/analysis.json" --html "../output/${book_name}/report.html" $cli_flags 2>&1 | tee "$log_file"
    else
        log_warn "audiobook-prep not found, using python module directly"
        python -m src.cli analyze "../$book_file" --output "../output/${book_name}/analysis.json" --html "../output/${book_name}/report.html" $cli_flags 2>&1 | tee "$log_file"
    fi

    return ${PIPESTATUS[0]}
}

# Run evaluation (calls oracle loop evaluate phase)
run_evaluation() {
    local book_name="$1"
    local log_file="$LOGS_DIR/evaluate_${book_name}_$(date '+%Y%m%d_%H%M%S').log"

    log_info "Evaluating output for $book_name"

    # Set up EVALUATION_STATE.md for this book
    cat > "$STATE_DIR/EVALUATION_STATE.md" << EOF
# Current Evaluation State

## Active Text
- **Name:** ${book_name}
- **Attempt:** 1
- **Phase:** awaiting_evaluation

## Output Files
- HTML: ../output/${book_name}/report.html
- JSON: ../output/${book_name}/analysis.json

## Latest Scores
(awaiting evaluation)
EOF

    # Run evaluate prompt
    cat "prompts/PROMPT_evaluate.md" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model opus \
        --verbose \
        2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

# ==========================================
# Regression Checking
# ==========================================

# Check per-category regression against baseline
# Returns: 0 if no regression, 1 if regression detected
check_category_regression() {
    local book_name="$1"
    local new_scores="$2"  # JSON object with category_scores

    local tolerance=$(get_threshold "category_regression_tolerance")
    tolerance="${tolerance:-0.5}"

    # Get baseline scores from checkpoints
    local baseline=$(jq ".known_good_baseline[\"$book_name\"].category_scores // {}" "$CHECKPOINTS_FILE" 2>/dev/null)

    if [ "$baseline" = "{}" ] || [ -z "$baseline" ]; then
        log_info "No baseline for $book_name, skipping regression check"
        return 0
    fi

    local categories=("structure" "characters" "profiles" "summaries" "pronunciation" "presentation")
    local regression_found=0

    for category in "${categories[@]}"; do
        local new_score=$(echo "$new_scores" | jq -r ".category_scores.$category // 0")
        local baseline_score=$(echo "$baseline" | jq -r ".$category // 0")

        if [ "$baseline_score" = "0" ] || [ "$baseline_score" = "null" ]; then
            continue
        fi

        local diff=$(echo "$new_score - $baseline_score" | bc -l 2>/dev/null)
        local threshold_neg=$(echo "-$tolerance" | bc -l 2>/dev/null)

        if [ "$(echo "$diff < $threshold_neg" | bc -l 2>/dev/null)" = "1" ]; then
            log_error "REGRESSION in $category: $new_score < $baseline_score (diff: $diff, tolerance: -$tolerance)"
            regression_found=1
        fi
    done

    return $regression_found
}

# ==========================================
# Update Experiment Results
# ==========================================

update_experiment_result() {
    local exp_id="$1"
    local book_name="$2"
    local scores="$3"  # JSON object with overall and category_scores
    local status="$4"  # "passed", "failed_screening", "failed_validation", "failed_regression"

    # Add result to experiments.json
    local overall=$(echo "$scores" | jq -r '.overall // 0')
    local category_scores=$(echo "$scores" | jq -r '.category_scores // {}')

    # Build result object
    local result_obj=$(cat << EOF
{
  "overall": $overall,
  "category_scores": $category_scores,
  "status": "$status",
  "timestamp": "$(date -Iseconds)"
}
EOF
)

    # Update experiments.json
    jq --arg exp_id "$exp_id" \
       --arg book_name "$book_name" \
       --argjson result "$result_obj" \
       '(.experiments[] | select(.id == $exp_id) | .results[$book_name]) = $result' \
       "$EXPERIMENTS_FILE" > "${EXPERIMENTS_FILE}.tmp" && \
       mv "${EXPERIMENTS_FILE}.tmp" "$EXPERIMENTS_FILE"

    log_info "Updated results for $exp_id/$book_name: $status (overall: $overall)"
}

update_experiment_status() {
    local exp_id="$1"
    local status="$2"  # "passed", "failed_screening", "failed_validation", "failed_regression"

    jq --arg exp_id "$exp_id" \
       --arg status "$status" \
       '(.experiments[] | select(.id == $exp_id) | .status) = $status' \
       "$EXPERIMENTS_FILE" > "${EXPERIMENTS_FILE}.tmp" && \
       mv "${EXPERIMENTS_FILE}.tmp" "$EXPERIMENTS_FILE"

    log_info "Updated experiment $exp_id status: $status"
}

# ==========================================
# Main Experiment Flow
# ==========================================

run_experiment() {
    local exp_id="$1"

    echo ""
    echo "========================================"
    echo "  EXPERIMENT: $exp_id"
    echo "========================================"

    local experiment=$(get_experiment "$exp_id")
    if [ -z "$experiment" ]; then
        log_error "Experiment $exp_id not found"
        return 1
    fi

    local description=$(echo "$experiment" | jq -r '.description')
    local status=$(echo "$experiment" | jq -r '.status')

    log_info "Description: $description"
    log_info "Current status: $status"

    if [ "$status" != "pending" ]; then
        log_warn "Experiment $exp_id is not pending (status: $status), skipping"
        return 0
    fi

    local screening_threshold=$(get_threshold "screening_threshold")
    local validation_threshold=$(get_threshold "validation_threshold")

    # PHASE 1: SCREENING (fast texts, fail-fast)
    echo ""
    log_info "=== PHASE 1: SCREENING ==="

    local screening_books=$(get_book_sets "screening")
    local screening_passed=true

    for book in $screening_books; do
        log_info "Screening: $book"

        # Run analysis
        if ! run_analysis_with_config "$exp_id" "$book"; then
            log_error "Analysis failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_analysis"
            screening_passed=false
            break
        fi

        # Run evaluation
        if ! run_evaluation "$book"; then
            log_error "Evaluation failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_evaluation"
            screening_passed=false
            break
        fi

        # Extract scores
        local scores=$(extract_category_scores)
        local overall=$(echo "$scores" | jq -r '.overall // 0')

        log_info "Score for $book: $overall/10"

        # Check screening threshold (any category below threshold)
        local min_category=$(echo "$scores" | jq -r '[.category_scores | to_entries[] | .value] | min')

        if [ "$(echo "$min_category < $screening_threshold" | bc -l 2>/dev/null)" = "1" ]; then
            log_error "FAILED SCREENING: $book has category score $min_category < $screening_threshold"
            update_experiment_result "$exp_id" "$book" "$scores" "failed_screening"
            update_experiment_status "$exp_id" "failed_screening"
            screening_passed=false
            break
        fi

        update_experiment_result "$exp_id" "$book" "$scores" "passed_screening"
    done

    if [ "$screening_passed" != "true" ]; then
        log_error "Experiment $exp_id failed screening"
        return 1
    fi

    log_success "Screening passed!"

    # PHASE 2: VALIDATION (harder texts)
    echo ""
    log_info "=== PHASE 2: VALIDATION ==="

    local validation_books=$(get_book_sets "validation")
    local validation_passed=true

    for book in $validation_books; do
        log_info "Validation: $book"

        if ! run_analysis_with_config "$exp_id" "$book"; then
            log_error "Analysis failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_analysis"
            validation_passed=false
            break
        fi

        if ! run_evaluation "$book"; then
            log_error "Evaluation failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_evaluation"
            validation_passed=false
            break
        fi

        local scores=$(extract_category_scores)
        local overall=$(echo "$scores" | jq -r '.overall // 0')

        log_info "Score for $book: $overall/10"

        local min_category=$(echo "$scores" | jq -r '[.category_scores | to_entries[] | .value] | min')

        if [ "$(echo "$min_category < $validation_threshold" | bc -l 2>/dev/null)" = "1" ]; then
            log_error "FAILED VALIDATION: $book has category score $min_category < $validation_threshold"
            update_experiment_result "$exp_id" "$book" "$scores" "failed_validation"
            update_experiment_status "$exp_id" "failed_validation"
            validation_passed=false
            break
        fi

        update_experiment_result "$exp_id" "$book" "$scores" "passed_validation"
    done

    if [ "$validation_passed" != "true" ]; then
        log_error "Experiment $exp_id failed validation"
        return 1
    fi

    log_success "Validation passed!"

    # PHASE 3: REGRESSION GATE (must not regress known-good books)
    echo ""
    log_info "=== PHASE 3: REGRESSION GATE ==="

    local regression_books=$(get_book_sets "regression")
    local regression_passed=true

    for book in $regression_books; do
        log_info "Regression check: $book"

        if ! run_analysis_with_config "$exp_id" "$book"; then
            log_error "Analysis failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_analysis"
            regression_passed=false
            break
        fi

        if ! run_evaluation "$book"; then
            log_error "Evaluation failed for $book"
            update_experiment_result "$exp_id" "$book" '{"overall": 0, "category_scores": {}}' "failed_evaluation"
            regression_passed=false
            break
        fi

        local scores=$(extract_category_scores)
        local overall=$(echo "$scores" | jq -r '.overall // 0')

        log_info "Score for $book: $overall/10"

        # Check per-category regression
        if ! check_category_regression "$book" "$scores"; then
            log_error "FAILED REGRESSION: $book regressed in at least one category"
            update_experiment_result "$exp_id" "$book" "$scores" "failed_regression"
            update_experiment_status "$exp_id" "failed_regression"
            regression_passed=false
            break
        fi

        update_experiment_result "$exp_id" "$book" "$scores" "passed_regression"
    done

    if [ "$regression_passed" != "true" ]; then
        log_error "Experiment $exp_id failed regression gate"
        return 1
    fi

    log_success "Regression gate passed!"

    # ALL GATES PASSED
    echo ""
    echo "========================================"
    log_success "EXPERIMENT $exp_id PASSED ALL GATES!"
    echo "========================================"

    update_experiment_status "$exp_id" "passed"

    return 0
}

# ==========================================
# Promotion to Baseline
# ==========================================

promote_to_baseline() {
    local exp_id="$1"

    log_info "Promoting experiment $exp_id to baseline"

    # Update old baseline status
    jq '(.experiments[] | select(.status == "baseline") | .status) = "superseded"' \
       "$EXPERIMENTS_FILE" > "${EXPERIMENTS_FILE}.tmp" && \
       mv "${EXPERIMENTS_FILE}.tmp" "$EXPERIMENTS_FILE"

    # Update new baseline status
    jq --arg exp_id "$exp_id" \
       '(.experiments[] | select(.id == $exp_id) | .status) = "baseline"' \
       "$EXPERIMENTS_FILE" > "${EXPERIMENTS_FILE}.tmp" && \
       mv "${EXPERIMENTS_FILE}.tmp" "$EXPERIMENTS_FILE"

    # Update checkpoints.json with new baseline scores
    local experiment=$(get_experiment "$exp_id")
    local results=$(echo "$experiment" | jq '.results')

    echo "$results" | jq -r 'keys[]' | while read book; do
        local book_result=$(echo "$results" | jq ".[\"$book\"]")
        local overall=$(echo "$book_result" | jq -r '.overall')
        local category_scores=$(echo "$book_result" | jq -r '.category_scores')

        # Get current commit
        local commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

        jq --arg book "$book" \
           --arg commit "$commit" \
           --argjson score "$overall" \
           --argjson cats "$category_scores" \
           '.known_good_baseline[$book] = {"commit": $commit, "score": $score, "category_scores": $cats}' \
           "$CHECKPOINTS_FILE" > "${CHECKPOINTS_FILE}.tmp" && \
           mv "${CHECKPOINTS_FILE}.tmp" "$CHECKPOINTS_FILE"
    done

    log_success "Experiment $exp_id promoted to baseline"
}

# ==========================================
# Summary Report
# ==========================================

print_summary() {
    echo ""
    echo "========================================"
    echo "  EXPERIMENT SUMMARY"
    echo "========================================"

    jq -r '.experiments[] | "\(.status | if . == "baseline" then "* " else "  " end)\(.id): \(.status) - \(.description)"' "$EXPERIMENTS_FILE"

    echo ""
    echo "Legend: * = current baseline"
}

# ==========================================
# Main Entry Point
# ==========================================

main() {
    echo ""
    echo "========================================"
    echo "  Experiment Framework"
    echo "========================================"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    if [ ! -f "$EXPERIMENTS_FILE" ]; then
        log_error "Experiments file not found: $EXPERIMENTS_FILE"
        exit 1
    fi

    # Collect experiment IDs to run
    local experiments_to_run=()

    if [ $# -gt 0 ]; then
        # Run specified experiments
        experiments_to_run=("$@")
        log_info "Running ${#experiments_to_run[@]} specified experiment(s): ${experiments_to_run[*]}"
    else
        # No arguments - show help instead of running all
        echo "Usage: $0 <experiment_id> [experiment_id2] [experiment_id3] ..."
        echo ""
        echo "Examples:"
        echo "  $0 exp_016_structure_qwen3_4b"
        echo "  $0 exp_016_structure_qwen3_4b exp_017_structure_qwen2_5_7b exp_018_structure_qwen3_8b"
        echo ""
        echo "Pending experiments:"
        local pending=$(get_pending_experiments)
        if [ -z "$pending" ]; then
            echo "  (none)"
        else
            for exp_id in $pending; do
                local desc=$(get_experiment "$exp_id" | jq -r '.description')
                echo "  $exp_id - $desc"
            done
        fi
        echo ""
        print_summary
        exit 0
    fi

    local passed_experiments=""

    for exp_id in "${experiments_to_run[@]}"; do
        if run_experiment "$exp_id"; then
            passed_experiments+="$exp_id "
        fi
    done

    print_summary

    # Offer to promote if any experiments passed
    if [ -n "$passed_experiments" ]; then
        echo ""
        echo "Experiments that passed all gates: $passed_experiments"
        read -p "Promote one to baseline? Enter experiment ID (or press Enter to skip): " -r
        if [ -n "$REPLY" ]; then
            promote_to_baseline "$REPLY"
        fi
    fi
}

main "$@"
