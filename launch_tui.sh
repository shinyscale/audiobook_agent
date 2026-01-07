#!/bin/bash
# Launcher script for Audiobook Prep TUI

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if JSON file argument provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <analysis.json>"
    echo ""
    echo "Opens the TUI with an existing analysis JSON file."
    echo ""
    echo "Example:"
    echo "  $0 output/gatsby.analysis.json"
    exit 1
fi

JSON_FILE="$1"

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: File not found: $JSON_FILE"
    exit 1
fi

# Launch TUI
python -m src.gui.tui "$JSON_FILE"





