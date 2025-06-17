#!/bin/bash
# Setup Deployment Monitoring Cron Jobs
# This script sets up automated monitoring for the NyTex Dashboard deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MONITOR_SCRIPT="$SCRIPT_DIR/deployment_monitor.py"
PYTHON_PATH="$(which python3)"

echo "============================================================"
echo "         Setting Up Deployment Monitoring"
echo "============================================================"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Check if monitoring script exists and is executable
if [[ ! -x "$MONITOR_SCRIPT" ]]; then
    echo "Making monitoring script executable..."
    chmod +x "$MONITOR_SCRIPT"
fi

# Test the monitoring script
echo "Testing monitoring script..."
if ! python3 "$MONITOR_SCRIPT" > /dev/null 2>&1; then
    echo "❌ Monitoring script test failed!"
    echo "Please check the script manually: python3 $MONITOR_SCRIPT"
    exit 1
fi
echo "✅ Monitoring script test passed"

# Create the cron job entries
CRON_JOBS=$(cat << EOF
# NyTex Dashboard Deployment Monitoring
# Check every 15 minutes during business hours (8 AM - 8 PM)
*/15 8-20 * * 1-5 cd $PROJECT_ROOT && $PYTHON_PATH $MONITOR_SCRIPT --auto-fix >> $PROJECT_ROOT/logs/monitoring.log 2>&1

# Check every hour outside business hours and on weekends
0 0-7,21-23 * * * cd $PROJECT_ROOT && $PYTHON_PATH $MONITOR_SCRIPT --auto-fix >> $PROJECT_ROOT/logs/monitoring.log 2>&1
0 * * * 0,6 cd $PROJECT_ROOT && $PYTHON_PATH $MONITOR_SCRIPT --auto-fix >> $PROJECT_ROOT/logs/monitoring.log 2>&1

# Daily comprehensive check at 6 AM with detailed logging
0 6 * * * cd $PROJECT_ROOT && $PYTHON_PATH $MONITOR_SCRIPT --auto-fix > $PROJECT_ROOT/logs/daily_health_\$(date +\%Y\%m\%d).log 2>&1
EOF
)

echo "Cron jobs to be added:"
echo "$CRON_JOBS"
echo ""

# Ask for confirmation
read -p "Add these cron jobs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Monitoring setup cancelled"
    exit 0
fi

# Backup existing crontab
echo "Backing up existing crontab..."
if crontab -l > /dev/null 2>&1; then
    crontab -l > "$PROJECT_ROOT/logs/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
    echo "✅ Crontab backed up"
else
    echo "ℹ️  No existing crontab found"
fi

# Add the new cron jobs
echo "Adding monitoring cron jobs..."
(
    # Keep existing crontab if it exists
    crontab -l 2>/dev/null || true
    echo ""
    echo "$CRON_JOBS"
) | crontab -

echo "✅ Cron jobs added successfully"

# Show current crontab
echo ""
echo "Current crontab:"
echo "============================================================"
crontab -l
echo "============================================================"

# Create monitoring management scripts
echo ""
echo "Creating monitoring management scripts..."

# Create start monitoring script
cat > "$SCRIPT_DIR/start_monitoring.sh" << 'EOF'
#!/bin/bash
# Start continuous monitoring in the background
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting continuous deployment monitoring..."
nohup python3 "$SCRIPT_DIR/deployment_monitor.py" --continuous 30 --auto-fix > "$PROJECT_ROOT/logs/continuous_monitoring.log" 2>&1 &
echo $! > "$PROJECT_ROOT/logs/monitoring.pid"
echo "✅ Monitoring started (PID: $(cat "$PROJECT_ROOT/logs/monitoring.pid"))"
echo "Log: $PROJECT_ROOT/logs/continuous_monitoring.log"
EOF

# Create stop monitoring script
cat > "$SCRIPT_DIR/stop_monitoring.sh" << 'EOF'
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
EOF

# Create check monitoring script
cat > "$SCRIPT_DIR/check_monitoring.sh" << 'EOF'
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
EOF

# Make scripts executable
chmod +x "$SCRIPT_DIR/start_monitoring.sh"
chmod +x "$SCRIPT_DIR/stop_monitoring.sh"
chmod +x "$SCRIPT_DIR/check_monitoring.sh"

echo "✅ Management scripts created:"
echo "  - $SCRIPT_DIR/start_monitoring.sh    (start continuous monitoring)"
echo "  - $SCRIPT_DIR/stop_monitoring.sh     (stop continuous monitoring)"
echo "  - $SCRIPT_DIR/check_monitoring.sh    (check monitoring status)"

echo ""
echo "============================================================"
echo "                 Setup Complete!"
echo "============================================================"
echo "Monitoring is now configured to:"
echo "  ✅ Check every 15 minutes during business hours"
echo "  ✅ Check hourly outside business hours"
echo "  ✅ Run daily comprehensive checks at 6 AM"
echo "  ✅ Automatically fix IAM permission issues"
echo "  ✅ Log all activity to $PROJECT_ROOT/logs/"
echo ""
echo "Management commands:"
echo "  ./scripts/check_monitoring.sh     # Check current status"
echo "  ./scripts/start_monitoring.sh     # Start continuous monitoring"
echo "  ./scripts/stop_monitoring.sh      # Stop continuous monitoring"
echo ""
echo "Manual monitoring:"
echo "  python3 scripts/deployment_monitor.py                # Single check"
echo "  python3 scripts/deployment_monitor.py --auto-fix     # Single check with auto-fix"
echo "  python3 scripts/deployment_monitor.py --continuous 30 # Continuous every 30 min" 