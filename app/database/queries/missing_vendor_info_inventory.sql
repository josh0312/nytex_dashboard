-- Missing Vendor Info Inventory Report Query (Updated to use items_view)
-- Purpose: Identifies items with missing vendor information using standardized items_view
-- Checks: vendor_name, vendor_code, and unit_cost from items_view
-- Excludes: No need to exclude archived items (items_view already filters them)
-- Data Source: items_view (standardized view that combines Square catalog export + API data)
-- Last Updated: 2025-06-20

-- Main query to get items missing vendor info from standardized items_view
SELECT DISTINCT
    item_name,
    -- Format price to currency with 2 decimal places
    CASE 
        WHEN price IS NOT NULL 
        THEN TO_CHAR(price, '$999,999.99') 
        ELSE 'No Price' 
    END AS price,
    COALESCE(total_qty, 0) as quantity,
    -- Display vendor name or appropriate status
    CASE 
        WHEN vendor_name IS NOT NULL AND vendor_name != '' 
        THEN vendor_name
        ELSE 'No Vendor'
    END AS vendor_name,
    -- Display vendor code or status  
    CASE 
        WHEN vendor_code IS NOT NULL AND vendor_code != '' 
        THEN vendor_code
        ELSE 'No Code'
    END AS vendor_sku,
    -- Determine the type of missing vendor information
    CASE 
        WHEN (vendor_name IS NULL OR vendor_name = '') 
            AND (vendor_code IS NULL OR vendor_code = '')
            AND (cost IS NULL OR cost = 0)
            THEN 'Missing All Vendor Info'
        WHEN (vendor_name IS NULL OR vendor_name = '') 
            AND (vendor_code IS NULL OR vendor_code = '')
            THEN 'No Vendor & No Code'
        WHEN (vendor_name IS NULL OR vendor_name = '') 
            AND (cost IS NULL OR cost = 0)
            THEN 'No Vendor & No Cost'
        WHEN (vendor_code IS NULL OR vendor_code = '')
            AND (cost IS NULL OR cost = 0)
            THEN 'No Code & No Cost'
        WHEN (vendor_name IS NULL OR vendor_name = '') 
            THEN 'No Vendor Name'
        WHEN (vendor_code IS NULL OR vendor_code = '')
            THEN 'No Vendor Code'
        WHEN (cost IS NULL OR cost = 0)
            THEN 'No Unit Cost'
        ELSE 'Has Vendor Info'
    END AS vendor_status,
    -- Show unit cost for reference
    CASE 
        WHEN cost IS NOT NULL AND cost > 0
        THEN TO_CHAR(cost, '$999,999.99') 
        ELSE 'No Cost' 
    END AS unit_cost
FROM items_view
WHERE (
    -- Items with missing vendor name
    (vendor_name IS NULL OR vendor_name = '')
    OR 
    -- Items with missing vendor code
    (vendor_code IS NULL OR vendor_code = '')
    OR
    -- Items with missing unit cost
    (cost IS NULL OR cost = 0)
)
ORDER BY item_name;

-- Note: This query shows:
-- 1. Items with missing vendor name (vendor_name is NULL or empty)
-- 2. Items with missing vendor code (vendor_code is NULL or empty)  
-- 3. Items with missing unit cost (unit_cost is NULL or zero)
-- 4. Uses standardized items_view which automatically excludes archived items
-- 5. items_view combines the best of Square catalog export + API sync data
-- 6. Vendor status indicates specific type of missing vendor information
-- 7. Quantity comes from total_qty field in items_view
-- 8. Unit cost sourced from items_view (combines export + API data)
-- 
-- Benefits of using items_view:
-- - Consistent with other reports  
-- - Automatically excludes archived items
-- - Combines best data from multiple sources
-- - Standardized field names and data types
-- - No need for complex CTEs and joins 