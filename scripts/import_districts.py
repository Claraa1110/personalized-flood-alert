"""
Import Taiwan township boundaries from shapefile into the districts table.
Usage: uv run python scripts/import_districts.py
"""
import asyncio
import os
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

SHAPEFILE = Path(__file__).parent.parent / "data" / "TOWN_MOI_1140318.shp"

_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(_url, poolclass=NullPool, connect_args={"statement_cache_size": 0})
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def to_multipolygon(geom) -> MultiPolygon:
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


async def main():
    gdf = gpd.read_file(SHAPEFILE)
    gdf = gdf.to_crs(epsg=4326)

    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE districts RESTART IDENTITY CASCADE"))
        await session.commit()

        count = 0
        for _, row in gdf.iterrows():
            geom = to_multipolygon(row.geometry)
            wkt = geom.wkt
            await session.execute(
                text("""
                    INSERT INTO districts
                        (town_id, town_code, town_name, town_eng, county_id, county_code, county_name, geometry)
                    VALUES
                        (:town_id, :town_code, :town_name, :town_eng,
                         :county_id, :county_code, :county_name,
                         ST_Multi(ST_GeomFromText(:wkt, 4326)))
                """),
                {
                    "town_id": row["TOWNID"],
                    "town_code": row.get("TOWNCODE"),
                    "town_name": row["TOWNNAME"],
                    "town_eng": row.get("TOWNENG"),
                    "county_id": row["COUNTYID"],
                    "county_code": row.get("COUNTYCODE"),
                    "county_name": row["COUNTYNAME"],
                    "wkt": wkt,
                },
            )
            count += 1

        await session.commit()
        print(f"Imported {count} districts.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
