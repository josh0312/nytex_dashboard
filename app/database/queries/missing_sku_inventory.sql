-- Missing SKU Inventory Report Query
-- Purpose: Identifies items with Square-generated or missing SKUs and shows their inventory levels by location
-- Excludes: Archived items, deleted items, and zero inventory items
-- Groups by: Location, then item name
-- Last Updated: 2024-01-02

WITH RECURSIVE 
-- Get location names for mapping location IDs
location_names AS (
    SELECT id, name 
    FROM locations
),

-- Identify items with problematic SKUs (missing or Square-generated)
missing_skus AS (
    SELECT 
        catalog_items.name AS item_name,
        catalog_variations.sku AS sku,
        catalog_variations.price_money->>'amount' AS price_amount,
        catalog_variations.price_money->>'currency' AS currency,
        catalog_items.category_id AS category_id,
        catalog_categories.name AS category_name,
        catalog_variations.present_at_location_ids AS location_ids,
        catalog_variations.id AS variation_id,
        CASE 
            WHEN catalog_variations.sku IS NULL OR catalog_variations.sku = '' 
                THEN 'Missing SKU'
            WHEN LENGTH(catalog_variations.sku) = 7 AND catalog_variations.sku ~ '[A-Za-z]' 
                THEN 'Square Generated'
        END AS sku_status
    FROM catalog_variations
    LEFT JOIN catalog_items 
        ON catalog_variations.item_id = catalog_items.id
    LEFT JOIN catalog_categories 
        ON catalog_items.category_id = catalog_categories.id
    WHERE (
        catalog_variations.sku IS NULL 
        OR catalog_variations.sku = '' 
        OR (LENGTH(catalog_variations.sku) = 7 AND catalog_variations.sku ~ '[A-Za-z]')
    )
    AND catalog_variations.is_deleted = false
    AND catalog_items.is_deleted = false
    AND catalog_items.is_archived = false
)

-- Main query to get inventory levels by location
SELECT 
    location_names.name AS location,
    item_name,
    sku,
    -- Format price to currency with 2 decimal places
    CASE 
        WHEN price_amount IS NOT NULL 
        THEN TO_CHAR(ROUND(price_amount::numeric/100, 2), '$999,999.99') 
        ELSE 'No Price' 
    END AS price,
    category_name,
    COALESCE(catalog_inventory.quantity, 0) as quantity,
    -- Categorize inventory status
    CASE 
        WHEN catalog_inventory.quantity > 0 THEN 'In Stock'
        WHEN catalog_inventory.quantity < 0 THEN 'Negative Stock'
        ELSE 'No Stock' 
    END AS stock_status
FROM missing_skus
CROSS JOIN location_names
LEFT JOIN catalog_inventory 
    ON catalog_inventory.variation_id = missing_skus.variation_id 
    AND catalog_inventory.location_id = location_names.id
WHERE COALESCE(catalog_inventory.quantity, 0) != 0  -- Exclude zero inventory
ORDER BY location_names.name, item_name;

-- Note: This query shows:
-- 1. Items with Square-generated SKUs (7 characters with letters)
-- 2. Items with missing SKUs (null or empty)
-- 3. Only non-zero inventory levels
-- 4. Only active (non-archived, non-deleted) items
-- 5. Inventory grouped by location and sorted by item name 