# Items Page Documentation

## Overview
The Items page (`/items`) provides comprehensive inventory management and item discovery functionality for NyTex Fireworks. It features advanced filtering, sorting, searching, and export capabilities built on the Tabulator.js library for professional data grid functionality.

## Page URL
- **Main Items**: `/items`
- **JSON Data API**: `/items/data`
- **Export Endpoint**: `/items/export`

## What This Page Does

The Items page serves as the central inventory management system with the following key functions:

1. **Comprehensive Item Browsing**: View all inventory items with detailed information
2. **Advanced Filtering**: Multi-dimensional filtering by category, vendor, item type, and more
3. **Real-time Search**: Global search across all item attributes
4. **Professional Data Grid**: Tabulator.js-powered table with sorting, pagination, and export
5. **Data Export**: Export filtered data to Excel, CSV, or JSON formats
6. **Item Comparison**: Side-by-side comparison of inventory items

## Page Components

### 1. **Advanced Data Grid (Tabulator.js)**
- **Professional Interface**: Enterprise-grade data table functionality
- **Column Sorting**: Click-to-sort on any column with visual indicators
- **Pagination**: Server-side pagination for large datasets
- **Responsive Design**: Adapts to different screen sizes
- **Row Selection**: Multi-row selection for bulk operations

**Data Source**:
- `ItemsService.get_items()` method
- Real-time database queries with filtering and sorting
- Server-side processing for optimal performance

### 2. **Multi-Dimensional Filtering**
- **Category Filter**: Filter by product categories
- **Vendor Filter**: Filter by supplier/vendor
- **Item Type Filter**: Filter by classification type
- **Global Search**: Text search across all columns
- **Filter Combinations**: Multiple filters applied simultaneously

**Data Source**:
- Filter options from `ItemsService.get_filter_options()`
- Dynamic filter combinations processed server-side
- Real-time filter results via HTMX

### 3. **Export System**
- **Multiple Formats**: Excel (.xlsx), CSV (.csv), JSON (.json)
- **Filtered Exports**: Export respects current filters and search
- **Formatted Output**: Professional formatting with headers
- **Large Dataset Support**: Handles exports of thousands of items

**Data Source**:
- Current filtered dataset
- Export processing via pandas DataFrames
- File generation in `app/static/exports/`

### 4. **Item Information Display**
- **Detailed Columns**: Name, SKU, description, price, cost, quantity
- **Vendor Information**: Supplier details and vendor codes
- **Category Classification**: Product categorization
- **Stock Status**: Current inventory levels
- **Price Information**: Both selling price and cost

**Data Source**:
- Comprehensive database joins across multiple tables
- Real-time inventory data
- Price and cost information from catalog variations

## Data Grid Features

### Tabulator.js Integration

The Items page uses Tabulator.js for professional data grid functionality:

**Key Features**:
- Server-side pagination and sorting
- Column resizing and reordering
- Advanced filtering with multiple operators
- Export functionality built-in
- Responsive design with mobile optimization

**Configuration**:
```javascript
var table = new Tabulator("#items-table", {
    ajaxURL: "/items/data",
    pagination: "remote",
    paginationSize: 50,
    layout: "fitColumns",
    responsiveLayout: "hide",
    columns: [
        {title: "Item Name", field: "item_name", sorter: "string"},
        {title: "SKU", field: "sku", sorter: "string"},
        {title: "Category", field: "category", sorter: "string"},
        {title: "Vendor", field: "vendor_name", sorter: "string"},
        {title: "Price", field: "price", sorter: "number", formatter: "money"},
        {title: "Quantity", field: "quantity", sorter: "number"}
    ]
});
```

### Server-Side Processing

The Items page implements efficient server-side data processing:

1. **Pagination**: Only loads visible rows
2. **Sorting**: Database-level sorting for performance
3. **Filtering**: SQL-based filtering for efficiency
4. **Search**: Full-text search across multiple columns

### Column Definitions

| Column | Description | Sortable | Filterable |
|--------|-------------|----------|------------|
| Item Name | Product name | Yes | Yes |
| SKU | Stock Keeping Unit | Yes | Yes |
| Description | Product description | No | Yes |
| Category | Product category | Yes | Yes |
| Vendor | Supplier name | Yes | Yes |
| Vendor Code | Supplier item code | Yes | Yes |
| Price | Selling price | Yes | No |
| Cost | Purchase cost | Yes | No |
| Quantity | Current stock | Yes | No |

## Filtering System

### Filter Types

1. **Category Filter**
   - Dropdown selection of all available categories
   - Hierarchical category support
   - Multi-select capability

2. **Vendor Filter**
   - Dropdown of all suppliers/vendors
   - Vendor name and code search
   - Active vendor filtering

3. **Item Type Filter**
   - Classification by item type
   - Custom type definitions
   - Type hierarchy support

4. **Global Search**
   - Searches across all text fields
   - Real-time search results
   - Highlighted matching terms

### Filter Implementation

```python
# Server-side filter processing
filters = {}
for key, value in query_params.items():
    if key.startswith('filter[') and '[field]' in key:
        # Parse Tabulator filter format
        filter_index = extract_filter_index(key)
        field_name = value
        filter_value = query_params.get(f'filter[{filter_index}][value]')
        
        if filter_value:
            filters[field_name] = filter_value

# Apply filters to query
items = await ItemsService.get_items(
    session=session,
    filters=filters,
    sort=sort_field,
    direction=sort_dir,
    search=global_search
)
```

## Data Sources and Flow

### Primary Data Sources

1. **Catalog Items Table** (`catalog_items`)
   - item_id, name, description, category_id
   - price_money, created_at, updated_at
   - is_deleted, square_item_id

2. **Catalog Variations Table** (`catalog_variations`)
   - variation_id, item_id, sku, name
   - price_money, cost_money, inventory_alert_type
   - track_inventory, quantity

3. **Vendors Table** (`vendors`)
   - vendor_id, name, vendor_code
   - contact_information, status

4. **Categories Table** (`catalog_categories`)
   - category_id, name, square_category_id
   - parent_category_id, is_deleted

5. **Inventory Table** (`catalog_inventory`)
   - inventory_id, catalog_object_id, location_id
   - quantity, updated_at

### Data Processing Pipeline

1. **Data Collection**
   ```python
   async def get_items(session, sort=None, direction="asc", search=None, filters=None):
       # Build complex query with joins
       query = """
       SELECT DISTINCT
           ci.name as item_name,
           cv.sku,
           ci.description,
           cc.name as category,
           v.name as vendor_name,
           v.vendor_code,
           cv.price_money as price,
           cv.cost_money as cost,
           COALESCE(SUM(inv.quantity), 0) as quantity
       FROM catalog_items ci
       LEFT JOIN catalog_variations cv ON ci.id = cv.item_id
       LEFT JOIN catalog_categories cc ON ci.category_id = cc.id
       LEFT JOIN vendors v ON ci.vendor_id = v.id
       LEFT JOIN catalog_inventory inv ON cv.id = inv.catalog_object_id
       WHERE ci.is_deleted = false
       """
       
       # Apply filters and sorting
       # Execute query and return results
   ```

2. **Filter Application**
   - Dynamic WHERE clause construction
   - Parameter binding for security
   - Multiple filter combination logic

3. **Result Processing**
   - Data type conversion
   - Currency formatting
   - Null value handling

## Export Functionality

### Export Formats

1. **Excel (XLSX)**
   - Professional spreadsheet format
   - Formatted columns with proper data types
   - Headers and styling applied

2. **CSV**
   - Comma-separated values
   - UTF-8 encoding
   - Standard delimiter format

3. **JSON**
   - Structured data format
   - Nested object support
   - API-friendly output

### Export Process

```python
@router.get("/export")
async def items_export(
    request: Request,
    format: str = "xlsx",
    global_search: Optional[str] = None,
    sort: Optional[str] = None,
    dir: str = "asc"
):
    # Get filtered data
    items = await ItemsService.get_items(
        session=session,
        search=global_search,
        sort=sort,
        direction=dir,
        filters=parsed_filters  # From query parameters
    )
    
    # Generate export file
    if format == "xlsx":
        filename = await export_to_excel(items)
    elif format == "csv":
        filename = await export_to_csv(items)
    elif format == "json":
        filename = await export_to_json(items)
    
    # Return file download
    return FileResponse(path=file_path, filename=filename)
```

### Export File Management

- **Storage Location**: `app/static/exports/`
- **Filename Convention**: `items_export_{timestamp}.{format}`
- **File Cleanup**: Automatic removal after 24 hours
- **Download Security**: Temporary URLs with expiration

## Technical Implementation

### Service Layer Architecture

```python
class ItemsService:
    @staticmethod
    async def get_items(session, sort=None, direction="asc", search=None, filters=None):
        """Get items with filtering, sorting, and search"""
        # Complex query building with dynamic WHERE clauses
        # Parameter binding for security
        # Result processing and formatting
        
    @staticmethod
    async def get_filter_options(session):
        """Get available filter options"""
        # Query unique categories, vendors, item types
        # Format for dropdown consumption
        
    @staticmethod
    async def export_items(items, format="xlsx"):
        """Export items to specified format"""
        # Format-specific export logic
        # File generation and storage
```

### HTMX Integration

While the Items page primarily uses Tabulator.js for interactivity, HTMX is used for:

1. **Filter Updates**: Dynamic filter option loading
2. **Export Triggers**: Initiating export operations
3. **Status Updates**: Real-time operation feedback

### Performance Optimizations

1. **Database Indexing**: Proper indexes on frequently queried columns
2. **Query Optimization**: Efficient JOIN operations and WHERE clauses
3. **Pagination**: Server-side pagination reduces memory usage
4. **Caching**: Filter options cached for performance
5. **Connection Pooling**: Efficient database connection management

## API Endpoints

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/items/` | GET | Main items page |
| `/items/data` | GET | JSON data for Tabulator |
| `/items/export` | GET | Export items data |
| `/items/table` | GET | HTML table component |
| `/items/comparison` | GET | Item comparison page |

### Data API Response Format

```json
{
  "data": [
    {
      "item_name": "Roman Candle 10-Shot",
      "sku": "RC-10-001",
      "description": "Premium 10-shot Roman candle",
      "category": "Roman Candles",
      "vendor_name": "Fireworks Wholesale Inc",
      "vendor_code": "FWI-RC10",
      "price": 15.99,
      "cost": 8.50,
      "quantity": 150
    }
  ],
  "last_page": 1,
  "last_row": 1250
}
```

## Configuration

### Table Configuration

| Setting | Purpose | Default |
|---------|---------|---------|
| `ITEMS_PAGE_SIZE` | Items per page | 50 |
| `ITEMS_MAX_EXPORT` | Maximum export rows | 10,000 |
| `ITEMS_CACHE_TTL` | Filter cache duration | 10 minutes |
| `ITEMS_SEARCH_MIN_LENGTH` | Minimum search length | 3 characters |

### Performance Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `DB_QUERY_TIMEOUT` | Query timeout | 30 seconds |
| `EXPORT_TIMEOUT` | Export timeout | 300 seconds |
| `PAGINATION_MAX_SIZE` | Maximum page size | 200 |

## Security Considerations

### Data Protection

1. **SQL Injection Prevention**: Parameterized queries and ORM usage
2. **Input Validation**: All user inputs sanitized
3. **Access Control**: Authentication required for sensitive data
4. **Export Security**: Temporary files with restricted access

### Performance Security

1. **Rate Limiting**: Prevent excessive API calls
2. **Query Complexity**: Limits on expensive operations
3. **Memory Management**: Pagination prevents memory exhaustion
4. **File Security**: Export file cleanup and access control

## Troubleshooting

### Common Issues

1. **Slow Loading**
   - Check database indexes on filtered columns
   - Review query execution plans
   - Verify connection pool settings

2. **Export Failures**
   - Check disk space in export directory
   - Verify pandas/openpyxl dependencies
   - Review export timeout settings

3. **Filter Not Working**
   - Verify filter parameter parsing
   - Check database column mappings
   - Review JavaScript console for errors

### Debug Tools

1. **SQL Query Logging**: Enable query logging for troubleshooting
2. **Performance Monitoring**: Track query execution times
3. **Error Logging**: Comprehensive error reporting and stack traces
4. **Browser DevTools**: Network tab for API debugging

## Integration Points

### With Other Pages

1. **Reports Page**: Links to detailed item reports
2. **Dashboard**: Summary statistics on dashboard
3. **Catalog Page**: Integration with catalog management
4. **Admin Page**: Item data sync status

### External Systems

1. **Square POS**: Source of item and inventory data
2. **Vendor Systems**: Export data for supplier communication
3. **Accounting Systems**: Cost and pricing data integration
4. **Warehouse Management**: Inventory level synchronization

The Items page serves as the comprehensive inventory management hub, providing detailed item information with advanced filtering, searching, and export capabilities essential for efficient business operations. 