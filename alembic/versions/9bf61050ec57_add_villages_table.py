"""add villages table

Revision ID: 9bf61050ec57
Revises: f06d5d47efcf
Create Date: 2026-05-14 19:21:20.959635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '9bf61050ec57'
down_revision: Union[str, Sequence[str], None] = 'f06d5d47efcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "villages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("county_name", sa.String(length=50), nullable=False),
        sa.Column("district_name", sa.String(length=50), nullable=False),
        sa.Column("village_name", sa.String(length=50), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geography(
                geometry_type="MULTIPOLYGON", srid=4326, dimension=2,
                from_text="ST_GeogFromText", name="geography", nullable=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("villages_geometry_idx", "villages", ["geometry"], unique=False, postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("villages_geometry_idx", table_name="villages", postgresql_using="gist")
    op.drop_table("villages")
