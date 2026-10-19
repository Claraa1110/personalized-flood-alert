"""dedupe rainfall_observations and add unique constraint

Revision ID: 0b35a9d80cb4
Revises: 3b2b06416b4f
Create Date: 2026-10-19 14:18:23.052962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b35a9d80cb4'
down_revision: Union[str, Sequence[str], None] = '3b2b06416b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "uq_rainfall_obs_station_time"


def upgrade() -> None:
    """
    清除 (station_id, observed_at) 重複列後建立唯一約束。

    順序不可對調：既有資料含約 9,300 筆重複，先建約束會直接失敗。
    保留每組中 id 最小者（最早寫入的那筆）。
    """
    op.execute("""
        DELETE FROM rainfall_observations a
        USING rainfall_observations b
        WHERE a.id > b.id
          AND a.station_id = b.station_id
          AND a.observed_at = b.observed_at
    """)

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "rainfall_observations",
        ["station_id", "observed_at"],
    )


def downgrade() -> None:
    """移除唯一約束。已刪除的重複列無法復原。"""
    op.drop_constraint(
        CONSTRAINT_NAME,
        "rainfall_observations",
        type_="unique",
    )
