#!/bin/bash
# Quick check if analysis is complete
TASK_OUTPUT="/tmp/claude/-home-zacharymandrews-Tools-audiobook-agent-oracle-loop/tasks/b78b20f.output"

if grep -q "Analysis complete" "$TASK_OUTPUT" 2>/dev/null; then
    echo "✅ COMPLETE"
    tail -10 "$TASK_OUTPUT"
    exit 0
elif grep -q "Error during analysis" "$TASK_OUTPUT" 2>/dev/null; then
    echo "❌ ERROR"
    tail -20 "$TASK_OUTPUT"
    exit 1
else
    echo "🔄 RUNNING"
    tail -3 "$TASK_OUTPUT" 2>/dev/null
    exit 2
fi
