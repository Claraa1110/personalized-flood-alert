import geopandas as gpd
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def import_villages():
    shp_path = "data/villages/villages_data/VILLAGE_NLSC_1150407.shp"
    gdf = gpd.read_file(shp_path)

    if gdf.crs is None or gdf.crs.to_epsg() is None:
        gdf = gdf.set_crs(epsg=4326, allow_override=True)

    print(f"總共 {len(gdf)} 個村里，開始匯入...")

    count = 0
    async with AsyncSessionLocal() as session:
        for idx, row in gdf.iterrows():
            try:
                county = row["COUNTYNAME"] or ""
                district = row["TOWNNAME"] or ""
                village = row["VILLNAME"] or ""
                geom_wkt = row.geometry.wkt

                await session.execute(
                    text("""
                        INSERT INTO villages
                            (county_name, district_name, village_name, geometry)
                        VALUES (
                            :county, :district, :village,
                            ST_Multi(ST_GeomFromText(:geom, 4326))::geography
                        )
                    """),
                    {
                        "county": county,
                        "district": district,
                        "village": village,
                        "geom": geom_wkt,
                    },
                )
                await session.commit()
                count += 1

                if count % 500 == 0:
                    print(f"已匯入 {count} 筆...")

            except Exception as e:
                print(f"第 {idx} 筆錯誤：{e}")
                await session.rollback()
                continue

        print(f"匯入完成！共 {count} 筆")


if __name__ == "__main__":
    asyncio.run(import_villages())
