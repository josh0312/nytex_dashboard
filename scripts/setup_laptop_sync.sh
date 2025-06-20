#!/bin/bash
# Setup script for laptop-friendly sync scheduling
# Handles missed syncs when laptop is asleep

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Setting up laptop-friendly sync scheduling"
echo "Project directory: $PROJECT_DIR"

# Make smart sync orchestrator executable
chmod +x "$SCRIPT_DIR/smart_sync_orchestrator.py"

echo ""
echo "Choose your preferred method:"
echo "1. launchd (Recommended for macOS) - Handles power management better"
echo "2. Enhanced cron with hourly checks - Works with existing cron setup"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "📋 Setting up launchd job..."
        
        # Copy plist to user LaunchAgents directory
        PLIST_SRC="$SCRIPT_DIR/com.nytex.daily-sync.plist"
        PLIST_DEST="$HOME/Library/LaunchAgents/com.nytex.daily-sync.plist"
        
        # Create LaunchAgents directory if it doesn't exist
        mkdir -p "$HOME/Library/LaunchAgents"
        
        # Copy the plist file
        cp "$PLIST_SRC" "$PLIST_DEST"
        
        echo "✅ Copied plist to: $PLIST_DEST"
        
        # Remove existing cron job if it exists
        echo "🧹 Removing existing cron job..."
        (crontab -l 2>/dev/null | grep -v "sync_orchestrator.py" || true) | crontab -
        
        # Load the launchd job
        launchctl load "$PLIST_DEST"
        
        echo ""
        echo "✅ launchd job setup complete!"
        echo ""
        echo "Commands to manage the job:"
        echo "  Start:   launchctl start com.nytex.daily-sync"
        echo "  Stop:    launchctl stop com.nytex.daily-sync"
        echo "  Unload:  launchctl unload $PLIST_DEST"
        echo "  Status:  launchctl list | grep nytex"
        echo ""
        echo "Logs will be written to:"
        echo "  Output: $PROJECT_DIR/logs/launchd_sync.log"
        echo "  Errors: $PROJECT_DIR/logs/launchd_sync_error.log"
        ;;
    
    2)
        echo ""
        echo "⏰ Setting up enhanced cron with hourly checks..."
        
        # Remove existing daily cron job
        echo "🧹 Removing existing daily cron job..."
        (crontab -l 2>/dev/null | grep -v "sync_orchestrator.py" || true) | crontab -
        
        # Add new hourly cron job that uses smart sync
        echo "➕ Adding hourly smart sync job..."
        (
            crontab -l 2>/dev/null || true
            echo ""
            echo "# Nytex Smart Sync - Check every hour for missed syncs"
            echo "0 * * * * cd $PROJECT_DIR && $PROJECT_DIR/.venv/bin/python $SCRIPT_DIR/smart_sync_orchestrator.py >> $PROJECT_DIR/logs/smart_sync.log 2>&1"
        ) | crontab -
        
        echo ""
        echo "✅ Enhanced cron setup complete!"
        echo ""
        echo "The sync will now:"
        echo "  - Check every hour if a sync is needed"
        echo "  - Run at 1 AM if laptop is awake"
        echo "  - Run when laptop wakes up if it missed the 1 AM sync"
        echo "  - Never run more than once per day"
        echo ""
        echo "Logs will be written to:"
        echo "  $PROJECT_DIR/logs/smart_sync.log"
        ;;
    
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "🧪 Testing the setup..."

# Test the smart sync orchestrator
echo "Running smart sync check..."
cd "$PROJECT_DIR"
python "$SCRIPT_DIR/smart_sync_orchestrator.py" --check-only

echo ""
echo "🎉 Setup complete!"
echo ""
echo "You can test the sync manually with:"
echo "  python $SCRIPT_DIR/smart_sync_orchestrator.py --check-only  # Check if sync is needed"
echo "  python $SCRIPT_DIR/smart_sync_orchestrator.py --force       # Force sync now"
echo "  python $SCRIPT_DIR/smart_sync_orchestrator.py              # Run smart sync" 