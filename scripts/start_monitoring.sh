#!/bin/bash
# Start continuous monitoring in the background
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting continuous deployment monitoring..."
nohup python3 "$SCRIPT_DIR/deployment_monitor.py" --continuous 30 --auto-fix > "$PROJECT_ROOT/logs/continuous_monitoring.log" 2>&1 &
echo $! > "$PROJECT_ROOT/logs/monitoring.pid"
echo "✅ Monitoring started (PID: $(cat "$PROJECT_ROOT/logs/monitoring.pid"))"
echo "Log: $PROJECT_ROOT/logs/continuous_monitoring.log" 