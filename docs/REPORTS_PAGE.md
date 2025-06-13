# Reports Page Documentation

## Overview
The Reports page (`/reports`) provides comprehensive business intelligence and inventory management reports for NyTex Fireworks. It offers detailed analysis tools for inventory optimization, data quality management, and operational insights.

## Page URL
- **Main Reports**: `/reports`
- **Report Exports**: `/reports/export/{query_name}`

## What This Page Does

The Reports page serves as the business intelligence hub with the following key functions:

1. **Inventory Analysis**: Detailed reports on stock levels, missing data, and inventory optimization
2. **Data Quality Management**: Identifies and helps resolve data inconsistencies
3. **Export Capabilities**: Generates Excel and PDF reports for offline analysis
4. **Interactive Filtering**: Dynamic filtering and sorting of report data
5. **Real-time Data**: Live inventory status and updated business metrics

## Available Reports

### 1. **Missing SKU Report** (`/reports/inventory/missing-sku`)

**Purpose**: Identifies inventory items that lack SKU (Stock Keeping Unit) information, which is critical for inventory tracking and vendor management.

**What It Shows**:
- Items without SKU codes
- Location-specific missing SKU data
- Vendor information for missing items
- Price and quantity information
- Category classification

**Data Source**: 
- SQL Query: `missing_sku_inventory.sql`
- Tables: `catalog_items`, `catalog_variations`, `catalog_inventory`, `locations`, `vendors`
- Logic: Joins inventory data to identify items where SKU is NULL or empty

**Key Columns**:
| Column | Description | Sortable |
|--------|-------------|----------|
| Location | Business location name | Yes |
| Item Name | Product name | Yes |
| Vendor | Supplier name | Yes |
| SKU | Stock Keeping Unit (shows as missing) | Yes |
| Price | Item price | Yes |
| Category | Product category | Yes |
| Quantity | Current stock level | Yes |

**Business Value**: Helps maintain accurate inventory tracking and enables proper vendor communication.

### 2. **Missing Category Report** (`/reports/inventory/missing-category`)

**Purpose**: Identifies inventory items that lack proper category classification, essential for organization and reporting.

**What It Shows**:
- Items without category assignments
- Vendor information for uncategorized items
- Price and quantity details
- Category status indicators

**Data Source**:
- SQL Query: `missing_category_inventory.sql`
- Tables: `catalog_items`, `catalog_categories`, `catalog_variations`, `vendors`
- Logic: Left joins to identify items where category relationships are missing

**Key Columns**:
| Column | Description | Sortable |
|--------|-------------|----------|
| Item Name | Product name | Yes |
| Vendor | Supplier name | Yes |
| Price | Item price | Yes |
| Quantity | Current stock level | Yes |
| Category Status | Shows categorization status | Yes |

**Business Value**: Ensures proper product organization and enables accurate category-based reporting.

### 3. **Missing Description Report** (`/reports/inventory/missing-description`)

**Purpose**: Identifies items lacking detailed descriptions, important for customer information and internal documentation.

**What It Shows**:
- Items with missing or incomplete descriptions
- Vendor and category information
- Current pricing and stock levels
- Items that need content updates

**Data Source**:
- SQL Query: `missing_description_inventory.sql`
- Tables: `catalog_items`, `catalog_variations`, `catalog_categories`, `vendors`
- Logic: Filters items where description fields are NULL, empty, or contain placeholder text

**Key Columns**:
| Column | Description | Sortable |
|--------|-------------|----------|
| Item Name | Product name | Yes |
| Vendor | Supplier name | Yes |
| Category | Product category | Yes |
| Price | Item price | Yes |
| Quantity | Current stock level | Yes |

**Business Value**: Improves customer experience and internal product knowledge.

### 4. **Missing Vendor Info Report** (`/reports/inventory/missing-vendor-info`)

**Purpose**: Identifies items with incomplete vendor information, critical for supply chain management.

**What It Shows**:
- Items missing vendor assignments
- Items with incomplete vendor data
- Product categories affected
- Stock levels for affected items

**Data Source**:
- SQL Query: `missing_vendor_info_inventory.sql`
- Tables: `catalog_items`, `vendors`, `catalog_variations`, `catalog_categories`
- Logic: Identifies items where vendor relationships are missing or incomplete

**Key Columns**:
| Column | Description | Sortable |
|--------|-------------|----------|
| Item Name | Product name | Yes |
| Category | Product category | Yes |
| Price | Item price | Yes |
| Quantity | Current stock level | Yes |
| Vendor Status | Shows vendor information status | Yes |

**Business Value**: Ensures proper supply chain tracking and vendor relationship management.

### 5. **Low Stock Report** (`/reports/inventory/low-stock`)

**Purpose**: Identifies items with stock levels below optimal thresholds, enabling proactive inventory management.

**What It Shows**:
- Items below minimum stock levels
- Location-specific stock levels
- Vendor information for reordering
- Total vs. location-specific views

**Data Source**:
- SQL Query: `low_stock_inventory.sql` (detailed) or `low_stock_inventory_simple.sql` (simplified)
- Tables: `catalog_inventory`, `catalog_items`, `catalog_variations`, `locations`, `vendors`
- Logic: Identifies items where current quantity is below defined thresholds

**View Options**:
- **Total View**: Aggregated stock across all locations
- **Location View**: Stock levels by individual location

**Key Columns**:
| Column | Description | Sortable |
|--------|-------------|----------|
| Item Name | Product name | Yes |
| Location | Business location (if location view) | Yes |
| Current Stock | Current quantity | Yes |
| Minimum Level | Reorder threshold | Yes |
| Vendor | Supplier for reordering | Yes |
| Category | Product category | Yes |

**Business Value**: Prevents stockouts and optimizes inventory turnover.

## Report Features

### Interactive Functionality

1. **Dynamic Sorting**
   - Click column headers to sort data
   - Toggle ascending/descending order
   - Multi-column sorting support
   - "None" option to return to original order

2. **HTMX Integration**
   - Real-time table updates without page refresh
   - Seamless sorting and filtering
   - Responsive user interface

3. **Export Options**
   - **Excel Export**: Full spreadsheet with formatting
   - **PDF Export**: Print-ready report format
   - **Filename Convention**: `{report_name}_{timestamp}.xlsx`

### Data Processing

1. **Query Execution**
   - Uses `QueryExecutor` service for consistent data access
   - Pandas DataFrame processing for data manipulation
   - Parameterized queries for security

2. **Error Handling**
   - Graceful degradation when data unavailable
   - User-friendly error messages
   - Logging for troubleshooting

3. **Performance Optimization**
   - Efficient SQL queries with proper indexing
   - Cached results where appropriate
   - Pagination for large datasets

## Data Sources and Flow

### Database Schema

The reports draw from the following key tables:

1. **`catalog_items`**: Core product information
   - item_id, name, description, category_id
   - vendor_id, price, cost, created_at, updated_at

2. **`catalog_variations`**: Product variations and SKUs
   - variation_id, item_id, sku, price, cost
   - quantity, units_per_case

3. **`catalog_inventory`**: Stock levels by location
   - inventory_id, item_id, location_id, quantity
   - updated_at, sync_status

4. **`locations`**: Business locations
   - location_id, name, address, status
   - postal_code (for weather integration)

5. **`vendors`**: Supplier information
   - vendor_id, name, contact_info, status
   - vendor_code, payment_terms

6. **`catalog_categories`**: Product categorization
   - category_id, name, description, parent_id

### Data Sync Process

1. **Square Integration**: Data synced from Square POS system
2. **Incremental Updates**: Regular sync to maintain data freshness
3. **Data Validation**: Quality checks during sync process
4. **Audit Trail**: Change tracking for data integrity

## Export System

### Export Formats

1. **Excel (XLSX)**
   - Formatted spreadsheets with headers
   - Data types preserved
   - Suitable for further analysis

2. **PDF**
   - Print-ready format
   - Professional appearance
   - Fixed layout for reports

### Export Process

1. **File Generation**
   ```python
   # Excel export
   filename = await executor.export_query_to_excel(query_name, params)
   
   # PDF export  
   filename = await executor.export_query_to_pdf(query_name, params)
   ```

2. **File Storage**
   - Location: `app/static/exports/`
   - Naming: `{query_name}_{timestamp}.{format}`
   - Cleanup: Automated removal of old files

3. **File Delivery**
   - Direct download via FileResponse
   - Proper MIME types
   - Browser-friendly filenames

## Technical Implementation

### HTMX Integration

Reports use HTMX for dynamic functionality:

```html
<!-- Sortable column headers -->
<th>
  <a hx-get="/reports/inventory/missing-sku?sort=item_name&direction=asc"
     hx-target="#report-table"
     hx-indicator="#loading-spinner">
    Item Name
  </a>
</th>

<!-- Export buttons -->
<a hx-get="/reports/export/missing_sku_inventory?format=xlsx"
   hx-indicator="#export-spinner">
  Export to Excel
</a>
```

### Query Execution

```python
# Report route handler
@router.get("/inventory/missing-sku")
async def missing_sku_report(request: Request, sort: str = None, direction: str = "asc"):
    # Execute query through QueryExecutor
    executor = QueryExecutor()
    df = await executor.execute_query_to_df("missing_sku_inventory")
    
    # Apply sorting
    if sort and direction != "none":
        df = df.sort_values(by=sort, ascending=(direction == "asc"))
    
    # Return appropriate template
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("reports/inventory/missing_sku_table.html", context)
    else:
        return templates.TemplateResponse("reports/inventory/missing_sku.html", context)
```

## Security and Access Control

### Data Protection

1. **SQL Injection Prevention**: Parameterized queries and ORM usage
2. **Input Validation**: All user inputs sanitized
3. **Access Logging**: Report access tracked for audit

### File Security

1. **Temporary Files**: Exports stored in secure temporary directory
2. **File Cleanup**: Automated removal of old export files
3. **Access Control**: Download links expire after use

## Performance Optimization

### Database Performance

1. **Query Optimization**: Efficient joins and WHERE clauses
2. **Index Usage**: Proper indexing on frequently queried columns
3. **Result Caching**: Cached results for expensive queries

### Frontend Performance

1. **Partial Updates**: HTMX enables partial page updates
2. **Lazy Loading**: Large datasets loaded progressively
3. **Client-side Caching**: Browser caching for static assets

## Configuration

### Report Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `REPORTS_EXPORT_DIR` | Export file storage location | `app/static/exports/` |
| `EXPORT_FILE_RETENTION` | How long to keep export files | 24 hours |
| `MAX_EXPORT_ROWS` | Maximum rows per export | 10,000 |
| `REPORT_CACHE_TTL` | Report data cache duration | 15 minutes |

### Query Configuration

Reports can be configured by modifying SQL files in `app/database/queries/`:

- `missing_sku_inventory.sql`
- `missing_category_inventory.sql`
- `missing_description_inventory.sql`
- `missing_vendor_info_inventory.sql`
- `low_stock_inventory.sql`

## Troubleshooting

### Common Issues

1. **Report Not Loading**
   - Check database connection
   - Verify SQL query syntax
   - Review application logs

2. **Export Failures**
   - Check disk space for export directory
   - Verify file permissions
   - Review export service logs

3. **Missing Data**
   - Ensure data sync is current
   - Check Square API connection
   - Verify table relationships

### Debug Information

1. **SQL Query Debugging**: Add logging to QueryExecutor
2. **Export Debugging**: Check export service logs
3. **Performance Monitoring**: Query execution times logged

## Integration Points

### With Other Systems

1. **Dashboard**: Summary metrics displayed on main dashboard
2. **Items Page**: Detailed item information accessible from reports  
3. **Admin Page**: Data sync status affects report accuracy
4. **Catalog Page**: Export data influences catalog management

### External Dependencies

1. **Square API**: Source of inventory data
2. **Database**: PostgreSQL for data storage
3. **File System**: Local storage for export files

The Reports page is essential for data-driven decision making, providing actionable insights into inventory management, data quality, and business operations. 