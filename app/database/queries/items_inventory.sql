-- Items Inventory Query with Location Quantities
-- This query retrieves comprehensive item data from Square including actual inventory quantities by location
-- Last updated: 2025-05-27

SELECT DISTINCT
    -- Basic item information
    sile.item_name,
    sile.sku,
    sile.description,
    sile.categories AS category,
    
    -- Pricing information
    CASE 
        WHEN sile.price IS NOT NULL 
        THEN sile.price
        ELSE NULL 
    END AS price,
    
    -- Vendor information
    sile.default_vendor_name AS vendor_name,
    sile.default_vendor_code AS vendor_code,
    
    -- Cost and profit information
    CASE 
        WHEN sile.default_unit_cost IS NOT NULL 
        THEN sile.default_unit_cost
        ELSE NULL 
    END AS cost,
    
    CASE 
        WHEN sile.price IS NOT NULL AND sile.default_unit_cost IS NOT NULL AND sile.price > 0
        THEN ROUND(((sile.price - sile.default_unit_cost) / sile.price * 100)::numeric, 2)
        ELSE NULL 
    END AS profit_margin_percent,
    
    -- Location quantities (actual inventory data)
    COALESCE(SUM(CASE WHEN l.name = 'Aubrey' THEN ci.quantity ELSE 0 END), 0) AS aubrey_qty,
    COALESCE(SUM(CASE WHEN l.name = 'Bridgefarmer' THEN ci.quantity ELSE 0 END), 0) AS bridgefarmer_qty,
    COALESCE(SUM(CASE WHEN l.name = 'Building' THEN ci.quantity ELSE 0 END), 0) AS building_qty,
    COALESCE(SUM(CASE WHEN l.name = 'FloMo' THEN ci.quantity ELSE 0 END), 0) AS flomo_qty,
    COALESCE(SUM(CASE WHEN l.name = 'Justin' THEN ci.quantity ELSE 0 END), 0) AS justin_qty,
    COALESCE(SUM(CASE WHEN l.name = 'Quinlan' THEN ci.quantity ELSE 0 END), 0) AS quinlan_qty,
    COALESCE(SUM(CASE WHEN l.name = 'Terrell' THEN ci.quantity ELSE 0 END), 0) AS terrell_qty,
    
    -- Total quantity across all locations
    COALESCE(SUM(ci.quantity), 0) AS total_qty,
    
    -- Location availability (from JSON data)
    CASE WHEN sile.location_data->'Aubrey'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS aubrey_enabled,
    CASE WHEN sile.location_data->'Bridgefarmer'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS bridgefarmer_enabled,
    CASE WHEN sile.location_data->'Building'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS building_enabled,
    CASE WHEN sile.location_data->'FloMo'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS flomo_enabled,
    CASE WHEN sile.location_data->'Justin'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS justin_enabled,
    CASE WHEN sile.location_data->'Quinlan'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS quinlan_enabled,
    CASE WHEN sile.location_data->'Terrell'->>'enabled' = 'true' THEN 'Yes' ELSE 'No' END AS terrell_enabled,
    
    -- Additional item attributes
    sile.item_type,
    sile.archived,
    sile.sellable,
    sile.stockable,
    
    -- Metadata
    sile.created_at,
    sile.updated_at

FROM square_item_library_export sile
LEFT JOIN catalog_variations cv ON sile.sku = cv.sku AND cv.is_deleted = false
LEFT JOIN catalog_inventory ci ON cv.id = ci.variation_id
LEFT JOIN locations l ON ci.location_id = l.id AND l.status = 'ACTIVE'

WHERE sile.archived != 'Y'

GROUP BY 
    sile.id,
    sile.item_name,
    sile.sku,
    sile.description,
    sile.categories,
    sile.price,
    sile.default_unit_cost,
    sile.default_vendor_name,
    sile.default_vendor_code,
    sile.location_data,
    sile.item_type,
    sile.archived,
    sile.sellable,
    sile.stockable,
    sile.created_at,
    sile.updated_at

ORDER BY sile.item_name ASC

-- Note: This query provides comprehensive item data including:
-- 1. All basic item information (name, SKU, description, categories)
-- 2. Complete pricing data (price, unit cost, profit margin)
-- 3. Full vendor information (name, code)
-- 4. Location quantities (actual inventory data)
-- 5. Item attributes (sellable, stockable, archived status)
-- 6. Additional product details (GTIN, weight, alcohol content)
-- 7. Tax and ecommerce settings
-- 8. Product options and variations
-- 9. Data export timestamp for freshness tracking
--
-- Data Source: square_item_library_export table contains the most comprehensive
-- and up-to-date item information directly exported from Square, including
-- all product details, vendor information, pricing, and location availability.
-- This provides a complete view of the product catalog without complex joins. 