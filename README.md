# NYTEX Dashboard

A FastAPI-based dashboard for monitoring sales data across NYTEX Fireworks locations.

## Features

- Real-time sales metrics from Square API
- Seasonal sales tracking with daily breakdowns
- Location-specific sales monitoring
- Interactive charts using Chart.js
- Responsive design with Tailwind CSS
- **Comprehensive reporting system with real-time data**
- **Automated daily data synchronization from Square**

## Data Synchronization

The dashboard maintains current data through an automated synchronization process that runs daily at 6:00 AM Central Time.

### Complete Sync Process

The **Complete Sync** (`/admin/complete-sync`) is a comprehensive 3-step process that ensures all data is current:

1. **Step 1: Locations** - Syncs store locations from Square API
2. **Step 2: Catalog Data** - Syncs categories, items, and variations  
3. **Step 3: Inventory** - Syncs current stock quantities for all locations

> **📖 Detailed Documentation**: See [`docs/COMPLETE_SYNC_PROCESS.md`](docs/COMPLETE_SYNC_PROCESS.md) for complete technical details including:
> - Step-by-step process flow
> - Database tables affected at each step
> - Square API endpoints used
> - Error handling and troubleshooting
> - Performance characteristics
> - Monitoring and alerting

### Quick Sync Operations

**Manual Sync**: Visit the [Admin Sync Page](https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync) or run:
```bash
curl -X POST "https://nytex-dashboard-932676587025.us-central1.run.app/admin/complete-sync"
```

**Health Check**: Monitor sync status anytime:
```bash
./scripts/check_production_health.sh
```

**Automated Schedule**: 
- **Daily**: 6:00 AM Central Time via Google Cloud Scheduler
- **Monitoring**: Every 4 hours via automated health checks

## Reports System

The dashboard includes a powerful reporting system that provides real-time insights into inventory and sales data directly from Square.

### Inventory Reports

#### Missing SKU Report
- **Purpose**: Identifies items with missing or auto-generated SKUs
- **Columns**: Location, Item Name, Vendor, SKU, Price, Category, Quantity
- **Features**: Real-time sorting, HTMX updates, Excel export
- **Access**: `/reports/inventory/missing-sku`

#### Missing Category Report ⭐ *New*
- **Purpose**: Identifies items with missing categories or orphaned category references
- **Columns**: Item Name, Vendor, Price, Quantity, Category Status
- **Features**: 
  - Real-time sorting on all columns
  - Color-coded status indicators:
    - 🔴 Red: No Category Assigned
    - 🟡 Yellow: Orphaned Category Reference
    - 🔵 Blue: Vendor information
    - 🟢 Green: Positive inventory quantities
  - Inventory aggregated across all locations
  - HTMX-powered updates for smooth user experience
  - Excel export capability
- **Access**: `/reports/inventory/missing-category`
- **Query**: `app/database/queries/missing_category_inventory.sql`

#### Missing Description Report ⭐ *New*
- **Purpose**: Identifies items with missing descriptions or incomplete description data
- **Columns**: Item Name, Vendor, Price, Quantity, Description Status
- **Features**: 
  - Real-time sorting on all columns
  - Color-coded status indicators:
    - 🔴 Red: No Description (all description fields empty)
    - 🟡 Yellow: HTML Only (has HTML description but missing main description)
    - 🟠 Orange: Plain Text Only (has plain text but missing main description)
    - 🔵 Blue: Vendor information
    - 🟢 Green: Positive inventory quantities
  - Checks all Square description fields: `description`, `description_html`, `description_plaintext`
  - Inventory aggregated across all locations
  - HTMX-powered updates for smooth user experience
  - Excel export capability
- **Access**: `/reports/inventory/missing-description`
- **Query**: `app/database/queries/missing_description_inventory.sql`
- **Data Source**: Square Catalog API - checks parent `CatalogItem` objects for description fields

#### Missing Vendor Info Report ⭐ *New*
- **Purpose**: Identifies items with missing vendor information or incomplete vendor data
- **Columns**: Item Name, Price, Quantity, Vendor, SKU, Status
- **Features**: 
  - Real-time sorting on all columns
  - Color-coded status indicators:
    - 🔴 Red: No Vendor & No SKU (critical - missing both)
    - 🟠 Orange: No Vendor Assigned (missing vendor assignment)
    - 🟡 Yellow: No SKU (missing SKU information)
    - 🟣 Purple: Orphaned Vendor ID (vendor ID exists but vendor record missing)
    - 🔵 Blue: Valid vendor information
    - 🟢 Green: Positive inventory quantities
  - Checks vendor assignment and SKU presence (vendor-specific SKU/cost not available in Square API)
  - Inventory aggregated across all locations
  - HTMX-powered updates for smooth user experience
  - Excel export capability
- **Access**: `/reports/inventory/missing-vendor-info`
- **Query**: `app/database/queries/missing_vendor_info_inventory.sql`
- **Data Source**: Square Catalog API - checks `catalog_vendor_info` and `catalog_variations` tables
- **Note**: Square's Catalog API doesn't store vendor-specific SKUs or costs separately from main item data

### Report Architecture

The reporting system follows a clean, modular architecture:

```
app/
├── database/
│   └── queries/                    # SQL queries for reports
│       ├── missing_sku_inventory.sql
│       ├── missing_category_inventory.sql
│       ├── missing_description_inventory.sql
│       └── missing_vendor_info_inventory.sql
├── services/
│   └── reports/
│       └── query_executor.py       # Generic SQL executor service
├── routes/
│   └── reports/
│       └── report_routes.py        # FastAPI route handlers
└── templates/
    └── reports/
        ├── index.html             # Reports landing page
        ├── base_report.html       # Base template for all reports
        └── inventory/             # Inventory-specific reports
            ├── missing_sku.html
            ├── missing_sku_table.html
            ├── missing_category.html
            ├── missing_category_table.html
            ├── missing_description.html
            ├── missing_description_table.html
            ├── missing_vendor_info.html
            └── missing_vendor_info_table.html
```

### Key Features

- **Real-time Data**: All reports query live Square data
- **HTMX Integration**: Smooth, fast updates without page reloads
- **Sortable Columns**: Click any column header to sort data
- **Export Functionality**: Download reports to Excel format
- **Responsive Design**: Works on all screen sizes
- **Template Inheritance**: Consistent UI across all reports
- **Modular SQL**: Queries stored in separate files for easy maintenance

## Recent Updates

- **Added Missing Vendor Info Report**: New inventory report to identify items without vendor assignments or SKUs (100% vendor coverage found!)
- **Added Missing Description Report**: New inventory report to identify items without proper descriptions (checks all Square description fields)
- **Added Missing Category Report**: New inventory report to identify items without proper category assignments
- Migrated from Flask to FastAPI for improved performance
- Fixed seasonal sales chart to:
  - Show all days in the season up to today (including days with zero sales)
  - Properly handle timezone conversions for date comparisons
  - Exclude future dates from the chart
- Improved database model relationships and initialization
- Added proper error handling and logging
- Implemented comprehensive reporting system with HTMX

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   npm install  # For Tailwind CSS
   ```

3. Set up environment variables in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
   SQUARE_ACCESS_TOKEN=your_square_token
   SQUARE_ENVIRONMENT=production
   SECRET_KEY=your_secret_key
   ```

4. Build CSS (for development):
   ```bash
   npx tailwindcss -i ./app/static/css/src/main.css -o ./app/static/css/dist/styles.css --watch
   ```

5. Run the application:
   ```bash
   python run.py
   ```

## Development

- The application uses SQLAlchemy for async database operations
- Templates are rendered using Jinja2 with HTMX for dynamic updates
- Static files are served from `app/static`
- Database models are in `app/database/models`
- Routes are in `app/routes`
- Services (business logic) are in `app/services`
- SQL queries are stored in `app/database/queries`

### Adding New Reports

1. Create SQL query in `app/database/queries/your_report.sql`
2. Add route handler in `app/routes/reports/report_routes.py`
3. Create templates in `app/templates/reports/category/`
4. Add link to `app/templates/reports/index.html`
5. Test with QueryExecutor: `await executor.execute_query_to_df('your_report')`

## Testing

Run the test suite:
```bash
pytest
```

Test specific reports:
```bash
python test_missing_category.py
python test_query_executor.py
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Submit a pull request

## License

Proprietary - All rights reserved 