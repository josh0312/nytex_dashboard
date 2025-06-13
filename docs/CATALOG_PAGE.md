# Catalog Page Documentation

## Overview
The Catalog page (`/catalog`) serves as the central hub for Square catalog management and export functionality. It provides tools for synchronizing product catalog data between Square POS systems and the local database, with comprehensive export capabilities matching Square's official format.

## Page URL
- **Main Catalog**: `/catalog`
- **Export Status**: `/catalog/status`
- **Export Trigger**: `/catalog/export`

## What This Page Does

The Catalog page provides comprehensive catalog management with the following key functions:

1. **Square Catalog Synchronization**: Syncs product catalog data from Square POS to local database
2. **Export Management**: Generates complete 76-column catalog exports matching Square's format
3. **Real-time Status Monitoring**: Shows current sync status and export progress
4. **Data Quality Validation**: Ensures catalog data integrity and completeness
5. **Excel Export**: Provides formatted Excel exports for offline analysis and vendor communication

## Page Components

### 1. **Catalog Status Dashboard**
- **Total Items**: Count of active catalog items
- **Total Variations**: Number of product variations
- **Total Inventory Records**: Inventory entries across all locations
- **Last Sync Time**: Timestamp of most recent data synchronization

**Data Source**:
- Real-time database queries
- Tables: `catalog_items`, `catalog_variations`, `catalog_inventory`, `locations`
- Formatted in Central Time for user convenience

### 2. **Export Control Panel**
- **Export to Database Button**: Triggers catalog sync from Square API
- **Export Status Indicator**: Shows running/completed/error states
- **Progress Monitoring**: Real-time updates during export process
- **Export History**: Timestamp and status of recent exports

**Data Source**:
- `SquareCatalogService` for export operations
- Export status tracking in database
- Real-time API status monitoring

### 3. **Excel Export System**
- **Complete Catalog Export**: 76-column export matching Square format
- **Formatted Spreadsheet**: Professional Excel formatting with headers
- **Download Management**: Secure file download with proper MIME types

**Data Source**:
- Complete catalog dataset from local database
- Advanced Excel formatting using pandas and openpyxl
- Export file storage in `app/static/exports/`

### 4. **API Health Monitor**
- **External API Status**: Monitors catalog export API service
- **Health Check Endpoint**: Validates API connectivity
- **Service Control**: Start/stop external API services

**Data Source**:
- External catalog export API service
- HTTP health checks
- Service status monitoring

## Catalog Export System

### Square Catalog Integration

The catalog system integrates with Square's Catalog API to maintain synchronized product data:

1. **Catalog Items**: Base products with names, descriptions, categories
2. **Catalog Variations**: Product variants with SKUs, prices, and inventory tracking
3. **Catalog Inventory**: Stock levels by location
4. **Categories**: Product categorization hierarchy
5. **Vendor Information**: Supplier data and relationships

### 76-Column Export Format

The system generates comprehensive Excel exports with 76 columns matching Square's official format:

**Core Product Information (Columns 1-20)**:
- Item ID, Variation ID, Item Name, Description
- Category, SKU, Price, Cost
- Inventory tracking, Units per case
- Creation and modification timestamps

**Location-Specific Data (Columns 21-50)**:
- Stock quantities by location
- Location-specific pricing
- Inventory alerts and thresholds
- Location status and settings

**Vendor and Supply Chain (Columns 51-65)**:
- Vendor names and codes
- Supplier contact information
- Purchase order data
- Lead times and reorder points

**Advanced Attributes (Columns 66-76)**:
- Custom attributes and modifiers
- Tax categories and settings
- Seasonal flags and restrictions
- Integration metadata

### Export Process Flow

1. **Data Collection**
   ```python
   async with get_session() as session:
       # Get comprehensive catalog data
       items_result = await session.execute(text("SELECT COUNT(*) FROM catalog_items"))
       variations_result = await session.execute(text("SELECT COUNT(*) FROM catalog_variations"))
       inventory_result = await session.execute(text("SELECT COUNT(*) FROM catalog_inventory"))
   ```

2. **Square API Synchronization**
   ```python
   catalog_service = SquareCatalogService()
   result = await catalog_service.export_catalog_to_database(session)
   ```

3. **Status Monitoring**
   - Real-time progress tracking
   - Error handling and reporting
   - Success confirmation with item counts

## Data Sources and Flow

### Primary Data Sources

1. **Square Catalog API**
   - **Endpoint**: Square Catalog Objects API
   - **Authentication**: Square Access Token
   - **Rate Limiting**: Respects Square API limits
   - **Data Types**: Items, Variations, Categories, Inventory

2. **Local Database Tables**
   - **`catalog_items`**: Core product information
   - **`catalog_variations`**: Product variations and SKUs
   - **`catalog_inventory`**: Stock levels by location
   - **`catalog_categories`**: Product categorization
   - **`vendors`**: Supplier information
   - **`locations`**: Business locations

3. **External Export Service**
   - **Health Check**: `/catalog/api/health`
   - **Service Management**: Start/stop API services
   - **Data Processing**: Advanced export formatting

### Data Synchronization Process

1. **Incremental Sync**: Updates only changed data since last sync
2. **Full Refresh**: Complete re-sync of all catalog data
3. **Validation**: Data integrity checks during sync
4. **Error Recovery**: Automatic retry with exponential backoff

### Export Status Tracking

The system tracks export status across multiple dimensions:

1. **Process Status**: Running, Completed, Error
2. **Item Counts**: Items processed, variations updated, inventory synced
3. **Timestamps**: Start time, completion time, last update
4. **Error Information**: Detailed error messages and stack traces

## Technical Implementation

### HTMX Integration

The catalog page uses HTMX for dynamic updates:

```html
<!-- Status component updates -->
<div hx-get="/catalog/status/component" 
     hx-trigger="every 5s"
     hx-target="#catalog-status">
  Loading status...
</div>

<!-- Export trigger -->
<button hx-post="/catalog/export"
        hx-indicator="#export-spinner"
        hx-target="#export-status">
  Start Export
</button>
```

### Service Architecture

```python
class SquareCatalogService:
    async def export_catalog_to_database(self, session):
        """Main export orchestration"""
        # 1. Check current status
        # 2. Trigger Square API sync
        # 3. Process and validate data
        # 4. Update local database
        # 5. Return status and metrics
        
    async def get_export_status(self, session):
        """Get current export status"""
        # Query database for status information
        # Format timestamps for display
        # Return structured status data
```

### Error Handling

1. **API Failures**: Graceful degradation with error messages
2. **Database Issues**: Transaction rollback and recovery
3. **Network Problems**: Retry logic with backoff
4. **Data Validation**: Schema validation and constraint checking

## Export File Management

### File Generation

1. **Excel Format**: Professional spreadsheet with formatting
2. **Filename Convention**: `catalog_export_{timestamp}.xlsx`
3. **Compression**: Efficient file size optimization
4. **Security**: Temporary file handling with cleanup

### File Storage

- **Location**: `app/static/exports/`
- **Retention**: Automatic cleanup of old files
- **Access Control**: Secure download URLs
- **MIME Types**: Proper content-type headers

### Download Process

```python
@router.get("/export/excel")
async def export_to_excel():
    # Generate Excel file
    filename = await generate_catalog_excel()
    
    # Return file response
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
```

## API Endpoints

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/catalog/` | GET | Main catalog management page |
| `/catalog/export` | POST | Trigger catalog export |
| `/catalog/status` | GET | Get export status (JSON) |
| `/catalog/status/component` | GET | Get status component (HTML) |
| `/catalog/export/excel` | GET | Download Excel export |

### Status API Response

```json
{
  "success": true,
  "data": {
    "total_items": 1250,
    "total_variations": 3875,
    "total_inventory": 15600,
    "last_export": "2024-01-15T10:30:00Z",
    "last_sync_central": "2024-01-15 04:30:00 AM CST",
    "has_data": true
  }
}
```

### Export API Response

```json
{
  "success": true,
  "message": "Successfully exported 1250 items",
  "data": {
    "status": "completed",
    "items_exported": 1250,
    "variations_exported": 3875,
    "inventory_records": 15600,
    "duration": "45.2 seconds"
  }
}
```

## Configuration

### Required Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `SQUARE_ACCESS_TOKEN` | Square API authentication | None (required) |
| `SQUARE_ENVIRONMENT` | API environment | `production` |
| `DATABASE_URL` | Database connection | Local PostgreSQL |

### Optional Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `CATALOG_EXPORT_BATCH_SIZE` | Items per batch | 100 |
| `EXPORT_FILE_RETENTION` | File cleanup period | 24 hours |
| `CATALOG_CACHE_TTL` | Status cache duration | 5 minutes |

### Export Configuration

- **Batch Processing**: Large catalogs processed in batches
- **Rate Limiting**: Respects Square API rate limits
- **Retry Logic**: Automatic retry on temporary failures
- **Progress Tracking**: Real-time status updates

## Performance Optimization

### Database Performance

1. **Efficient Queries**: Optimized joins and aggregations
2. **Index Usage**: Proper indexing on foreign keys
3. **Batch Operations**: Bulk inserts and updates
4. **Connection Pooling**: Efficient connection management

### API Performance

1. **Parallel Processing**: Concurrent API requests where possible
2. **Response Caching**: Cache frequently accessed data
3. **Compression**: Efficient data transfer
4. **Timeout Handling**: Proper timeout configuration

### File Export Performance

1. **Streaming**: Large exports streamed to avoid memory issues
2. **Compression**: Efficient Excel file generation
3. **Temporary Files**: Proper cleanup and management
4. **Progress Indicators**: User feedback during long operations

## Security Considerations

### API Security

1. **Token Management**: Secure storage of Square API tokens
2. **HTTPS Only**: All API calls use secure connections
3. **Input Validation**: Sanitize all user inputs
4. **Rate Limiting**: Prevent API abuse

### File Security

1. **Temporary Storage**: Secure handling of export files
2. **Access Control**: Authenticated downloads only
3. **File Cleanup**: Automatic removal of temporary files
4. **Path Validation**: Prevent directory traversal attacks

## Troubleshooting

### Common Issues

1. **Export Not Starting**
   - Check Square API token configuration
   - Verify database connectivity
   - Review application logs for errors

2. **Missing Data in Export**
   - Ensure Square API has proper permissions
   - Check catalog data sync status
   - Verify location and category mappings

3. **Excel Export Failures**
   - Check disk space in export directory
   - Verify file permissions
   - Review pandas/openpyxl dependencies

### Debug Tools

1. **Status Monitoring**: Real-time export status dashboard
2. **API Health Check**: Verify external service connectivity
3. **Database Statistics**: View sync status and data counts
4. **Log Analysis**: Detailed error logging and stack traces

## Integration Points

### With Other Pages

1. **Dashboard**: Shows catalog status summary
2. **Reports Page**: Uses catalog data for inventory reports
3. **Items Page**: Displays detailed item information from catalog
4. **Admin Page**: Provides comprehensive sync controls

### External Systems

1. **Square POS**: Source of catalog data
2. **Vendor Systems**: Export data for supplier communication
3. **Inventory Management**: Stock level synchronization
4. **Reporting Systems**: Data feeds for business intelligence

The Catalog page is essential for maintaining accurate product information and enabling efficient inventory management across the NyTex Fireworks business operations. 