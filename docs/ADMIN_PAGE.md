# Admin Page Documentation

## Overview
The Admin page (`/admin`) provides comprehensive system administration capabilities for the NyTex Fireworks platform. It offers advanced data synchronization, system monitoring, and administrative tools for managing the entire business intelligence infrastructure.

## Page URL
- **Main Admin**: `/admin/sync`
- **System Status**: `/admin/status`
- **Sync Operations**: `/admin/complete-sync`, `/admin/incremental-sync`

## What This Page Does

The Admin page serves as the system administration center with the following key functions:

1. **Complete Data Synchronization**: Full refresh of all data from Square POS systems
2. **Incremental Data Updates**: Efficient updates of only changed data
3. **System Status Monitoring**: Real-time health monitoring of all system components
4. **Historical Data Management**: Management of historical order and transaction data
5. **Database Administration**: Direct database management and maintenance tools
6. **Advanced Diagnostics**: Comprehensive system diagnostics and troubleshooting

## Page Components

### 1. **Data Synchronization Dashboard**
- **Complete Sync Control**: Full data refresh from Square APIs
- **Incremental Sync Options**: Efficient update of changed data only
- **Historical Sync Management**: Specialized historical order synchronization
- **Progress Monitoring**: Real-time sync progress tracking with detailed metrics

**Data Source**:
- Square APIs (Locations, Catalog, Inventory, Orders)
- Local database status tracking
- Sync progress monitoring system
- Error logging and recovery systems

### 2. **System Status Monitor**
- **Database Health**: Connection status and performance metrics
- **Square API Status**: API connectivity and configuration validation
- **Service Health**: External service status and availability
- **Data Quality Metrics**: Validation of data integrity and completeness

**Data Source**:
- Real-time database connection testing
- Square API health checks
- System configuration validation
- Data count verification across tables

### 3. **Historical Data Sync**
- **Date Range Selection**: Configurable sync periods
- **Progress Tracking**: Chunk-based processing with detailed progress
- **Error Recovery**: Automatic retry and error handling
- **Performance Optimization**: Batch processing with rate limiting

**Data Source**:
- Square Orders API with historical data
- Configurable date ranges (default: 2018-present)
- Batch processing with 30-day chunks
- Rate-limited API calls (100 requests/minute)

### 4. **Database Administration**
- **Table Management**: Create/update database tables
- **Data Migration**: Advanced data migration utilities
- **Bulk Operations**: Efficient bulk data import/export
- **System Diagnostics**: Advanced troubleshooting tools

**Data Source**:
- Direct database schema management
- SQLAlchemy model definitions
- Bulk data processing capabilities
- System configuration and environment validation

## Administrative Functions

### 1. **Complete Data Synchronization** (`/admin/complete-sync`)

**Purpose**: Performs comprehensive synchronization of all data from Square POS to local database.

**Process Flow**:
1. **Locations Sync**: Synchronize all business locations
2. **Catalog Sync**: Update complete product catalog
3. **Inventory Sync**: Refresh all inventory data
4. **Vendor Sync**: Update supplier information
5. **Validation**: Verify data integrity and completeness

**Data Sources**:
- Square Locations API
- Square Catalog API  
- Square Inventory API
- Local vendor management system

**Key Features**:
- **Full Refresh Option**: Complete data replacement
- **Incremental Mode**: Update only changed data (default)
- **Error Recovery**: Automatic retry with exponential backoff
- **Progress Tracking**: Real-time sync statistics and timing

**Technical Implementation**:
```python
@router.post("/complete-sync")
async def complete_sync(request: Request):
    # Parse full_refresh flag from request
    request_body = await request.json()
    full_refresh = request_body.get('full_refresh', False)
    
    # Sync locations first
    locations_result = await sync_locations_incremental(
        square_access_token, base_url, db_url, full_refresh
    )
    
    # Sync catalog data
    catalog_result = await sync_catalog_incremental(
        square_access_token, base_url, db_url, full_refresh
    )
    
    # Sync inventory data
    inventory_result = await sync_inventory_incremental(
        square_access_token, base_url, db_url, full_refresh
    )
    
    # Return comprehensive results
    return JSONResponse({
        "success": True,
        "message": "Complete sync finished successfully",
        "sync_stats": sync_statistics
    })
```

### 2. **Historical Orders Synchronization** (`/admin/historical-orders-sync`)

**Purpose**: Specialized synchronization for historical order data with advanced progress tracking.

> 📚 **Detailed Reference**: For comprehensive technical details about historical orders sync, see [HISTORICAL_ORDERS_SYNC.md](./HISTORICAL_ORDERS_SYNC.md)

**Configuration**:
```python
@dataclass
class SyncConfig:
    start_date: datetime = datetime(2018, 1, 1, tzinfo=timezone.utc)
    end_date: datetime = datetime.now(timezone.utc)
    chunk_size_days: int = 30      # Process 30 days at a time
    batch_size: int = 100          # Insert 100 orders at a time
    max_requests_per_minute: int = 100
    request_delay: float = 0.6     # 60s / 100 requests
```

**Process Features**:
- **Chunked Processing**: Processes data in 30-day chunks
- **Rate Limiting**: Respects Square API limits
- **Progress Tracking**: Global progress state with estimates
- **Error Handling**: Comprehensive error recovery
- **Data Validation**: Timestamp parsing and data integrity checks

**Progress Tracking**:
```python
historical_sync_progress = {
    "is_running": False,
    "total_chunks": 0,
    "completed_chunks": 0,
    "current_chunk_info": "",
    "total_orders_synced": 0,
    "errors": [],
    "start_time": None,
    "estimated_completion": None,
    "last_update": None
}
```

### 3. **System Status and Diagnostics** (`/admin/status`)

**Purpose**: Comprehensive system health monitoring and diagnostics.

**Status Checks**:
1. **Database Connectivity**: Connection status and query performance
2. **Square API Configuration**: Token validation and API accessibility  
3. **Table Existence**: Verification of all required database tables
4. **Data Counts**: Validation of data completeness
5. **Environment Configuration**: System settings verification

**Response Format**:
```json
{
  "database": "connected",
  "square_config": "configured", 
  "tables_exist": true,
  "location_count": 3,
  "locations": [
    {"name": "Main Store", "status": "ACTIVE"},
    {"name": "Warehouse", "status": "ACTIVE"}
  ],
  "debug": {
    "env_vars": {
      "DB_USER": "nytex_user",
      "DB_NAME": "nytex_dashboard",
      "CLOUD_SQL_CONNECTION_NAME": "project:region:instance"
    },
    "constructed_url": "postgresql+asyncpg://user:***@host/db"
  }
}
```

### 4. **Database Administration Tools**

**Table Management** (`/admin/create-tables`):
- Creates all required database tables
- Uses SQLAlchemy metadata for schema definition
- Handles foreign key constraints and indexes

**Data Migration** (`/admin/table-migration`):
- Migrates missing or updated table structures
- Handles schema changes and data preservation
- Validates migration success

**Bulk Data Operations** (`/admin/bulk-data-sync`):
- Efficient bulk insert/update operations
- Batch processing for large datasets
- Transaction management for data integrity

## Synchronization Architecture

### Incremental Sync Strategy

The admin system uses sophisticated incremental synchronization:

**Change Detection**:
- **Timestamp Comparison**: Compare last update times
- **Version Tracking**: Track object versions from Square
- **Delta Processing**: Process only changed records
- **Efficient Updates**: Minimize API calls and database operations

**Sync Process Flow**:
```python
async def sync_catalog_incremental(access_token, base_url, db_url, full_refresh=False):
    if not full_refresh:
        # Get last sync timestamp
        last_sync = await get_last_catalog_sync_time(db_url)
        
        # Query Square API for changes since last sync
        changed_objects = await fetch_changed_catalog_objects(
            access_token, base_url, last_sync
        )
    else:
        # Full refresh: get all objects
        changed_objects = await fetch_all_catalog_objects(
            access_token, base_url
        )
    
    # Process changes in batches
    for batch in chunk_objects(changed_objects, batch_size=100):
        await process_catalog_batch(batch, db_url)
    
    # Update sync timestamp
    await update_last_sync_time(db_url)
```

### Error Handling and Recovery

**Comprehensive Error Management**:
1. **API Failures**: Automatic retry with exponential backoff
2. **Database Errors**: Transaction rollback and recovery
3. **Network Issues**: Connection timeout and retry logic
4. **Data Validation**: Schema validation and constraint checking
5. **Partial Failures**: Continued processing with error logging

**Error Recovery Example**:
```python
async def sync_with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
```

## Data Sources and Integration

### Square API Integration

**API Endpoints Used**:
1. **Locations API**: Business location data
2. **Catalog API**: Product and category information
3. **Inventory API**: Stock levels and tracking
4. **Orders API**: Transaction and sales data

**Authentication and Security**:
- Square Access Token authentication
- Environment-specific API endpoints (sandbox/production)
- Rate limiting compliance
- HTTPS-only communication

### Database Schema Management

**Core Tables**:
- `locations`: Business locations and settings
- `catalog_items`: Product information
- `catalog_variations`: Product variants and SKUs
- `catalog_inventory`: Inventory levels by location
- `catalog_categories`: Product categorization
- `vendors`: Supplier information
- `orders`: Transaction data
- `order_line_items`: Detailed order items

**Data Relationships**:
- Foreign key constraints ensure data integrity
- Indexes optimize query performance
- Audit trails track data changes
- Soft deletes preserve historical data

## API Endpoints

### Administrative Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/sync` | GET | Main admin sync page |
| `/admin/status` | GET | System status (JSON) |
| `/admin/complete-sync` | POST | Trigger complete sync |
| `/admin/incremental-sync` | POST | Trigger incremental sync |
| `/admin/foundation-sync` | POST | Sync foundation data only |
| `/admin/historical-orders-sync` | POST | Sync historical orders |
| `/admin/historical-orders-sync-status` | GET | Historical sync progress |
| `/admin/create-tables` | POST | Create database tables |
| `/admin/table-migration` | POST | Migrate table schema |
| `/admin/bulk-data-sync` | POST | Bulk data operations |

### API Response Formats

**Complete Sync Response**:
```json
{
  "success": true,
  "message": "Complete sync finished successfully",
  "sync_stats": {
    "locations": {"created": 0, "updated": 3, "deleted": 0},
    "categories": {"created": 5, "updated": 12, "deleted": 0},
    "items": {"created": 45, "updated": 120, "deleted": 3},
    "variations": {"created": 89, "updated": 200, "deleted": 5},
    "inventory": {"created": 150, "updated": 500, "deleted": 0},
    "vendors": {"created": 2, "updated": 8, "deleted": 0}
  },
  "duration": "3.5 minutes",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Historical Sync Status**:
```json
{
  "is_running": true,
  "total_chunks": 24,
  "completed_chunks": 8,
  "current_chunk_info": "Processing 2023-08-01 to 2023-08-31",
  "total_orders_synced": 1250,
  "errors": [],
  "start_time": "2024-01-15T09:00:00Z",
  "estimated_completion": "2024-01-15T11:30:00Z",
  "progress_percentage": 33.3
}
```

## Configuration and Settings

### Sync Configuration

| Setting | Purpose | Default |
|---------|---------|---------|
| `SQUARE_ACCESS_TOKEN` | Square API authentication | Required |
| `SQUARE_ENVIRONMENT` | API environment | `production` |
| `SYNC_BATCH_SIZE` | Records per batch | 100 |
| `SYNC_TIMEOUT` | Operation timeout | 1800 seconds |
| `MAX_RETRIES` | Maximum retry attempts | 3 |

### Historical Sync Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `HISTORICAL_START_DATE` | Start date for historical sync | 2018-01-01 |
| `CHUNK_SIZE_DAYS` | Days per processing chunk | 30 |
| `BATCH_SIZE` | Orders per batch | 100 |
| `MAX_REQUESTS_PER_MINUTE` | Rate limit | 100 |

### Database Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `DATABASE_URL` | Database connection string | Required |
| `DB_POOL_SIZE` | Connection pool size | 10 |
| `DB_TIMEOUT` | Query timeout | 30 seconds |
| `MIGRATION_TIMEOUT` | Migration timeout | 300 seconds |

## Performance Optimization

### Batch Processing

**Efficient Data Processing**:
1. **Chunked Operations**: Large datasets processed in manageable chunks
2. **Parallel Processing**: Multiple operations run concurrently where safe
3. **Memory Management**: Streaming data processing for large datasets
4. **Connection Pooling**: Efficient database connection reuse

### Rate Limiting

**API Rate Management**:
1. **Request Throttling**: Respect Square API rate limits
2. **Exponential Backoff**: Intelligent retry strategies
3. **Request Queuing**: Queue requests during high-load periods
4. **Monitoring**: Track API usage and performance

### Database Optimization

**Query Performance**:
1. **Index Strategy**: Optimal indexing for frequent queries
2. **Bulk Operations**: Efficient bulk insert/update operations
3. **Transaction Management**: Minimize transaction scope
4. **Query Optimization**: Efficient SQL with proper joins

## Security and Access Control

### Administrative Security

1. **Authentication Required**: All admin operations require authentication
2. **Audit Logging**: Complete audit trail of all administrative actions
3. **API Token Security**: Secure handling and storage of API credentials
4. **Input Validation**: Comprehensive validation of all inputs

### Data Protection

1. **Transaction Integrity**: Database transactions ensure data consistency
2. **Backup Procedures**: Regular backup validation and restore procedures
3. **Error Isolation**: Errors don't compromise overall system integrity
4. **Secure Communication**: HTTPS for all external API communication

## Monitoring and Logging

### System Monitoring

**Health Checks**:
- Database connectivity and performance
- External API availability and response times
- System resource usage and availability
- Data quality and integrity validation

**Performance Metrics**:
- Sync operation duration and throughput
- API response times and error rates
- Database query performance
- System resource utilization

### Comprehensive Logging

**Log Categories**:
1. **Operation Logs**: Detailed sync operation logging
2. **Error Logs**: Comprehensive error tracking and stack traces
3. **Performance Logs**: Timing and performance metrics
4. **Audit Logs**: Administrative action tracking

**Log Retention**:
- Real-time logs for immediate troubleshooting
- Historical logs for trend analysis
- Error logs for debugging and improvement
- Audit logs for compliance and security

## Troubleshooting

### Common Issues

1. **Sync Failures**
   - Verify Square API token configuration
   - Check database connectivity and permissions
   - Review API rate limiting status
   - Validate network connectivity

2. **Performance Issues**
   - Monitor database query performance
   - Check system resource utilization
   - Review API response times
   - Validate network bandwidth

3. **Data Inconsistencies**
   - Run data validation queries
   - Check sync timestamps and completion status
   - Verify foreign key relationships
   - Review error logs for failed operations

### Debug Tools

1. **Status Endpoints**: Real-time system health monitoring
2. **Log Analysis**: Comprehensive logging for troubleshooting
3. **Database Queries**: Direct database access for verification
4. **API Testing**: Direct API endpoint testing and validation

## Integration Points

### With Other System Components

1. **Dashboard**: Provides sync status and health metrics
2. **Reports**: Uses synchronized data for business intelligence
3. **Catalog Page**: Utilizes admin sync for catalog management
4. **Tools Page**: Leverages admin functionality for specialized tools

### External System Integration

1. **Square POS**: Primary data source for all business data
2. **Google Cloud**: Production secrets and configuration management
3. **Monitoring Services**: Integration with external monitoring tools
4. **Backup Systems**: Integration with backup and disaster recovery

The Admin page serves as the nerve center for the NyTex Fireworks platform, providing comprehensive system administration capabilities essential for maintaining data integrity, system performance, and operational efficiency. 