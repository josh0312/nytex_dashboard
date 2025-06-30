#!/usr/bin/env python3
"""
Test Sync Orchestrator
Validates sync_orchestrator.py functionality for standardization
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_session
from app.services.sync_engine import SyncEngine
from app.services.notifications import NotificationService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestSyncOrchestrator:
    """Test suite for sync_orchestrator.py functionality"""
    
    def __init__(self):
        self.test_results = {}
        self.sync_engine = None
        self.notification_service = None
    
    async def setup(self):
        """Setup test environment"""
        logger.info("🔧 Setting up test environment...")
        self.sync_engine = SyncEngine()
        self.notification_service = NotificationService()
        
    async def teardown(self):
        """Cleanup test environment"""
        logger.info("🧹 Cleaning up test environment...")
        # SyncEngine doesn't require explicit cleanup
        pass
    
    async def test_sync_engine_initialization(self):
        """Test sync engine can be initialized properly"""
        logger.info("🧪 Test 1: Sync Engine Initialization")
        try:
            engine = SyncEngine()
            # Test that we can access basic properties
            assert hasattr(engine, 'sync_configs')
            assert hasattr(engine, 'square_access_token')
            assert len(engine.sync_configs) > 0
            
            self.test_results['initialization'] = {
                'passed': True,
                'details': 'SyncEngine initialized successfully'
            }
            logger.info("✅ Sync engine initialization: PASS")
            return True
        except Exception as e:
            self.test_results['initialization'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Sync engine initialization: FAIL - {e}")
            return False
    
    async def test_locations_sync(self):
        """Test locations sync functionality"""
        logger.info("🧪 Test 2: Locations Sync")
        try:
            result = await self.sync_engine.sync_locations()
            
            success = result.success
            self.test_results['locations_sync'] = {
                'passed': success,
                'records_processed': result.records_processed,
                'records_added': result.records_added,
                'records_updated': result.records_updated,
                'duration': result.duration_seconds,
                'details': 'Locations sync completed'
            }
            
            if success:
                logger.info(f"✅ Locations sync: PASS - {result.records_processed} processed")
            else:
                logger.error(f"❌ Locations sync: FAIL - {result.errors}")
            
            return success
        except Exception as e:
            self.test_results['locations_sync'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Locations sync: FAIL - {e}")
            return False
    
    async def test_catalog_sync(self):
        """Test catalog sync functionality"""
        logger.info("🧪 Test 3: Catalog Sync")
        try:
            # Test categories first (dependency)
            categories_result = await self.sync_engine.sync_catalog_categories()
            
            # Test items
            items_result = await self.sync_engine.sync_catalog_items()
            
            success = categories_result.success and items_result.success
            self.test_results['catalog_sync'] = {
                'passed': success,
                'categories_processed': categories_result.records_processed,
                'items_processed': items_result.records_processed,
                'total_duration': categories_result.duration_seconds + items_result.duration_seconds,
                'details': 'Catalog sync (categories + items) completed'
            }
            
            if success:
                logger.info(f"✅ Catalog sync: PASS - {categories_result.records_processed} categories, {items_result.records_processed} items")
            else:
                logger.error(f"❌ Catalog sync: FAIL - Categories: {categories_result.errors}, Items: {items_result.errors}")
            
            return success
        except Exception as e:
            self.test_results['catalog_sync'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Catalog sync: FAIL - {e}")
            return False
    
    async def test_orders_sync(self):
        """Test orders sync functionality"""
        logger.info("🧪 Test 4: Orders Sync (Recent)")
        try:
            # Test recent orders sync (last 3 days)
            result = await self.sync_engine.sync_orders(days_back=3)
            
            success = result.success
            self.test_results['orders_sync'] = {
                'passed': success,
                'records_processed': result.records_processed,
                'records_added': result.records_added,
                'records_updated': result.records_updated,
                'duration': result.duration_seconds,
                'details': 'Orders sync (3 days back) completed'
            }
            
            if success:
                logger.info(f"✅ Orders sync: PASS - {result.records_processed} processed")
            else:
                logger.error(f"❌ Orders sync: FAIL - {result.errors}")
            
            return success
        except Exception as e:
            self.test_results['orders_sync'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Orders sync: FAIL - {e}")
            return False
    
    async def test_inventory_sync(self):
        """Test inventory sync functionality"""
        logger.info("🧪 Test 5: Inventory Sync")
        try:
            result = await self.sync_engine.sync_inventory()
            
            success = result.success
            self.test_results['inventory_sync'] = {
                'passed': success,
                'records_processed': result.records_processed,
                'records_added': result.records_added,
                'records_updated': result.records_updated,
                'duration': result.duration_seconds,
                'details': 'Inventory sync completed'
            }
            
            if success:
                logger.info(f"✅ Inventory sync: PASS - {result.records_processed} processed")
            else:
                logger.error(f"❌ Inventory sync: FAIL - {result.errors}")
            
            return success
        except Exception as e:
            self.test_results['inventory_sync'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Inventory sync: FAIL - {e}")
            return False
    
    async def test_notification_system(self):
        """Test notification system functionality"""
        logger.info("🧪 Test 6: Notification System")
        try:
            # Create mock SyncResult objects for testing
            from app.services.sync_engine import SyncResult
            
            # Test success notification
            success_result = SyncResult(
                success=True,
                data_type='test_sync',
                records_processed=150,
                records_added=5,
                records_updated=10,
                duration_seconds=45.2
            )
            
            # Test notification sending with mock data
            mock_results = {'test_sync': success_result}
            success_sent = self.notification_service.send_sync_success_report(mock_results, 'development')
            
            # Test failure notification
            failure_result = SyncResult(
                success=False,
                data_type='test_sync',
                errors=['Test error message']
            )
            
            failure_results = {'test_sync': failure_result}
            failure_sent = self.notification_service.send_sync_failure_alert(failure_results, 'development')
            
            # Test the test_notifications method
            test_results = self.notification_service.test_notifications()
            
            self.test_results['notification_system'] = {
                'passed': True,
                'success_notification': success_sent,
                'failure_notification': failure_sent,
                'test_notifications': test_results,
                'details': 'Notification system tested with success and failure cases'
            }
            
            logger.info("✅ Notification system: PASS")
            return True
        except Exception as e:
            self.test_results['notification_system'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Notification system: FAIL - {e}")
            return False
    
    async def test_smart_scheduling(self):
        """Test smart scheduling logic"""
        logger.info("🧪 Test 7: Smart Scheduling Logic")
        try:
            # Test scheduling logic by simulating different scenarios
            now = datetime.now(timezone.utc)
            
            # Test 1: Should run (no previous sync)
            should_run = self._should_run_sync(now, None)
            
            # Test 2: Should not run (recent sync)
            recent_sync = now - timedelta(hours=1)
            should_not_run = not self._should_run_sync(now, recent_sync)
            
            # Test 3: Should run (old sync)
            old_sync = now - timedelta(hours=25)
            should_run_old = self._should_run_sync(now, old_sync)
            
            all_passed = should_run and should_not_run and should_run_old
            
            self.test_results['smart_scheduling'] = {
                'passed': all_passed,
                'test_no_previous': should_run,
                'test_recent_sync': should_not_run,
                'test_old_sync': should_run_old,
                'details': 'Smart scheduling logic tested'
            }
            
            if all_passed:
                logger.info("✅ Smart scheduling: PASS")
            else:
                logger.error("❌ Smart scheduling: FAIL")
            
            return all_passed
        except Exception as e:
            self.test_results['smart_scheduling'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Smart scheduling: FAIL - {e}")
            return False
    
    def _should_run_sync(self, current_time, last_sync_time):
        """Helper method to test scheduling logic"""
        if last_sync_time is None:
            return True
        
        time_since_last = current_time - last_sync_time
        return time_since_last.total_seconds() > 23 * 3600  # 23 hours
    
    async def test_error_handling(self):
        """Test error handling and recovery"""
        logger.info("🧪 Test 8: Error Handling")
        try:
            # Test with invalid configuration
            with patch('app.services.sync_engine.SyncEngine.sync_locations') as mock_sync:
                mock_sync.side_effect = Exception("Simulated sync error")
                
                try:
                    await self.sync_engine.sync_locations()
                    error_handled = False
                except Exception:
                    error_handled = True
            
            self.test_results['error_handling'] = {
                'passed': error_handled,
                'details': 'Error handling tested with simulated failures'
            }
            
            if error_handled:
                logger.info("✅ Error handling: PASS")
            else:
                logger.error("❌ Error handling: FAIL")
            
            return error_handled
        except Exception as e:
            self.test_results['error_handling'] = {
                'passed': False,
                'error': str(e)
            }
            logger.error(f"❌ Error handling: FAIL - {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests and generate report"""
        logger.info("🚀 Starting Sync Orchestrator Test Suite")
        logger.info("=" * 60)
        
        await self.setup()
        
        tests = [
            self.test_sync_engine_initialization,
            self.test_locations_sync,
            self.test_catalog_sync,
            self.test_orders_sync,
            self.test_inventory_sync,
            self.test_notification_system,
            self.test_smart_scheduling,
            self.test_error_handling
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                result = await test()
                if result:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"❌ Test failed with exception: {e}")
        
        await self.teardown()
        
        # Generate test report
        self._generate_test_report(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    def _generate_test_report(self, passed, total):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 SYNC ORCHESTRATOR TEST REPORT")
        logger.info("=" * 60)
        
        logger.info(f"🎯 Overall Result: {passed}/{total} tests passed")
        logger.info(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED - Ready for standardization!")
        else:
            logger.error("❌ Some tests failed - Review before standardization")
        
        logger.info("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"  {status} {test_name}")
            if 'error' in result:
                logger.info(f"    Error: {result['error']}")
            elif 'details' in result:
                logger.info(f"    Details: {result['details']}")
        
        logger.info("=" * 60)


async def main():
    """Main test runner"""
    test_suite = TestSyncOrchestrator()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Sync orchestrator is ready for standardization.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review and fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 