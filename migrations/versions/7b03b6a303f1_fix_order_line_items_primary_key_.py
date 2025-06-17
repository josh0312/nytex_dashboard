"""fix_order_line_items_primary_key_constraint

Revision ID: 7b03b6a303f1
Revises: 97a14bf992d7
Create Date: 2025-06-13 22:42:42.546316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b03b6a303f1'
down_revision = '97a14bf992d7'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix order_line_items primary key constraint to match development database.
    
    Changes:
    1. Drop existing primary key constraint 
    2. Add composite primary key on (order_id, uid)
    3. Remove the separate unique constraint if it exists (now redundant)
    
    This fixes the sync issue where Square API reuses uid values across different orders.
    """
    
    # Get connection to check existing constraints
    connection = op.get_bind()
    
    # Check what constraints exist
    result = connection.execute(sa.text("""
        SELECT conname, contype 
        FROM pg_constraint 
        WHERE conrelid = 'order_line_items'::regclass
    """))
    constraints = {row[0]: row[1] for row in result}
    
    # Step 1: Drop the existing primary key constraint
    op.drop_constraint('order_line_items_pkey', 'order_line_items', type_='primary')
    
    # Step 2: Drop the unique constraint if it exists (production has this, dev doesn't)
    if 'uix_order_line_items_order_uid' in constraints:
        op.drop_constraint('uix_order_line_items_order_uid', 'order_line_items', type_='unique')
    
    # Step 3: Create composite primary key on (order_id, uid)
    op.create_primary_key('order_line_items_pkey', 'order_line_items', ['order_id', 'uid'])


def downgrade():
    """
    Revert back to single uid primary key (original schema).
    
    WARNING: This downgrade will fail if there are duplicate uid values
    across different orders, which is expected after the historical sync.
    """
    
    # Step 1: Drop the composite primary key
    op.drop_constraint('order_line_items_pkey', 'order_line_items', type_='primary')
    
    # Step 2: Recreate single uid primary key
    op.create_primary_key('order_line_items_pkey', 'order_line_items', ['uid'])
    
    # Step 3: Recreate the unique constraint
    op.create_unique_constraint('uix_order_line_items_order_uid', 'order_line_items', ['order_id', 'uid'])
