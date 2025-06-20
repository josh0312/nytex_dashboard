#!/usr/bin/env python3
"""
Smart Sync Orchestrator - Handles missed syncs for laptop environments

This script:
1. Checks if a sync should have run but didn't (laptop was asleep)
2. Runs the sync if it's overdue
3. Can be run more frequently (e.g., every hour) to catch missed syncs

Usage:
    python scripts/smart_sync_orchestrator.py              # Check and run if needed
    python scripts/smart_sync_orchestrator.py --force      # Force sync regardless
    python scripts/smart_sync_orchestrator.py --check-only # Just check, don't run
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.sync_orchestrator import SyncOrchestrator, OrchestratorConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger('smart_sync')

class SmartSyncOrchestrator:
    """Smart orchestrator that handles missed syncs"""
    
    def __init__(self):
        self.config = OrchestratorConfig()
        self.orchestrator = SyncOrchestrator(self.config)
        self.last_sync_file = Path('logs/last_sync_check.txt')
        self.scheduled_hour = 1  # 1 AM Central
        
    def get_last_successful_sync(self) -> datetime:
        """Get the timestamp of the last successful sync"""
        try:
            if self.last_sync_file.exists():
                with open(self.last_sync_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"Could not read last sync timestamp: {e}")
        
        # Default to yesterday if no record
        return datetime.now() - timedelta(days=1)
    
    def record_successful_sync(self):
        """Record the current time as last successful sync"""
        try:
            os.makedirs(self.last_sync_file.parent, exist_ok=True)
            with open(self.last_sync_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logger.error(f"Could not record sync timestamp: {e}")
    
    def should_sync_now(self) -> tuple[bool, str]:
        """Check if we should sync now and return reason"""
        now = datetime.now()
        last_sync = self.get_last_successful_sync()
        
        # Check if we're past the scheduled time for today
        today_scheduled = now.replace(hour=self.scheduled_hour, minute=0, second=0, microsecond=0)
        
        # If it's past 1 AM today and we haven't synced since yesterday
        if now > today_scheduled and last_sync < today_scheduled:
            hours_overdue = (now - today_scheduled).total_seconds() / 3600
            return True, f"Sync overdue by {hours_overdue:.1f} hours (last sync: {last_sync.strftime('%Y-%m-%d %H:%M')})"
        
        # If we're in the scheduled hour (1-2 AM) and haven't synced today
        if now.hour == self.scheduled_hour and last_sync.date() < now.date():
            return True, f"In scheduled hour and no sync today (last sync: {last_sync.strftime('%Y-%m-%d %H:%M')})"
        
        # If it's been more than 25 hours since last sync (missed yesterday)
        hours_since_sync = (now - last_sync).total_seconds() / 3600
        if hours_since_sync > 25:
            return True, f"Been {hours_since_sync:.1f} hours since last sync (overdue)"
        
        return False, f"No sync needed (last sync: {last_sync.strftime('%Y-%m-%d %H:%M')}, next: {(today_scheduled + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')})"
    
    async def run_smart_sync(self, force: bool = False, check_only: bool = False) -> bool:
        """Run sync intelligently based on schedule and missed runs"""
        logger.info("🧠 Smart Sync Orchestrator")
        logger.info("=" * 50)
        
        should_sync, reason = self.should_sync_now()
        
        if force:
            should_sync = True
            reason = "Forced sync requested"
        
        logger.info(f"📊 Status: {reason}")
        
        if not should_sync:
            logger.info("✅ No sync needed at this time")
            return True
        
        if check_only:
            logger.info("🔍 Check-only mode: Would run sync now")
            return True
        
        logger.info("🚀 Running sync...")
        
        try:
            # Run the actual sync
            results = await self.orchestrator.run_sync()
            
            # Check if sync was successful
            successful_syncs = sum(1 for result in results.values() if result.success)
            total_syncs = len(results)
            
            if successful_syncs == total_syncs and total_syncs > 0:
                logger.info(f"✅ Sync completed successfully ({successful_syncs}/{total_syncs} succeeded)")
                self.record_successful_sync()
                return True
            else:
                logger.error(f"❌ Sync partially failed ({successful_syncs}/{total_syncs} succeeded)")
                return False
                
        except Exception as e:
            logger.error(f"❌ Sync failed with error: {e}")
            return False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Smart Sync Orchestrator')
    parser.add_argument('--force', action='store_true', help='Force sync regardless of schedule')
    parser.add_argument('--check-only', action='store_true', help='Check if sync is needed but don\'t run')
    
    args = parser.parse_args()
    
    smart_sync = SmartSyncOrchestrator()
    success = await smart_sync.run_smart_sync(force=args.force, check_only=args.check_only)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 