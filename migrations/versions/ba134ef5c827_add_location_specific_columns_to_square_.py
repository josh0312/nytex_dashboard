"""add_location_specific_columns_to_square_export

Revision ID: ba134ef5c827
Revises: auth_001
Create Date: 2025-06-12 21:03:16.696931

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba134ef5c827'
down_revision = 'auth_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add location-specific columns for Aubrey
    op.add_column('square_item_library_export', sa.Column('enabled_aubrey', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_aubrey', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_aubrey', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_aubrey', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_aubrey', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_aubrey', sa.String(255), nullable=True))
    
    # Add location-specific columns for Bridgefarmer
    op.add_column('square_item_library_export', sa.Column('enabled_bridgefarmer', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_bridgefarmer', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_bridgefarmer', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_bridgefarmer', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_bridgefarmer', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_bridgefarmer', sa.String(255), nullable=True))
    
    # Add location-specific columns for Building
    op.add_column('square_item_library_export', sa.Column('enabled_building', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_building', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_building', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_building', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_building', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_building', sa.String(255), nullable=True))
    
    # Add location-specific columns for FloMo
    op.add_column('square_item_library_export', sa.Column('enabled_flomo', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_flomo', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_flomo', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_flomo', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_flomo', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_flomo', sa.String(255), nullable=True))
    
    # Add location-specific columns for Justin
    op.add_column('square_item_library_export', sa.Column('enabled_justin', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_justin', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_justin', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_justin', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_justin', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_justin', sa.String(255), nullable=True))
    
    # Add location-specific columns for Quinlan
    op.add_column('square_item_library_export', sa.Column('enabled_quinlan', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_quinlan', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_quinlan', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_quinlan', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_quinlan', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_quinlan', sa.String(255), nullable=True))
    
    # Add location-specific columns for Terrell
    op.add_column('square_item_library_export', sa.Column('enabled_terrell', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('current_quantity_terrell', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('new_quantity_terrell', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_enabled_terrell', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('stock_alert_count_terrell', sa.String(255), nullable=True))
    op.add_column('square_item_library_export', sa.Column('price_terrell', sa.String(255), nullable=True))


def downgrade():
    # Remove location-specific columns for Terrell
    op.drop_column('square_item_library_export', 'price_terrell')
    op.drop_column('square_item_library_export', 'stock_alert_count_terrell')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_terrell')
    op.drop_column('square_item_library_export', 'new_quantity_terrell')
    op.drop_column('square_item_library_export', 'current_quantity_terrell')
    op.drop_column('square_item_library_export', 'enabled_terrell')
    
    # Remove location-specific columns for Quinlan
    op.drop_column('square_item_library_export', 'price_quinlan')
    op.drop_column('square_item_library_export', 'stock_alert_count_quinlan')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_quinlan')
    op.drop_column('square_item_library_export', 'new_quantity_quinlan')
    op.drop_column('square_item_library_export', 'current_quantity_quinlan')
    op.drop_column('square_item_library_export', 'enabled_quinlan')
    
    # Remove location-specific columns for Justin
    op.drop_column('square_item_library_export', 'price_justin')
    op.drop_column('square_item_library_export', 'stock_alert_count_justin')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_justin')
    op.drop_column('square_item_library_export', 'new_quantity_justin')
    op.drop_column('square_item_library_export', 'current_quantity_justin')
    op.drop_column('square_item_library_export', 'enabled_justin')
    
    # Remove location-specific columns for FloMo
    op.drop_column('square_item_library_export', 'price_flomo')
    op.drop_column('square_item_library_export', 'stock_alert_count_flomo')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_flomo')
    op.drop_column('square_item_library_export', 'new_quantity_flomo')
    op.drop_column('square_item_library_export', 'current_quantity_flomo')
    op.drop_column('square_item_library_export', 'enabled_flomo')
    
    # Remove location-specific columns for Building
    op.drop_column('square_item_library_export', 'price_building')
    op.drop_column('square_item_library_export', 'stock_alert_count_building')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_building')
    op.drop_column('square_item_library_export', 'new_quantity_building')
    op.drop_column('square_item_library_export', 'current_quantity_building')
    op.drop_column('square_item_library_export', 'enabled_building')
    
    # Remove location-specific columns for Bridgefarmer
    op.drop_column('square_item_library_export', 'price_bridgefarmer')
    op.drop_column('square_item_library_export', 'stock_alert_count_bridgefarmer')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_bridgefarmer')
    op.drop_column('square_item_library_export', 'new_quantity_bridgefarmer')
    op.drop_column('square_item_library_export', 'current_quantity_bridgefarmer')
    op.drop_column('square_item_library_export', 'enabled_bridgefarmer')
    
    # Remove location-specific columns for Aubrey
    op.drop_column('square_item_library_export', 'price_aubrey')
    op.drop_column('square_item_library_export', 'stock_alert_count_aubrey')
    op.drop_column('square_item_library_export', 'stock_alert_enabled_aubrey')
    op.drop_column('square_item_library_export', 'new_quantity_aubrey')
    op.drop_column('square_item_library_export', 'current_quantity_aubrey')
    op.drop_column('square_item_library_export', 'enabled_aubrey')
