"""Fix items_view permissions

Revision ID: fix_permissions_001
Revises: create_items_view_001
Create Date: 2025-06-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_permissions_001'
down_revision = 'create_items_view_001'
branch_labels = None
depends_on = None


def upgrade():
    """Grant proper permissions on items_view"""
    
    # Grant permissions to nytex_user for administrative access
    op.execute("""
        DO $$
        BEGIN
            -- Check if nytex_user role exists before granting
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nytex_user') THEN
                GRANT SELECT ON items_view TO nytex_user;
            END IF;
        END
        $$;
    """)
    
    # Ensure nytex_app has permissions (should already have as owner, but being explicit)
    op.execute("GRANT SELECT ON items_view TO nytex_app")


def downgrade():
    """Revoke permissions (if needed)"""
    
    # Revoke permissions from nytex_user
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nytex_user') THEN
                REVOKE SELECT ON items_view FROM nytex_user;
            END IF;
        END
        $$;
    """) 