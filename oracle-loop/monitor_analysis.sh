#!/bin/bash
# Monitor the Frankenstein analysis and report when complete

TASK_OUTPUT="/tmp/claude/-home-zacharymandrews-Tools-audiobook-agent-oracle-loop/tasks/b78b20f.output"
CHECK_INTERVAL=60  # Check every 60 seconds

echo "Monitoring Frankenstein analysis (task b78b20f)..."
echo "Started at: $(date)"
echo ""

while true; do
    # Check if the process is still running
    if ps aux | grep -q "[a]udiobook-prep analyze"; then
        # Get last few lines to show progress
        echo "=== $(date) ==="
        tail -5 "$TASK_OUTPUT" 2>/dev/null
        echo ""
        sleep $CHECK_INTERVAL
    else
        echo "=== Analysis Complete at $(date) ==="
        tail -20 "$TASK_OUTPUT"
        break
    fi
done

echo ""
echo "Output files:"
ls -lh ../output/frankenstein/ 2>/dev/null || echo "Output directory not found"
