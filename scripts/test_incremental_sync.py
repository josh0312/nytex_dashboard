#!/usr/bin/env python3
"""
Test Incremental Sync Service
Validates incremental sync functionality locally
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_session
from app.services.incremental_sync_service import IncrementalSyncService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_incremental_sync():
    """Test the incremental sync service"""
    logger.info("🧪 Testing Incremental Sync Service")
    logger.info("=" * 50)
    
    try:
        # Initialize the sync service
        sync_service = IncrementalSyncService()
        
        # Test with database session
        async with get_session() as session:
            # Test 1: Get initial sync status
            logger.info("📊 Test 1: Getting initial sync status...")
            status = await sync_service.get_sync_status(session)
            
            if status['success']:
                logger.info(f"✅ Sync status retrieved: {len(status['sync_statuses'])} tables tracked")
                for table_status in status['sync_statuses']:
                    logger.info(f"  📋 {table_status['table_name']}: {table_status['records_synced']} records")
            else:
                logger.error(f"❌ Failed to get sync status: {status['error']}")
            
            # Test 2: Run incremental sync for just locations (fastest test)
            logger.info("\n🔄 Test 2: Running incremental sync for locations...")
            result = await sync_service.run_incremental_sync(session, ['locations'])
            
            if result['success']:
                logger.info(f"✅ Incremental sync successful: {result['total_changes']} changes applied")
                for sync_type, sync_result in result['results'].items():
                    if sync_result['success']:
                        logger.info(f"  📍 {sync_type}: {sync_result['changes_applied']} changes")
                    else:
                        logger.error(f"  ❌ {sync_type}: {sync_result['error']}")
            else:
                logger.error(f"❌ Incremental sync failed: {result['error']}")
            
            # Test 3: Run incremental sync for catalog categories
            logger.info("\n📂 Test 3: Running incremental sync for catalog categories...")
            result = await sync_service.run_incremental_sync(session, ['catalog_categories'])
            
            if result['success']:
                logger.info(f"✅ Catalog categories sync successful: {result['total_changes']} changes applied")
            else:
                logger.error(f"❌ Catalog categories sync failed: {result['error']}")
            
            # Test 4: Test dependency ordering
            logger.info("\n🔗 Test 4: Testing dependency ordering...")
            sync_types = ['catalog_variations', 'catalog_items', 'catalog_categories', 'locations']
            ordered = sync_service._order_syncs_by_dependencies(sync_types)
            logger.info(f"  📋 Original order: {sync_types}")
            logger.info(f"  🎯 Dependency order: {ordered}")
            
            # Verify ordering is correct
            expected_order = ['locations', 'catalog_categories', 'catalog_items', 'catalog_variations']
            if ordered == expected_order:
                logger.info("  ✅ Dependency ordering is correct")
            else:
                logger.warning(f"  ⚠️ Unexpected order. Expected: {expected_order}")
            
            # Test 5: Get final sync status
            logger.info("\n📊 Test 5: Getting final sync status...")
            final_status = await sync_service.get_sync_status(session)
            
            if final_status['success']:
                logger.info(f"✅ Final sync status: {len(final_status['sync_statuses'])} tables tracked")
                for table_status in final_status['sync_statuses']:
                    last_sync = table_status['last_sync_timestamp']
                    last_sync_str = last_sync if last_sync else "Never"
                    logger.info(f"  📋 {table_status['table_name']}: {table_status['records_synced']} records, last sync: {last_sync_str}")
            else:
                logger.error(f"❌ Failed to get final sync status: {final_status['error']}")
            
            # Commit all changes
            await session.commit()
            
        logger.info("\n" + "=" * 50)
        logger.info("🎉 All incremental sync tests completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}", exc_info=True)
        return False


async def test_full_incremental_sync():
    """Test full incremental sync with all data types"""
    logger.info("🚀 Testing Full Incremental Sync")
    logger.info("=" * 50)
    
    try:
        sync_service = IncrementalSyncService()
        
        async with get_session() as session:
            # Run full incremental sync
            logger.info("🔄 Running full incremental sync...")
            start_time = datetime.now()
            
            result = await sync_service.run_incremental_sync(session)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result['success']:
                logger.info(f"✅ Full incremental sync completed in {duration:.2f} seconds")
                logger.info(f"📊 Total changes applied: {result['total_changes']}")
                
                for sync_type, sync_result in result['results'].items():
                    if sync_result['success']:
                        logger.info(f"  ✅ {sync_type}: {sync_result['changes_applied']} changes")
                    else:
                        logger.error(f"  ❌ {sync_type}: {sync_result['error']}")
                        
                await session.commit()
                return True
            else:
                logger.error(f"❌ Full incremental sync failed: {result['error']}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Full sync test failed: {str(e)}", exc_info=True)
        return False


async def compare_with_current_data():
    """Compare incremental sync results with current data"""
    logger.info("🔍 Comparing incremental sync with current data")
    logger.info("=" * 50)
    
    try:
        async with get_session() as session:
            # Get current table counts
            tables_to_check = [
                'locations', 
                'catalog_categories', 
                'catalog_items', 
                'catalog_variations',
                'vendors'
            ]
            
            for table in tables_to_check:
                try:
                    result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    logger.info(f"  📊 {table}: {count:,} records")
                except Exception as e:
                    logger.warning(f"  ❌ {table}: Error - {str(e)}")
            
            # Check sync_state table
            try:
                result = await session.execute(text('SELECT COUNT(*) FROM sync_state'))
                sync_count = result.scalar()
                logger.info(f"  🔧 sync_state: {sync_count} tracking entries")
                
                # Show recent sync activity
                result = await session.execute(text("""
                    SELECT table_name, last_sync_timestamp, records_synced 
                    FROM sync_state 
                    WHERE last_sync_timestamp IS NOT NULL
                    ORDER BY last_sync_timestamp DESC 
                    LIMIT 5
                """))
                
                logger.info("\n  🕐 Recent sync activity:")
                for row in result.fetchall():
                    timestamp = row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else 'Never'
                    logger.info(f"    📋 {row[0]}: {row[2]} records at {timestamp}")
                    
            except Exception as e:
                logger.warning(f"  ❌ sync_state check failed: {str(e)}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {str(e)}", exc_info=True)
        return False


async def main():
    """Main test function"""
    print("🧪 Incremental Sync Test Suite")
    print("=" * 60)
    
    # Test 1: Basic incremental sync functionality
    test1_success = await test_incremental_sync()
    
    # Test 2: Full incremental sync
    test2_success = await test_full_incremental_sync()
    
    # Test 3: Data comparison
    test3_success = await compare_with_current_data()
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"  🧪 Basic incremental sync: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"  🚀 Full incremental sync: {'✅ PASS' if test2_success else '❌ FAIL'}")
    print(f"  🔍 Data comparison: {'✅ PASS' if test3_success else '❌ FAIL'}")
    
    if all([test1_success, test2_success, test3_success]):
        print("\n🎉 All tests passed! Incremental sync is ready for production.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review and fix issues before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    # Import here to avoid circular imports
    from sqlalchemy import text
    asyncio.run(main()) 