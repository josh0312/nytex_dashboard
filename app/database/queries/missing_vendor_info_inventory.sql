-- Missing Vendor Info Inventory Report Query
-- Purpose: Identifies items with missing vendor information using Square catalog data
-- Checks: default_vendor_name, default_vendor_code from square_item_library_export and default_unit_cost from catalog_variations
-- Excludes: Archived items
-- Data Source: square_item_library_export table (Square catalog export) + catalog_variations (Square API sync)
-- Last Updated: 2025-01-27

WITH 
-- Get unit cost data from catalog_variations (Square API sync)
unit_cost_data AS (
    SELECT 
        cv.id as item_variation_id,
        cv.name as variation_name,
        ci.name as item_name,
        -- Extract unit cost amount from JSONB and convert to decimal
        CASE 
            WHEN cv.default_unit_cost IS NOT NULL 
                AND cv.default_unit_cost->>'amount' IS NOT NULL
            THEN (cv.default_unit_cost->>'amount')::numeric / 100.0  -- Convert cents to dollars
            ELSE NULL
        END as unit_cost_dollars
    FROM catalog_variations cv
    JOIN catalog_items ci ON cv.item_id = ci.id
    WHERE cv.is_deleted = false
    AND ci.is_deleted = false
),

-- Identify items with missing vendor information from catalog export
missing_vendor_info AS (
    SELECT 
        sile.item_name,
        sile.sku,
        sile.price,
        sile.default_vendor_name,
        sile.default_vendor_code,
        -- Get unit cost from catalog_variations instead of square_item_library_export
        ucd.unit_cost_dollars as default_unit_cost,
        -- Determine the type of missing vendor information
        CASE 
            WHEN (sile.default_vendor_name IS NULL OR sile.default_vendor_name = '') 
                AND (sile.default_vendor_code IS NULL OR sile.default_vendor_code = '')
                AND (ucd.unit_cost_dollars IS NULL OR ucd.unit_cost_dollars = 0)
                THEN 'Missing All Vendor Info'
            WHEN (sile.default_vendor_name IS NULL OR sile.default_vendor_name = '') 
                AND (sile.default_vendor_code IS NULL OR sile.default_vendor_code = '')
                THEN 'No Vendor & No Code'
            WHEN (sile.default_vendor_name IS NULL OR sile.default_vendor_name = '') 
                AND (ucd.unit_cost_dollars IS NULL OR ucd.unit_cost_dollars = 0)
                THEN 'No Vendor & No Cost'
            WHEN (sile.default_vendor_code IS NULL OR sile.default_vendor_code = '')
                AND (ucd.unit_cost_dollars IS NULL OR ucd.unit_cost_dollars = 0)
                THEN 'No Code & No Cost'
            WHEN (sile.default_vendor_name IS NULL OR sile.default_vendor_name = '') 
                THEN 'No Vendor Name'
            WHEN (sile.default_vendor_code IS NULL OR sile.default_vendor_code = '')
                THEN 'No Vendor Code'
            WHEN (ucd.unit_cost_dollars IS NULL OR ucd.unit_cost_dollars = 0)
                THEN 'No Unit Cost'
            ELSE 'Has Vendor Info'
        END AS vendor_status,
        -- Calculate quantity based on location data if available
        CASE 
            WHEN sile.location_data IS NOT NULL AND jsonb_typeof(sile.location_data) = 'object'
            THEN (
                SELECT COALESCE(SUM((value->>'quantity')::numeric), 0)
                FROM jsonb_each(sile.location_data)
                WHERE value->>'quantity' IS NOT NULL 
                AND (value->>'quantity')::numeric > 0
            )
            ELSE 0
        END AS total_quantity
    FROM square_item_library_export sile
    LEFT JOIN unit_cost_data ucd ON sile.item_name = ucd.item_name
    WHERE sile.archived != 'Y'  -- Exclude archived items
    AND (
        -- Items with missing vendor name
        (sile.default_vendor_name IS NULL OR sile.default_vendor_name = '')
        OR 
        -- Items with missing vendor code
        (sile.default_vendor_code IS NULL OR sile.default_vendor_code = '')
        OR
        -- Items with missing unit cost (now from catalog_variations)
        (ucd.unit_cost_dollars IS NULL OR ucd.unit_cost_dollars = 0)
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
    -- Show unit cost for reference (now from catalog_variations)
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
-- 3. Items with missing unit cost (default_unit_cost from catalog_variations via Square API)
-- 4. Only non-archived items
-- 5. Uses Square catalog export data for vendor info + catalog_variations for unit cost
-- 6. Vendor status indicates specific type of missing vendor information
-- 7. Quantity calculated from location_data JSON field when available
-- 8. Unit cost now sourced from Square API sync data in catalog_variations table
-- 
-- Data Sources: 
-- - square_item_library_export: vendor name/code from Square export
-- - catalog_variations: unit cost from Square API (default_unit_cost JSONB field)
-- This combines the best of both data sources for comprehensive vendor analysis. 