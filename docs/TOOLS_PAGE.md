# Tools Page Documentation

## Overview
The Tools page (`/tools`) provides administrative utilities and specialized tools for managing the NyTex Fireworks system. It offers dedicated interfaces for catalog export, inventory updates, and system maintenance operations that support daily business operations.

## Page URL
- **Main Tools**: `/tools`
- **Square Catalog Export**: `/tools/square-catalog-export`
- **Square Inventory Update**: `/tools/square-inventory-update`

## What This Page Does

The Tools page serves as the utility hub with the following key functions:

1. **Administrative Tools Access**: Centralized access to system management tools
2. **Square Catalog Export**: Dedicated interface for catalog data export operations
3. **Square Inventory Update**: Specialized tool for inventory synchronization
4. **System Maintenance**: Utilities for routine system maintenance and updates
5. **Quick Operations**: Fast access to frequently used administrative functions

## Page Components

### 1. **Tools Landing Page**
- **Tool Navigation**: Links to all available administrative tools
- **Quick Access**: Direct links to most commonly used functions
- **Status Overview**: High-level status of various system components
- **User-Friendly Interface**: Simplified access to complex operations

**Data Source**:
- Static tool configuration
- Real-time system status checks
- User permission-based tool visibility

### 2. **Square Catalog Export Tool**
- **Export Interface**: User-friendly interface for catalog export operations
- **Status Monitoring**: Real-time status of export operations
- **Progress Tracking**: Visual indicators of export progress
- **Export History**: History of recent export operations

**Data Source**:
- `SquareCatalogService` for export operations
- Database status queries for export tracking
- Square API integration for data source

### 3. **Square Inventory Update Tool**
- **Inventory Sync Interface**: Dedicated interface for inventory updates
- **Location-Specific Status**: Status breakdown by business location
- **Update Controls**: Start/stop controls for inventory sync operations
- **Detailed Reporting**: Comprehensive status and statistics

**Data Source**:
- Direct database queries on inventory tables
- Integration with complete sync system
- Location-specific inventory tracking

## Available Tools

### 1. **Square Catalog Export Tool** (`/tools/square-catalog-export`)

**Purpose**: Provides a dedicated interface for exporting catalog data from Square to the local database.

**Features**:
- **One-Click Export**: Simple button to trigger catalog export
- **Real-Time Status**: Live updates on export progress
- **Error Handling**: Clear error messages and recovery options
- **Export Metrics**: Detailed statistics on exported data

**Data Source**:
- `SquareCatalogService.export_catalog_to_database()`
- Status tracking in local database
- Square Catalog API for source data

**Key Components**:
| Component | Description | Function |
|-----------|-------------|----------|
| Export Button | Triggers catalog export | Initiates Square API sync |
| Status Display | Shows current export status | Real-time progress monitoring |
| Metrics Panel | Export statistics | Item counts and timing data |
| Error Display | Error messages and recovery | User-friendly error handling |

**Technical Implementation**:
```python
@router.get("/square-catalog-export")
async def square_catalog_export_tool(request: Request):
    # Get current export status
    async with get_session() as session:
        catalog_service = SquareCatalogService()
        status = await catalog_service.get_export_status(session)
    
    return templates.TemplateResponse("tools/square_catalog_export.html", {
        "request": request,
        "status": status
    })
```

### 2. **Square Inventory Update Tool** (`/tools/square-inventory-update`)

**Purpose**: Provides a specialized interface for updating inventory data from Square POS systems.

**Features**:
- **Inventory Sync Control**: Start/stop inventory update operations
- **Location Breakdown**: Status by individual business location
- **Comprehensive Statistics**: Total records, update times, location details
- **Error Recovery**: Automatic retry and error handling

**Data Source**:
- Direct inventory status queries using `get_inventory_status_direct()`
- Complete sync system integration via admin endpoints
- Location-specific inventory data from `catalog_inventory` table

**Key Components**:
| Component | Description | Function |
|-----------|-------------|----------|
| Update Button | Triggers inventory sync | Initiates complete sync process |
| Status Dashboard | Current inventory status | Real-time inventory statistics |
| Location Stats | Per-location breakdown | Location-specific inventory data |
| Progress Monitor | Sync progress tracking | Real-time operation monitoring |

**Status Information**:
- **Total Records**: Count of inventory records across all locations
- **Last Update**: Timestamp of most recent inventory sync
- **Location Stats**: Item count and quantity by location
- **Data Freshness**: Indicates if data is current

**Technical Implementation**:
```python
async def get_inventory_status_direct(session):
    """Get inventory status using direct database queries"""
    # Get total inventory records
    count_result = await session.execute(
        text("SELECT COUNT(*) FROM catalog_inventory")
    )
    total_records = count_result.scalar()
    
    # Get location-specific statistics
    location_result = await session.execute(
        text("""
            SELECT l.name, COUNT(ci.id) as item_count, SUM(ci.quantity) as total_qty
            FROM catalog_inventory ci
            JOIN locations l ON ci.location_id = l.id
            WHERE l.status = 'ACTIVE'
            GROUP BY l.name
            ORDER BY l.name
        """)
    )
    
    return {
        'total_records': total_records,
        'last_update': latest_update,
        'location_stats': location_stats,
        'has_data': total_records > 0
    }
```

## Tool Integration

### HTMX-Powered Interfaces

All tools use HTMX for dynamic updates and seamless user experience:

**Real-Time Updates**:
```html
<!-- Status component with auto-refresh -->
<div hx-get="/tools/square-inventory-update/status/component"
     hx-trigger="every 10s"
     hx-target="#inventory-status">
  Loading status...
</div>

<!-- Operation trigger -->
<button hx-post="/tools/square-inventory-update/start"
        hx-indicator="#sync-spinner"
        hx-target="#sync-status">
  Start Inventory Update
</button>
```

**Progressive Enhancement**:
- Tools work without JavaScript (graceful degradation)
- Enhanced experience with HTMX enabled
- Real-time updates without page refreshes
- Visual feedback for long-running operations

### Backend Integration

Tools integrate with core system services:

1. **Catalog Export Tool**
   - Uses `SquareCatalogService` for all operations
   - Integrates with Square Catalog API
   - Tracks status in database

2. **Inventory Update Tool**
   - Leverages complete sync system (`/admin/complete-sync`)
   - Uses direct database queries for status
   - Integrates with location management

### Error Handling and Recovery

**Comprehensive Error Management**:
1. **User-Friendly Messages**: Clear, actionable error descriptions
2. **Automatic Retry**: Built-in retry logic for transient failures
3. **Manual Recovery**: Options for users to retry failed operations
4. **Error Logging**: Detailed error information for troubleshooting

**Error Display Example**:
```html
<!-- Error component -->
<div class="error-panel" id="error-display">
  <h4>Operation Failed</h4>
  <p>{{ error_message }}</p>
  <button hx-post="/tools/retry-operation">
    Retry Operation
  </button>
</div>
```

## Data Flow and Integration

### System Integration Points

1. **Square API Integration**
   - Direct connection to Square Catalog API
   - Authentication via Square Access Token
   - Rate limiting and error handling

2. **Database Operations**
   - Real-time status queries
   - Transaction management for data integrity
   - Efficient bulk operations for large datasets

3. **Admin System Integration**
   - Leverages admin panel sync operations
   - Shares configuration and authentication
   - Consistent error handling and logging

### Data Sources

**Primary Data Sources**:
1. **Square APIs**: Catalog and inventory data from Square POS
2. **Local Database**: Status tracking and historical data
3. **System Configuration**: Tool settings and permissions

**Database Tables Used**:
- `catalog_items`: Product information
- `catalog_variations`: Product variations and SKUs
- `catalog_inventory`: Inventory levels by location
- `locations`: Business location information

## API Endpoints

### Tool Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tools/` | GET | Main tools landing page |
| `/tools/square-catalog-export` | GET | Catalog export tool interface |
| `/tools/square-inventory-update` | GET | Inventory update tool interface |
| `/tools/square-inventory-update/start` | POST | Start inventory update |
| `/tools/square-inventory-update/status` | GET | Get inventory status (JSON) |
| `/tools/square-inventory-update/status/component` | GET | Get status component (HTML) |

### API Response Formats

**Inventory Status Response**:
```json
{
  "success": true,
  "data": {
    "total_records": 15600,
    "last_update": "2024-01-15T10:30:00Z",
    "has_data": true,
    "location_stats": [
      {
        "location": "Main Store",
        "item_count": 1250,
        "total_quantity": 8500
      },
      {
        "location": "Warehouse",
        "item_count": 980,
        "total_quantity": 7100
      }
    ]
  }
}
```

**Operation Status Response**:
```json
{
  "success": true,
  "message": "Inventory update completed successfully",
  "data": {
    "operation": "inventory_update",
    "status": "completed",
    "records_processed": 15600,
    "duration": "2.5 minutes",
    "errors": 0
  }
}
```

## Configuration and Settings

### Tool Configuration

| Setting | Purpose | Default |
|---------|---------|---------|
| `TOOLS_ENABLED` | Enable/disable tools access | `true` |
| `TOOL_TIMEOUT` | Operation timeout | 300 seconds |
| `STATUS_REFRESH_INTERVAL` | Auto-refresh frequency | 10 seconds |
| `MAX_CONCURRENT_OPERATIONS` | Limit concurrent operations | 1 |

### Security Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `TOOLS_REQUIRE_AUTH` | Require authentication | `true` |
| `TOOLS_ADMIN_ONLY` | Restrict to admin users | `false` |
| `OPERATION_LOGGING` | Log all tool operations | `true` |

## Performance Considerations

### Optimization Strategies

1. **Efficient Database Queries**: Optimized queries for status information
2. **Background Processing**: Long operations run in background
3. **Real-Time Updates**: Efficient HTMX updates without full page loads
4. **Caching**: Status information cached to reduce database load

### Resource Management

1. **Memory Management**: Efficient handling of large datasets
2. **Connection Pooling**: Optimal database connection usage
3. **Rate Limiting**: Respects external API limits
4. **Timeout Handling**: Proper timeout management for operations

## Security and Access Control

### Access Control

1. **Authentication Required**: All tools require valid user session
2. **Operation Logging**: All tool usage logged for audit trail
3. **Error Information**: Sensitive error details restricted
4. **Input Validation**: All user inputs validated and sanitized

### Security Best Practices

1. **API Token Security**: Secure handling of Square API tokens
2. **Database Security**: Parameterized queries prevent SQL injection
3. **File Security**: Temporary files managed securely
4. **Network Security**: HTTPS for all external API calls

## Troubleshooting

### Common Issues

1. **Tool Not Loading**
   - Check user authentication status
   - Verify database connectivity
   - Review application logs for errors

2. **Export/Update Failures**
   - Verify Square API token configuration
   - Check internet connectivity
   - Review API rate limiting status

3. **Status Not Updating**
   - Check HTMX JavaScript loading
   - Verify endpoint accessibility
   - Review browser console for errors

### Debug Resources

1. **Application Logs**: Detailed operation logging
2. **Status Endpoints**: Direct API access for debugging
3. **Browser DevTools**: Network and console debugging
4. **Database Queries**: Direct database access for verification

## Integration Points

### With Other Pages

1. **Admin Page**: Advanced administrative functions
2. **Catalog Page**: Catalog management integration
3. **Dashboard**: Status summaries on main dashboard
4. **Reports Page**: Data quality reports

### External Systems

1. **Square POS**: Primary data source for catalog and inventory
2. **Database Systems**: Local data storage and status tracking
3. **Monitoring Systems**: Integration with system monitoring tools

The Tools page provides essential administrative utilities that simplify complex operations and enable efficient system management for NyTex Fireworks business operations. 