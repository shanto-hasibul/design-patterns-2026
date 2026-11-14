"""automation_rules

Revision ID: e5b9c340f745
Revises: d4f8a129e634
Create Date: 2026-11-13 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5b9c340f745'
down_revision: Union[str, Sequence[str], None] = 'd4f8a129e634'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'automation_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_key', sa.String(length=64), server_default=sa.text("'conservative'"), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_id', name='uq_automation_rules_location_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('automation_rules')