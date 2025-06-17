#!/bin/bash
# Check monitoring status
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/monitoring.pid"

echo "============================================================"
echo "         Deployment Monitoring Status"
echo "============================================================"

# Check cron jobs
echo "Cron Jobs:"
crontab -l | grep -E "(NyTex|deployment_monitor)" || echo "No monitoring cron jobs found"

echo ""

# Check continuous monitoring
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Continuous Monitoring: ✅ Running (PID: $PID)"
    else
        echo "Continuous Monitoring: ❌ Not running (stale PID file)"
    fi
else
    echo "Continuous Monitoring: ⚪ Not started"
fi

echo ""

# Show recent logs
echo "Recent monitoring activity:"
if [[ -f "$PROJECT_ROOT/logs/monitoring.log" ]]; then
    tail -5 "$PROJECT_ROOT/logs/monitoring.log"
else
    echo "No monitoring logs found"
fi 