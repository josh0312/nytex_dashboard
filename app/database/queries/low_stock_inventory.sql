-- Low Stock Inventory Query with Units Per Case Analysis
-- This query identifies items with low inventory levels based on Units Per Case custom field
-- Low stock is defined as quantity < 15% of units per case
-- Last updated: 2025-05-28

WITH inventory_summary AS (
    SELECT 
        cv.id AS variation_id,
        cv.item_id,
        cv.sku,
        cv.name AS variation_name,
        cv.units_per_case AS variation_units_per_case,
        ci.name AS item_name,
        ci.units_per_case AS item_units_per_case,
        -- Get pricing from price_money JSON field
        CASE 
            WHEN cv.price_money->>'amount' IS NOT NULL 
            THEN (cv.price_money->>'amount')::numeric / 100 
            ELSE NULL 
        END AS price,
        -- Get vendor information from vendor table through catalog_vendor_info
        v.name AS vendor_name,
        -- Use variation Units Per Case if available, otherwise item Units Per Case
        COALESCE(cv.units_per_case, ci.units_per_case) AS units_per_case,
        
        -- Calculate quantities by location
        COALESCE(SUM(CASE WHEN l.name = 'Aubrey' THEN inv.quantity ELSE 0 END), 0) AS aubrey_qty,
        COALESCE(SUM(CASE WHEN l.name = 'Bridgefarmer' THEN inv.quantity ELSE 0 END), 0) AS bridgefarmer_qty,
        COALESCE(SUM(CASE WHEN l.name = 'Building' THEN inv.quantity ELSE 0 END), 0) AS building_qty,
        COALESCE(SUM(CASE WHEN l.name = 'FloMo' THEN inv.quantity ELSE 0 END), 0) AS flomo_qty,
        COALESCE(SUM(CASE WHEN l.name = 'Justin' THEN inv.quantity ELSE 0 END), 0) AS justin_qty,
        COALESCE(SUM(CASE WHEN l.name = 'Quinlan' THEN inv.quantity ELSE 0 END), 0) AS quinlan_qty,
        COALESCE(SUM(CASE WHEN l.name = 'Terrell' THEN inv.quantity ELSE 0 END), 0) AS terrell_qty,
        
        -- Total quantity across all locations
        COALESCE(SUM(inv.quantity), 0) AS total_qty
        
    FROM catalog_variations cv
    LEFT JOIN catalog_items ci ON cv.item_id = ci.id
    LEFT JOIN catalog_inventory inv ON cv.id = inv.variation_id
    LEFT JOIN locations l ON inv.location_id = l.id AND l.status = 'ACTIVE'
    LEFT JOIN catalog_vendor_info cvi ON cv.id = cvi.variation_id AND cvi.is_deleted = false
    LEFT JOIN vendors v ON cvi.vendor_id = v.id
    
    WHERE cv.is_deleted = false 
    AND ci.is_deleted = false
    AND (cv.units_per_case IS NOT NULL OR ci.units_per_case IS NOT NULL)
    
    GROUP BY 
        cv.id, cv.item_id, cv.sku, cv.name, cv.units_per_case,
        ci.name, ci.units_per_case, v.name
),

low_stock_analysis AS (
    SELECT 
        *,
        -- Calculate 15% threshold for low stock
        ROUND(units_per_case * 0.15) AS low_stock_threshold,
        
        -- Determine if total inventory is low stock
        CASE 
            WHEN total_qty < ROUND(units_per_case * 0.15) THEN true
            ELSE false
        END AS is_low_stock_total,
        
        -- Calculate percentage of case in stock
        CASE 
            WHEN units_per_case > 0 THEN ROUND((total_qty::numeric / units_per_case * 100), 1)
            ELSE 0
        END AS case_percentage,
        
        -- Check which locations have low stock
        CASE WHEN aubrey_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS aubrey_low_stock,
        CASE WHEN bridgefarmer_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS bridgefarmer_low_stock,
        CASE WHEN building_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS building_low_stock,
        CASE WHEN flomo_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS flomo_low_stock,
        CASE WHEN justin_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS justin_low_stock,
        CASE WHEN quinlan_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS quinlan_low_stock,
        CASE WHEN terrell_qty < ROUND(units_per_case * 0.15) THEN true ELSE false END AS terrell_low_stock
        
    FROM inventory_summary
)

SELECT 
    item_name,
    variation_name,
    sku,
    -- Add category placeholder (not available in current schema)
    'N/A' AS category,
    vendor_name,
    price,
    -- Add cost placeholder (not available in current schema)
    NULL AS cost,
    units_per_case,
    low_stock_threshold,
    case_percentage,
    
    -- Total inventory data
    total_qty,
    is_low_stock_total,
    
    -- Location-specific data
    aubrey_qty,
    aubrey_low_stock,
    bridgefarmer_qty,
    bridgefarmer_low_stock,
    building_qty,
    building_low_stock,
    flomo_qty,
    flomo_low_stock,
    justin_qty,
    justin_low_stock,
    quinlan_qty,
    quinlan_low_stock,
    terrell_qty,
    terrell_low_stock,
    
    -- Summary fields for filtering
    CASE 
        WHEN aubrey_low_stock OR bridgefarmer_low_stock OR building_low_stock OR 
             flomo_low_stock OR justin_low_stock OR quinlan_low_stock OR terrell_low_stock
        THEN true 
        ELSE false 
    END AS has_location_low_stock,
    
    -- Count of locations with low stock
    (aubrey_low_stock::int + bridgefarmer_low_stock::int + building_low_stock::int + 
     flomo_low_stock::int + justin_low_stock::int + quinlan_low_stock::int + terrell_low_stock::int) AS locations_with_low_stock

FROM low_stock_analysis

-- Order by most critical items first (lowest case percentage)
ORDER BY case_percentage ASC, item_name ASC

-- Note: This query provides comprehensive low stock analysis including:
-- 1. Items with Units Per Case data (from either item or variation level)
-- 2. 15% threshold calculation for low stock determination
-- 3. Total inventory low stock status across all locations
-- 4. Individual location low stock status
-- 5. Case percentage to show how much of a case is in stock
-- 6. Vendor and pricing information for reordering
-- 7. Support for both NyTex Inventory (total) and Location Inventory views
--
-- Low Stock Logic:
-- - Uses Units Per Case custom field from Square
-- - Calculates 15% of units per case as threshold
-- - Items below threshold are flagged as low stock
-- - Supports filtering by total inventory or individual locations 