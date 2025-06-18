-- Items inventory query using optimized database view
-- This query uses the items_view which consolidates all profit calculations
-- View created via Alembic migration: create_items_view.py
-- Last updated: 2025-01-08

SELECT * FROM items_view 
ORDER BY item_name ASC; 