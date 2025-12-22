#!/bin/bash
# Launcher script for Audiobook Prep Analysis with TUI

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if file argument provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <book.pdf|book.epub|book.docx|book.txt> [options]"
    echo ""
    echo "Analyzes a book and opens the TUI with results."
    echo ""
    echo "Options:"
    echo "  --output PATH    Save JSON to specific path"
    echo "  --html PATH      Also generate HTML report"
    echo "  --wpm N          Words per minute (default: 150)"
    echo "  --no-tui         Don't open TUI after analysis"
    echo ""
    echo "Examples:"
    echo "  $0 book.pdf"
    echo "  $0 book.epub --html report.html"
    echo "  $0 book.txt --wpm 160"
    exit 1
fi

BOOK_FILE="$1"
shift  # Remove first argument, pass rest to audiobook-prep

# Run analysis with TUI
./venv/bin/audiobook-prep analyze "$BOOK_FILE" --tui "$@"




