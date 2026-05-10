"""add location_geom to news_articles

Revision ID: f06d5d47efcf
Revises: 669cacc62c48
Create Date: 2026-05-10 13:25:01.652869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'f06d5d47efcf'
down_revision: Union[str, Sequence[str], None] = '669cacc62c48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('news_articles', sa.Column('location_geom', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeogFromText', name='geography'), nullable=True))
    op.create_index('idx_news_articles_location_geom', 'news_articles', ['location_geom'], unique=False, postgresql_using='gist')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_news_articles_location_geom', table_name='news_articles', postgresql_using='gist')
    op.drop_column('news_articles', 'location_geom')
