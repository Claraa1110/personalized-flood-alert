"""
Import Taipei flood risk zones from shapefile into flood_risk_zones table.
Usage: uv run python scripts/import_flood_risk.py
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

SHAPEFILE = Path(__file__).parent.parent / "data" / "flood_taipei" / "SHP" / "tp_24h_r200_polygon_class_1.shp"
SCENARIO = "24h_200mm"

_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(_url, poolclass=NullPool, connect_args={"statement_cache_size": 0})
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def to_multipolygon(geom) -> MultiPolygon:
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


async def main():
    gdf = gpd.read_file(SHAPEFILE)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    print(f"總共 {len(gdf)} 筆，開始匯入...")

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM flood_risk_zones WHERE scenario = :scenario"),
            {"scenario": SCENARIO},
        )
        await session.commit()

        for idx, row in gdf.iterrows():
            geom = to_multipolygon(row.geometry)
            await session.execute(
                text("""
                    INSERT INTO flood_risk_zones (scenario, risk_level, geometry)
                    VALUES (:scenario, :risk_level,
                        ST_Multi(ST_GeomFromText(:wkt, 4326))::geography)
                """),
                {
                    "scenario": SCENARIO,
                    "risk_level": int(row["GRIDCODE"]),
                    "wkt": geom.wkt,
                },
            )
            print(f"  已匯入 GRIDCODE={row['GRIDCODE']}")

        await session.commit()
        print("匯入完成！")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
