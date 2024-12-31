# Reports Section

## Overview
This section contains all reporting templates for the NYTEX Dashboard. The reports are organized into categories for easy navigation and maintenance. Each report is designed to be modular, reusable, and follow consistent design patterns.

## Structure
```
app/
├── database/
│   └── queries/                    # All SQL queries
│       ├── missing_sku_inventory.sql
│       └── other_reports.sql
├── services/
│   └── reports/
│       ├── __init__.py
│       ├── query_executor.py       # Generic SQL executor service
│       └── report_service.py       # Report-specific logic
├── routes/
│   └── reports/
│       ├── __init__.py
│       └── report_routes.py        # HTMX-friendly route handlers
└── templates/
    └── reports/
        ├── index.html             # Reports landing page
        ├── inventory/             # Inventory-related reports
        │   ├── missing_sku.html
        │   └── ...
        ├── sales/                 # Sales-related reports
        │   └── ...
        └── customers/             # Customer-related reports
            └── ...
```

## Architecture
The reports section follows a clean separation of concerns:

1. **SQL Queries** (`app/database/queries/`):
   - Pure SQL files
   - Version controlled
   - Independent of frontend
   - Easy to modify without touching templates

2. **Services** (`app/services/reports/`):
   - Query execution logic
   - Data transformation
   - Business logic
   - Report-specific operations

3. **Routes** (`app/routes/reports/`):
   - HTMX-friendly endpoints
   - Handle request parameters
   - Coordinate between services and templates
   - Return HTML fragments for dynamic updates

4. **Templates** (`app/templates/reports/`):
   - Pure HTML/Jinja2 templates
   - HTMX attributes for interactivity
   - No embedded SQL
   - Focused on presentation

## Categories

### Inventory Reports
Reports focused on inventory management, stock levels, and SKU integrity:
- Missing/Generated SKU Report
- Low Stock Report
- Dead Stock Report
- Inventory Discrepancy Report

### Sales Reports
Reports focused on sales performance and trends:
- Daily Sales Report
- Seasonal Comparison
- Product Performance
- Location Performance

### Customer Reports
Reports focused on customer behavior and demographics:
- Customer Demographics
- Purchase Patterns
- Loyalty Program Stats

## Design Goals
1. **Consistency**: All reports follow the same design patterns and UI components
2. **Modularity**: Each report is self-contained and reusable
3. **Performance**: Reports use HTMX for dynamic updates without full page reloads
4. **Scalability**: Structure supports easy addition of new reports and categories
5. **User Experience**: 
   - Intuitive navigation
   - Consistent filtering and sorting
   - Clear data presentation
   - Mobile-responsive design

## Features
Each report includes:
- Filtering capabilities
- Sortable columns
- Export functionality
- Print-friendly version
- Last updated timestamp
- Loading indicators
- Error handling

## Navigation
- Main navbar "Reports" link leads to reports landing page
- Landing page organizes reports by category
- Each report card shows:
  - Report name
  - Brief description
  - Last run timestamp
  - Quick stats preview
  - "View Report" button

## Implementation Notes
- Uses HTMX for dynamic content updates
- Implements responsive design principles
- Follows project's established CSS framework
- Uses consistent component templates
- Implements proper error handling and loading states 