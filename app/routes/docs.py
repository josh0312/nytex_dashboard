from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from app.logger import logger
import markdown
from pathlib import Path
import re
from typing import Dict, List

router = APIRouter(tags=["documentation"])

# User Help Documentation Structure - USER-FACING ONLY
HELP_STRUCTURE = {
    "getting-started": {
        "title": "Getting Started",
        "content": """
# Getting Started with NyTex Dashboard

Welcome to the NyTex Fireworks Dashboard! This guide will help you navigate and use all the features available to you.

## What is this system?
The NyTex Dashboard is your central hub for managing inventory, viewing sales reports, and monitoring business performance across all store locations.

## Main Sections

### 🏠 Dashboard
Your home page showing key metrics, sales performance, and quick insights about your business.

### 📊 Reports  
Generate detailed reports about inventory, sales, and business performance. Perfect for analyzing trends and making informed decisions.

### 📦 Catalog
Manage your product catalog and export data. This connects with your Square POS system to keep everything synchronized.

### 🔍 Items
Search and browse your entire inventory with powerful filtering options. Find specific products quickly and efficiently.

### 🛠️ Tools
Administrative utilities for managing your system and performing maintenance tasks.

### ⚙️ Admin
System administration tools for data synchronization and system maintenance.

## Navigation Tips
- Use the top navigation bar to switch between sections
- Look for help icons (?) next to section titles for specific guidance
- The dashboard automatically updates with fresh data
- Most reports can be exported to Excel for further analysis

## Need More Help?
Each section has its own detailed help guide. Click the help icon (?) in any section to learn more about that specific area.
        """,
        "description": "Learn the basics of using the NyTex Dashboard"
    },
    "dashboard": {
        "title": "Using the Dashboard",
        "content": """
# How to Use the Dashboard

The Dashboard is your main overview of business performance and key metrics.

## What You'll See

### Key Metrics Cards
- **Total Sales**: Current period sales performance
- **Total Orders**: Number of orders processed
- **Active Locations**: Your store locations and their status
- **Low Stock Items**: Products that need restocking

### Charts and Graphs
- **Sales trends** over time
- **Location performance** comparison
- **Seasonal patterns** in your sales data

## How to Use It

### Reading the Metrics
1. **Green numbers** typically indicate positive performance
2. **Red numbers** may indicate areas needing attention
3. **Percentages** show change from previous periods

### Interacting with Charts
- **Hover** over chart elements to see detailed information
- **Charts refresh automatically** every few minutes
- **Time periods** may be adjustable depending on the chart

### Location Comparison
- Each location shows its individual performance
- Compare sales, orders, and inventory across stores
- Identify top-performing and underperforming locations

## What Actions Can You Take?
- **Export data** for further analysis
- **Click on metrics** to drill down into detailed reports
- **Monitor trends** to make informed business decisions
- **Identify issues** early through low stock alerts

## Troubleshooting
- If data seems outdated, try refreshing your browser
- Charts should update automatically - if they don't, check your internet connection
- Contact support if you see error messages

## Pro Tips
- Check the dashboard first thing each morning for overnight activity
- Use the trends to plan inventory orders
- Monitor seasonal patterns to prepare for busy periods
        """,
        "description": "Learn how to read and use the main dashboard"
    },
    "reports": {
        "title": "Generating Reports",
        "content": """
# How to Use the Reports Section

The Reports section helps you generate detailed business insights and export data for analysis.

## Available Reports

### Inventory Reports
- **Missing SKU Report**: Find products without proper SKU codes
- **Category Report**: Analyze products by category
- **Description Report**: Review product descriptions and details
- **Vendor Information**: Track supplier and vendor data
- **Low Stock Report**: Identify products that need restocking

## How to Generate Reports

### Step 1: Select Report Type
1. Navigate to the Reports section
2. Choose the type of report you want from the available options
3. Each report serves a different business purpose

### Step 2: Apply Filters (if available)
- **Date ranges**: Select specific time periods
- **Locations**: Filter by specific store locations
- **Categories**: Focus on particular product categories
- **Status**: Filter by product status (active, discontinued, etc.)

### Step 3: Generate and Review
1. Click "Generate Report" button
2. Wait for the report to load (may take a few moments for large datasets)
3. Review the results in the table format

### Step 4: Export Data
- **Excel**: Download as spreadsheet for further analysis
- **PDF**: Create printable reports for meetings
- **CSV**: Export raw data for custom analysis

## Understanding Report Data

### Column Meanings
- **SKU**: Stock Keeping Unit - unique product identifier
- **Description**: Product name and details
- **Category**: Product grouping/classification
- **Quantity**: Current stock levels
- **Location**: Which store the item is associated with

### Common Use Cases
- **Inventory Planning**: Use stock reports for ordering decisions
- **Category Analysis**: Understand which product types perform best
- **Data Quality**: Find and fix missing information
- **Vendor Management**: Track which suppliers provide which products

## Best Practices
- Run reports regularly to stay on top of inventory
- Export data before making major business decisions
- Use filters to focus on specific issues or opportunities
- Keep exported reports organized for historical comparison

## Troubleshooting
- Large reports may take longer to generate - be patient
- If a report fails to load, try refreshing and generating again
- Check your filters if you're not seeing expected data
- Contact support if you consistently have issues with specific reports
        """,
        "description": "Learn how to generate and use business reports"
    },
    "catalog": {
        "title": "Managing Your Catalog",
        "content": """
# How to Use Catalog Management

The Catalog section helps you manage your product catalog and keep it synchronized with your Square POS system.

## What is Catalog Management?
Your catalog contains all your product information - names, prices, categories, and inventory levels. This system keeps everything synchronized between your dashboard and Square POS.

## Main Features

### Catalog Export
- **Full Export**: Download your complete product catalog
- **Excel Format**: Get data in spreadsheet format for easy editing
- **Square Compatibility**: Data formatted to match Square's requirements

### Synchronization Status
- **Real-time Updates**: See when your catalog was last synchronized
- **Sync Progress**: Monitor ongoing synchronization processes
- **Error Notifications**: Get alerts if synchronization issues occur

## How to Export Your Catalog

### Step 1: Access Catalog Export
1. Navigate to the Catalog section
2. Look for the "Export Catalog" button or section
3. Choose your export options

### Step 2: Select Export Type
- **Complete Catalog**: All products and information
- **Recent Changes**: Only recently modified items
- **Specific Categories**: Filter by product category

### Step 3: Download and Use
1. Click "Start Export" to begin the process
2. Wait for the export to complete (shown by progress indicator)
3. Download the resulting Excel file
4. Open and review your catalog data

## Understanding Catalog Data

### Key Fields
- **Item Name**: Product title as shown to customers
- **SKU**: Unique identifier for inventory tracking
- **Category**: Product grouping for organization
- **Price**: Current selling price
- **Inventory**: Current stock levels
- **Location**: Which store(s) carry this item

## Synchronization Process

### How It Works
1. **Automatic Sync**: System regularly updates with Square POS
2. **Real-time Changes**: New products and price changes sync automatically
3. **Conflict Resolution**: System handles differences between systems

### Monitoring Sync Status
- **Green Status**: Everything synchronized successfully
- **Yellow Status**: Sync in progress - be patient
- **Red Status**: Issue needs attention - check error messages

## Best Practices
- **Regular Exports**: Download catalog data regularly for backup
- **Review Changes**: Check synchronized data for accuracy
- **Category Management**: Keep products properly categorized
- **Price Verification**: Ensure prices match your intended pricing

## Common Issues and Solutions

### Export Takes Too Long
- Large catalogs need more time - be patient
- Try exporting smaller sections if needed
- Check your internet connection

### Synchronization Errors
- Review error messages for specific issues
- Ensure Square POS system is accessible
- Contact support for persistent sync problems

### Data Discrepancies
- Compare exported data with Square POS
- Look for recent changes that might not have synced yet
- Run a fresh synchronization if needed

## Pro Tips
- Export your catalog before making major changes
- Use exported data to plan product additions or removals
- Keep exported files organized with dates for historical reference
- Review sync status regularly to catch issues early
        """,
        "description": "Learn how to manage and export your product catalog"
    },
    "items": {
        "title": "Searching and Managing Items",
        "content": """
# How to Use the Items Section

The Items section provides powerful search and filtering tools to help you find and manage specific products in your inventory.

## What You Can Do Here
- **Search** for specific products by name, SKU, or description
- **Filter** items by category, location, stock status, and more
- **Sort** results by different criteria
- **Export** filtered results for analysis
- **View** detailed item information

## How to Search for Items

### Basic Search
1. **Use the search box** at the top of the Items page
2. **Type keywords** like product names, SKU codes, or descriptions
3. **Press Enter** or click search to see results
4. **Results update automatically** as you type

### Advanced Filtering
- **Category Filter**: Show only items from specific categories
- **Location Filter**: See items from particular store locations
- **Stock Status**: Filter by in-stock, low-stock, or out-of-stock items
- **Price Range**: Find items within specific price ranges

## Understanding the Results

### Item Information Displayed
- **Product Name**: The item's title and description
- **SKU**: Unique inventory identifier
- **Category**: Product classification
- **Current Stock**: How many are available
- **Location**: Which store(s) have this item
- **Last Updated**: When information was last synchronized

### Sorting Options
- **Name**: Alphabetical order
- **Stock Level**: Highest to lowest (or vice versa)
- **Category**: Group similar items together
- **Location**: Organize by store location

## Working with Search Results

### Viewing Item Details
- **Click on any item** to see complete information
- **View stock history** and changes over time
- **See related items** in the same category

### Exporting Results
1. **Apply your filters** to show exactly what you need
2. **Click "Export"** button (usually Excel, CSV, or PDF options)
3. **Download the file** with your filtered results
4. **Use exported data** for inventory planning or analysis

## Common Search Scenarios

### Finding Low Stock Items
1. Use the stock status filter
2. Select "Low Stock" or set minimum quantity
3. Review items that need reordering
4. Export list for purchasing decisions

### Category Analysis
1. Filter by specific category
2. Sort by stock levels or sales performance
3. Identify top and bottom performers
4. Plan category-specific promotions

### Location-Specific Inventory
1. Filter by specific store location
2. See what's available at each store
3. Plan transfers between locations
4. Identify location-specific needs

## Best Practices

### Effective Searching
- **Use specific keywords** for faster results
- **Try different search terms** if you don't find what you're looking for
- **Use SKU codes** for exact matches
- **Combine filters** for precise results

### Regular Maintenance
- **Search for items without SKUs** to clean up data
- **Check for duplicate entries** using similar names
- **Review items with no category** for better organization
- **Find items with zero stock** for inventory management

## Troubleshooting

### Can't Find an Item
- **Check spelling** of search terms
- **Try shorter keywords** instead of full names
- **Use partial SKU codes** if you don't remember the complete code
- **Clear filters** that might be hiding results

### Search is Slow
- **Be more specific** with search terms to reduce results
- **Use filters** to narrow down the dataset
- **Check your internet connection**
- **Try refreshing the page** if it becomes unresponsive

### Data Looks Wrong
- **Check when data was last updated** (shown on the page)
- **Try refreshing** to get latest information
- **Compare with Square POS** if numbers seem incorrect
- **Contact support** for persistent data issues

## Pro Tips
- **Bookmark common searches** by saving the filtered URL
- **Export regularly** for offline analysis and backup
- **Use category filters** to focus on specific product lines
- **Combine multiple filters** for very specific searches
- **Save time** by using SKU codes for exact matches
        """,
        "description": "Learn how to search, filter, and manage your inventory items"
    }
}

# Cross-reference mappings for user help - SAFE INTERNAL LINKS ONLY
HELP_CROSS_REFERENCES = {
    "Dashboard": "/help/dashboard",
    "Reports": "/help/reports", 
    "Catalog": "/help/catalog",
    "Items": "/help/items",
    "search": "/help/items",
    "inventory": "/help/items",
    "export": "/help/catalog",
    "getting started": "/help/getting-started"
}

# Removed file reading functions since we're using inline content now

def process_cross_references(html_content: str, current_topic: str = None) -> str:
    """Add automatic cross-reference links to help content"""
    for term, link in HELP_CROSS_REFERENCES.items():
        # Skip self-references (don't link "Dashboard" on the dashboard page)
        if current_topic and link.endswith(f"/{current_topic}"):
            continue
            
        # Simple replacement - just avoid replacing if already in a link
        # Check if term is not already part of a link by looking for <a...>term</a> pattern
        if f'>{term}<' not in html_content and f'>{term.lower()}<' not in html_content:
            pattern = rf'\b{re.escape(term)}\b'
            replacement = f'<a href="{link}" class="help-link text-blue-600 dark:text-blue-400 hover:underline">{term}</a>'
            html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
    
    return html_content

def convert_markdown_to_html(markdown_content: str, current_topic: str = None) -> tuple[str, str]:
    """Convert markdown to HTML with extensions"""
    md = markdown.Markdown(
        extensions=[
            'toc',          # Table of contents
            'tables',       # Table support
            'fenced_code',  # Fenced code blocks
        ],
        extension_configs={
            'toc': {
                'permalink': False,  # Disable paragraph symbols
                'anchorlink': False  # Disable anchor links completely
            }
        }
    )
    
    html = md.convert(markdown_content)
    
    # Add cross-reference links (but avoid self-references)
    html = process_cross_references(html, current_topic)
    
    return html, getattr(md, 'toc', '')

# Removed complex path finding functions since we're using simple topic-based routing now

@router.get("/", response_class=HTMLResponse)
async def help_index(request: Request):
    """User help index page"""
    try:
        return templates.TemplateResponse("help/index.html", {
            "request": request,
            "title": "Help Center",
            "help_structure": HELP_STRUCTURE,
            "breadcrumbs": [{"title": "Help", "url": "/help"}]
        })
    except Exception as e:
        logger.error(f"Error loading help index: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading help")

@router.get("/{help_topic}", response_class=HTMLResponse)
async def help_page(request: Request, help_topic: str):
    """Serve individual help pages"""
    try:
        # Find the help entry
        if help_topic not in HELP_STRUCTURE:
            raise HTTPException(status_code=404, detail="Help topic not found")
        
        help_entry = HELP_STRUCTURE[help_topic]
        
        # Convert markdown content to HTML
        html_content, toc = convert_markdown_to_html(help_entry['content'], help_topic)
        
        # Generate breadcrumbs
        breadcrumbs = [
            {"title": "Help", "url": "/help"},
            {"title": help_entry['title'], "url": f"/help/{help_topic}"}
        ]
        
        return templates.TemplateResponse("help/page.html", {
            "request": request,
            "title": f"{help_entry['title']} - Help",
            "page_title": help_entry['title'],
            "description": help_entry.get('description', ''),
            "content": html_content,
            "toc": toc,
            "breadcrumbs": breadcrumbs,
            "help_structure": HELP_STRUCTURE
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading help page {help_topic}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading help page") 