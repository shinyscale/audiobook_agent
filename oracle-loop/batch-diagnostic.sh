#!/bin/bash
set -euo pipefail

# =============================================================================
# Oracle Loop — Cross-Book Diagnostic Mode
# =============================================================================
# Instead of perfecting one text at a time (overfitting), this script runs
# ALL texts through the pipeline and scores them to build a failure matrix.
# Systemic patterns across many texts are identified for targeted fixes.
#
# Usage:
#   ./batch-diagnostic.sh                    # Run all incomplete texts
#   ./batch-diagnostic.sh --all              # Run ALL texts (including passing)
#   ./batch-diagnostic.sh --texts dracula,frankenstein  # Run specific texts
#   ./batch-diagnostic.sh --score-only       # Skip analysis, just re-score existing output
#   ./batch-diagnostic.sh --report           # Just regenerate the report from existing scores
#
# Output:
#   state/diagnostic_matrix.json   — Machine-readable failure matrix
#   state/diagnostic_report.md     — Human-readable diagnostic report
#   logs/diagnostic_<timestamp>/   — Per-text analysis and scoring logs
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

STATE_DIR="state"
PROMPTS_DIR="prompts"
LOGS_DIR="logs"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"  # output/ lives at project root, not oracle-loop/

# Parse arguments
RUN_ALL=false
SCORE_ONLY=false
REPORT_ONLY=false
SPECIFIC_TEXTS=""
SCORER="claude"  # "claude" or "local"

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_ALL=true
            shift
            ;;
        --texts)
            SPECIFIC_TEXTS="$2"
            shift 2
            ;;
        --score-only)
            SCORE_ONLY=true
            shift
            ;;
        --report)
            REPORT_ONLY=true
            shift
            ;;
        --scorer)
            SCORER="$2"
            shift 2
            ;;
        -h|--help)
            head -20 "$0" | grep "^#" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Timestamp for this diagnostic run
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DIAG_LOG_DIR="$LOGS_DIR/diagnostic_${TIMESTAMP}"
mkdir -p "$DIAG_LOG_DIR"

MATRIX_FILE="$STATE_DIR/diagnostic_matrix.json"
REPORT_FILE="$STATE_DIR/diagnostic_report.md"

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$DIAG_LOG_DIR/batch.log"
}

# Get the list of texts to process (priority order: big novels first)
get_text_list() {
    local texts_json
    texts_json=$(jq -r '.texts[] | @json' "$STATE_DIR/manifest.json")

    # Priority order for diagnostic mode: big untested novels first
    local priority_order=(
        "dracula"
        "frankenstein"
        "don_quixote"
        "east_of_eden"
        "one_hundred_years_of_solitude"
        "gatsby"
        "i_have_no_mouth"
        "flowers_for_algernon"
        "john_g"
        "american_sir"
        "cask_of_amontillado"
        "masque_of_red_death"
        "berenice"
        "monkeys_paw"
        "gift_of_the_magi"
        "a_camping_trip"
    )

    if [ -n "$SPECIFIC_TEXTS" ]; then
        # User specified specific texts
        echo "$SPECIFIC_TEXTS" | tr ',' '\n'
        return
    fi

    for name in "${priority_order[@]}"; do
        local complete
        complete=$(jq -r ".texts[] | select(.name == \"$name\") | .complete" "$STATE_DIR/manifest.json")

        if [ "$RUN_ALL" = "true" ] || [ "$complete" = "false" ]; then
            echo "$name"
        fi
    done
}

# Get the file path for a text from manifest
get_text_file() {
    local name="$1"
    jq -r ".texts[] | select(.name == \"$name\") | .file" "$STATE_DIR/manifest.json"
}

# Get model config from gui_settings.json
get_model_flags() {
    local settings="$HOME/.config/audiobook_prep/gui_settings.json"
    if [ ! -f "$settings" ]; then
        echo ""
        return
    fi

    local model
    model=$(jq -r '.agent_models.structure // .llm_settings.model' "$settings")

    echo "--structure-model $model --character-model $model --summary-model $model --pronunciation-model $model"
}

# Run the analysis pipeline for a single text
run_analysis() {
    local name="$1"
    local file="$2"
    local text_log="$DIAG_LOG_DIR/${name}_analyze.log"
    local output_dir="$OUTPUT_DIR/$name"

    mkdir -p "$output_dir"

    log "Analyzing: $name ($file)"
    local start_time=$SECONDS

    # Build the command
    local model_flags
    model_flags=$(get_model_flags)

    # Get competitive mode from manifest
    local comp_mode
    comp_mode=$(jq -r '.competitive_mode // "single"' "$STATE_DIR/manifest.json")
    local comp_flags=""
    if [ "$comp_mode" = "single" ]; then
        comp_flags="--competitive-consensus"
    fi

    # Run analysis from project root
    cd "$PROJECT_ROOT"

    local cmd="python -m src.cli analyze \"$file\" \
        --html \"$output_dir/report.html\" \
        --output \"$output_dir/analysis.json\" \
        $comp_flags \
        $model_flags"

    log "Command: $cmd"

    if eval "$cmd" > "$text_log" 2>&1; then
        local elapsed=$(( SECONDS - start_time ))
        log "  DONE: $name (${elapsed}s)"
        cd "$SCRIPT_DIR"
        return 0
    else
        local elapsed=$(( SECONDS - start_time ))
        log "  FAILED: $name (${elapsed}s) — see $text_log"
        cd "$SCRIPT_DIR"
        return 1
    fi
}

# Score a text's output using Claude
score_with_claude() {
    local name="$1"
    local score_log="$DIAG_LOG_DIR/${name}_score.log"
    local scores_file="$DIAG_LOG_DIR/${name}_scores.json"

    log "Scoring: $name (using Claude)"

    # Build a focused scoring prompt
    local prompt
    prompt=$(cat << SCOREEOF
You are scoring the output of an audiobook analysis pipeline for the text "$name".

## Task
Examine the analysis output and HTML report, then score each category on a 1-10 scale.

## Files to Read
1. ../output/$name/analysis.json — the pipeline output (relative to oracle-loop/)
2. ../output/$name/report.html — the HTML report

## Scoring Rubric
Score each category 1-10 based on these criteria:

- **Structure** (chapter/section detection): 10=perfect boundaries, 8=minor issues, 6=significant errors, 4=major failures
- **Characters** (extraction & identity): 10=all characters correct, 8=minor missing/extra, 6=identity confusion, 4=major failures
- **Profiles** (descriptions, quotes, relationships): 10=rich+accurate, 8=mostly complete, 6=significant gaps, 4=mostly empty
- **Summaries** (chapter summaries): 10=accurate+complete, 8=minor inaccuracies, 6=significant errors, 4=misleading
- **Pronunciation** (IPA guide): 10=complete+accurate, 8=minor gaps, 6=many false positives/missing, 4=unusable
- **Presentation** (HTML report): 10=polished+navigable, 8=functional+clean, 6=layout issues, 4=broken

## Output Format
After your analysis, output EXACTLY this JSON block (and nothing else after it):

\`\`\`json
{
  "text": "$name",
  "scores": {
    "structure": <score>,
    "characters": <score>,
    "profiles": <score>,
    "summaries": <score>,
    "pronunciation": <score>,
    "presentation": <score>
  },
  "overall": <weighted_average>,
  "pass": <true if ALL categories >= 8.0>,
  "issues": [
    {"category": "<category>", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "description": "<brief description>"}
  ],
  "notes": "<1-2 sentence summary of key findings>"
}
\`\`\`
SCOREEOF
)

    cd "$SCRIPT_DIR"

    # Use Claude for scoring
    # Find claude binary - may not be in PATH when run via SSH
    local claude_bin
    claude_bin=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")

    echo "$prompt" | "$claude_bin" -p \
        --model opus \
        --dangerously-skip-permissions \
        2>&1 | tee "$score_log"

    # Extract the JSON scores from Claude's plain text output
    local json_block
    json_block=$(python3 - "$score_log" << 'EXTRACTEOF'
import re, json, sys

with open(sys.argv[1]) as f:
    text = f.read()

# Try fenced JSON block first
m = re.search(r'```json\s*\n(.*?)```', text, re.DOTALL)
if m:
    try:
        parsed = json.loads(m.group(1).strip())
        print(json.dumps(parsed))
        sys.exit(0)
    except json.JSONDecodeError:
        pass

# Try to find a JSON object with 'scores' key by matching braces
for m in re.finditer(r'\{', text):
    start = m.start()
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                try:
                    parsed = json.loads(candidate)
                    if 'scores' in parsed:
                        print(json.dumps(parsed))
                        sys.exit(0)
                except json.JSONDecodeError:
                    pass
                break
EXTRACTEOF
)

    if [ -n "$json_block" ]; then
        echo "$json_block" > "$scores_file"
        log "  Scores saved: $scores_file"

        # Show scores inline
        local overall
        overall=$(echo "$json_block" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{d[\"overall\"]:.2f}')" 2>/dev/null || echo "?")
        local pass_status
        pass_status=$(echo "$json_block" | python3 -c "import json,sys; d=json.load(sys.stdin); print('PASS' if d.get('pass') else 'FAIL')" 2>/dev/null || echo "?")
        log "  Result: $name — $overall/10 ($pass_status)"
        return 0
    else
        log "  WARNING: Could not extract scores from Claude output for $name"
        return 1
    fi
}

# Build the failure matrix from all score files
build_matrix() {
    log "Building failure matrix..."

    local matrix='{"timestamp": "'$(date -Iseconds)'", "texts": {}, "column_stats": {}}'

    # Collect all score files
    for scores_file in "$DIAG_LOG_DIR"/*_scores.json; do
        [ -f "$scores_file" ] || continue

        local name
        name=$(python3 -c "import json; d=json.load(open('$scores_file')); print(d['text'])" 2>/dev/null || continue)

        matrix=$(echo "$matrix" | python3 -c "
import json, sys
matrix = json.load(sys.stdin)
scores = json.load(open('$scores_file'))
matrix['texts'][scores['text']] = scores
json.dump(matrix, sys.stdout)
" 2>/dev/null)
    done

    # Also incorporate historical known-good baselines from checkpoints.json
    matrix=$(echo "$matrix" | python3 -c "
import json, sys
matrix = json.load(sys.stdin)

try:
    checkpoints = json.load(open('$STATE_DIR/checkpoints.json'))
    baselines = checkpoints.get('known_good_baseline', {})
    for name, data in baselines.items():
        if name not in matrix['texts']:
            # Use historical data for texts we didn't score this run
            matrix['texts'][name] = {
                'text': name,
                'scores': data.get('category_scores', {}),
                'overall': data.get('score', 0),
                'pass': all(v >= 8.0 for v in data.get('category_scores', {}).values() if v),
                'issues': [],
                'notes': '(historical baseline from checkpoints.json)',
                'source': 'historical'
            }
except Exception as e:
    pass

# Compute column statistics
categories = ['structure', 'characters', 'profiles', 'summaries', 'pronunciation', 'presentation']
for cat in categories:
    scores = []
    failing = []
    for name, data in matrix['texts'].items():
        s = data.get('scores', {}).get(cat)
        if s is not None and s > 0:
            scores.append(s)
            if s < 8.0:
                failing.append(name)

    if scores:
        matrix['column_stats'][cat] = {
            'mean': round(sum(scores) / len(scores), 2),
            'min': min(scores),
            'max': max(scores),
            'count': len(scores),
            'failing_count': len(failing),
            'failing_texts': failing
        }

json.dump(matrix, sys.stdout, indent=2)
")

    echo "$matrix" > "$MATRIX_FILE"
    log "Matrix saved: $MATRIX_FILE"
}

# Generate the human-readable diagnostic report
generate_report() {
    log "Generating diagnostic report..."

    python3 << 'PYEOF' > "$REPORT_FILE"
import json
from datetime import datetime

matrix = json.load(open("state/diagnostic_matrix.json"))
texts = matrix.get("texts", {})
stats = matrix.get("column_stats", {})

categories = ["structure", "characters", "profiles", "summaries", "pronunciation", "presentation"]
cat_weights = {"structure": 0.20, "characters": 0.25, "profiles": 0.15, "summaries": 0.20, "pronunciation": 0.10, "presentation": 0.10}

print("# Cross-Book Diagnostic Report")
print(f"\nGenerated: {matrix.get('timestamp', 'unknown')}")
print(f"Texts scored: {len(texts)}")
print()

# === Failure Matrix ===
print("## Failure Matrix")
print()
header = f"{'Text':<35}  {'Str':>5} {'Chr':>5} {'Pro':>5} {'Sum':>5} {'Prn':>5} {'Prs':>5}  {'Avg':>5} {'':>6}"
print(header)
print("-" * len(header))

for name in sorted(texts.keys()):
    data = texts[name]
    scores = data.get("scores", {})
    row = f"{name:<35} "
    for cat in categories:
        s = scores.get(cat, 0)
        if s == 0:
            row += f" {'?':>4} "
        elif s < 8.0:
            row += f"{s:5.1f}*"  # asterisk marks failing
        else:
            row += f"{s:5.1f} "

    overall = data.get("overall", 0)
    status = "PASS" if data.get("pass") else "FAIL"
    row += f" {overall:5.2f} {status:>6}"
    print(row)

print()
print("(* = below 8.0 threshold)")
print()

# === Column Analysis ===
print("## Systemic Patterns (Column Analysis)")
print()

# Sort categories by number of failures (worst first)
sorted_cats = sorted(categories, key=lambda c: stats.get(c, {}).get("failing_count", 0), reverse=True)

for cat in sorted_cats:
    s = stats.get(cat, {})
    if not s:
        continue

    failing = s.get("failing_count", 0)
    total = s.get("count", 0)
    fail_rate = (failing / total * 100) if total > 0 else 0

    severity = "CRITICAL" if fail_rate >= 50 else "HIGH" if fail_rate >= 30 else "MEDIUM" if fail_rate >= 15 else "LOW"

    print(f"### {cat.title()} — {severity} ({failing}/{total} texts failing, {fail_rate:.0f}%)")
    print(f"  Mean: {s.get('mean', 0):.2f} | Min: {s.get('min', 0):.1f} | Max: {s.get('max', 0):.1f}")

    if s.get("failing_texts"):
        print(f"  Failing: {', '.join(s['failing_texts'])}")
    print()

# === Priority Fix Recommendations ===
print("## Priority Fix Recommendations")
print()
print("Fix systemic patterns (column issues) before per-text issues (row issues).")
print("A fix is only accepted if it helps multiple texts without regressing others.")
print()

fix_num = 1
for cat in sorted_cats:
    s = stats.get(cat, {})
    failing = s.get("failing_count", 0)
    if failing >= 2:  # Only recommend fixes for patterns across 2+ texts
        fail_pct = (failing / s.get("count", 1)) * 100
        print(f"{fix_num}. **{cat.title()}** ({failing} texts failing, weight: {cat_weights[cat]*100:.0f}%)")

        # Collect common issues for this category across failing texts
        common_issues = []
        for text_name in s.get("failing_texts", []):
            tdata = texts.get(text_name, {})
            for issue in tdata.get("issues", []):
                if issue.get("category", "").lower() == cat:
                    common_issues.append(f"  - [{text_name}] {issue.get('description', 'unknown')}")

        if common_issues:
            for ci in common_issues[:5]:  # Show top 5
                print(ci)
        print()
        fix_num += 1

if fix_num == 1:
    print("No systemic patterns detected across 2+ texts. Consider running more texts.")

# === Per-Text Summary ===
print()
print("## Per-Text Notes")
print()
for name in sorted(texts.keys()):
    data = texts[name]
    notes = data.get("notes", "")
    source = data.get("source", "fresh")
    if notes:
        src_tag = " (historical)" if source == "historical" else ""
        print(f"- **{name}**{src_tag}: {notes}")

PYEOF

    log "Report saved: $REPORT_FILE"
}

# =============================================================================
# Main Flow
# =============================================================================

echo ""
echo "========================================"
echo "  Oracle Loop — Cross-Book Diagnostic"
echo "========================================"
echo "Timestamp: $TIMESTAMP"
echo "Scorer: $SCORER"
echo "Log dir: $DIAG_LOG_DIR"
echo "========================================"
echo ""

if [ "$REPORT_ONLY" = "true" ]; then
    if [ -f "$MATRIX_FILE" ]; then
        generate_report
        log "Report regenerated from existing matrix."
        cat "$REPORT_FILE"
        exit 0
    else
        echo "Error: No matrix file found at $MATRIX_FILE. Run diagnostic first."
        exit 1
    fi
fi

# Get texts to process
TEXTS=($(get_text_list))
TOTAL=${#TEXTS[@]}

log "Texts to process ($TOTAL): ${TEXTS[*]}"

if [ "$TOTAL" -eq 0 ]; then
    echo "No texts to process. Use --all to include passing texts."
    exit 0
fi

# Process each text
ANALYZED=0
SCORED=0
FAILED_ANALYSIS=()
FAILED_SCORING=()

for name in "${TEXTS[@]}"; do
    echo ""
    echo "========================================"
    echo "  [$((ANALYZED + 1))/$TOTAL] $name"
    echo "========================================"

    file=$(get_text_file "$name")

    if [ -z "$file" ]; then
        log "WARNING: No file found for $name in manifest"
        FAILED_ANALYSIS+=("$name")
        continue
    fi

    # Step 1: Run analysis (unless --score-only)
    if [ "$SCORE_ONLY" = "false" ]; then
        # Check if output already exists (skip if recent, within 24h)
        local_analysis="$OUTPUT_DIR/$name/analysis.json"
        if [ -f "$local_analysis" ]; then
            age=$(( $(date +%s) - $(stat -c %Y "$local_analysis" 2>/dev/null || echo 0) ))
            if [ "$age" -lt 86400 ]; then
                log "  Skipping analysis (output < 24h old). Use --all to force."
            else
                if ! run_analysis "$name" "$file"; then
                    FAILED_ANALYSIS+=("$name")
                    continue
                fi
            fi
        else
            if ! run_analysis "$name" "$file"; then
                FAILED_ANALYSIS+=("$name")
                continue
            fi
        fi
    fi

    ANALYZED=$((ANALYZED + 1))

    # Step 2: Score the output
    if [ "$SCORER" = "claude" ]; then
        if ! score_with_claude "$name"; then
            FAILED_SCORING+=("$name")
            continue
        fi
    else
        log "  Local scoring not yet implemented. Use --scorer claude"
        FAILED_SCORING+=("$name")
        continue
    fi

    SCORED=$((SCORED + 1))

    # Brief pause between texts to avoid rate limiting
    if [ "$SCORED" -lt "$TOTAL" ]; then
        log "  Pausing 3s before next text..."
        sleep 3
    fi
done

echo ""
echo "========================================"
echo "  Analysis Complete"
echo "========================================"
echo "  Analyzed: $ANALYZED/$TOTAL"
echo "  Scored:   $SCORED/$TOTAL"
if [ ${#FAILED_ANALYSIS[@]} -gt 0 ]; then
    echo "  Failed analysis: ${FAILED_ANALYSIS[*]}"
fi
if [ ${#FAILED_SCORING[@]} -gt 0 ]; then
    echo "  Failed scoring: ${FAILED_SCORING[*]}"
fi
echo "========================================"
echo ""

# Step 3: Build the failure matrix
build_matrix

# Step 4: Generate the diagnostic report
generate_report

echo ""
echo "========================================"
echo "  Diagnostic Report"
echo "========================================"
cat "$REPORT_FILE"

echo ""
echo "Files:"
echo "  Matrix: $MATRIX_FILE"
echo "  Report: $REPORT_FILE"
echo "  Logs:   $DIAG_LOG_DIR/"
echo ""
