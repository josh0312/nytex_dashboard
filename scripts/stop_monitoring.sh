#!/bin/bash
# Stop continuous monitoring
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/monitoring.pid"

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm "$PID_FILE"
        echo "✅ Monitoring stopped (PID: $PID)"
    else
        echo "⚠️  Process $PID not running"
        rm "$PID_FILE"
    fi
else
    echo "ℹ️  No monitoring PID file found"
fi 