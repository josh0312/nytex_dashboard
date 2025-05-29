-- Simple Low Stock Inventory Query using square_item_library_export
-- This query works with the available catalog export data
-- Last updated: 2025-05-29

SELECT 
    item_name,
    variation_name,
    sku,
    categories AS category,
    default_vendor_name AS vendor_name,
    price,
    default_unit_cost AS cost,
    
    -- Placeholder values since we don't have inventory data
    0 AS units_per_case,
    0 AS low_stock_threshold,
    0 AS case_percentage,
    
    -- Total inventory data (all zeros since no inventory)
    0 AS total_qty,
    false AS is_low_stock_total,
    
    -- Location-specific data (all zeros)
    0 AS aubrey_qty,
    false AS aubrey_low_stock,
    0 AS bridgefarmer_qty,
    false AS bridgefarmer_low_stock,
    0 AS building_qty,
    false AS building_low_stock,
    0 AS flomo_qty,
    false AS flomo_low_stock,
    0 AS justin_qty,
    false AS justin_low_stock,
    0 AS quinlan_qty,
    false AS quinlan_low_stock,
    0 AS terrell_qty,
    false AS terrell_low_stock,
    
    -- Summary fields
    false AS has_location_low_stock,
    0 AS locations_with_low_stock

FROM square_item_library_export
WHERE item_name IS NOT NULL
AND item_name != ''
ORDER BY item_name ASC
LIMIT 100

-- Note: This is a simplified query that shows catalog data
-- but no actual inventory since the inventory tables are empty.
-- To get real inventory data, we need to:
-- 1. Fix the inventory sync to populate catalog_inventory table, or
-- 2. Enhance this query to join with actual inventory data 