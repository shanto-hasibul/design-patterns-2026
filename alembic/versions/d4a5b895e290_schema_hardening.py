"""schema_hardening

Revision ID: d4a5b895e290
Revises: c3f4a784d189
Create Date: 2026-11-14 19:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4a5b895e290'
down_revision: Union[str, Sequence[str], None] = 'c3f4a784d189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with composite indexes and idempotent demo seed."""
    op.create_index(
        'ix_alerts_status_created_at',
        'alerts',
        ['status', sa.text('created_at DESC')],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        'ix_devices_location_zone',
        'devices',
        ['location_id', 'zone_id'],
        unique=False,
        if_not_exists=True,
    )

    # Idempotent seed: demo location, zone, simulation sensor (5s interval, tracking=true), actuator, and initial reading
    op.execute(
        """
        INSERT INTO locations (id, name)
        VALUES ('11111111-1111-1111-1111-111111111111', 'Demo Greenhouse North')
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO zones (id, location_id, name, moisture_threshold_low, moisture_threshold_high, schedule)
        VALUES (
            '22222222-2222-2222-2222-222222222222',
            '11111111-1111-1111-1111-111111111111',
            'Zone A — Seedlings',
            0.3000,
            0.7000,
            '{}'::jsonb
        )
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO devices (
            id, device_type, role, device_family, display_name,
            default_config, sampling_interval_seconds, tracking_enabled,
            zone_id, location_id
        )
        VALUES (
            '33333333-3333-3333-3333-333333333333',
            'moisture_sensor',
            'sensor',
            'simulation',
            'Demo Soil Moisture Sensor (5s)',
            '{"unit": "vwc", "sampling_interval_seconds": 5}'::jsonb,
            5,
            true,
            '22222222-2222-2222-2222-222222222222',
            '11111111-1111-1111-1111-111111111111'
        )
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO devices (
            id, device_type, role, device_family, display_name,
            default_config, sampling_interval_seconds, tracking_enabled,
            zone_id, location_id
        )
        VALUES (
            '44444444-4444-4444-4444-444444444444',
            'water_pump',
            'actuator',
            'simulation',
            'Demo Irrigation Pump',
            '{"flow_rate_lpm": 2.5}'::jsonb,
            300,
            true,
            '22222222-2222-2222-2222-222222222222',
            '11111111-1111-1111-1111-111111111111'
        )
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO actuator_states (device_id, state)
        VALUES ('44444444-4444-4444-4444-444444444444', 'idle')
        ON CONFLICT (device_id) DO NOTHING;

        INSERT INTO sensor_readings (id, device_id, value, unit, source)
        VALUES (
            '55555555-5555-5555-5555-555555555555',
            '33333333-3333-3333-3333-333333333333',
            0.4200,
            'vwc',
            'simulation'
        )
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_devices_location_zone', table_name='devices', if_exists=True)
    op.drop_index('ix_alerts_status_created_at', table_name='alerts', if_exists=True)