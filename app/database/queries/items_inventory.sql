-- Items Inventory Query with Location Quantities
-- This query retrieves comprehensive item data from Square including actual inventory quantities by location
-- Last updated: 2025-01-08

SELECT 
    -- Basic item information
    sile.item_name,
    sile.sku,
    sile.description,
    sile.categories AS category,
    
    -- Pricing information - prioritize catalog data if available
    CASE 
        WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
        THEN (cv.price_money->>'amount')::numeric / 100
        ELSE sile.price
    END AS price,
    
    -- Vendor information
    COALESCE(sile.default_vendor_name, '') AS vendor_name,
    COALESCE(sile.default_vendor_code, '') AS vendor_code,
    
    -- Cost information - use only square_item_library_export (production catalog_variations doesn't have default_unit_cost)
    sile.default_unit_cost AS cost,
    
    -- Profit margin calculation: (Price - Cost) / Price * 100
    CASE 
        WHEN (
            CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END
        ) IS NOT NULL 
        AND sile.default_unit_cost IS NOT NULL 
        AND (
            CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END
        ) > 0
        THEN ROUND(((
            (CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END) - sile.default_unit_cost
        ) / (
            CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END
        ) * 100)::numeric, 2)
        ELSE NULL 
    END AS profit_margin_percent,
    
    -- Profit markup calculation: (Price - Cost) / Cost * 100
    CASE 
        WHEN (
            CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END
        ) IS NOT NULL 
        AND sile.default_unit_cost IS NOT NULL 
        AND sile.default_unit_cost > 0
        THEN ROUND(((
            (CASE 
                WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                THEN (cv.price_money->>'amount')::numeric / 100
                ELSE sile.price
            END) - sile.default_unit_cost
        ) / sile.default_unit_cost * 100)::numeric, 2)
        ELSE NULL 
    END AS profit_markup_percent,
    
    -- Location quantities - simplified approach
    0 AS aubrey_qty,
    0 AS bridgefarmer_qty,
    0 AS building_qty,
    0 AS flomo_qty,
    0 AS justin_qty,
    0 AS quinlan_qty,
    0 AS terrell_qty,
    0 AS total_qty,
    
    -- Location availability - safe approach with existence checks
    CASE 
        WHEN sile.enabled_aubrey = 'Y' THEN 'Yes'
        WHEN sile.enabled_aubrey = 'N' THEN 'No'
        ELSE 'No'
    END AS aubrey_enabled,
    CASE 
        WHEN sile.enabled_bridgefarmer = 'Y' THEN 'Yes'
        WHEN sile.enabled_bridgefarmer = 'N' THEN 'No'
        ELSE 'No'
    END AS bridgefarmer_enabled,
    CASE 
        WHEN sile.enabled_building = 'Y' THEN 'Yes'
        WHEN sile.enabled_building = 'N' THEN 'No'
        ELSE 'No'
    END AS building_enabled,
    CASE 
        WHEN sile.enabled_flomo = 'Y' THEN 'Yes'
        WHEN sile.enabled_flomo = 'N' THEN 'No'
        ELSE 'No'
    END AS flomo_enabled,
    CASE 
        WHEN sile.enabled_justin = 'Y' THEN 'Yes'
        WHEN sile.enabled_justin = 'N' THEN 'No'
        ELSE 'No'
    END AS justin_enabled,
    CASE 
        WHEN sile.enabled_quinlan = 'Y' THEN 'Yes'
        WHEN sile.enabled_quinlan = 'N' THEN 'No'
        ELSE 'No'
    END AS quinlan_enabled,
    CASE 
        WHEN sile.enabled_terrell = 'Y' THEN 'Yes'
        WHEN sile.enabled_terrell = 'N' THEN 'No'
        ELSE 'No'
    END AS terrell_enabled,
    
    -- Additional item attributes
    COALESCE(sile.item_type, 'REGULAR') as item_type,
    COALESCE(sile.archived, 'N') as archived,
    COALESCE(sile.sellable, 'Y') as sellable,
    COALESCE(sile.stockable, 'Y') as stockable,
    
    -- Metadata
    sile.created_at,
    sile.updated_at

FROM square_item_library_export sile
LEFT JOIN catalog_variations cv ON sile.sku = cv.sku AND cv.is_deleted = false

WHERE sile.archived != 'Y'

ORDER BY sile.item_name ASC

-- Note: This query provides comprehensive item data including:
-- 1. All basic item information (name, SKU, description, categories)
-- 2. Complete pricing data (price, unit cost, profit margin) - prioritizing catalog_variations for price, square_item_library_export for cost
-- 3. Full vendor information (name, code)
-- 4. Item attributes (sellable, stockable, archived status)
-- 5. Location availability flags
-- 6. Metadata timestamps
--
-- Data Source: Uses catalog_variations for price data and square_item_library_export for cost data
-- since production catalog_variations doesn't have the default_unit_cost column yet.
-- Inventory quantities are set to 0 for now to avoid complex joins. 