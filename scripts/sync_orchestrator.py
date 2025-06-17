#!/usr/bin/env python3
"""
Sync Orchestrator Script

Coordinates daily synchronization of all Square data types:
- Orders (incremental)
- Catalog Items (full sync)
- Catalog Categories (full sync)
- Locations (full sync)
- Inventory (full sync)

Features:
- Configurable sync schedules
- Email notifications on failures
- Comprehensive logging
- Retry logic with exponential backoff
- Performance metrics tracking
- Environment-aware configuration

Usage:
    python scripts/sync_orchestrator.py [--data-type TYPE] [--force] [--dry-run]
    
Examples:
    python scripts/sync_orchestrator.py                    # Run all scheduled syncs
    python scripts/sync_orchestrator.py --data-type orders # Sync only orders
    python scripts/sync_orchestrator.py --force           # Force sync regardless of schedule
    python scripts/sync_orchestrator.py --dry-run         # Show what would be synced
"""

import sys
import os
import argparse
import logging
import smtplib
import asyncio
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dataclasses import dataclass
import time
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.sync_engine import SyncEngine, SyncConfig, SyncResult
from app.services.notifications import NotificationService

@dataclass
class NotificationConfig:
    """Email notification configuration"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_emails: List[str] = None
    enabled: bool = False

@dataclass
class OrchestratorConfig:
    """Orchestrator configuration"""
    # Sync schedules (hours between syncs)
    orders_schedule_hours: int = 24
    catalog_schedule_hours: int = 24
    locations_schedule_hours: int = 168  # Weekly
    inventory_schedule_hours: int = 24
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    retry_backoff_multiplier: float = 2.0
    
    # Notification settings
    notifications: NotificationConfig = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/sync_orchestrator.log"

class SyncOrchestrator:
    """Orchestrates synchronization across all Square data types"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.sync_engine = SyncEngine()
        self.notification_service = NotificationService()
        self.logger = self._setup_logging()
        
        # Define sync configurations for each data type
        self.sync_configs = {
            'orders': SyncConfig(
                data_type='orders',
                method='incremental',
                batch_size=500
            ),
            'catalog_items': SyncConfig(
                data_type='catalog_items',
                method='full',
                batch_size=100
            ),
            'catalog_categories': SyncConfig(
                data_type='catalog_categories',
                method='full',
                batch_size=100
            ),
            'locations': SyncConfig(
                data_type='locations',
                method='full',
                batch_size=50
            ),
            'inventory': SyncConfig(
                data_type='inventory',
                method='incremental',
                batch_size=100
            )
        }
        
        # Schedule mapping
        self.schedules = {
            'orders': self.config.orders_schedule_hours,
            'catalog_items': self.config.catalog_schedule_hours,
            'catalog_categories': self.config.catalog_schedule_hours,
            'locations': self.config.locations_schedule_hours,
            'inventory': self.config.inventory_schedule_hours
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('sync_orchestrator')
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.config.log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    async def _is_sync_due(self, data_type: str) -> bool:
        """Check if a sync is due for the given data type"""
        try:
            last_sync = await self.sync_engine._get_last_sync_timestamp(data_type)
            if not last_sync:
                return True
            
            schedule_hours = self.schedules.get(data_type, 24)
            time_since_sync = datetime.now() - last_sync
            
            return time_since_sync >= timedelta(hours=schedule_hours)
            
        except Exception as e:
            self.logger.warning(f"Could not check sync schedule for {data_type}: {e}")
            return True  # Default to syncing if we can't determine
    
    async def _sync_with_retry(self, data_type: str) -> SyncResult:
        """Sync a data type with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.info(f"Starting sync for {data_type} (attempt {attempt + 1})")
                
                # Call the appropriate sync method based on data type
                if data_type == 'orders':
                    result = await self.sync_engine.sync_orders()
                elif data_type == 'catalog_items':
                    result = await self.sync_engine.sync_catalog_items()
                elif data_type == 'catalog_categories':
                    result = await self.sync_engine.sync_catalog_categories()
                elif data_type == 'locations':
                    result = await self.sync_engine.sync_locations()
                elif data_type == 'inventory':
                    result = await self.sync_engine.sync_inventory()
                else:
                    raise ValueError(f"Unknown data type: {data_type}")
                
                if result.success:
                    self.logger.info(f"Successfully synced {data_type}: {result.records_processed} records")
                    return result
                else:
                    error_msg = ', '.join(result.errors) if result.errors else "Unknown error"
                    self.logger.warning(f"Sync failed for {data_type}: {error_msg}")
                    last_exception = Exception(error_msg)
                    
            except Exception as e:
                self.logger.error(f"Sync attempt {attempt + 1} failed for {data_type}: {e}")
                last_exception = e
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay_seconds * (self.config.retry_backoff_multiplier ** attempt)
                self.logger.info(f"Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)
        
        # All retries failed
        error_msg = f"All {self.config.max_retries + 1} sync attempts failed for {data_type}"
        if last_exception:
            error_msg += f": {last_exception}"
        
        return SyncResult(
            success=False,
            data_type=data_type,
            records_processed=0,
            errors=[error_msg],
            duration_seconds=0
        )
    
    def _get_environment(self) -> str:
        """Determine the current environment"""
        return os.getenv('ENVIRONMENT', os.getenv('ENV', 'development'))
    
    async def run_sync(self, data_types: Optional[List[str]] = None, force: bool = False, dry_run: bool = False) -> Dict[str, SyncResult]:
        """Run synchronization for specified data types or all scheduled syncs"""
        start_time = datetime.now()
        self.logger.info(f"Starting sync orchestrator at {start_time}")
        
        # Determine which data types to sync
        if data_types:
            sync_targets = [dt for dt in data_types if dt in self.sync_configs]
        else:
            sync_targets = list(self.sync_configs.keys())
        
        # Filter by schedule unless forced
        if not force:
            # Check each data type asynchronously
            due_checks = await asyncio.gather(*[self._is_sync_due(dt) for dt in sync_targets])
            sync_targets = [dt for dt, is_due in zip(sync_targets, due_checks) if is_due]
        
        if dry_run:
            self.logger.info("DRY RUN - Would sync the following data types:")
            for dt in sync_targets:
                last_sync = await self.sync_engine._get_last_sync_timestamp(dt)
                self.logger.info(f"  {dt}: last sync = {last_sync or 'never'}")
            return {}
        
        if not sync_targets:
            self.logger.info("No syncs are due at this time")
            return {}
        
        self.logger.info(f"Syncing data types: {sync_targets}")
        
        # Execute syncs
        results = {}
        failed_syncs = []
        
        for data_type in sync_targets:
            self.logger.info(f"Processing {data_type}...")
            result = await self._sync_with_retry(data_type)
            results[data_type] = result
            
            if not result.success:
                failed_syncs.append(data_type)
        
        # Generate summary
        end_time = datetime.now()
        total_duration = end_time - start_time
        
        summary = self._generate_summary(results, total_duration)
        self.logger.info(summary)
        
        # Send notifications
        if failed_syncs:
            # Send failure alert
            self.notification_service.send_sync_failure_alert(results, self._get_environment())
        else:
            # Send success report (only if all syncs succeeded)
            self.notification_service.send_sync_success_report(results, self._get_environment())
        
        return results
    
    def _generate_summary(self, results: Dict[str, SyncResult], total_duration: timedelta) -> str:
        """Generate a summary of sync results"""
        summary_lines = [
            "=== SYNC ORCHESTRATOR SUMMARY ===",
            f"Total Duration: {total_duration}",
            f"Data Types Processed: {len(results)}",
            ""
        ]
        
        successful = 0
        failed = 0
        total_records = 0
        
        for data_type, result in results.items():
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            duration = f"{result.duration_seconds:.1f}s"
            records = result.records_processed
            
            summary_lines.append(f"{data_type}: {status} - {records} records in {duration}")
            
            if result.success:
                successful += 1
                total_records += records
            else:
                failed += 1
                if result.error_message:
                    summary_lines.append(f"  Error: {result.error_message}")
        
        summary_lines.extend([
            "",
            f"Summary: {successful} successful, {failed} failed",
            f"Total Records Processed: {total_records}",
            "================================="
        ])
        
        return "\n".join(summary_lines)

def load_config() -> OrchestratorConfig:
    """Load configuration from environment variables and defaults"""
    config = OrchestratorConfig()
    
    # Notification configuration
    notifications = NotificationConfig()
    notifications.enabled = os.getenv('SYNC_NOTIFICATIONS_ENABLED', 'false').lower() == 'true'
    notifications.sender_email = os.getenv('SYNC_NOTIFICATION_EMAIL', '')
    notifications.sender_password = os.getenv('SYNC_NOTIFICATION_PASSWORD', '')
    notifications.recipient_emails = os.getenv('SYNC_NOTIFICATION_RECIPIENTS', '').split(',')
    notifications.recipient_emails = [email.strip() for email in notifications.recipient_emails if email.strip()]
    
    config.notifications = notifications
    
    # Sync schedules (can be overridden via environment)
    config.orders_schedule_hours = int(os.getenv('SYNC_ORDERS_SCHEDULE_HOURS', '24'))
    config.catalog_schedule_hours = int(os.getenv('SYNC_CATALOG_SCHEDULE_HOURS', '24'))
    config.locations_schedule_hours = int(os.getenv('SYNC_LOCATIONS_SCHEDULE_HOURS', '168'))
    config.inventory_schedule_hours = int(os.getenv('SYNC_INVENTORY_SCHEDULE_HOURS', '24'))
    
    # Retry configuration
    config.max_retries = int(os.getenv('SYNC_MAX_RETRIES', '3'))
    config.retry_delay_seconds = int(os.getenv('SYNC_RETRY_DELAY', '300'))
    
    # Logging
    config.log_level = os.getenv('SYNC_LOG_LEVEL', 'INFO')
    config.log_file = os.getenv('SYNC_LOG_FILE', 'logs/sync_orchestrator.log')
    
    return config

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NYTEX Square Data Sync Orchestrator')
    parser.add_argument('--data-type', choices=['orders', 'catalog_items', 'catalog_categories', 'locations', 'inventory'],
                       help='Sync only the specified data type')
    parser.add_argument('--force', action='store_true',
                       help='Force sync regardless of schedule')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be synced without actually syncing')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Create orchestrator
    orchestrator = SyncOrchestrator(config)
    
    # Determine data types to sync
    data_types = [args.data_type] if args.data_type else None
    
    try:
        # Run sync
        results = await orchestrator.run_sync(
            data_types=data_types,
            force=args.force,
            dry_run=args.dry_run
        )
        
        # Exit with error code if any syncs failed
        if any(not result.success for result in results.values()):
            sys.exit(1)
        
    except Exception as e:
        orchestrator.logger.error(f"Orchestrator failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 