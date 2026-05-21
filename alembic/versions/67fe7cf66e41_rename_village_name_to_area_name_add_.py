"""rename village_name to area_name, add unique constraint

Revision ID: 67fe7cf66e41
Revises: f67a9ed5758b
Create Date: 2026-05-21 09:34:58.932204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '67fe7cf66e41'
down_revision: Union[str, Sequence[str], None] = 'f67a9ed5758b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_wra_thresholds_location", table_name="wra_alert_thresholds")
    op.drop_column("wra_alert_thresholds", "village_name")
    op.add_column("wra_alert_thresholds", sa.Column("area_name", sa.String(length=50), nullable=False, server_default=""))
    op.alter_column("wra_alert_thresholds", "area_name", server_default=None)
    op.create_index("idx_wra_thresholds_location", "wra_alert_thresholds", ["county_name", "district_name", "area_name"], unique=False)
    op.create_unique_constraint("uq_wra_thresholds_location", "wra_alert_thresholds", ["county_name", "district_name", "area_name"])


def downgrade() -> None:
    op.drop_constraint("uq_wra_thresholds_location", "wra_alert_thresholds", type_="unique")
    op.drop_index("idx_wra_thresholds_location", table_name="wra_alert_thresholds")
    op.drop_column("wra_alert_thresholds", "area_name")
    op.add_column("wra_alert_thresholds", sa.Column("village_name", sa.String(length=50), nullable=False, server_default=""))
    op.alter_column("wra_alert_thresholds", "village_name", server_default=None)
    op.create_index("idx_wra_thresholds_location", "wra_alert_thresholds", ["county_name", "district_name", "village_name"], unique=False)
