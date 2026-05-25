"""add codis_raw_rainfall table

Revision ID: 59279725fb27
Revises: 12d0a67b0dd5
Create Date: 2026-05-24 23:05:35.777920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59279725fb27'
down_revision: Union[str, Sequence[str], None] = '12d0a67b0dd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('codis_raw_rainfall',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('flood_event_id', sa.BigInteger(), nullable=False),
    sa.Column('station_id', sa.String(length=20), nullable=False),
    sa.Column('station_name', sa.String(length=100), nullable=True),
    sa.Column('distance_km', sa.Float(), nullable=True),
    sa.Column('obs_time', sa.DateTime(), nullable=False),
    sa.Column('rainfall_mm', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('flood_event_id', 'station_id', 'obs_time', name='codis_unique')
    )


def downgrade() -> None:
    op.drop_table('codis_raw_rainfall')
