"""add postgis location to properties

Revision ID: 600b24bfc3e6
Revises: 0bb296ed3b5f
Create Date: 2026-05-02 15:14:36.433832

"""
from typing import Sequence, Union

import geoalchemy2
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '600b24bfc3e6'
down_revision: Union[str, Sequence[str], None] = '0bb296ed3b5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('properties', sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=True))
    op.create_index('properties_location_idx', 'properties', ['location'], unique=False, postgresql_using='gist')
    op.drop_column('properties', 'latitude')
    op.drop_column('properties', 'longitude')


def downgrade() -> None:
    op.add_column('properties', sa.Column('longitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('properties', sa.Column('latitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_index('properties_location_idx', table_name='properties', postgresql_using='gist')
    op.drop_column('properties', 'location')
