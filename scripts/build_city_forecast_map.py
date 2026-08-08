"""
一次性探測腳本：找出各縣市「未來3天鄉鎮預報」對應的 F-D0047-XXX 編號。
執行方式：cd /Users/zhangtianxun/Desktop/FF && uv run python scripts/build_city_forecast_map.py
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

CWA_API_KEY = os.getenv("CWA_API_KEY")
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"


async def main():
    if not CWA_API_KEY:
        print("❌ 找不到 CWA_API_KEY，請確認 .env")
        return

    mapping: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
        for n in range(1, 88, 2):  # 奇數 001~087
            endpoint = f"F-D0047-{n:03d}"
            url = f"{BASE_URL}/{endpoint}"
            try:
                resp = await client.get(url, params={
                    "Authorization": CWA_API_KEY,
                    "format": "JSON",
                    "limit": 1,
                })
                if resp.status_code != 200:
                    print(f"  {endpoint}: HTTP {resp.status_code}")
                    continue

                data = resp.json()
                records = data.get("records", {})
                desc = records.get("datasetDescription", "")
                loc_groups = records.get("Locations", [])
                if not loc_groups:
                    print(f"  {endpoint}: 無 Locations")
                    continue

                county = loc_groups[0].get("LocationsName", "")

                # 判斷方式：含「3小時降雨機率」的是未來3天版本；含「12小時」的是未來1週版本
                loc_inner = loc_groups[0].get("Location", [])
                we_names = []
                if loc_inner:
                    we_names = [w.get("ElementName", "") for w in loc_inner[0].get("WeatherElement", [])]

                if any("3小時降雨機率" in n for n in we_names):
                    mapping[county] = endpoint
                    print(f"✓ {endpoint}: {county}（3小時降雨機率 → 未來3天）")
                else:
                    rain_el = next((n for n in we_names if "降雨" in n), "無降雨欄位")
                    print(f"  {endpoint}: {county} — 略過（{rain_el}）")

            except Exception as e:
                print(f"  {endpoint}: 例外 {type(e).__name__}: {e}")

    print(f"\n=== 找到 {len(mapping)} 個縣市 ===")
    for county, ep in sorted(mapping.items(), key=lambda x: x[1]):
        print(f"  '{county}': '{ep}',")

    if len(mapping) == 0:
        print("❌ 沒有找到任何縣市，請確認 API key 是否有效")
        return

    # 寫入常數檔
    out_path = "app/services/city_forecast_map.py"
    lines = ['# 自動生成，請勿手動修改。執行 scripts/build_city_forecast_map.py 重新產生。\n',
             'CITY_FORECAST_MAP: dict[str, str] = {\n']
    for county, ep in sorted(mapping.items(), key=lambda x: x[1]):
        lines.append(f"    '{county}': '{ep}',\n")
    lines.append('}\n')

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✅ 已寫入 {out_path}")


asyncio.run(main())
