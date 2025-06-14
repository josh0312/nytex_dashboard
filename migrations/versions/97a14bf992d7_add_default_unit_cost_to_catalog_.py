"""Add default_unit_cost to catalog_variations

Revision ID: 97a14bf992d7
Revises: ba134ef5c827
Create Date: 2025-06-13 20:38:22.110446

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '97a14bf992d7'
down_revision = 'ba134ef5c827'
branch_labels = None
depends_on = None


def upgrade():
    # Convert existing default_unit_cost column from NUMERIC to JSONB
    op.execute("ALTER TABLE catalog_variations ALTER COLUMN default_unit_cost TYPE JSONB USING CASE WHEN default_unit_cost IS NULL THEN NULL ELSE json_build_object('amount', (default_unit_cost * 100)::integer, 'currency', 'USD') END")


def downgrade():
    # Convert default_unit_cost column back from JSONB to NUMERIC
    op.execute("ALTER TABLE catalog_variations ALTER COLUMN default_unit_cost TYPE NUMERIC(10,2) USING CASE WHEN default_unit_cost IS NULL THEN NULL ELSE (default_unit_cost->>'amount')::numeric / 100 END")
