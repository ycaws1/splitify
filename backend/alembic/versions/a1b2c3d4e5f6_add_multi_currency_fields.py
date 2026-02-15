"""add multi-currency fields

Revision ID: a1b2c3d4e5f6
Revises: 5e6f7802cb5e
Create Date: 2026-02-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5e6f7802cb5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('groups', sa.Column('base_currency', sa.String(3), nullable=False, server_default='SGD'))
    op.add_column('receipts', sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('receipts', 'exchange_rate')
    op.drop_column('groups', 'base_currency')
