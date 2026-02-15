"""add failed status to receipt enum

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c8d9e0f1a2b3'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres requires manual SQL to modify ENUM types
    # We use a transaction-safe way if possible, but ALTER TYPE cannot run inside a transaction block 
    # in some setups. So we execute it directly.
    connection = op.get_bind()
    connection.execute(sa.text("ALTER TYPE receiptstatus ADD VALUE IF NOT EXISTS 'failed'"))


def downgrade() -> None:
    # Cannot remove value from ENUM in Postgres easily without dropping and recreating type
    pass
