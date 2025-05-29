-- Missing Description Inventory Report Query
-- Purpose: Identifies items with missing descriptions and shows their inventory levels
-- Checks: description, description_html, and description_plaintext fields on catalog_items
-- Excludes: Archived items, deleted items, and zero inventory items
-- Aggregates: Inventory across all locations (no location breakdown)
-- Last Updated: 2025-01-27

WITH 
-- Identify items with missing descriptions
missing_descriptions AS (
    SELECT 
        catalog_items.name AS item_name,
        catalog_items.id AS item_id,
        catalog_variations.id AS variation_id,
        catalog_variations.price_money->>'amount' AS price_amount,
        catalog_variations.price_money->>'currency' AS currency,
        catalog_items.description,
        catalog_items.description_html,
        catalog_items.description_plaintext,
        -- Get vendor information with vendor name
        vendors.name AS vendor_name,
        -- Get category information with category name
        catalog_categories.name AS category_name,
        -- Determine the type of missing description
        CASE 
            WHEN (catalog_items.description IS NULL OR catalog_items.description = '') 
                 AND (catalog_items.description_html IS NULL OR catalog_items.description_html = '')
                 AND (catalog_items.description_plaintext IS NULL OR catalog_items.description_plaintext = '')
                THEN 'No Description'
            WHEN (catalog_items.description IS NULL OR catalog_items.description = '') 
                 AND (catalog_items.description_plaintext IS NULL OR catalog_items.description_plaintext = '')
                 AND catalog_items.description_html IS NOT NULL AND catalog_items.description_html != ''
                THEN 'HTML Only'
            WHEN (catalog_items.description IS NULL OR catalog_items.description = '') 
                 AND (catalog_items.description_html IS NULL OR catalog_items.description_html = '')
                 AND catalog_items.description_plaintext IS NOT NULL AND catalog_items.description_plaintext != ''
                THEN 'Plain Text Only'
            ELSE 'Has Description'
        END AS description_status
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
        (
            -- Items with no description at all
            (catalog_items.description IS NULL OR catalog_items.description = '') 
            AND (catalog_items.description_html IS NULL OR catalog_items.description_html = '')
            AND (catalog_items.description_plaintext IS NULL OR catalog_items.description_plaintext = '')
        ) OR (
            -- Items with only partial descriptions (missing main description field)
            (catalog_items.description IS NULL OR catalog_items.description = '')
            AND (
                (catalog_items.description_html IS NOT NULL AND catalog_items.description_html != '')
                OR (catalog_items.description_plaintext IS NOT NULL AND catalog_items.description_plaintext != '')
            )
        )
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

-- Main query to get items missing descriptions with aggregated inventory
SELECT DISTINCT ON (item_name)
    item_name,
    -- Display vendor name or 'No Vendor' if not available
    COALESCE(vendor_name, 'No Vendor') AS vendor_name,
    -- Display category name or 'No Category' if not available
    COALESCE(category_name, 'No Category') AS category_name,
    -- Format price to currency with 2 decimal places
    CASE 
        WHEN price_amount IS NOT NULL 
        THEN TO_CHAR(ROUND(price_amount::numeric/100, 2), '$999,999.99') 
        ELSE 'No Price' 
    END AS price,
    COALESCE(aggregated_inventory.total_quantity, 0) as quantity,
    description_status,
    -- Show what description fields exist (for debugging/analysis)
    CASE 
        WHEN description IS NOT NULL AND description != '' THEN 'Yes' 
        ELSE 'No' 
    END AS has_description,
    CASE 
        WHEN description_html IS NOT NULL AND description_html != '' THEN 'Yes' 
        ELSE 'No' 
    END AS has_html_description,
    CASE 
        WHEN description_plaintext IS NOT NULL AND description_plaintext != '' THEN 'Yes' 
        ELSE 'No' 
    END AS has_plaintext_description
FROM missing_descriptions
LEFT JOIN aggregated_inventory 
    ON missing_descriptions.variation_id = aggregated_inventory.variation_id
WHERE COALESCE(aggregated_inventory.total_quantity, 0) != 0  -- Exclude zero inventory
ORDER BY item_name, aggregated_inventory.total_quantity DESC;  -- Get highest quantity variant per item

-- Note: This query shows:
-- 1. Items with missing descriptions (all description fields are null or empty)
-- 2. Items with partial descriptions (missing main description field but have HTML or plaintext)
-- 3. Only non-zero inventory levels (aggregated across all locations)
-- 4. Only active (non-archived, non-deleted) items
-- 5. One entry per item name (highest quantity variant)
-- 6. Vendor information when available (vendor name from vendors table)
-- 7. Category information when available (category name from catalog_categories table)
-- 8. No location breakdown - inventory is summed across all locations
-- 9. Description status and field availability for analysis 