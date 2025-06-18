-- Items Inventory Query - Uses Database View
-- This query uses the items_view database view for simplified and reliable data access
-- The view handles all the complex joins and calculations
-- Last updated: 2025-01-08

SELECT * FROM items_view 
ORDER BY item_name ASC; 