"""devices

Revision ID: a8f4c912d301
Revises: 2e9095105f26
Create Date: 2026-11-11 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8f4c912d301'
down_revision: Union[str, Sequence[str], None] = '2e9095105f26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_type', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=32), server_default=sa.text("'sensor'"), nullable=False),
        sa.Column('display_name', sa.String(length=128), nullable=True),
        sa.Column('default_config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_devices_role', 'devices', ['role'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_devices_role', table_name='devices')
    op.drop_table('devices')