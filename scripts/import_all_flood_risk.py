"""
Import all Taiwan county flood risk zones (24h 200mm scenario) into flood_risk_zones table.
Usage: uv run python scripts/import_all_flood_risk.py
"""

import asyncio
import os

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

SCENARIO = "24h_200mm"

FLOOD_SHAPEFILES = [
    "data/taipei/SHP/tp_24h_r200_polygon_class_1.shp",
    "data/newtaipei/SHP/24h200r.shp",
    "data/taoyuan/SHP/ty_24h_200mm.shp",
    "data/taichung/SHP/24Hr200r.shp",
    "data/tainan/SHP/24h200.shp",
    "data/kaohsiung/SHP/24h200r.shp",
    "data/keelung/SHP/24h200r.shp",
    "data/hsinchu/07_shp_新竹縣市/SHP-新竹市/24hr200mm.shp",
    "data/hsinchu/07_shp_新竹縣市/SHP-新竹縣/24hr200mm.shp",
    "data/miaoli/SHP/24hr200mm.shp",
    "data/changhua/SHP/24h200r.shp",
    "data/nantou/SHP/24hr_200mm.shp",
    "data/yunlin/SHP/yl_24h_r200_polygon_class.shp",
    "data/chiayi/08_shp_嘉義縣市/SHP-嘉義市/i_24hr200.shp",
    "data/chiayi/08_shp_嘉義縣市/SHP-嘉義縣/q_24hr200.shp",
    "data/pingtung/SHP/PT24H200mm.shp",
    "data/yilan/SHP/24H200R.shp",
    "data/hualien/SHP/24h200r.shp",
    "data/taitung/SHP/24H200R.shp",
    "data/kinmen/18_SHP_金門縣/24hr200mm.shp",
    "data/lienchiang/19_SHP_連江縣/24hr200mm.shp",
    "data/penghu/17_SHP_澎湖縣/24hr200mm.shp",
]

_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(
    _url, poolclass=NullPool, connect_args={"statement_cache_size": 0}
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


NANTOU_TYPE_MAP = {
    "0-0.3": 0,
    "0~0.3": 0,
    "0.3-0.5": 1,
    "0.3~0.5": 1,
    "0.5-1": 2,
    "0.5~1": 2,
    "1-2": 3,
    "1~2": 3,
    "2-3": 4,
    "2~3": 4,
    ">3": 4,
}


def get_risk_level(row) -> int:
    for col in ["GRIDCODE", "色階", "RANK"]:
        if col in row.index and row[col] is not None:
            return int(row[col])
    if "Type" in row.index and row["Type"] is not None:
        return NANTOU_TYPE_MAP.get(str(row["Type"]).strip(), 1)
    return 1


def to_multipolygon(geom) -> MultiPolygon:
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


def force_2d(geom):
    from shapely.ops import transform

    return transform(lambda x, y, z=None: (x, y), geom)


async def import_one(shp_path: str) -> int:
    try:
        gdf = gpd.read_file(shp_path)
    except Exception as e:
        print(f"  讀取失敗：{e}")
        return 0

    if gdf.crs is None:
        # 座標值小於 360 通常是 WGS84，否則是 TWD97
        sample_x = gdf.geometry.iloc[0].bounds[0]
        epsg = 4326 if sample_x < 360 else 3826
        gdf = gdf.set_crs(epsg=epsg)

    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    count = 0
    async with AsyncSessionLocal() as session:
        for idx, row in gdf.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                continue
            try:
                risk_level = get_risk_level(row)
                geom = force_2d(to_multipolygon(row.geometry))
                await session.execute(
                    text("""
                        INSERT INTO flood_risk_zones (scenario, risk_level, geometry)
                        VALUES (:scenario, :risk_level,
                            ST_Multi(ST_GeomFromText(:wkt, 4326))::geography)
                    """),
                    {"scenario": SCENARIO, "risk_level": risk_level, "wkt": geom.wkt},
                )
                count += 1
                if count % 50 == 0:
                    await session.commit()
                    print(f"  已處理 {count} 筆...")
            except Exception as e:
                await session.rollback()
                print(f"  第 {idx} 筆錯誤：{e}")
                continue
        await session.commit()
    return count


async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM flood_risk_zones WHERE scenario = :scenario"),
            {"scenario": SCENARIO},
        )
        await session.commit()
        print("已清空舊資料\n")

    total = 0
    for shp_path in FLOOD_SHAPEFILES:
        print(f"匯入：{shp_path}")
        count = await import_one(shp_path)
        total += count
        print(f"完成，{count} 筆\n")

    print(f"全部完成！總共 {total} 筆")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
