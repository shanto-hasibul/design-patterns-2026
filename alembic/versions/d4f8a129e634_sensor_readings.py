"""sensor_readings

Revision ID: d4f8a129e634
Revises: c7a1e934b523
Create Date: 2026-11-12 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4f8a129e634'
down_revision: Union[str, Sequence[str], None] = 'c7a1e934b523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'devices',
        sa.Column(
            'sampling_interval_seconds',
            sa.Integer(),
            server_default=sa.text('300'),
            nullable=False,
        ),
    )
    op.add_column(
        'devices',
        sa.Column(
            'tracking_enabled',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
        ),
    )

    # Backfill sampling_interval_seconds from default_config JSONB when present
    op.execute(
        """
        UPDATE devices
        SET sampling_interval_seconds = GREATEST(5, (default_config->>'sampling_interval_seconds')::int)
        WHERE default_config ? 'sampling_interval_seconds'
          AND (default_config->>'sampling_interval_seconds') ~ '^[0-9]+$'
        """
    )

    op.create_table(
        'sensor_readings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('value', sa.Numeric(precision=12, scale=4, asdecimal=False), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_sensor_readings_device_recorded_at',
        'sensor_readings',
        ['device_id', sa.text('recorded_at DESC')],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sensor_readings_device_recorded_at', table_name='sensor_readings')
    op.drop_table('sensor_readings')
    op.drop_column('devices', 'tracking_enabled')
    op.drop_column('devices', 'sampling_interval_seconds')