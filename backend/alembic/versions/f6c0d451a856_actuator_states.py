"""actuator_states

Revision ID: f6c0d451a856
Revises: e5b9c340f745
Create Date: 2026-11-13 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6c0d451a856'
down_revision: Union[str, Sequence[str], None] = 'e5b9c340f745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'actuator_states',
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state', sa.String(length=32), server_default=sa.text("'idle'"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('device_id'),
    )

    # Seed existing actuator devices to 'idle'
    op.execute(
        """
        INSERT INTO actuator_states (device_id, state, updated_at)
        SELECT id, 'idle', now()
        FROM devices
        WHERE role = 'actuator'
        ON CONFLICT (device_id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('actuator_states')