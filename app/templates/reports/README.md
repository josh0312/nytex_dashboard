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

## Design System
To maintain consistency with the dashboard, we follow these design patterns:

### Color Schemes
1. **Inventory Section (Blue)**
   ```html
   <!-- Card -->
   bg-blue-100 dark:bg-blue-800/40
   <!-- Icon Background -->
   bg-blue-200 dark:bg-blue-700
   <!-- Icon -->
   text-blue-600 dark:text-blue-400
   <!-- Hover States -->
   hover:bg-blue-50 dark:hover:bg-blue-700/50
   ```

2. **Sales Section (Indigo)**
   ```html
   <!-- Card -->
   bg-indigo-100 dark:bg-indigo-800/40
   <!-- Icon Background -->
   bg-indigo-200 dark:bg-indigo-700
   <!-- Icon -->
   text-indigo-600 dark:text-indigo-400
   <!-- Hover States -->
   hover:bg-indigo-50 dark:hover:bg-indigo-700/50
   ```

3. **Customer Section (Green)**
   ```html
   <!-- Card -->
   bg-green-100 dark:bg-green-800/40
   <!-- Icon Background -->
   bg-green-200 dark:bg-green-700
   <!-- Icon -->
   text-green-600 dark:text-green-400
   <!-- Hover States -->
   hover:bg-green-50 dark:hover:bg-green-700/50
   ```

4. **Alert Section (Red)**
   ```html
   <!-- Card -->
   bg-red-100 dark:bg-red-800/40
   <!-- Icon Background -->
   bg-red-200 dark:bg-red-700
   <!-- Icon -->
   text-red-600 dark:text-red-400
   <!-- Hover States -->
   hover:bg-red-50 dark:hover:bg-red-700/50
   ```

5. **Status Section (Yellow)**
   ```html
   <!-- Card -->
   bg-yellow-100 dark:bg-yellow-800/40
   <!-- Icon Background -->
   bg-yellow-200 dark:bg-yellow-700
   <!-- Icon -->
   text-yellow-600 dark:text-yellow-400
   <!-- Hover States -->
   hover:bg-yellow-50 dark:hover:bg-yellow-700/50
   ```

### Usage Guidelines
- **Blue**: Used for inventory and data-focused sections
- **Indigo**: Primary color for sales and revenue sections
- **Green**: Used for customer and success metrics
- **Red**: Reserved for alerts, warnings, and critical notifications
- **Yellow**: Ideal for status indicators, pending states, or attention-needed items

### Component Patterns
1. **Card Structure**
   ```html
   <div class="bg-{color}-100 dark:bg-{color}-800/40 shadow-sm rounded-lg overflow-hidden">
     <div class="p-4">
       <!-- Content -->
     </div>
   </div>
   ```

2. **Icon Containers**
   ```html
   <div class="p-3 bg-{color}-200 dark:bg-{color}-700 rounded-full mr-4">
     <i class="h-6 w-6 text-{color}-600 dark:text-{color}-400"></i>
   </div>
   ```

3. **Spacing**
   - Grid gap: `gap-4`
   - Padding: `p-4`
   - Margins: `mb-4`
   - Icon spacing: `mr-4`

4. **Typography**
   - Headers: `text-2xl font-semibold`
   - Subheaders: `text-xl font-semibold`
   - Body: `text-sm text-gray-500 dark:text-gray-400`
   - Links: `font-medium text-gray-900 dark:text-white`

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