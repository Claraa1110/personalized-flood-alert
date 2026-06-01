"""add corrected_thresholds table

Revision ID: 3b2b06416b4f
Revises: 59279725fb27
Create Date: 2026-05-28 16:16:58.562329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b2b06416b4f'
down_revision: Union[str, Sequence[str], None] = '59279725fb27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('corrected_thresholds',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('county_name', sa.String(length=50), nullable=False),
    sa.Column('district_name', sa.String(length=50), nullable=False),
    sa.Column('original_1h', sa.Float(), nullable=True),
    sa.Column('original_3h', sa.Float(), nullable=True),
    sa.Column('original_6h', sa.Float(), nullable=True),
    sa.Column('min_rainfall_1h', sa.Float(), nullable=True),
    sa.Column('min_rainfall_3h', sa.Float(), nullable=True),
    sa.Column('min_rainfall_6h', sa.Float(), nullable=True),
    sa.Column('corrected_1h', sa.Float(), nullable=True),
    sa.Column('corrected_3h', sa.Float(), nullable=True),
    sa.Column('corrected_6h', sa.Float(), nullable=True),
    sa.Column('event_count', sa.BigInteger(), nullable=False),
    sa.Column('adjustment_rate_1h', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('corrected_thresholds')
