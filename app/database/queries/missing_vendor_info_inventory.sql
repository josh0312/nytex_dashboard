-- Missing Vendor Info Inventory Report Query
-- Purpose: Identifies items with missing vendor information using Square catalog export data
-- Checks: default_vendor_name, default_vendor_code, and default_unit_cost from square_item_library_export table
-- Excludes: Archived items
-- Data Source: square_item_library_export table (Square catalog export)
-- Last Updated: 2025-01-27

WITH 
-- Identify items with missing vendor information from catalog export
missing_vendor_info AS (
    SELECT 
        item_name,
        sku,
        price,
        default_unit_cost,
        default_vendor_name,
        default_vendor_code,
        -- Determine the type of missing vendor information
        CASE 
            WHEN (default_vendor_name IS NULL OR default_vendor_name = '') 
                AND (default_vendor_code IS NULL OR default_vendor_code = '')
                AND (default_unit_cost IS NULL OR default_unit_cost = 0)
                THEN 'Missing All Vendor Info'
            WHEN (default_vendor_name IS NULL OR default_vendor_name = '') 
                AND (default_vendor_code IS NULL OR default_vendor_code = '')
                THEN 'No Vendor & No Code'
            WHEN (default_vendor_name IS NULL OR default_vendor_name = '') 
                AND (default_unit_cost IS NULL OR default_unit_cost = 0)
                THEN 'No Vendor & No Cost'
            WHEN (default_vendor_code IS NULL OR default_vendor_code = '')
                AND (default_unit_cost IS NULL OR default_unit_cost = 0)
                THEN 'No Code & No Cost'
            WHEN (default_vendor_name IS NULL OR default_vendor_name = '') 
                THEN 'No Vendor Name'
            WHEN (default_vendor_code IS NULL OR default_vendor_code = '')
                THEN 'No Vendor Code'
            WHEN (default_unit_cost IS NULL OR default_unit_cost = 0)
                THEN 'No Unit Cost'
            ELSE 'Has Vendor Info'
        END AS vendor_status,
        -- Calculate quantity based on location data if available
        CASE 
            WHEN location_data IS NOT NULL AND jsonb_typeof(location_data) = 'object'
            THEN (
                SELECT COALESCE(SUM((value->>'quantity')::numeric), 0)
                FROM jsonb_each(location_data)
                WHERE value->>'quantity' IS NOT NULL 
                AND (value->>'quantity')::numeric > 0
            )
            ELSE 0
        END AS total_quantity
    FROM square_item_library_export
    WHERE archived != 'Y'  -- Exclude archived items
    AND (
        -- Items with missing vendor name
        (default_vendor_name IS NULL OR default_vendor_name = '')
        OR 
        -- Items with missing vendor code
        (default_vendor_code IS NULL OR default_vendor_code = '')
        OR
        -- Items with missing unit cost
        (default_unit_cost IS NULL OR default_unit_cost = 0)
    )
),

-- Filter to items with inventory or other relevant criteria
filtered_missing_vendor_info AS (
    SELECT *
    FROM missing_vendor_info
    -- Include all items missing any vendor information
)

-- Main query to get items missing vendor info
SELECT DISTINCT
    item_name,
    -- Format price to currency with 2 decimal places
    CASE 
        WHEN price IS NOT NULL 
        THEN TO_CHAR(price, '$999,999.99') 
        ELSE 'No Price' 
    END AS price,
    COALESCE(total_quantity, 0) as quantity,
    -- Display vendor name or appropriate status
    CASE 
        WHEN default_vendor_name IS NOT NULL AND default_vendor_name != '' 
        THEN default_vendor_name
        ELSE 'No Vendor'
    END AS vendor_name,
    -- Display vendor code or status
    CASE 
        WHEN default_vendor_code IS NOT NULL AND default_vendor_code != '' 
        THEN default_vendor_code
        ELSE 'No Code'
    END AS vendor_sku,
    vendor_status,
    -- Show unit cost for reference
    CASE 
        WHEN default_unit_cost IS NOT NULL 
        THEN TO_CHAR(default_unit_cost, '$999,999.99') 
        ELSE 'No Cost' 
    END AS unit_cost
FROM filtered_missing_vendor_info
ORDER BY item_name;

-- Note: This query shows:
-- 1. Items with missing vendor name (default_vendor_name is NULL or empty)
-- 2. Items with missing vendor code (default_vendor_code is NULL or empty)
-- 3. Items with missing unit cost (default_unit_cost is NULL or 0)
-- 4. Only non-archived items
-- 5. Uses Square catalog export data which includes comprehensive vendor information
-- 6. Vendor status indicates specific type of missing vendor information
-- 7. Quantity calculated from location_data JSON field when available
-- 8. Comprehensive vendor data analysis for inventory management
-- 
-- Data Source: square_item_library_export table contains complete vendor information
-- exported directly from Square, including vendor name, code, and cost which are
-- critical for vendor management and inventory valuation. 