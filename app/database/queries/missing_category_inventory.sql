-- Missing Category Inventory Report Query
-- Purpose: Identifies items with missing categories and shows their inventory levels
-- Includes: Items with NULL/empty category_id AND items with orphaned category references
-- Excludes: Archived items, deleted items, and zero inventory items
-- Aggregates: Inventory across all locations (no location breakdown)
-- Last Updated: 2025-01-27

WITH 
-- Identify items with missing or orphaned categories
missing_categories AS (
    SELECT 
        catalog_items.name AS item_name,
        catalog_items.id AS item_id,
        catalog_variations.id AS variation_id,
        catalog_variations.price_money->>'amount' AS price_amount,
        catalog_variations.price_money->>'currency' AS currency,
        catalog_items.category_id,
        -- Get vendor information with vendor name
        vendors.name AS vendor_name,
        -- Determine the type of missing category
        CASE 
            WHEN catalog_items.category_id IS NULL OR catalog_items.category_id = '' 
                THEN 'No Category Assigned'
            WHEN catalog_categories.id IS NULL 
                THEN 'Orphaned Category Reference'
            ELSE 'Has Category'
        END AS category_status
    FROM catalog_items
    LEFT JOIN catalog_variations 
        ON catalog_items.id = catalog_variations.item_id
    LEFT JOIN catalog_categories 
        ON catalog_items.category_id = catalog_categories.id
    LEFT JOIN catalog_vendor_info 
        ON catalog_variations.id = catalog_vendor_info.variation_id
        AND catalog_vendor_info.is_deleted = false
    LEFT JOIN vendors 
        ON catalog_vendor_info.vendor_id = vendors.id
    WHERE (
        -- Items with no category assigned
        (catalog_items.category_id IS NULL OR catalog_items.category_id = '')
        OR 
        -- Items with orphaned category references (category_id exists but category record doesn't)
        (catalog_items.category_id IS NOT NULL 
         AND catalog_items.category_id != '' 
         AND catalog_categories.id IS NULL)
    )
    AND catalog_variations.is_deleted = false
    AND catalog_items.is_deleted = false
    AND (catalog_items.is_archived = false OR catalog_items.is_archived IS NULL)
),

-- Aggregate inventory across all locations for each variation
aggregated_inventory AS (
    SELECT 
        variation_id,
        SUM(COALESCE(quantity, 0)) as total_quantity
    FROM catalog_inventory
    GROUP BY variation_id
)

-- Main query to get items missing categories with aggregated inventory
SELECT DISTINCT ON (item_name)
    item_name,
    -- Display vendor name or 'No Vendor' if not available
    COALESCE(vendor_name, 'No Vendor') AS vendor_name,
    -- Format price to currency with 2 decimal places
    CASE 
        WHEN price_amount IS NOT NULL 
        THEN TO_CHAR(ROUND(price_amount::numeric/100, 2), '$999,999.99') 
        ELSE 'No Price' 
    END AS price,
    COALESCE(aggregated_inventory.total_quantity, 0) as quantity,
    category_status
FROM missing_categories
LEFT JOIN aggregated_inventory 
    ON missing_categories.variation_id = aggregated_inventory.variation_id
WHERE COALESCE(aggregated_inventory.total_quantity, 0) != 0  -- Exclude zero inventory
ORDER BY item_name, aggregated_inventory.total_quantity DESC;  -- Get highest quantity variant per item

-- Note: This query shows:
-- 1. Items with missing categories (null or empty category_id)
-- 2. Items with orphaned category references (category_id exists but category record is missing)
-- 3. Only non-zero inventory levels (aggregated across all locations)
-- 4. Only active (non-archived, non-deleted) items
-- 5. One entry per item name (highest quantity variant)
-- 6. Vendor information when available (vendor name from vendors table)
-- 7. No location breakdown - inventory is summed across all locations
-- 8. Category status to distinguish between different types of missing categories 