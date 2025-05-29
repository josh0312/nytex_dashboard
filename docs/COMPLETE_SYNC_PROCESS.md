# Complete Sync Process Documentation

## Overview

The Complete Sync process (`/admin/complete-sync`) is a comprehensive data synchronization operation that pulls all necessary data from the Square API and populates the production database. This process ensures that the NyTex Dashboard has the most current information from Square for locations, catalog items, and inventory levels.

## Process Flow

The complete sync runs in **3 sequential steps** that must be executed in order due to foreign key dependencies:

```
Step 1: Locations → Step 2: Catalog Data → Step 3: Inventory Data
```

If any step fails, the entire process stops to maintain data integrity.

---

## Step 1: Location Sync (`sync_locations_direct`)

### Purpose
Synchronizes store locations from Square API. This is the foundation step as locations are required for all inventory tracking.

### Square API Endpoint
- **GET** `https://connect.squareup.com/v2/locations`

### Database Operations

#### Tables Cleared (in dependency order):
1. `catalog_inventory` - Inventory quantities
2. `catalog_variations` - Product variations
3. `catalog_items` - Catalog items  
4. `catalog_categories` - Product categories
5. `locations` - Store locations

> **⚠️ Important:** This step clears ALL catalog and inventory data to ensure a clean sync with proper foreign key relationships.

#### Tables Populated:
**`locations`** table:
```sql
INSERT INTO locations (id, name, address, timezone, status, created_at, updated_at)
VALUES (...)
```

### Data Structure
- **id**: Square location ID (primary key)
- **name**: Location name (e.g., "Aubrey", "Terrell")
- **address**: JSON object with address details
- **timezone**: Location timezone
- **status**: "ACTIVE" or "INACTIVE"
- **created_at/updated_at**: Sync timestamps

### Expected Results
- Typically syncs **9 locations** (7 active, 2 inactive)
- All dependent tables are cleared for fresh data

---

## Step 2: Catalog Data Sync (`sync_catalog_direct`)

### Purpose
Synchronizes the complete product catalog including categories, items, and variations from Square.

### Square API Endpoint
- **POST** `https://connect.squareup.com/v2/catalog/search`

### Process Order
Catalog data is synced in dependency order:

#### 2.1 Categories Sync
**Square Object Type:** `CATEGORY`

**`catalog_categories`** table:
```sql
INSERT INTO catalog_categories (id, name, is_deleted, created_at, updated_at)
VALUES (...)
```

#### 2.2 Items Sync  
**Square Object Type:** `ITEM`

**`catalog_items`** table:
```sql
INSERT INTO catalog_items (id, name, description, category_id, is_deleted, created_at, updated_at)
VALUES (...)
```

#### 2.3 Variations Sync
**Square Object Type:** `ITEM_VARIATION`

**`catalog_variations`** table:
```sql
INSERT INTO catalog_variations (id, name, item_id, sku, price_money, is_deleted, created_at, updated_at)
VALUES (...)
```

### Data Structure

#### Categories
- **id**: Square category ID
- **name**: Category name
- **is_deleted**: Always `false` (active categories only)

#### Items
- **id**: Square item ID
- **name**: Product name
- **description**: Product description
- **category_id**: Foreign key to `catalog_categories.id`
- **is_deleted**: Always `false` (active items only)

#### Variations
- **id**: Square variation ID
- **name**: Variation name (e.g., size, color)
- **item_id**: Foreign key to `catalog_items.id`
- **sku**: Product SKU code
- **price_money**: JSON object with pricing info
- **is_deleted**: Always `false` (active variations only)

### Expected Results
- Categories: Variable count based on Square catalog
- Items: Hundreds of products
- Variations: Each item may have multiple variations

---

## Step 3: Inventory Sync (`sync_inventory_direct`)

### Purpose
Synchronizes current inventory quantities for all product variations across all active locations.

### Square API Endpoint
- **POST** `https://connect.squareup.com/v2/inventory/counts/batch-retrieve`

### Process Flow

#### 3.1 Location Processing
For each **ACTIVE** location:
1. Query Square API for inventory counts
2. Process all inventory items for that location
3. Insert inventory records

#### 3.2 Inventory Data Processing

**`catalog_inventory`** table:
```sql
INSERT INTO catalog_inventory (variation_id, location_id, quantity, calculated_at)
VALUES (...)
```

### Data Structure
- **variation_id**: Foreign key to `catalog_variations.id`
- **location_id**: Foreign key to `locations.id`
- **quantity**: Current stock quantity (integer)
- **calculated_at**: Timestamp when quantity was calculated

### API Request Details
```json
{
  "location_ids": ["location_id"],
  "updated_after": "2020-01-01T00:00:00Z"
}
```

### Expected Results
- Thousands of inventory records
- One record per variation per location (where inventory exists)
- Covers all active locations

---

## Database Schema Relationships

```
locations (id)
    ↓
catalog_inventory (location_id) ← catalog_variations (id)
                                        ↓
                                 catalog_items (id) ← catalog_categories (id)
                                        ↓
                                 catalog_variations (item_id)
```

## Error Handling

### Failure Points
1. **Square API Authentication**: Invalid or expired access token
2. **Network Issues**: Timeouts or connectivity problems  
3. **Database Constraints**: Foreign key violations
4. **Data Consistency**: Missing required fields

### Recovery Process
- If Step 1 fails: No data is changed
- If Step 2 fails: Only locations remain, all catalog data is cleared
- If Step 3 fails: Locations and catalog data exist, but no current inventory

### Monitoring
Use the health check script to monitor sync status:
```bash
./scripts/check_production_health.sh
```

---

## Scheduling

### Automated Schedule
- **Frequency**: Daily at 6:00 AM Central Time
- **Scheduler**: Google Cloud Scheduler
- **Job Name**: `daily-sync-job`
- **Endpoint**: `/admin/complete-sync`

### Manual Execution
```bash
# Via API
curl -X POST "https://nytex-dashboard-932676587025.us-central1.run.app/admin/complete-sync"

# Via Admin Interface
https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync
```

---

## Performance Characteristics

### Typical Execution Time
- **Step 1 (Locations)**: 5-10 seconds
- **Step 2 (Catalog)**: 30-60 seconds
- **Step 3 (Inventory)**: 60-180 seconds
- **Total**: 2-4 minutes

### API Limits
- **Timeout**: 600 seconds (10 minutes) for catalog/inventory operations
- **Rate Limits**: Managed by Square API throttling
- **Batch Size**: 1000 objects per catalog request

### Resource Usage
- **Memory**: Moderate (catalog data held in memory during processing)
- **Database**: High write activity during sync
- **Network**: Intensive API communication with Square

---

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
ERROR: AUTHENTICATION_ERROR - UNAUTHORIZED
```
**Solution**: Check Square access token configuration

#### 2. Location Sync Failures
```
ERROR: Location sync failed
```
**Check**: Network connectivity, Square API status

#### 3. Foreign Key Violations
```
ERROR: insert or update on table violates foreign key constraint
```
**Cause**: Data inconsistency, partial sync failure
**Solution**: Re-run complete sync

### Diagnostic Commands
```bash
# Check sync status
./scripts/check_production_health.sh

# View recent logs
gcloud run services logs read nytex-dashboard --region us-central1

# Check table counts
curl -s "https://nytex-dashboard-932676587025.us-central1.run.app/admin/table-counts"
```

---

## Data Dependencies

### Required for Sync Success
1. **Valid Square Access Token**: Must be production token with proper permissions
2. **Active Square Account**: Account must be in good standing
3. **Database Connectivity**: PostgreSQL connection must be stable
4. **Location Data**: At least one active location required for inventory sync

### Data Relationships
- **Categories** → **Items** (many items per category)
- **Items** → **Variations** (many variations per item)  
- **Variations** × **Locations** → **Inventory** (quantity per variation per location)

### Report Dependencies
All inventory reports depend on this sync data:
- Low Stock Reports
- Missing SKU Reports  
- Inventory by Location
- Category Analysis

---

## Security Considerations

### Access Control
- Sync endpoint requires proper authentication
- Square API tokens are stored as environment variables
- Database credentials are secured in Cloud Run environment

### Data Privacy
- No customer PII is synced (inventory/catalog only)
- Square business data is internal use only
- Logs may contain item names but no sensitive customer data

---

## Monitoring and Alerts

### Health Checks
- **Automated**: Every 4 hours via health-check-job
- **Manual**: `./scripts/check_production_health.sh`
- **Metrics**: Response time, success rate, data freshness

### Key Metrics to Monitor
1. **Sync Success Rate**: Should be 100% for daily runs
2. **Data Freshness**: Last sync timestamp
3. **Record Counts**: Verify expected data volumes
4. **Error Rates**: Monitor for authentication/network issues

### Alert Conditions
- Sync failures for 24+ hours
- Zero inventory records after sync
- Authentication errors
- Significant data count discrepancies

---

This documentation should be updated whenever the sync process changes to ensure operational teams have current information for troubleshooting and monitoring. 