"""Add units_per_case to catalog items and variations

Revision ID: ca4bae3faf93
Revises: 60da471fb9ec
Create Date: 2025-05-28 14:45:24.099156

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ca4bae3faf93'
down_revision = '60da471fb9ec'
branch_labels = None
depends_on = None


def upgrade():
    # Add units_per_case column to catalog_items table
    # This will store Units Per Case data when it's set at the item level
    op.add_column('catalog_items', sa.Column('units_per_case', sa.Integer(), nullable=True))
    
    # Add units_per_case column to catalog_variations table
    # This will store Units Per Case data when it's set at the variation level
    op.add_column('catalog_variations', sa.Column('units_per_case', sa.Integer(), nullable=True))


def downgrade():
    # Remove units_per_case column from catalog_variations table
    op.drop_column('catalog_variations', 'units_per_case')
    
    # Remove units_per_case column from catalog_items table
    op.drop_column('catalog_items', 'units_per_case')
