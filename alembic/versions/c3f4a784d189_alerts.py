"""alerts

Revision ID: c3f4a784d189
Revises: b2e3f673c078
Create Date: 2026-11-14 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3f4a784d189'
down_revision: Union[str, Sequence[str], None] = 'b2e3f673c078'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('severity', sa.String(length=32), server_default=sa.text("'warning'"), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_created_at', 'alerts', [sa.text('created_at DESC')], unique=False)
    op.create_index('ix_alerts_location_zone', 'alerts', ['location_id', 'zone_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_alerts_location_zone', table_name='alerts')
    op.drop_index('ix_alerts_created_at', table_name='alerts')
    op.drop_table('alerts')