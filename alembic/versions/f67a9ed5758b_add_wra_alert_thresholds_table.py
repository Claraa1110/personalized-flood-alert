"""add wra_alert_thresholds table

Revision ID: f67a9ed5758b
Revises: 9bf61050ec57
Create Date: 2026-05-19 13:59:52.898450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f67a9ed5758b'
down_revision: Union[str, Sequence[str], None] = '9bf61050ec57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wra_alert_thresholds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("county_name", sa.String(length=50), nullable=False),
        sa.Column("district_name", sa.String(length=50), nullable=False),
        sa.Column("village_name", sa.String(length=50), nullable=False),
        sa.Column("threshold_1h_lv2", sa.Float(), nullable=True),
        sa.Column("threshold_1h_lv1", sa.Float(), nullable=True),
        sa.Column("threshold_3h_lv2", sa.Float(), nullable=True),
        sa.Column("threshold_3h_lv1", sa.Float(), nullable=True),
        sa.Column("threshold_6h_lv2", sa.Float(), nullable=True),
        sa.Column("threshold_6h_lv1", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wra_thresholds_location", "wra_alert_thresholds", ["county_name", "district_name", "village_name"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_wra_thresholds_location", table_name="wra_alert_thresholds")
    op.drop_table("wra_alert_thresholds")
