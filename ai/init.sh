#!/bin/bash
# Environment bootstrap for audiobook_agent development
# This script validates the development environment and shows feature status

set -e

echo "=== Audiobook Agent Development Environment ==="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$python_version" != "3.10" && "$python_version" != "3.11" && "$python_version" != "3.12" ]]; then
    echo "ERROR: Python 3.10+ required, found $python_version"
    exit 1
else
    echo "Python: $python_version"
fi

# Check virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "WARNING: No virtual environment active"
    echo "  Run: python -m venv venv && source venv/bin/activate"
else
    echo "Venv: $(basename $VIRTUAL_ENV)"
fi

# Install dependencies (quiet mode)
echo ""
echo "Checking dependencies..."
pip install -e ".[dev]" --quiet 2>/dev/null || echo "  (install skipped - run manually if needed)"

# Download spaCy model if missing
if python -c "import spacy; spacy.load('en_core_web_lg')" 2>/dev/null; then
    echo "spaCy: en_core_web_lg loaded"
else
    echo "WARNING: spaCy model missing"
    echo "  Run: python -m spacy download en_core_web_lg"
fi

# Check Ollama
echo ""
if command -v ollama &> /dev/null; then
    echo "Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
    echo "Models available:"
    ollama list 2>/dev/null | head -10 || echo "  (ollama not running)"
else
    echo "WARNING: Ollama not found. Install from https://ollama.ai"
fi

# Check test corpus
echo ""
echo "Test corpus status:"
for book in gatsby frankenstein; do
    if [[ -f "Test_Texts/${book}.txt" ]]; then
        word_count=$(wc -w < "Test_Texts/${book}.txt")
        echo "  ${book}.txt (${word_count} words)"
    else
        echo "  ${book}.txt (MISSING)"
    fi
done

# Run quick validation
echo ""
echo "Import check..."
python3 -c "from src.analyzer import AudiobookAnalyzer; print('  src.analyzer OK')" 2>/dev/null || echo "  src.analyzer FAILED"
python3 -c "from src.agents.base import Agent; print('  src.agents OK')" 2>/dev/null || echo "  src.agents FAILED"

# Show feature status
echo ""
echo "Feature status:"
if [[ -f "ai/feature_list.json" ]]; then
    python3 -c "
import json
with open('ai/feature_list.json') as f:
    data = json.load(f)
print(f'  Phase: {data[\"current_phase\"]}')
print()
for f in data['features']:
    status = f['status']
    icon = 'PASS' if status == 'passing' else 'FAIL' if status == 'failing' else 'SKIP'
    grad = f.get('graduation', {})
    grad_status = grad.get('status', 'n/a') if isinstance(grad, dict) else 'n/a'
    print(f'  [{icon:4}] {f[\"id\"]:30} (grad: {grad_status})')
"
else
    echo "  (no feature_list.json found)"
fi

# Show recent progress
echo ""
if [[ -f "ai/progress.log" ]]; then
    echo "Recent progress (last 5 lines):"
    tail -5 ai/progress.log | sed 's/^/  /'
else
    echo "No progress.log found (will be created on first session)"
fi

echo ""
echo "=== Ready for development ==="
echo ""
echo "Next steps:"
echo "  1. Run: python ai/run_analysis.py gatsby"
echo "  2. Ask Claude Code to evaluate the output"
echo "  3. Iterate on failing features"
