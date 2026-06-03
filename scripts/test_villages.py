import geopandas as gpd

gdf = gpd.read_file('data/villages/villages_data/VILLAGE_NLSC_1150407.shp')

print("=== 欄位名稱 ===")
print(gdf.columns.tolist())

print("\n=== 前 3 筆（不含 geometry）===")
print(gdf.drop(columns=['geometry']).head(3).to_string())