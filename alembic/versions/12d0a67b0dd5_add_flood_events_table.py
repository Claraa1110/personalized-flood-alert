"""add flood_events table

Revision ID: 12d0a67b0dd5
Revises: 67fe7cf66e41
Create Date: 2026-05-23 15:55:25.072144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12d0a67b0dd5'
down_revision: Union[str, Sequence[str], None] = '67fe7cf66e41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flood_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("news_article_id", sa.String(length=100), nullable=True),
        sa.Column("news_title", sa.String(length=500), nullable=True),
        sa.Column("news_time", sa.DateTime(), nullable=True),
        sa.Column("location_name", sa.String(length=200), nullable=True),
        sa.Column("county_name", sa.String(length=50), nullable=True),
        sa.Column("district_name", sa.String(length=50), nullable=True),
        sa.Column("village_name", sa.String(length=50), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("est_flood_time", sa.DateTime(), nullable=True),
        sa.Column("confidence", sa.String(length=10), nullable=True),
        sa.Column("rainfall_1h", sa.Float(), nullable=True),
        sa.Column("rainfall_3h", sa.Float(), nullable=True),
        sa.Column("rainfall_6h", sa.Float(), nullable=True),
        sa.Column("wra_threshold_1h", sa.Float(), nullable=True),
        sa.Column("wra_threshold_3h", sa.Float(), nullable=True),
        sa.Column("wra_threshold_6h", sa.Float(), nullable=True),
        sa.Column("needs_adjustment", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("flood_events")
