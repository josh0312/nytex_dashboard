"""Add units_per_case to items_view

Revision ID: 20250623_182639
Revises: create_items_view_001
Create Date: 2025-01-23 18:26:39.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250623_182639'
down_revision = 'fix_permissions_001'
branch_labels = None
depends_on = None


def upgrade():
    """Add units_per_case to items_view"""
    
    # First, drop the existing view  
    op.execute("DROP VIEW IF EXISTS items_view")
    
    # Grant permissions to nytex_app after view creation
    def create_view_and_grant_permissions():
        op.execute("""
        CREATE VIEW items_view AS
        SELECT 
            -- Basic item information
            sile.item_name,
            sile.sku,
            sile.description,
            sile.categories AS category,
            
            -- Pricing information
            sile.price,
            
            -- Vendor information
            COALESCE(sile.default_vendor_name, '') AS vendor_name,
            COALESCE(sile.default_vendor_code, '') AS vendor_code,
            
            -- Cost information (simplified for now)
            sile.default_unit_cost AS cost,
            
            -- Profit margin calculation: (Price - Cost) / Price * 100
            CASE 
                WHEN sile.price IS NOT NULL 
                AND sile.default_unit_cost IS NOT NULL 
                AND sile.price > 0
                THEN ROUND(((sile.price - sile.default_unit_cost) / sile.price * 100)::numeric, 2)
                ELSE NULL 
            END AS profit_margin_percent,
            
            -- Profit markup calculation: (Price - Cost) / Cost * 100
            CASE 
                WHEN sile.price IS NOT NULL 
                AND sile.default_unit_cost IS NOT NULL 
                AND sile.default_unit_cost > 0
                THEN ROUND(((sile.price - sile.default_unit_cost) / sile.default_unit_cost * 100)::numeric, 2)
                ELSE NULL 
            END AS profit_markup_percent,
            
            -- Location quantities (from square_item_library_export)
            CASE 
                WHEN sile.current_quantity_aubrey IS NOT NULL AND sile.current_quantity_aubrey ~ '^[0-9]+$'
                THEN sile.current_quantity_aubrey::integer
                ELSE 0
            END AS aubrey_qty,
            CASE 
                WHEN sile.current_quantity_bridgefarmer IS NOT NULL AND sile.current_quantity_bridgefarmer ~ '^[0-9]+$'
                THEN sile.current_quantity_bridgefarmer::integer
                ELSE 0
            END AS bridgefarmer_qty,
            CASE 
                WHEN sile.current_quantity_building IS NOT NULL AND sile.current_quantity_building ~ '^[0-9]+$'
                THEN sile.current_quantity_building::integer
                ELSE 0
            END AS building_qty,
            CASE 
                WHEN sile.current_quantity_flomo IS NOT NULL AND sile.current_quantity_flomo ~ '^[0-9]+$'
                THEN sile.current_quantity_flomo::integer
                ELSE 0
            END AS flomo_qty,
            CASE 
                WHEN sile.current_quantity_justin IS NOT NULL AND sile.current_quantity_justin ~ '^[0-9]+$'
                THEN sile.current_quantity_justin::integer
                ELSE 0
            END AS justin_qty,
            CASE 
                WHEN sile.current_quantity_quinlan IS NOT NULL AND sile.current_quantity_quinlan ~ '^[0-9]+$'
                THEN sile.current_quantity_quinlan::integer
                ELSE 0
            END AS quinlan_qty,
            CASE 
                WHEN sile.current_quantity_terrell IS NOT NULL AND sile.current_quantity_terrell ~ '^[0-9]+$'
                THEN sile.current_quantity_terrell::integer
                ELSE 0
            END AS terrell_qty,
            
            -- Total quantity
            (
                CASE 
                    WHEN sile.current_quantity_aubrey IS NOT NULL AND sile.current_quantity_aubrey ~ '^[0-9]+$'
                    THEN sile.current_quantity_aubrey::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_bridgefarmer IS NOT NULL AND sile.current_quantity_bridgefarmer ~ '^[0-9]+$'
                    THEN sile.current_quantity_bridgefarmer::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_building IS NOT NULL AND sile.current_quantity_building ~ '^[0-9]+$'
                    THEN sile.current_quantity_building::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_flomo IS NOT NULL AND sile.current_quantity_flomo ~ '^[0-9]+$'
                    THEN sile.current_quantity_flomo::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_justin IS NOT NULL AND sile.current_quantity_justin ~ '^[0-9]+$'
                    THEN sile.current_quantity_justin::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_quinlan IS NOT NULL AND sile.current_quantity_quinlan ~ '^[0-9]+$'
                    THEN sile.current_quantity_quinlan::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_terrell IS NOT NULL AND sile.current_quantity_terrell ~ '^[0-9]+$'
                    THEN sile.current_quantity_terrell::integer
                    ELSE 0
                END
            ) AS total_qty,
            
            -- Units per case - get from catalog variations first, then catalog items
            COALESCE(
                (SELECT cv.units_per_case 
                 FROM catalog_variations cv 
                 WHERE cv.sku = sile.sku 
                 AND cv.is_deleted = false 
                 AND cv.units_per_case IS NOT NULL 
                 LIMIT 1),
                (SELECT ci.units_per_case 
                 FROM catalog_items ci 
                 JOIN catalog_variations cv ON ci.id = cv.item_id 
                 WHERE cv.sku = sile.sku 
                 AND ci.is_deleted = false 
                 AND cv.is_deleted = false 
                 AND ci.units_per_case IS NOT NULL 
                 LIMIT 1),
                12  -- Default fallback value
            ) AS units_per_case,
            
            -- Location availability status
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
            
            -- Item metadata
            COALESCE(sile.item_type, 'REGULAR') as item_type,
            COALESCE(sile.archived, 'N') as archived,
            COALESCE(sile.sellable, 'Y') as sellable,
            COALESCE(sile.stockable, 'Y') as stockable,
            
            sile.created_at,
            sile.updated_at
            
        FROM square_item_library_export sile
        WHERE sile.archived != 'Y'
    """)


def downgrade():
    """Revert items_view to previous version without units_per_case"""
    
    # Revert to the original view without units_per_case
    op.execute("""
        CREATE OR REPLACE VIEW items_view AS
        SELECT 
            -- Basic item information
            sile.item_name,
            sile.sku,
            sile.description,
            sile.categories AS category,
            
            -- Pricing information
            sile.price,
            
            -- Vendor information
            COALESCE(sile.default_vendor_name, '') AS vendor_name,
            COALESCE(sile.default_vendor_code, '') AS vendor_code,
            
            -- Cost information (simplified for now)
            sile.default_unit_cost AS cost,
            
            -- Profit margin calculation: (Price - Cost) / Price * 100
            CASE 
                WHEN sile.price IS NOT NULL 
                AND sile.default_unit_cost IS NOT NULL 
                AND sile.price > 0
                THEN ROUND(((sile.price - sile.default_unit_cost) / sile.price * 100)::numeric, 2)
                ELSE NULL 
            END AS profit_margin_percent,
            
            -- Profit markup calculation: (Price - Cost) / Cost * 100
            CASE 
                WHEN sile.price IS NOT NULL 
                AND sile.default_unit_cost IS NOT NULL 
                AND sile.default_unit_cost > 0
                THEN ROUND(((sile.price - sile.default_unit_cost) / sile.default_unit_cost * 100)::numeric, 2)
                ELSE NULL 
            END AS profit_markup_percent,
            
            -- Location quantities (from square_item_library_export)
            CASE 
                WHEN sile.current_quantity_aubrey IS NOT NULL AND sile.current_quantity_aubrey ~ '^[0-9]+$'
                THEN sile.current_quantity_aubrey::integer
                ELSE 0
            END AS aubrey_qty,
            CASE 
                WHEN sile.current_quantity_bridgefarmer IS NOT NULL AND sile.current_quantity_bridgefarmer ~ '^[0-9]+$'
                THEN sile.current_quantity_bridgefarmer::integer
                ELSE 0
            END AS bridgefarmer_qty,
            CASE 
                WHEN sile.current_quantity_building IS NOT NULL AND sile.current_quantity_building ~ '^[0-9]+$'
                THEN sile.current_quantity_building::integer
                ELSE 0
            END AS building_qty,
            CASE 
                WHEN sile.current_quantity_flomo IS NOT NULL AND sile.current_quantity_flomo ~ '^[0-9]+$'
                THEN sile.current_quantity_flomo::integer
                ELSE 0
            END AS flomo_qty,
            CASE 
                WHEN sile.current_quantity_justin IS NOT NULL AND sile.current_quantity_justin ~ '^[0-9]+$'
                THEN sile.current_quantity_justin::integer
                ELSE 0
            END AS justin_qty,
            CASE 
                WHEN sile.current_quantity_quinlan IS NOT NULL AND sile.current_quantity_quinlan ~ '^[0-9]+$'
                THEN sile.current_quantity_quinlan::integer
                ELSE 0
            END AS quinlan_qty,
            CASE 
                WHEN sile.current_quantity_terrell IS NOT NULL AND sile.current_quantity_terrell ~ '^[0-9]+$'
                THEN sile.current_quantity_terrell::integer
                ELSE 0
            END AS terrell_qty,
            
            -- Total quantity
            (
                CASE 
                    WHEN sile.current_quantity_aubrey IS NOT NULL AND sile.current_quantity_aubrey ~ '^[0-9]+$'
                    THEN sile.current_quantity_aubrey::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_bridgefarmer IS NOT NULL AND sile.current_quantity_bridgefarmer ~ '^[0-9]+$'
                    THEN sile.current_quantity_bridgefarmer::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_building IS NOT NULL AND sile.current_quantity_building ~ '^[0-9]+$'
                    THEN sile.current_quantity_building::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_flomo IS NOT NULL AND sile.current_quantity_flomo ~ '^[0-9]+$'
                    THEN sile.current_quantity_flomo::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_justin IS NOT NULL AND sile.current_quantity_justin ~ '^[0-9]+$'
                    THEN sile.current_quantity_justin::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_quinlan IS NOT NULL AND sile.current_quantity_quinlan ~ '^[0-9]+$'
                    THEN sile.current_quantity_quinlan::integer
                    ELSE 0
                END +
                CASE 
                    WHEN sile.current_quantity_terrell IS NOT NULL AND sile.current_quantity_terrell ~ '^[0-9]+$'
                    THEN sile.current_quantity_terrell::integer
                    ELSE 0
                END
            ) AS total_qty,
            
            -- Location availability status
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
            
            -- Item metadata
            COALESCE(sile.item_type, 'REGULAR') as item_type,
            COALESCE(sile.archived, 'N') as archived,
            COALESCE(sile.sellable, 'Y') as sellable,
            COALESCE(sile.stockable, 'Y') as stockable,
            
            sile.created_at,
            sile.updated_at
            
        FROM square_item_library_export sile
        WHERE sile.archived != 'Y'
    """) 