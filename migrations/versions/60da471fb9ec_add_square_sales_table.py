"""Add square sales table

Revision ID: 60da471fb9ec
Revises: 
Create Date: 2024-12-28 13:57:49.845715

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60da471fb9ec'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('square_sales',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('order_id', sa.String(), nullable=False),
    sa.Column('location_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('payment_id', sa.String(), nullable=True),
    sa.Column('item_count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('square_sales')
    # ### end Alembic commands ###