"""device_family

Revision ID: b9e5d823f412
Revises: a8f4c912d301
Create Date: 2026-11-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9e5d823f412'
down_revision: Union[str, Sequence[str], None] = 'a8f4c912d301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'devices',
        sa.Column(
            'device_family',
            sa.String(length=32),
            server_default=sa.text("'simulation'"),
            nullable=False,
        ),
    )
    op.execute("UPDATE devices SET device_family = 'simulation' WHERE device_family IS NULL")
    op.create_index('ix_devices_family', 'devices', ['device_family'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_devices_family', table_name='devices')
    op.drop_column('devices', 'device_family')