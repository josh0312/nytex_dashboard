# Admin Sync System Documentation

## Overview

The Admin Sync System provides comprehensive data synchronization between Square's API and the local production database. As of the latest update, the system supports both **Incremental** and **Full Refresh** sync modes to provide flexibility and safety in data management.

## Sync Modes

### 1. Incremental Sync (Default - Recommended)
- **Purpose**: Safely updates only the data that has changed since the last sync
- **Behavior**: 
  - Adds new records from Square
  - Updates existing records that have changed
  - Marks deleted records (soft deletes - preserves data for historical reporting)
  - Only processes changes, leaving unchanged data untouched
- **Safety**: Non-destructive, preserves existing data relationships
- **Performance**: Faster execution, minimal database impact
- **Use Cases**: Regular daily/weekly syncs, production maintenance

### 2. Full Refresh Mode (Use with Caution)
- **Purpose**: Completely rebuilds the database from Square data
- **Behavior**:
  - **DESTRUCTIVE**: Deletes all existing data in proper dependency order
  - Rebuilds entire dataset from Square API
  - Recreates all data relationships from scratch
- **Safety**: ⚠️ **CAUTION REQUIRED** - Wipes all existing data
- **Performance**: Slower execution, heavy database impact
- **Use Cases**: Initial setup, data corruption recovery, major schema changes

## Access & Interface

### Web Interface
- **URL**: `/admin/sync`
- **Location**: Admin navigation menu → "Admin"
- **Authentication**: Requires admin-level access
- **Additional Features**: Historical Orders Sync, Database Migration

### API Endpoints
- **Complete Sync**: `POST /admin/complete-sync` - Current catalog and inventory
- **Historical Sync**: `POST /admin/historical-orders-sync` - All orders from 2018-present
- **Migration**: `POST /admin/migrate-order-line-items` - Database schema updates
- **Content-Type**: `application/json`
- **Body**: `{"full_refresh": true/false}` (for complete sync only)

## Complete Production Sync Process

The sync process follows a strict three-step sequence to maintain data integrity:

### Step 1: Location Sync 📍
**What it syncs**: Store locations from Square
**API Called**: `GET /v2/locations`
**Database Tables**: `locations`

**Incremental Mode**:
- Adds new locations
- Updates existing location details (name, address, timezone, status)
- Marks removed locations as 'INACTIVE' (preserves historical data)

**Full Refresh Mode**:
- Deletes ALL existing data (locations, categories, items, variations, inventory)
- Rebuilds locations table from Square data

### Step 2: Catalog Data Sync 📋
**What it syncs**: Categories, items, and variations from Square
**API Called**: `POST /v2/catalog/search` (for CATEGORY, ITEM, ITEM_VARIATION)
**Database Tables**: `catalog_categories`, `catalog_items`, `catalog_variations`

**Incremental Mode**:
- Upserts (INSERT...ON CONFLICT DO UPDATE) for each record type
- Marks items not found in Square as `is_deleted = true`
- Preserves historical product data

**Full Refresh Mode**:
- Tables already cleared in Step 1
- Inserts all catalog data fresh from Square

### Step 3: Inventory Sync 📦
**What it syncs**: Current inventory quantities per location
**API Called**: `POST /v2/inventory/counts/batch-retrieve`
**Database Tables**: `catalog_inventory`

**Incremental Mode**:
- Adds new inventory records for new products
- Updates quantities only when they've actually changed
- Preserves unchanged inventory history

**Full Refresh Mode**:
- Table already cleared in Step 1
- Rebuilds entire inventory dataset

## Usage Guidelines

### When to Use Incremental Sync (Default)
✅ **Recommended for**:
- Regular scheduled syncs (daily/weekly)
- Production maintenance
- Routine data updates
- When preserving historical data is important
- When sync speed matters

### When to Use Full Refresh
⚠️ **Use only when**:
- Initial system setup
- Data corruption detected
- Major schema changes require clean slate
- Troubleshooting data relationship issues
- Explicitly instructed by development team

## Monitoring & Statistics

The sync system provides detailed statistics for each operation:

### Sync Statistics Tracked
- **Created**: New records added
- **Updated**: Existing records modified
- **Deleted**: Records marked as deleted (incremental) or physically removed (full refresh)

### Per-Category Stats
- Locations: Created, Updated, Deleted
- Categories: Created, Updated, Deleted  
- Items: Created, Updated, Deleted
- Variations: Created, Updated, Deleted
- Inventory: Created, Updated, Deleted

### Logging
- Real-time progress updates in web interface
- Detailed server logs for troubleshooting
- Performance metrics (execution time, records processed)

## Error Handling

### Automatic Safeguards
- Configuration validation before sync starts
- Square API connectivity verification
- Database connection testing
- Step-by-step failure isolation (if Step 1 fails, Steps 2&3 don't run)

### Common Error Scenarios
1. **Square API Token Issues**: Sync fails early with clear message
2. **Network Connectivity**: Timeout handling with retry logic
3. **Database Constraints**: Foreign key validation prevents orphaned records
4. **Partial Failures**: Failed steps are clearly identified in logs

## Security & Permissions

### Required Permissions
- Admin-level access to sync interface
- Square API access token with proper scopes:
  - `MERCHANT_PROFILE_READ` (for locations)
  - `ITEMS_READ` (for catalog data)  
  - `INVENTORY_READ` (for inventory quantities)

### Production Safeguards
- Full refresh mode requires explicit checkbox confirmation
- Clear visual warnings for destructive operations
- Detailed logging for audit trail
- Transaction rollback on failures

## Best Practices

### 1. Regular Sync Schedule
```
Recommended: Run incremental sync daily/weekly
Emergency: Use full refresh only when needed
```

### 2. Pre-Sync Verification
- Verify Square API connectivity
- Check database space availability
- Ensure no other critical operations running

### 3. Post-Sync Validation
- Review sync statistics for anomalies
- Verify report data accuracy
- Check error logs for warnings

### 4. Backup Strategy
```
Before major syncs: Create database backup
Full refresh: Always backup before destructive operations
```

## Troubleshooting

### Common Issues

#### 1. Sync Fails on Step 1 (Locations)
**Symptoms**: "Location sync failed" error
**Likely Causes**: 
- Square API token expired/invalid
- Network connectivity issues
- Database connection problems
**Resolution**: Check configuration, verify API token, test database connectivity

#### 2. Sync Fails on Step 2 (Catalog)
**Symptoms**: "Catalog sync failed" error  
**Likely Causes**:
- Large dataset timeout
- Square API rate limiting
- Foreign key constraint violations
**Resolution**: Retry sync, check for API limits, verify location data exists

#### 3. Sync Fails on Step 3 (Inventory)
**Symptoms**: "Inventory sync failed" error
**Likely Causes**:
- No active locations found
- Inventory API permissions
- Large inventory dataset timeout
**Resolution**: Verify locations are ACTIVE, check API permissions, increase timeout if needed

### Emergency Recovery

#### If Full Refresh Corrupts Data
1. **Stop all operations immediately**
2. **Restore from latest database backup**
3. **Investigate root cause before retry**
4. **Consider incremental sync instead**

#### If Incremental Sync Shows Anomalies
1. **Review sync statistics for unusual patterns**
2. **Check Square API for data changes**
3. **Verify data integrity with spot checks**
4. **Consider full refresh if data corruption suspected**

## Technical Implementation

### Database Operations
- **Incremental**: Uses PostgreSQL `INSERT...ON CONFLICT DO UPDATE` (UPSERT)
- **Full Refresh**: Uses `DELETE FROM` followed by `INSERT`
- **Transactions**: Each step runs in database transaction for atomicity
- **Foreign Keys**: Proper dependency order maintained

### API Integration
- **Pagination**: Handles large datasets with cursor-based pagination
- **Rate Limiting**: Respects Square API rate limits
- **Timeouts**: Configurable timeouts per operation type
- **Retry Logic**: Automatic retry for transient failures

### Performance Optimization
- **Batch Processing**: Processes data in configurable batches
- **Concurrent Requests**: Uses async HTTP for improved performance
- **Database Indexing**: Optimized queries with proper indexes
- **Memory Management**: Streaming processing for large datasets

## Configuration

### Environment Variables
```
SQUARE_ACCESS_TOKEN=your_square_token_here
SQUARE_ENVIRONMENT=production  # or 'sandbox'
DATABASE_URL=your_database_connection_string
```

### Sync Settings
```python
# Timeouts (seconds)
LOCATION_SYNC_TIMEOUT = 300
CATALOG_SYNC_TIMEOUT = 600  
INVENTORY_SYNC_TIMEOUT = 600

# Batch sizes
CATALOG_BATCH_SIZE = 1000
INVENTORY_BATCH_SIZE = 500
```

## Future Enhancements

### Planned Features
- **Scheduled Syncs**: Automatic daily/weekly sync scheduling
- **Incremental Timestamps**: Track last sync time per data type
- **Selective Sync**: Choose specific data types to sync
- **Sync History**: Maintain history of all sync operations
- **Email Notifications**: Automatic notifications on sync completion/failure

### Performance Improvements
- **Delta Sync**: Only sync records changed since last sync timestamp
- **Parallel Processing**: Concurrent location processing for inventory
- **Caching**: Cache frequently accessed Square API data
- **Compression**: Compress large API responses

---

**Last Updated**: 2024-01-XX  
**Version**: 2.0  
**Author**: Development Team 